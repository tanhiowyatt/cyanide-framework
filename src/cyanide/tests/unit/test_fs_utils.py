from unittest.mock import patch

from cyanide.core.fs_utils import get_fs_config_dir, list_profiles, resolve_os_profile


def test_get_fs_config_dir():
    with patch("pathlib.Path.exists", return_value=True):
        res = get_fs_config_dir()
        assert "profiles" in str(res)


def test_list_profiles_empty():
    with patch("pathlib.Path.exists", return_value=False):
        assert list_profiles() == ["debian"]


def test_list_profiles_with_data(tmp_path):
    profile_dir = tmp_path / "profiles"
    profile_dir.mkdir()
    debian_dir = profile_dir / "debian"
    debian_dir.mkdir()
    (debian_dir / "base.yaml").write_text("dummy")

    with patch("cyanide.core.fs_utils.get_fs_config_dir", return_value=profile_dir):
        profiles = list_profiles()
        assert "debian" in profiles


def test_resolve_os_profile():
    with patch("cyanide.core.fs_utils.list_profiles", return_value=["debian", "rhel"]):
        assert resolve_os_profile("debian") == "debian"
        assert resolve_os_profile("random") in ["debian", "rhel"]
        assert resolve_os_profile("nonexistent") == "debian"
