from datetime import datetime
from app.config import DATETIME_FORMAT


def _integer_value(value, default=0):
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if value.is_integer() else default
    if isinstance(value, str):
        value = value.strip()
        if value.lstrip("+-").isdigit():
            return int(value)
        return default
    try:
        parsed = int(value)
        return parsed if parsed == value else default
    except (ValueError, TypeError, OverflowError):
        return default


class User:
    def __init__(self, user_id, name, user_type, department, semester, contact_number, email):
        self.user_id = user_id
        self.name = name
        self.user_type = user_type
        self.department = department
        self.semester = semester
        self.contact_number = contact_number
        self.email = email

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "name": self.name,
            "user_type": self.user_type,
            "department": self.department,
            "semester": self.semester,
            "contact_number": self.contact_number,
            "email": self.email
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            user_id=data.get("user_id", ""),
            name=data.get("name", ""),
            user_type=data.get("user_type", ""),
            department=data.get("department", ""),
            semester=data.get("semester", ""),
            contact_number=data.get("contact_number", ""),
            email=data.get("email", "")
        )


class Resource:
    def __init__(self, resource_id, name, category, location, quantity, condition, availability, booking_count=0):
        self.resource_id = resource_id
        self.name = name
        self.category = category
        self.location = location
        self.quantity = _integer_value(quantity)
        self.condition = condition
        self.availability = availability
        self.booking_count = _integer_value(booking_count)

    def to_dict(self):
        return {
            "resource_id": self.resource_id,
            "name": self.name,
            "category": self.category,
            "location": self.location,
            "quantity": self.quantity,
            "condition": self.condition,
            "availability": self.availability,
            "booking_count": self.booking_count
        }

    @classmethod
    def from_dict(cls, data):
        category = data.get("category", "")
        from app.config import EQUIPMENT_CATEGORIES, ROOM_CATEGORIES, SPORTS_CATEGORIES
        if category in ROOM_CATEGORIES:
            return Room.from_dict(data)
        elif category in SPORTS_CATEGORIES:
            return SportsResource.from_dict(data)
        elif category in EQUIPMENT_CATEGORIES:
            return Equipment.from_dict(data)
        return cls(
            resource_id=data.get("resource_id", ""),
            name=data.get("name", ""),
            category=category,
            location=data.get("location", ""),
            quantity=data.get("quantity", 1),
            condition=data.get("condition", "Good"),
            availability=data.get("availability", "Available"),
            booking_count=data.get("booking_count", 0)
        )


class Equipment(Resource):
    def __init__(self, resource_id, name, category, location, quantity, condition, availability, booking_count=0, brand="", model_number=""):
        super().__init__(resource_id, name, category, location, quantity, condition, availability, booking_count)
        self.brand = brand
        self.model_number = model_number

    def to_dict(self):
        data = super().to_dict()
        data["brand"] = self.brand
        data["model_number"] = self.model_number
        return data

    @classmethod
    def from_dict(cls, data):
        return cls(
            resource_id=data.get("resource_id", ""),
            name=data.get("name", ""),
            category=data.get("category", ""),
            location=data.get("location", ""),
            quantity=data.get("quantity", 1),
            condition=data.get("condition", "Good"),
            availability=data.get("availability", "Available"),
            booking_count=data.get("booking_count", 0),
            brand=data.get("brand", ""),
            model_number=data.get("model_number", "")
        )


class Room(Resource):
    def __init__(self, resource_id, name, category, location, quantity, condition, availability, booking_count=0, capacity=0, has_projector=False):
        super().__init__(resource_id, name, category, location, quantity, condition, availability, booking_count)
        self.capacity = capacity
        self.has_projector = has_projector

    def to_dict(self):
        data = super().to_dict()
        data["capacity"] = self.capacity
        data["has_projector"] = self.has_projector
        return data

    @classmethod
    def from_dict(cls, data):
        return cls(
            resource_id=data.get("resource_id", ""),
            name=data.get("name", ""),
            category=data.get("category", ""),
            location=data.get("location", ""),
            quantity=data.get("quantity", 1),
            condition=data.get("condition", "Good"),
            availability=data.get("availability", "Available"),
            booking_count=data.get("booking_count", 0),
            capacity=data.get("capacity", 0),
            has_projector=data.get("has_projector", False)
        )


class SportsResource(Resource):
    def __init__(self, resource_id, name, category, location, quantity, condition, availability, booking_count=0, sport_type=""):
        super().__init__(resource_id, name, category, location, quantity, condition, availability, booking_count)
        self.sport_type = sport_type

    def to_dict(self):
        data = super().to_dict()
        data["sport_type"] = self.sport_type
        return data

    @classmethod
    def from_dict(cls, data):
        return cls(
            resource_id=data.get("resource_id", ""),
            name=data.get("name", ""),
            category=data.get("category", ""),
            location=data.get("location", ""),
            quantity=data.get("quantity", 1),
            condition=data.get("condition", "Good"),
            availability=data.get("availability", "Available"),
            booking_count=data.get("booking_count", 0),
            sport_type=data.get("sport_type", "")
        )


class Booking:
    def __init__(self, booking_id, user_id, resource_id, booking_date, start_time, end_time, purpose, quantity_requested, status, created_at=None):
        self.booking_id = booking_id
        self.user_id = user_id
        self.resource_id = resource_id
        self.booking_date = booking_date
        self.start_time = start_time
        self.end_time = end_time
        self.purpose = purpose
        self.quantity_requested = _integer_value(quantity_requested)
        self.status = status
        self.created_at = created_at or datetime.now().strftime(DATETIME_FORMAT)

    def time_range(self):
        return (self.start_time, self.end_time)

    def to_dict(self):
        return {
            "booking_id": self.booking_id,
            "user_id": self.user_id,
            "resource_id": self.resource_id,
            "booking_date": self.booking_date,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "purpose": self.purpose,
            "quantity_requested": self.quantity_requested,
            "status": self.status,
            "created_at": self.created_at
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            booking_id=data.get("booking_id", ""),
            user_id=data.get("user_id", ""),
            resource_id=data.get("resource_id", ""),
            booking_date=data.get("booking_date", ""),
            start_time=data.get("start_time", ""),
            end_time=data.get("end_time", ""),
            purpose=data.get("purpose", ""),
            quantity_requested=data.get("quantity_requested", 1),
            status=data.get("status", ""),
            created_at=data.get("created_at")
        )


class BookingManager:
    def __init__(self, bookings=None, booking_attempts=None, resources=None, users=None):
        self.bookings = bookings if bookings is not None else []
        self.booking_attempts = booking_attempts if booking_attempts is not None else []
        self.resources = resources if resources is not None else []
        self.users = users if users is not None else []

    def _get_next_id(self, records, prefix):
        max_num = 0
        for record in records:
            if isinstance(record, dict):
                record_id = record.get("booking_id", "")
            else:
                record_id = getattr(record, "booking_id", "")
            record_id = str(record_id)
            if record_id.startswith(prefix):
                try:
                    number = int(record_id[len(prefix):])
                    max_num = max(max_num, number)
                except ValueError:
                    pass
        return f"{prefix}{max_num + 1:04d}"

    def get_next_booking_id(self):
        return self._get_next_id(self.bookings, "BK")

    def get_next_attempt_id(self):
        return self._get_next_id(self.booking_attempts, "BA")

    def migrate_booking_attempt_ids(self):
        max_num = 0
        for attempt in self.booking_attempts:
            attempt_id = attempt.get("booking_id", "") if isinstance(attempt, dict) else getattr(attempt, "booking_id", "")
            attempt_id = str(attempt_id)
            if attempt_id.startswith("BA"):
                try:
                    max_num = max(max_num, int(attempt_id[2:]))
                except ValueError:
                    pass

        changed = False
        for attempt in self.booking_attempts:
            attempt_id = attempt.get("booking_id", "") if isinstance(attempt, dict) else getattr(attempt, "booking_id", "")
            attempt_id = str(attempt_id)
            if not attempt_id.startswith("BA") or not attempt_id[2:].isdigit():
                max_num += 1
                new_id = f"BA{max_num:04d}"
                if isinstance(attempt, dict):
                    attempt["booking_id"] = new_id
                else:
                    attempt.booking_id = new_id
                changed = True
        return changed

    def find_booking(self, booking_id):
        for b in self.bookings:
            if isinstance(b, dict):
                bid = b.get("booking_id", "")
            else:
                bid = getattr(b, "booking_id", "")
            if bid == booking_id:
                return b
        return None


class ReportGenerator:
    def __init__(self, resources=None, bookings=None, users=None):
        self.resources = resources if resources is not None else []
        self.bookings = bookings if bookings is not None else []
        self.users = users if users is not None else []

    def get_category_stats(self, filtered_bookings=None):
        bookings_to_use = filtered_bookings if filtered_bookings is not None else self.bookings
        stats = {}
        for r in self.resources:
            if not isinstance(r, dict) and not hasattr(r, "category"):
                continue
            cat = r.get("category", "Unknown") if isinstance(r, dict) else r.category
            cat = cat if isinstance(cat, str) and cat else "Unknown"
            if cat not in stats:
                stats[cat] = {"total": 0, "available": 0, "booked": 0}
            qty = r.get("quantity", 1) if isinstance(r, dict) else r.quantity
            qty = _integer_value(qty)
            if qty < 1:
                continue
            avail = r.get("availability", "") if isinstance(r, dict) else r.availability
            condition = r.get("condition", "") if isinstance(r, dict) else r.condition
            stats[cat]["total"] += qty
            if avail == "Available" and str(condition).strip().lower() != "under repair":
                stats[cat]["available"] += qty
        from app.config import USAGE_STATUSES
        for b in bookings_to_use:
            if not isinstance(b, dict) and not hasattr(b, "status"):
                continue
            status = b.get("status", "") if isinstance(b, dict) else b.status
            if status in USAGE_STATUSES:
                rid = b.get("resource_id", "") if isinstance(b, dict) else b.resource_id
                qty_req = b.get("quantity_requested", 1) if isinstance(b, dict) else b.quantity_requested
                if not isinstance(rid, str):
                    continue
                qty_req = _integer_value(qty_req)
                if qty_req < 1:
                    continue
                for r in self.resources:
                    if not isinstance(r, dict) and not hasattr(r, "resource_id"):
                        continue
                    r_id = r.get("resource_id", "") if isinstance(r, dict) else r.resource_id
                    if r_id == rid:
                        cat = r.get("category", "Unknown") if isinstance(r, dict) else r.category
                        if cat in stats:
                            stats[cat]["booked"] += qty_req
                        break
        return stats
