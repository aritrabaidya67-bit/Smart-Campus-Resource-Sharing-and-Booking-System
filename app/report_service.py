from datetime import datetime
import re
from app.config import DATETIME_FORMAT, USAGE_STATUSES, DATE_FORMAT
from app.booking_service import calculate_booking_duration
from app.storage import save_report_to_file
from app.models import ReportGenerator


def _integer_value(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if value.is_integer() else None
    if isinstance(value, str):
        value = value.strip()
        if re.fullmatch(r"[+-]?\d+", value):
            return int(value)
        return None
    try:
        parsed = int(value)
        return parsed if parsed == value else None
    except (ValueError, TypeError, OverflowError):
        return None


def generate_resource_report(resources, bookings, users, date_filter=None, month_filter=None):
    resources = [item for item in resources if isinstance(item, dict)] if isinstance(resources, list) else []
    bookings = [item for item in bookings if isinstance(item, dict)] if isinstance(bookings, list) else []
    users = [item for item in users if isinstance(item, dict)] if isinstance(users, list) else []
    now = datetime.now()
    report = {
        "report_generation_date": now.strftime(DATETIME_FORMAT),
        "total_resources": len(resources),
        "available_resources": 0,
        "booked_resources": 0,
        "reserved_units_in_period": 0,
        "cancelled_bookings": 0,
        "completed_bookings": 0,
        "most_frequently_booked_resource": "N/A",
        "most_active_user": "N/A",
        "most_used_location": "N/A",
        "total_booking_hours": 0.0,
        "category_stats": {},
        "filter_applied": "None"
    }

    for r in resources:
        if not isinstance(r, dict):
            continue
        is_under_repair = str(r.get("condition", "")).strip().lower() == "under repair"
        if r.get("availability") == "Available" and not is_under_repair:
            report["available_resources"] += 1

    filtered_bookings = _filter_bookings(bookings, date_filter, month_filter)
    if date_filter:
        report["filter_applied"] = f"Daily: {date_filter}"
    elif month_filter:
        report["filter_applied"] = f"Monthly: {month_filter}"

    resource_booking_counts = {}
    booked_resource_ids = set()
    user_booking_counts = {}
    location_counts = {}
    total_hours = 0.0
    reserved_units = 0

    for b in filtered_bookings:
        if not isinstance(b, dict):
            continue
        status = b.get("status", "")
        rid = b.get("resource_id", "")
        uid = b.get("user_id", "")
        rid = rid if isinstance(rid, str) else str(rid)
        uid = uid if isinstance(uid, str) else str(uid)
        status = status if isinstance(status, str) else "Unknown"

        if status == "Cancelled":
            report["cancelled_bookings"] += 1
        elif status == "Completed":
            report["completed_bookings"] += 1

        if status in USAGE_STATUSES:
            quantity = _integer_value(b.get("quantity_requested", 1))
            if quantity is not None and quantity > 0:
                reserved_units += quantity
            booked_resource_ids.add(rid)

        if status in USAGE_STATUSES:
            resource_booking_counts[rid] = resource_booking_counts.get(rid, 0) + 1
            user_booking_counts[uid] = user_booking_counts.get(uid, 0) + 1
            duration = calculate_booking_duration(b.get("start_time", ""), b.get("end_time", ""))
            total_hours += duration

            for r in resources:
                if isinstance(r, dict) and r.get("resource_id") == rid:
                    loc = r.get("location", "Unknown")
                    loc = loc if isinstance(loc, str) else str(loc)
                    location_counts[loc] = location_counts.get(loc, 0) + 1
                    break

    report["reserved_units_in_period"] = reserved_units
    report["booked_units_in_period"] = reserved_units
    report["booked_resources"] = len(booked_resource_ids)
    report["total_booking_hours"] = round(total_hours, 2)

    if resource_booking_counts:
        most_booked_rid = max(resource_booking_counts, key=resource_booking_counts.get)
        for r in resources:
            if isinstance(r, dict) and r.get("resource_id") == most_booked_rid:
                report["most_frequently_booked_resource"] = f"{r.get('name', most_booked_rid)} ({resource_booking_counts[most_booked_rid]} bookings)"
                break

    if user_booking_counts:
        most_active_uid = max(user_booking_counts, key=user_booking_counts.get)
        for u in users:
            if isinstance(u, dict) and u.get("user_id") == most_active_uid:
                report["most_active_user"] = f"{u.get('name', most_active_uid)} ({user_booking_counts[most_active_uid]} bookings)"
                break

    if location_counts:
        most_used_loc = max(location_counts, key=location_counts.get)
        report["most_used_location"] = f"{most_used_loc} ({location_counts[most_used_loc]} bookings)"

    report["category_stats"] = ReportGenerator(resources, bookings, users).get_category_stats(filtered_bookings)

    return report


def _filter_bookings(bookings, date_filter=None, month_filter=None):
    if not isinstance(bookings, list):
        return []
    if date_filter is not None and not isinstance(date_filter, str):
        return []
    if month_filter is not None and not isinstance(month_filter, str):
        return []
    if not date_filter and not month_filter:
        return [b for b in bookings if isinstance(b, dict)]
    filtered = []
    for b in bookings:
        if not isinstance(b, dict):
            continue
        bd = b.get("booking_date", "")
        if not isinstance(bd, str):
            continue
        if date_filter and bd == date_filter:
            filtered.append(b)
        elif month_filter and bd.startswith(month_filter + "-"):
            filtered.append(b)
    return filtered


def validate_report_filter(filter_type, filter_value):
    if filter_type == "Daily":
        if not isinstance(filter_value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", filter_value):
            return False, "Please enter a date (YYYY-MM-DD)."
        try:
            datetime.strptime(filter_value, DATE_FORMAT)
        except (ValueError, TypeError):
            return False, "Invalid date format. Use YYYY-MM-DD."
    elif filter_type == "Monthly":
        if not isinstance(filter_value, str) or not re.fullmatch(r"\d{4}-\d{2}", filter_value):
            return False, "Please enter a month (YYYY-MM)."
        try:
            datetime.strptime(filter_value + "-01", DATE_FORMAT)
        except (ValueError, TypeError):
            return False, "Invalid month format. Use YYYY-MM."
    elif filter_type != "All":
        return False, "Filter must be All, Daily, or Monthly."
    return True, ""


def format_report_text(report):
    lines = []
    lines.append("=" * 60)
    lines.append("SMART CAMPUS RESOURCE SHARING - RESOURCE REPORT")
    lines.append("=" * 60)
    lines.append(f"Report Generated: {report.get('report_generation_date', 'N/A')}")
    lines.append(f"Filter Applied: {report.get('filter_applied', 'None')}")
    lines.append("-" * 60)
    lines.append(f"Total Resources: {report.get('total_resources', 0)}")
    lines.append(f"Available Resources: {report.get('available_resources', 0)}")
    lines.append(f"Booked Resources in Period: {report.get('booked_resources', 0)}")
    lines.append(f"Booked Units in Period: {report.get('booked_units_in_period', report.get('reserved_units_in_period', 0))}")
    lines.append(f"Cancelled Bookings: {report.get('cancelled_bookings', 0)}")
    lines.append(f"Completed Bookings: {report.get('completed_bookings', 0)}")
    lines.append(f"Most Frequently Booked: {report.get('most_frequently_booked_resource', 'N/A')}")
    lines.append(f"Most Active User: {report.get('most_active_user', 'N/A')}")
    lines.append(f"Most Used Location: {report.get('most_used_location', 'N/A')}")
    lines.append(f"Total Booking Hours: {report.get('total_booking_hours', 0.0)}")
    lines.append("-" * 60)
    lines.append("CATEGORY-WISE STATISTICS:")
    lines.append("-" * 60)
    for cat, stats in report.get("category_stats", {}).items():
        lines.append(f"  {cat}:")
        lines.append(f"    Total Units: {stats.get('total', 0)}")
        lines.append(f"    Available: {stats.get('available', 0)}")
        lines.append(f"    Booked Units in Period: {stats.get('booked', 0)}")
    lines.append("=" * 60)
    return "\n".join(lines)


def save_generated_report(report, filename=None):
    text = format_report_text(report)
    return save_report_to_file(text, filename)
