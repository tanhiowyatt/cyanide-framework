import argparse
from pathlib import PurePosixPath

import aiohttp

from .base import Command


class CurlCommand(Command):
    """
    Real implementation of curl.
    Downloads files from the internet.
    If output is a file, saves to both fake FS and quarantine.
    If output is stdout, prints to terminal but STILL saves to quarantine for analysis.
    """

    async def _fetch_url(
        self, session: aiohttp.ClientSession, current_url: str, parsed: argparse.Namespace
    ) -> tuple[int, dict, bytes, str, int]:
        """Fetch the URL, handle redirect, error status, or content retrieval.
        Returns:
            (status, headers, content, error_msg, rc)
        """
        if not isinstance(current_url, str) or not current_url.startswith(("http://", "https://")):
            return 0, {}, b"", "curl: (3) Malformed URL\n", 3

        is_valid, error, _ = self.validate_url(current_url)
        if not is_valid:
            return 0, {}, b"", f"curl: (1) Redirect to unsafe URL blocked: {error}\n", 1

        if parsed.head:
            async with session.head(
                current_url,
                headers={},
                timeout=aiohttp.ClientTimeout(total=10),
                allow_redirects=False,
            ) as resp:
                if resp.status in (301, 302, 303, 307, 308):
                    return resp.status, dict(resp.headers), b"", "", 0
                return 200, {}, self._handle_head_response(resp).encode("utf-8"), "", 0

        async with session.get(
            current_url,
            headers={},
            timeout=aiohttp.ClientTimeout(total=10),
            allow_redirects=False,
        ) as resp:
            if resp.status in (301, 302, 303, 307, 308):
                return resp.status, dict(resp.headers), b"", "", 0

            if resp.status >= 400:
                err_msg = (
                    ""
                    if parsed.silent
                    else f"curl: (22) The requested URL returned error: {resp.status}\n"
                )
                return resp.status, {}, b"", err_msg, 22

            content = await resp.read()
            return 200, {}, content, "", 0

    async def execute(self, args: list[str], input_data: str = "") -> tuple[str, str, int]:
        """Execute the curl command."""
        parsed, unknown = self._parse_curl_args(args)
        url = self._get_url(parsed, unknown)
        if not url:
            return "", "curl: try 'curl --help' for more information\n", 1

        is_valid, error, resolved_ip = self.validate_url(url)

        # ML: C2/DGA intelligence
        self._log_event(
            "curl_url_resolve",
            {
                "url": url,
                "resolved_ip": resolved_ip or "unresolved",
                "is_valid": is_valid,
            },
        )

        if not is_valid:
            return "", f"curl: (1) {error}\n", 1

        save_to_file, filename = self._get_output_config(url, parsed)
        return await self._handle_redirects_and_save(url, parsed, save_to_file, filename)

    async def _handle_redirects_and_save(
        self, url: str, parsed: argparse.Namespace, save_to_file: bool, filename: str | None
    ) -> tuple[str, str, int]:
        max_redirects = 5
        current_url = url
        try:
            async with aiohttp.ClientSession() as session:
                for _ in range(max_redirects):
                    status, headers, content, err_msg, rc = await self._fetch_url(
                        session, current_url, parsed
                    )
                    if rc != 0 or err_msg:
                        return "", err_msg, rc

                    if status in (301, 302, 303, 307, 308):
                        current_url = headers.get("Location", "")
                        if not current_url:
                            break
                        continue

                    # We successfully fetched the content
                    if parsed.head:
                        return content.decode("utf-8", errors="ignore"), "", 0

                    q_filename = filename if filename else PurePosixPath(url).name or "index.html"
                    if self.emulator.quarantine_callback:
                        self.emulator.quarantine_callback(q_filename, content)

                    if save_to_file:
                        return self._handle_file_save(filename, content, parsed.silent)

                    return content.decode("utf-8", errors="ignore"), "", 0

                return "", "curl: (47) Maximum redirects followed\n", 47

        except aiohttp.ClientError as e:
            return "", f"curl: (6) Could not resolve host: {e}\n", 6
        except Exception as e:
            return "", f"curl: (1) Protocol not supported or error: {e}\n", 1

    def _parse_curl_args(self, args: list[str]) -> tuple[argparse.Namespace, list[str]]:
        """Parse curl arguments."""
        parser = argparse.ArgumentParser(prog="curl", add_help=False)
        parser.add_argument("-o", "--output", dest="output", help="write to file")
        parser.add_argument(
            "-O",
            "--remote-name",
            action="store_true",
            help="write to file named like remote file",
        )
        parser.add_argument("-I", "--head", action="store_true", help="show headers only")
        parser.add_argument("-s", "--silent", action="store_true", help="silent mode")
        parser.add_argument("url", nargs="?", help="URL to fetch")

        try:
            return parser.parse_known_args(args)
        except SystemExit:
            self._log_event(
                "curl_parse_fail",
                {"full_cmd": " ".join(args)},
            )
            raise

    def _get_url(self, parsed: argparse.Namespace, unknown: list[str]) -> str | None:
        """Extract URL from parsed or unknown args."""
        url = parsed.url
        if isinstance(url, str):
            return url
        if unknown:
            return unknown[-1]
        return None

    def _get_output_config(self, url: str, parsed: argparse.Namespace) -> tuple[bool, str | None]:
        """Determine if saving to file and the filename."""
        if parsed.output:
            return True, parsed.output
        if parsed.remote_name:
            filename = PurePosixPath(url).name or "index.html"
            return True, filename
        return False, None

    def _handle_head_response(self, resp: aiohttp.ClientResponse) -> str:
        """Format header output for HEAD requests."""
        version_str = f"{resp.version.major}.{resp.version.minor}" if resp.version else "1.1"
        headers_out = f"HTTP/{version_str} {resp.status} {resp.reason}\r\n"
        for k, v in resp.headers.items():
            headers_out += f"{k}: {v}\r\n"
        headers_out += "\r\n"
        return headers_out

    def _handle_file_save(
        self, filename: str | None, content: bytes, silent: bool
    ) -> tuple[str, str, int]:
        """Save content to fake FS and return result."""
        full_path = self.emulator.resolve_path(filename)
        parent_dir = str(PurePosixPath(full_path).parent)

        if not self.fs.exists(parent_dir):
            return "", f"curl: (23) Failed writing body (0 != {len(content)})\n", 23

        if (
            self.fs.mkfile(
                full_path,
                content=content.decode("utf-8", errors="ignore"),
                owner=self.username,
            )
            is None
        ):
            return "", "curl: (23) Check output path\n", 23

        if not silent:
            stderr = (
                "  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n"
                f"                                 Dload  Upload   Total   Spent    Left  Speed\n"
                f"100  {len(content)}  100  {len(content)}    0     0   {len(content)}      0 --:--:-- --:--:-- --:--:--  {len(content)}\n"
            )
            return "", stderr, 0
        return "", "", 0
