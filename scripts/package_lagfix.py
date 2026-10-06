from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

raise SystemExit("Bản Cockpit cần gói đầy đủ. Chạy python scripts/package_release.py thay vì script bản vá cũ.")

root = Path(__file__).resolve().parents[1]
files = ['config.py','core/types.py','core/runtime.py','ui/live_monitor.py',
         'ui/settings.py','tests/test_live_image.py','HOTFIX_LAG.md']
target = root.parent/'DriverGuard_LagFix.zip'
with ZipFile(target,'w',compression=ZIP_DEFLATED) as archive:
    for name in files:
        archive.write(root/name,'DriverGuard/'+name)
with ZipFile(target) as archive:
    assert archive.testzip() is None
print(f'{target.name}: {target.stat().st_size} bytes; only the listed patch files')
