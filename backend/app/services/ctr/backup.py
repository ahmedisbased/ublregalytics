from datetime import datetime
from pathlib import Path
import shutil


def backup_file(source, backup_dir=None):
    """Copy a CTR source file to a timestamped backup and return its path."""
    source_path = Path(source).resolve()
    if not source_path.is_file():
        raise FileNotFoundError(f"Source file does not exist: {source_path}")

    destination_dir = Path(backup_dir) if backup_dir else source_path.parent / "backups"
    destination_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destination = destination_dir / f"{source_path.stem}.{timestamp}.bak{source_path.suffix}"
    shutil.copy2(source_path, destination)
    return destination


def restore_file(backup, destination):
    """Restore a file previously created by :func:`backup_file`."""
    backup_path = Path(backup).resolve()
    destination_path = Path(destination).resolve()
    if not backup_path.is_file():
        raise FileNotFoundError(f"Backup file does not exist: {backup_path}")

    destination_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(backup_path, destination_path)
    return destination_path
