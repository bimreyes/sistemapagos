import os, shutil, glob, time
def perform_backup(db_path='sistemapagos.db', backups_dir='backups', keep=7):
    os.makedirs(backups_dir, exist_ok=True)
    ts = time.strftime('%Y%m%d_%H%M%S')
    dst = os.path.join(backups_dir, f'sistemapagos_{ts}.db')
    shutil.copy2(db_path, dst)
    # rotate older backups keep last `keep`
    files = sorted(glob.glob(os.path.join(backups_dir, 'sistemapagos_*.db')), reverse=True)
    for f in files[keep:]:
        try:
            os.remove(f)
        except Exception:
            pass
    return dst
