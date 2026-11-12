from datetime import datetime
import re
from app.config import (
    MAX_BOOKING_DURATION_HOURS, DATE_FORMAT, TIME_FORMAT,
    DATETIME_FORMAT, ACTIVE_STATUSES, VALID_STATUSES,
    VALID_STATUS_TRANSITIONS, BOOKING_STATUSES
)
from app.resource_service import search_resource_recursively
from app.models import Booking, BookingManager


def check_booking_status(resource_available, conflict, valid_data):
    if not valid_data:
        return "Invalid"
    elif conflict:
        return "Conflict"
    elif resource_available:
        return "Confirmed"
    else:
        return "Pending"


def _integer_value(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if value.is_integer() else None
    if isinstance(value, str):
        value = value.strip()
        if not re.fullmatch(r"[+-]?\d+", value):
            return None
        return int(value)
    try:
        parsed = int(value)
        return parsed if parsed == value else None
    except (ValueError, TypeError, OverflowError):
        return None


def _resource_booking_error(resource):
    if not isinstance(resource, dict):
        return "Resource data is invalid."
    if resource.get("availability") != "Available":
        return "Resource is marked as Unavailable."
    if str(resource.get("condition", "")).strip().lower() == "under repair":
        return "Resource is Under Repair and cannot be booked."
    return ""


def sync_booking_counts(resources, bookings):
    if not isinstance(resources, list) or not isinstance(bookings, list):
        return False
    counts = {}
    for booking in bookings:
        if not isinstance(booking, dict):
            continue
        if booking.get("status") in BOOKING_STATUSES:
            resource_id = booking.get("resource_id")
            if isinstance(resource_id, str):
                counts[resource_id] = counts.get(resource_id, 0) + 1
    changed = False
    for resource in resources:
        if not isinstance(resource, dict):
            continue
        resource_id = resource.get("resource_id")
        expected = counts.get(resource_id, 0) if isinstance(resource_id, str) else 0
        if resource.get("booking_count") != expected:
            resource["booking_count"] = expected
            changed = True
    return changed


def complete_past_bookings(bookings, now=None):
    if not isinstance(bookings, list):
        return False
    now = now or datetime.now()
    changed = False
    for booking in bookings:
        if not isinstance(booking, dict) or booking.get("status") not in ACTIVE_STATUSES:
            continue
        try:
            end_dt = datetime.strptime(
                f"{booking.get('booking_date')} {booking.get('end_time')}",
                f"{DATE_FORMAT} {TIME_FORMAT}"
            )
        except (ValueError, TypeError):
            continue
        if end_dt <= now:
            booking["status"] = "Completed"
            changed = True
    return changed


def validate_booking_time(booking_date, start_time, end_time):
    errors = []
    if not isinstance(booking_date, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", booking_date):
        errors.append("Invalid date format. Use YYYY-MM-DD.")
        return errors
    try:
        b_date = datetime.strptime(booking_date, DATE_FORMAT)
    except (ValueError, TypeError):
        errors.append("Invalid date format. Use YYYY-MM-DD.")
        return errors

    if not isinstance(start_time, str) or not re.fullmatch(r"\d{2}:\d{2}", start_time):
        errors.append("Invalid start time. Use HH:MM format with hours 00-23.")
        return errors
    try:
        s_time = datetime.strptime(start_time, TIME_FORMAT)
    except (ValueError, TypeError):
        errors.append("Invalid start time. Use HH:MM format with hours 00-23.")
        return errors

    if not isinstance(end_time, str) or not re.fullmatch(r"\d{2}:\d{2}", end_time):
        errors.append("Invalid end time. Use HH:MM format with hours 00-23.")
        return errors
    try:
        e_time = datetime.strptime(end_time, TIME_FORMAT)
    except (ValueError, TypeError):
        errors.append("Invalid end time. Use HH:MM format with hours 00-23.")
        return errors

    now = datetime.now()
    booking_start = b_date.replace(hour=s_time.hour, minute=s_time.minute)

    if b_date.date() < now.date():
        errors.append("Booking date cannot be in the past.")
    elif b_date.date() == now.date() and booking_start <= now:
        errors.append("Start time is already in the past for today.")

    if s_time >= e_time:
        errors.append("Start time must be earlier than end time.")

    return errors


def calculate_booking_duration(start_time, end_time):
    if not isinstance(start_time, str) or not re.fullmatch(r"\d{2}:\d{2}", start_time):
        return 0.0
    if not isinstance(end_time, str) or not re.fullmatch(r"\d{2}:\d{2}", end_time):
        return 0.0
    try:
        s = datetime.strptime(start_time, TIME_FORMAT)
        e = datetime.strptime(end_time, TIME_FORMAT)
        duration = (e - s).total_seconds() / 3600.0
        return max(0, duration)
    except (ValueError, TypeError):
        return 0.0


def _bookings_overlap(start1, end1, start2, end2):
    values = [start1, end1, start2, end2]
    if any(not isinstance(value, str) or not re.fullmatch(r"\d{2}:\d{2}", value) for value in values):
        return False
    try:
        s1 = datetime.strptime(start1, TIME_FORMAT)
        e1 = datetime.strptime(end1, TIME_FORMAT)
        s2 = datetime.strptime(start2, TIME_FORMAT)
        e2 = datetime.strptime(end2, TIME_FORMAT)
        return s1 < e2 and e1 > s2
    except (ValueError, TypeError):
        return False


def _get_peak_usage(bookings, resource_id, booking_date, start_time, end_time, exclude_booking_id=None):
    overlapping = []
    for b in bookings:
        if not isinstance(b, dict):
            continue
        bid = b.get("booking_id", "")
        if exclude_booking_id and bid == exclude_booking_id:
            continue
        if b.get("status") not in ACTIVE_STATUSES:
            continue
        if b.get("resource_id") != resource_id:
            continue
        if b.get("booking_date") != booking_date:
            continue
        b_start = b.get("start_time", "")
        b_end = b.get("end_time", "")
        if _bookings_overlap(start_time, end_time, b_start, b_end):
            quantity = _integer_value(b.get("quantity_requested", 1))
            if quantity is None or quantity < 1:
                continue
            overlapping.append((
                datetime.strptime(b_start, TIME_FORMAT),
                datetime.strptime(b_end, TIME_FORMAT),
                quantity
            ))

    if not overlapping:
        return 0

    try:
        req_start = datetime.strptime(start_time, TIME_FORMAT)
        req_end = datetime.strptime(end_time, TIME_FORMAT)
    except (ValueError, TypeError):
        return 0

    time_points = set()
    time_points.add(req_start)
    for b_start, b_end, qty in overlapping:
        if req_start < b_start < req_end:
            time_points.add(b_start)
        if req_start < b_end < req_end:
            time_points.add(b_end)

    peak = 0
    for tp in sorted(time_points):
        usage = sum(qty for b_start, b_end, qty in overlapping if b_start <= tp < b_end)
        peak = max(peak, usage)

    return peak


def check_booking_conflict(bookings, resource_id, booking_date, start_time, end_time, quantity_requested, resource_quantity, exclude_booking_id=None):
    if not isinstance(bookings, list):
        return True, "Booking data is invalid."
    quantity_requested = _integer_value(quantity_requested)
    resource_quantity = _integer_value(resource_quantity)
    if quantity_requested is None or resource_quantity is None:
        return True, "Resource quantity is invalid."
    if quantity_requested < 1 or resource_quantity < 1:
        return True, "Resource quantity must be positive."
    if not isinstance(resource_id, str) or not isinstance(booking_date, str):
        return True, "Resource ID and booking date must be text."
    if validate_booking_time(booking_date, start_time, end_time):
        return True, "Booking date or time is invalid."
    peak = _get_peak_usage(bookings, resource_id, booking_date, start_time, end_time, exclude_booking_id)
    remaining = resource_quantity - peak
    if quantity_requested > remaining:
        return True, f"Resource capacity conflict. Available: {remaining}, Requested: {quantity_requested}."
    return False, ""


def _check_user_overlap(bookings, user_id, booking_date, start_time, end_time, exclude_booking_id=None):
    for b in bookings:
        if not isinstance(b, dict):
            continue
        bid = b.get("booking_id", "")
        if exclude_booking_id and bid == exclude_booking_id:
            continue
        if b.get("status") not in ACTIVE_STATUSES:
            continue
        if b.get("user_id") != user_id:
            continue
        if b.get("booking_date") != booking_date:
            continue
        if _bookings_overlap(start_time, end_time, b.get("start_time", ""), b.get("end_time", "")):
            return True, f"User already has an overlapping booking (ID: {bid}) at this time."
    return False, ""


def book_resource(resources, users, bookings, booking_attempts, booking_data):
    if not isinstance(booking_data, dict):
        return False, "Invalid", "Booking data must be a dictionary."
    if not all(isinstance(records, list) for records in (resources, users, bookings, booking_attempts)):
        return False, "Invalid", "Resources, users, bookings, and attempts must be lists."

    raw_user_id = booking_data.get("user_id", "")
    raw_resource_id = booking_data.get("resource_id", "")
    raw_booking_date = booking_data.get("booking_date", "")
    raw_start_time = booking_data.get("start_time", "")
    raw_end_time = booking_data.get("end_time", "")
    raw_purpose = booking_data.get("purpose", "")
    raw_booking_id = booking_data.get("booking_id", "")
    user_id = raw_user_id.strip() if isinstance(raw_user_id, str) else ""
    resource_id = raw_resource_id.strip() if isinstance(raw_resource_id, str) else ""
    booking_date = raw_booking_date.strip() if isinstance(raw_booking_date, str) else ""
    start_time = raw_start_time.strip() if isinstance(raw_start_time, str) else ""
    end_time = raw_end_time.strip() if isinstance(raw_end_time, str) else ""
    purpose = raw_purpose.strip() if isinstance(raw_purpose, str) else ""
    booking_id = raw_booking_id.strip() if isinstance(raw_booking_id, str) else ""
    quantity_requested = _integer_value(booking_data.get("quantity_requested", 1))
    if quantity_requested is None:
        quantity_requested = 0

    manager = BookingManager(bookings, booking_attempts, resources, users)
    manager.migrate_booking_attempt_ids()
    if not booking_id:
        booking_id = manager.get_next_booking_id()
    attempt_record = {
        "booking_id": manager.get_next_attempt_id(),
        "user_id": user_id,
        "resource_id": resource_id,
        "booking_date": booking_date,
        "start_time": start_time,
        "end_time": end_time,
        "purpose": purpose,
        "quantity_requested": quantity_requested,
        "status": "Invalid",
        "created_at": datetime.now().strftime(DATETIME_FORMAT)
    }

    if manager.find_booking(booking_id):
        booking_attempts.append(attempt_record)
        return False, "Invalid", f"Booking ID '{booking_id}' already exists."

    if raw_booking_id not in (None, "") and not isinstance(raw_booking_id, str):
        attempt_record["status"] = "Invalid"
        booking_attempts.append(attempt_record)
        return False, "Invalid", "Booking ID must be text."

    if not user_id or not resource_id:
        attempt_record["status"] = "Invalid"
        booking_attempts.append(attempt_record)
        return False, "Invalid", "User ID and resource ID are required."

    if raw_purpose is not None and not isinstance(raw_purpose, str):
        attempt_record["status"] = "Invalid"
        booking_attempts.append(attempt_record)
        return False, "Invalid", "Booking purpose must be text."

    user_found = False
    for u in users:
        if isinstance(u, dict) and u.get("user_id") == user_id:
            user_found = True
            break
    if not user_found:
        attempt_record["status"] = check_booking_status(False, False, False)
        booking_attempts.append(attempt_record)
        return False, "Invalid", f"User ID '{user_id}' does not exist."

    resource = search_resource_recursively(resources, 0, resource_id)
    if resource is None:
        attempt_record["status"] = check_booking_status(False, False, False)
        booking_attempts.append(attempt_record)
        return False, "Invalid", f"Resource ID '{resource_id}' does not exist."

    resource_error = _resource_booking_error(resource)
    if resource_error:
        attempt_record["status"] = check_booking_status(False, False, False)
        booking_attempts.append(attempt_record)
        return False, "Invalid", resource_error

    resource_quantity = _integer_value(resource.get("quantity", 1))
    if resource_quantity is None or resource_quantity < 1:
        attempt_record["status"] = "Invalid"
        booking_attempts.append(attempt_record)
        return False, "Invalid", "Resource quantity is invalid."

    time_errors = validate_booking_time(booking_date, start_time, end_time)
    if time_errors:
        attempt_record["status"] = check_booking_status(False, False, False)
        booking_attempts.append(attempt_record)
        return False, "Invalid", " ".join(time_errors)

    if quantity_requested < 1:
        attempt_record["status"] = check_booking_status(False, False, False)
        booking_attempts.append(attempt_record)
        return False, "Invalid", "Quantity must be a positive integer."

    if quantity_requested > resource_quantity:
        attempt_record["status"] = check_booking_status(False, False, False)
        booking_attempts.append(attempt_record)
        return False, "Invalid", f"Requested quantity ({quantity_requested}) exceeds total resource quantity ({resource_quantity})."

    if not purpose:
        attempt_record["status"] = check_booking_status(False, False, False)
        booking_attempts.append(attempt_record)
        return False, "Invalid", "Booking purpose is required."

    duration = calculate_booking_duration(start_time, end_time)
    if duration > MAX_BOOKING_DURATION_HOURS:
        attempt_record["status"] = check_booking_status(False, False, False)
        booking_attempts.append(attempt_record)
        return False, "Invalid", f"Booking duration ({duration:.1f}h) exceeds maximum allowed ({MAX_BOOKING_DURATION_HOURS}h)."

    has_conflict, conflict_msg = check_booking_conflict(
        bookings, resource_id, booking_date, start_time, end_time,
        quantity_requested, resource_quantity
    )
    if has_conflict:
        attempt_record["status"] = check_booking_status(True, True, True)
        booking_attempts.append(attempt_record)
        return False, "Conflict", conflict_msg

    user_overlap, user_msg = _check_user_overlap(bookings, user_id, booking_date, start_time, end_time)
    if user_overlap:
        attempt_record["status"] = check_booking_status(True, True, True)
        booking_attempts.append(attempt_record)
        return False, "Conflict", user_msg

    status = check_booking_status(
        resource_available=True,
        conflict=False,
        valid_data=True
    )

    booking_record = {
        "booking_id": booking_id,
        "user_id": user_id,
        "resource_id": resource_id,
        "booking_date": booking_date,
        "start_time": start_time,
        "end_time": end_time,
        "purpose": purpose,
        "quantity_requested": quantity_requested,
        "status": status,
        "created_at": datetime.now().strftime(DATETIME_FORMAT)
    }
    bookings.append(Booking.from_dict(booking_record).to_dict())

    sync_booking_counts(resources, bookings)

    return True, status, "Booking confirmed successfully."


def cancel_booking(bookings, booking_id, resources=None):
    if not isinstance(bookings, list) or (resources is not None and not isinstance(resources, list)):
        return False, "Bookings and resources must be lists."
    booking = BookingManager(bookings).find_booking(booking_id)
    if booking is None:
        return False, f"Booking ID '{booking_id}' not found."
    current_status = booking.get("status", "")
    if current_status == "Cancelled":
        return False, "Booking is already cancelled."
    if current_status == "Completed":
        return False, "Cannot cancel a completed booking."
    if current_status not in ACTIVE_STATUSES:
        return False, f"Cannot cancel booking with status '{current_status}'."
    booking["status"] = "Cancelled"
    if resources is not None:
        sync_booking_counts(resources, bookings)
    return True, "Booking cancelled successfully."


def update_booking_status(bookings, resources, users, booking_id, new_status):
    if not isinstance(bookings, list) or not isinstance(resources, list) or not isinstance(users, list):
        return False, "Bookings, resources, and users must be lists."
    if not isinstance(new_status, str) or new_status not in VALID_STATUSES:
        return False, f"Invalid status. Must be one of: {', '.join(VALID_STATUSES)}."

    booking = BookingManager(bookings).find_booking(booking_id)
    if booking is None:
        return False, f"Booking ID '{booking_id}' not found."

    current_status = booking.get("status", "")

    if current_status == new_status:
        return False, f"Booking is already '{new_status}'."

    allowed = VALID_STATUS_TRANSITIONS.get(current_status, [])
    if new_status not in allowed:
        return False, f"Cannot change from '{current_status}' to '{new_status}'."

    if new_status == "Completed":
        try:
            end_dt = datetime.strptime(
                f"{booking.get('booking_date')} {booking.get('end_time')}",
                f"{DATE_FORMAT} {TIME_FORMAT}"
            )
            if datetime.now() < end_dt:
                return False, "Cannot mark as Completed before the booking's scheduled end time."
        except (ValueError, TypeError):
            return False, "Booking date or end time is invalid."

    if current_status == "Cancelled" and new_status in ACTIVE_STATUSES:
        user_exists = any(
            isinstance(user, dict) and user.get("user_id") == booking.get("user_id")
            for user in users
        )
        if not user_exists:
            return False, "User no longer exists."
        resource = search_resource_recursively(resources, 0, booking.get("resource_id", ""))
        if resource is None:
            return False, "Resource no longer exists."
        resource_error = _resource_booking_error(resource)
        if resource_error:
            return False, resource_error

        quantity_requested = _integer_value(booking.get("quantity_requested", 1))
        resource_quantity = _integer_value(resource.get("quantity", 1))
        if quantity_requested is None or resource_quantity is None:
            return False, "Booking quantity is invalid."
        if quantity_requested < 1 or quantity_requested > resource_quantity:
            return False, "Booking quantity is no longer valid for this resource."

        time_errors = validate_booking_time(
            booking.get("booking_date", ""),
            booking.get("start_time", ""),
            booking.get("end_time", "")
        )
        if time_errors:
            return False, f"Cannot reactivate: {' '.join(time_errors)}"

        duration = calculate_booking_duration(
            booking.get("start_time", ""), booking.get("end_time", "")
        )
        if duration > MAX_BOOKING_DURATION_HOURS:
            return False, (
                f"Cannot reactivate: booking duration ({duration:.1f}h) exceeds "
                f"maximum allowed ({MAX_BOOKING_DURATION_HOURS}h)."
            )

        has_conflict, conflict_msg = check_booking_conflict(
            bookings, booking.get("resource_id", ""),
            booking.get("booking_date", ""), booking.get("start_time", ""),
            booking.get("end_time", ""), quantity_requested,
            resource.get("quantity", 1), exclude_booking_id=booking_id
        )
        if has_conflict:
            return False, f"Cannot reactivate: {conflict_msg}"

        user_overlap, user_msg = _check_user_overlap(
            bookings, booking.get("user_id", ""),
            booking.get("booking_date", ""), booking.get("start_time", ""),
            booking.get("end_time", ""), exclude_booking_id=booking_id
        )
        if user_overlap:
            return False, f"Cannot reactivate: {user_msg}"

    booking["status"] = new_status
    sync_booking_counts(resources, bookings)
    return True, f"Booking status updated to '{new_status}'."


def delete_booking(bookings, booking_id, resources=None):
    if not isinstance(bookings, list) or (resources is not None and not isinstance(resources, list)):
        return False, "Bookings and resources must be lists."
    for i, booking in enumerate(bookings):
        if not isinstance(booking, dict) or booking.get("booking_id") != booking_id:
            continue
        if booking.get("status") in ACTIVE_STATUSES:
            return False, "Cannot delete an active booking. Cancel it first."
        bookings.pop(i)
        if resources is not None:
            sync_booking_counts(resources, bookings)
        return True, "Booking deleted successfully."
    return False, f"Booking ID '{booking_id}' not found."


def display_user_bookings(bookings, user_id):
    if not isinstance(bookings, list):
        return []
    result = []
    for b in bookings:
        if isinstance(b, dict) and b.get("user_id") == user_id:
            result.append(b)
    result.sort(key=lambda x: (x.get("booking_date", ""), x.get("start_time", "")))
    return result


def check_availability(resources, bookings, resource_id, booking_date, start_time, end_time, quantity_requested):
    if not isinstance(resources, list) or not isinstance(bookings, list):
        return False, "Resources and bookings must be lists."
    resource = search_resource_recursively(resources, 0, resource_id)
    if resource is None:
        return False, "Resource not found."
    resource_error = _resource_booking_error(resource)
    if resource_error:
        return False, resource_error

    quantity_requested = _integer_value(quantity_requested)
    if quantity_requested is None:
        return False, "Quantity must be a valid positive integer."

    if quantity_requested < 1:
        return False, "Quantity must be a positive integer."

    total_qty = _integer_value(resource.get("quantity", 1))
    if total_qty is None or total_qty < 1:
        return False, "Resource quantity is invalid."
    if quantity_requested > total_qty:
        return False, f"Requested quantity ({quantity_requested}) exceeds total ({total_qty})."

    time_errors = validate_booking_time(booking_date, start_time, end_time)
    if time_errors:
        return False, " ".join(time_errors)

    duration = calculate_booking_duration(start_time, end_time)
    if duration > MAX_BOOKING_DURATION_HOURS:
        return False, f"Duration ({duration:.1f}h) exceeds maximum ({MAX_BOOKING_DURATION_HOURS}h)."

    has_conflict, msg = check_booking_conflict(
        bookings, resource_id, booking_date, start_time, end_time,
        quantity_requested, total_qty
    )
    if has_conflict:
        return False, msg

    peak = _get_peak_usage(bookings, resource_id, booking_date, start_time, end_time)
    remaining = total_qty - peak
    return True, f"Available. {total_qty} total, {remaining} available for the requested time."
