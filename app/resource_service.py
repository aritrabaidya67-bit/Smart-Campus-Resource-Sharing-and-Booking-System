import re
from app.config import (
    VALID_CONDITIONS,
    VALID_AVAILABILITY,
    VALID_USER_TYPES,
    RESOURCE_CATEGORIES,
    CAMPUS_LOCATIONS,
)
from app.models import Resource, User


def _text_value(value):
    return value.strip() if isinstance(value, str) else ""


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


def validate_resource_data(name, category, location, quantity, condition, availability):
    errors = []
    name = _text_value(name)
    category = _text_value(category)
    location = _text_value(location)
    if not name:
        errors.append("Resource name is required.")
    elif len(name) > 100:
        errors.append("Resource name must be 100 characters or fewer.")
    if not category:
        errors.append("Category is required.")
    elif category not in RESOURCE_CATEGORIES:
        errors.append(f"Category must be one of: {', '.join(RESOURCE_CATEGORIES)}.")
    if not location:
        errors.append("Location is required.")
    elif location not in CAMPUS_LOCATIONS:
        errors.append(f"Location must be one of: {', '.join(CAMPUS_LOCATIONS)}.")
    qty = _integer_value(quantity)
    if qty is None:
        errors.append("Quantity must be a valid positive integer.")
    elif qty < 1:
        errors.append("Quantity must be a positive integer.")
    if condition not in VALID_CONDITIONS:
        errors.append(f"Condition must be one of: {', '.join(VALID_CONDITIONS)}.")
    if availability not in VALID_AVAILABILITY:
        errors.append(f"Availability must be one of: {', '.join(VALID_AVAILABILITY)}.")
    if condition == "Under Repair" and availability == "Available":
        errors.append("A resource under repair must be marked as Unavailable.")
    return errors


def add_resource(resources, resource_data):
    if not isinstance(resources, list) or not isinstance(resource_data, dict):
        return False, ["Resource data must be a dictionary and resources must be a list."]
    resource_data = dict(resource_data)
    for field in ["resource_id", "name", "category", "location", "condition", "availability"]:
        if isinstance(resource_data.get(field), str):
            resource_data[field] = resource_data[field].strip()

    errors = validate_resource_data(
        resource_data.get("name", ""),
        resource_data.get("category", ""),
        resource_data.get("location", ""),
        resource_data.get("quantity", 0),
        resource_data.get("condition", ""),
        resource_data.get("availability", "")
    )
    if errors:
        return False, errors

    resource_id = resource_data.get("resource_id", "")
    if not isinstance(resource_id, str) or not resource_id.strip():
        return False, ["Resource ID is required."]
    resource_id = resource_id.strip()
    resource_data["resource_id"] = resource_id

    for r in resources:
        if isinstance(r, dict) and r.get("resource_id") == resource_id:
            return False, [f"Resource ID '{resource_id}' already exists."]

    resource_data["quantity"] = _integer_value(resource_data["quantity"])
    booking_count = _integer_value(resource_data.get("booking_count", 0))
    if booking_count is None or booking_count < 0:
        return False, ["Booking count must be a non-negative integer."]
    resource_data["booking_count"] = booking_count
    resource = Resource.from_dict(resource_data)
    resources.append(resource.to_dict())
    return True, ["Resource added successfully."]


def display_resources(resources):
    return [resource for resource in resources if isinstance(resource, dict)] if isinstance(resources, list) else []


def search_resource(resources, name="", category="", location="", availability="", condition=""):
    if not isinstance(resources, list):
        return []
    filters = [name, category, location, availability, condition]
    if any(value is not None and not isinstance(value, str) for value in filters):
        return []
    name = _text_value(name).lower()
    category = _text_value(category).lower()
    location = _text_value(location).lower()
    availability = _text_value(availability).lower()
    condition = _text_value(condition).lower()
    results = []
    for r in resources:
        if not isinstance(r, dict):
            continue
        match = True
        if name and name not in str(r.get("name", "")).lower():
            match = False
        if category and category not in str(r.get("category", "")).lower():
            match = False
        if location and location not in str(r.get("location", "")).lower():
            match = False
        if availability and availability != str(r.get("availability", "")).lower():
            match = False
        if condition and condition != str(r.get("condition", "")).lower():
            match = False
        if match:
            results.append(r)
    return results


def search_resource_recursively(resources, index, resource_id):
    if not isinstance(resources, list) or not isinstance(index, int) or index < 0 or index >= len(resources):
        return None
    resource = resources[index]
    if isinstance(resource, dict) and resource.get("resource_id") == resource_id:
        return resource
    return search_resource_recursively(resources, index + 1, resource_id)


def get_next_resource_id(resources):
    max_num = 0
    for r in resources if isinstance(resources, list) else []:
        if not isinstance(r, dict):
            continue
        rid = r.get("resource_id", "")
        try:
            num = int(str(rid).replace("RES", ""))
            if num > max_num:
                max_num = num
        except (ValueError, AttributeError):
            pass
    return f"RES{max_num + 1:04d}"


def validate_user_data(user_id, name, user_type, department, contact_number, email, semester=""):
    errors = []
    user_id = _text_value(user_id)
    name = _text_value(name)
    department = _text_value(department)
    contact_number = _text_value(contact_number)
    email = _text_value(email)
    semester = _text_value(semester)
    if not user_id:
        errors.append("User ID is required.")
    if not name:
        errors.append("Name is required.")
    if user_type not in VALID_USER_TYPES:
        errors.append("User type must be Student or Teacher.")
    if user_type == "Student" and not semester:
        errors.append("Semester is required for students.")
    elif semester and _integer_value(semester) is None:
        errors.append("Semester must be a positive integer.")
    elif semester and _integer_value(semester) < 1:
        errors.append("Semester must be a positive integer.")
    if not department:
        errors.append("Department is required.")
    if not contact_number:
        errors.append("Contact number is required.")
    elif not re.fullmatch(r"\d{7,15}", contact_number):
        errors.append("Contact number must be 7-15 digits.")
    if not email:
        errors.append("Email is required.")
    elif not re.fullmatch(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", email):
        errors.append("Invalid email format.")
    return errors


def register_user(users, user_data):
    if not isinstance(users, list) or not isinstance(user_data, dict):
        return False, ["User data must be a dictionary and users must be a list."]
    user_data = dict(user_data)
    for field in ["user_id", "name", "user_type", "department", "semester", "contact_number", "email"]:
        if isinstance(user_data.get(field), str):
            user_data[field] = user_data[field].strip()

    errors = validate_user_data(
        user_data.get("user_id", ""),
        user_data.get("name", ""),
        user_data.get("user_type", ""),
        user_data.get("department", ""),
        user_data.get("contact_number", ""),
        user_data.get("email", ""),
        user_data.get("semester", "")
    )
    if errors:
        return False, errors

    for u in users:
        if isinstance(u, dict) and u.get("user_id") == user_data["user_id"]:
            return False, [f"User ID '{user_data['user_id']}' already exists."]

    user = User.from_dict(user_data)
    users.append(user.to_dict())
    return True, ["User registered successfully."]


def delete_resource(resources, bookings, resource_id):
    if not isinstance(resources, list) or not isinstance(bookings, list):
        return False, "Resources and bookings must be lists."
    has_history = any(isinstance(b, dict) and b.get("resource_id") == resource_id for b in bookings)
    if has_history:
        return False, "Cannot delete: resource has associated booking history."
    for i, r in enumerate(resources):
        if isinstance(r, dict) and r.get("resource_id") == resource_id:
            resources.pop(i)
            return True, "Resource deleted successfully."
    return False, f"Resource ID '{resource_id}' not found."


def delete_user(users, bookings, user_id):
    if not isinstance(users, list) or not isinstance(bookings, list):
        return False, "Users and bookings must be lists."
    has_history = any(isinstance(b, dict) and b.get("user_id") == user_id for b in bookings)
    if has_history:
        return False, "Cannot delete: user has associated booking history."
    for i, u in enumerate(users):
        if isinstance(u, dict) and u.get("user_id") == user_id:
            users.pop(i)
            return True, "User deleted successfully."
    return False, f"User ID '{user_id}' not found."


def display_users(users):
    return [user for user in users if isinstance(user, dict)] if isinstance(users, list) else []


def get_next_user_id(users):
    max_num = 0
    for u in users if isinstance(users, list) else []:
        if not isinstance(u, dict):
            continue
        uid = u.get("user_id", "")
        try:
            num = int(str(uid).replace("USR", ""))
            if num > max_num:
                max_num = num
        except (ValueError, AttributeError):
            pass
    return f"USR{max_num + 1:04d}"
