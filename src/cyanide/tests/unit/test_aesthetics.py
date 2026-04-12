from unittest.mock import patch

from cyanide.core.aesthetics import (
    _get_logo_raw,
    _get_service_status,
    print_startup_banner,
)


def test_get_logo_raw(tmp_path):
    with patch("cyanide.core.aesthetics.Path") as mock_path:
        logo_file = tmp_path / "logo.txt"
        # Mock Path(__file__).resolve().parent.parent / "assets/branding/logo.txt"
        mock_path.return_value.resolve.return_value.parent.parent.__truediv__.return_value = (
            logo_file
        )

        assert _get_logo_raw() == []
        logo_file.write_text("LOGO\nTEXT")
        assert _get_logo_raw() == ["LOGO", "TEXT"]


def test_get_service_status():
    config = {"ssh": {"port": 2222, "enabled": True}, "telnet": {"enabled": False}}
    assert _get_service_status(config, "ssh", 22) == "2222 (enabled)"
    assert _get_service_status(config, "telnet", 23) == "23 (disabled)"


def test_print_startup_banner(capsys):
    config = {"hostname": "test", "os_profile": "alpine"}
    with patch("cyanide.core.aesthetics._get_logo_raw", return_value=["LOGO"]):
        print_startup_banner(config, "alpine")

    out, err = capsys.readouterr()
    assert "LOGO" in out
    assert "alpine" in out


def test_print_startup_banner_no_logo(capsys):
    config = {"hostname": "test"}
    with patch("cyanide.core.aesthetics._get_logo_raw", return_value=[]):
        print_startup_banner(config)
    out, err = capsys.readouterr()
    assert out == ""
