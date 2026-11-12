import json
import shutil
from pathlib import Path
from datetime import datetime


def _get_data_dir():
    return Path(__file__).resolve().parent.parent / "data"


def _get_reports_dir():
    return Path(__file__).resolve().parent.parent / "reports"


def _ensure_dir(path):
    path.parent.mkdir(parents=True, exist_ok=True)


def _safe_read_json(filepath):
    path = Path(filepath)
    if not path.exists():
        return []
    try:
        text = path.read_text(encoding="utf-8")
        if not text.strip():
            raise ValueError("File is empty. Expected a JSON list.")
        data = json.loads(text)
        if not isinstance(data, list) or any(not isinstance(item, dict) for item in data):
            raise ValueError(f"Expected a JSON list of objects in {path.name}.")
        return data
    except (json.JSONDecodeError, ValueError) as error:
        backup_message = ""
        backup_path = path.with_suffix(f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.json")
        try:
            shutil.copy2(path, backup_path)
            backup_message = f" A backup was saved as {backup_path.name}."
        except OSError:
            backup_message = " The original file could not be backed up automatically."
        raise ValueError(
            f"Could not read {path.name}: {error}.{backup_message} "
            f"Please fix {path.name} before using this data again."
        ) from error
    except (OSError, UnicodeError) as error:
        raise ValueError(f"Could not access {path.name}: {error}") from error


def _safe_write_json(filepath, data):
    path = Path(filepath)
    _ensure_dir(path)
    tmp_path = path.with_suffix(".tmp")
    try:
        tmp_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp_path.replace(path)
    except (OSError, TypeError, ValueError):
        tmp_path.unlink(missing_ok=True)
        raise


def save_resources_to_file(resources, filepath=None):
    if filepath is None:
        filepath = _get_data_dir() / "resources.json"
    _safe_write_json(filepath, resources)


def load_resources_from_file(filepath=None):
    if filepath is None:
        filepath = _get_data_dir() / "resources.json"
    return _safe_read_json(filepath)


def save_users_to_file(users, filepath=None):
    if filepath is None:
        filepath = _get_data_dir() / "users.json"
    _safe_write_json(filepath, users)


def load_users_from_file(filepath=None):
    if filepath is None:
        filepath = _get_data_dir() / "users.json"
    return _safe_read_json(filepath)


def save_bookings_to_file(bookings, filepath=None):
    if filepath is None:
        filepath = _get_data_dir() / "bookings.json"
    _safe_write_json(filepath, bookings)


def load_bookings_from_file(filepath=None):
    if filepath is None:
        filepath = _get_data_dir() / "bookings.json"
    return _safe_read_json(filepath)


def save_booking_attempts_to_file(attempts, filepath=None):
    if filepath is None:
        filepath = _get_data_dir() / "booking_attempts.json"
    _safe_write_json(filepath, attempts)


def load_booking_attempts_from_file(filepath=None):
    if filepath is None:
        filepath = _get_data_dir() / "booking_attempts.json"
    return _safe_read_json(filepath)


def save_report_to_file(report_data, filename=None):
    reports_dir = _get_reports_dir()
    reports_dir.mkdir(parents=True, exist_ok=True)
    if filename is None:
        filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    if not isinstance(filename, str) or not filename.strip() or Path(filename).name != filename or filename in {".", ".."}:
        raise ValueError("Report filename must be a non-empty file name without a directory path.")
    filepath = reports_dir / filename
    if isinstance(report_data, dict):
        filepath = filepath.with_suffix(".json")
        _safe_write_json(filepath, report_data)
    else:
        filepath.write_text(str(report_data), encoding="utf-8")
    return str(filepath)
