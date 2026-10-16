import sqlite3
import tarfile
from pathlib import Path
import pytest
from scripts.export_database import export_database
from scripts.build_kali_package import build_package, TOP


def test_export_database_consistent_wal_and_no_overwrite(tmp_path):
    source = tmp_path / "source.sqlite"
    live = sqlite3.connect(source)
    try:
        live.execute("PRAGMA journal_mode=WAL")
        live.execute("CREATE TABLE prices(value INTEGER)")
        live.execute("INSERT INTO prices VALUES (12345)")
        live.commit()
        target = tmp_path / "backup.sqlite"
        export_database(source, target)
        backup = sqlite3.connect(target)
        try:
            assert backup.execute("SELECT value FROM prices").fetchone()[0] == 12345
            assert backup.execute("PRAGMA quick_check").fetchone()[0] == "ok"
        finally:
            backup.close()
        with pytest.raises(FileExistsError):
            export_database(source, target)
        with pytest.raises(ValueError):
            export_database(source, source)
    finally:
        live.close()


def test_export_missing_source_does_not_create_empty_database(tmp_path):
    target = tmp_path / "backup.sqlite"
    with pytest.raises(ValueError):
        export_database(tmp_path / "missing.sqlite", target)
    assert not target.exists()


def test_kali_package_excludes_secrets_and_has_unix_installer(tmp_path):
    target = build_package(tmp_path / "package.tar.gz")
    with tarfile.open(target) as archive:
        names = archive.getnames()
        assert TOP + "/monitor/__main__.py" in names
        assert TOP + "/LEIA-ME-KALI.md" in names
        assert TOP + "/requirements-server.txt" in names
        assert TOP + "/PROMOCOES.md" in names
        assert TOP + "/monitor/deals/service.py" in names
        assert TOP + "/monitor/deals/category_seed.json" in names
        assert TOP + "/monitor/menu.py" in names
        assert TOP + "/MENU-TELEGRAM.md" in names
        assert TOP + "/.env" not in names
        assert all(
            "/data/" not in n and "/.venv/" not in n and "__pycache__" not in n
            for n in names
        )
        assert all(not n.startswith("/") and ".." not in Path(n).parts for n in names)
        info = archive.getmember(TOP + "/deploy/install-kali.sh")
        assert info.mode == 0o755
        script = archive.extractfile(info).read()
        assert script.startswith(b"#!/usr/bin/env bash\n") and b"\r" not in script
        assert not any(m.issym() or m.islnk() for m in archive.getmembers())
    assert target.with_suffix(".gz.sha256").exists()
