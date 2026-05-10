from cyanide.vfs.profile_loader import invalidate, load


def test_sqlite_corruption_fallback(tmp_path):
    profile_dir = tmp_path / "profiles"
    debian_dir = profile_dir / "debian"
    debian_dir.mkdir(parents=True)

    (debian_dir / "static.yaml").write_text("static: {'/test.txt': {'content': 'OK'}}")
    (debian_dir / "base.yaml").write_text("metadata: {os_id: debian}")

    load("debian", profile_dir)
    db_file = debian_dir / ".compiled.db"
    assert db_file.exists()

    db_file.write_text("NOT_A_SQLITE_FILE")
    invalidate()

    # Patch the logger to suppress the intentional warning in test output
    from unittest.mock import patch

    with patch("cyanide.vfs.profile_loader.logger") as mock_logger:
        data = load("debian", profile_dir)
        mock_logger.warning.assert_called()

    assert data["backend_path"] == str(db_file)
    assert db_file.stat().st_size > 100
