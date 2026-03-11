import socket
import sys
import time
import os
import asyncio


# Function 328: Performs operations related to check port.
def check_port(host, port, timeout=5):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError):
        return False


# Function 329: Performs operations related to check ssh functional.
async def check_ssh_functional(host, port):
    """Try to login and execute a simple command."""
    try:
        import asyncssh

        async with asyncssh.connect(
            host, port=port, username="root", password="admin", known_hosts=None
        ) as conn:
            result = await conn.run("whoami", check=True)
            stdout = result.stdout
            if isinstance(stdout, bytes):
                out_str = stdout.decode("utf-8", errors="replace")
            else:
                out_str = str(stdout or "")

            if "root" in out_str:
                return True, "Login and command execution OK"
            return False, f"Unexpected output: {out_str}"
    except Exception as e:
        return False, str(e)


# Function 330: Runs unit tests for the smoke_test functionality.
def smoke_test():
    host = "127.0.0.1"
    ssh_port = int(os.getenv("CYANIDE_SSH_PORT", 2222))
    telnet_port = int(os.getenv("CYANIDE_TELNET_PORT", 2223))
    metrics_port = int(os.getenv("CYANIDE_METRICS_PORT", 9090))
    ports = {"SSH": ssh_port, "Telnet": telnet_port, "Metrics": metrics_port}

    print("[*] Starting Smoke Test...")
    all_passed = True

    # Wait for service startup
    for i in range(10):
        if check_port(host, metrics_port):
            break
        print(f"Waiting for metrics service on {metrics_port}... {i+1}/10")
        time.sleep(2)

    for name, port in ports.items():
        if check_port(host, port):
            print(f"[+] {name} (Port {port}): UP")
        else:
            print(f"[-] {name} (Port {port}): DOWN")
            all_passed = False

    # Functional SSH Test
    try:
        ok, msg = asyncio.run(check_ssh_functional(host, ssh_port))
        if ok:
            print(f"[+] SSH Functional: {msg}")
        else:
            print(f"[-] SSH Functional FAILED: {msg}")
            all_passed = False
    except Exception as e:
        print(f"[-] SSH Functional Error: {e}")
        all_passed = False

    # Check /health endpoint with retries
    print("[*] Checking Health Endpoint...")
    max_retries = 3
    health_ok = False
    for attempt in range(max_retries):
        try:
            data = None
            try:
                import requests  # type: ignore

                response = requests.get(f"http://{host}:{metrics_port}/health", timeout=5)
                if response.status_code == 200:
                    data = response.json()
            except ImportError:
                import json
                import urllib.request

                with urllib.request.urlopen(
                    f"http://{host}:{metrics_port}/health", timeout=5
                ) as response:
                    if response.status == 200:
                        data = json.loads(response.read().decode())

            if data:
                if data.get("status") == "healthy":
                    print("[+] Health Endpoint: OK")
                    health_ok = True
                    break
                else:
                    print(
                        f"[-] Health Endpoint (Attempt {attempt+1}/{max_retries}): UNHEALTHY ({data})"
                    )
            else:
                print(f"[-] Health Endpoint (Attempt {attempt+1}/{max_retries}): FAILED (No data)")

        except Exception as e:
            print(f"[-] Health Endpoint Error (Attempt {attempt+1}/{max_retries}): {e}")

        if attempt < max_retries - 1:
            time.sleep(2)

    if not health_ok:
        all_passed = False

    if all_passed:
        print("[*] Smoke Test PASSED")
        sys.exit(0)
    else:
        print("[!] Smoke Test FAILED")
        sys.exit(1)


if __name__ == "__main__":
    smoke_test()
