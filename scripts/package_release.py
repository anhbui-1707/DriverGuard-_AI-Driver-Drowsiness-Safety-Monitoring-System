"""Source-only ZIP; never bundle user SQLite, snapshots, API key or virtualenv."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED


def main():
    root = Path(__file__).resolve().parents[1]
    output = root.parent / "DriverGuard_Complete.zip"
    skipped_dirs = {".venv", ".git", "__pycache__", ".pytest_cache", "data"}
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        # Launcher outside the inner project prevents the wrong-folder error.
        archive.writestr("START_DRIVERGUARD.bat", '@echo off\r\ncall "%~dp0DriverGuard\\run.bat"\r\nif errorlevel 1 pause\r\n')
        for path in sorted(root.rglob("*")):
            relative = path.relative_to(root)
            if not path.is_file() or skipped_dirs.intersection(relative.parts):
                continue
            if path.name == '.env' or path.suffix in ('.pyc', '.db', '.download'):
                continue
            if relative.parts[:2] == ('assets', 'screenshots'):
                continue
            archive.write(path, Path('DriverGuard') / relative)
    with ZipFile(output) as archive:
        assert archive.testzip() is None
        assert 'DriverGuard/models/face_landmarker.task' in archive.namelist()
        assert 'DriverGuard/assets/sounds/alarm.wav' in archive.namelist()
        assert 'DriverGuard/.streamlit/config.toml' in archive.namelist()
        assert 'DriverGuard/ui/assets/live.html' in archive.namelist()
        assert 'DriverGuard/ui/assets/live.js' in archive.namelist()
        assert 'DriverGuard/ui/assets/live.css' in archive.namelist()
    print(f"Packaged {output.name}: {output.stat().st_size:,} bytes")


if __name__ == '__main__':
    main()
