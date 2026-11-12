MAX_BOOKING_DURATION_HOURS = 8
DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%H:%M"
DISPLAY_DATE_FORMAT = "%d %b %Y"
DISPLAY_TIME_FORMAT = "%I:%M %p"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

VALID_STATUSES = ["Confirmed", "Conflict", "Invalid", "Cancelled", "Completed", "Pending"]
ACTIVE_STATUSES = ["Confirmed", "Pending"]
USAGE_STATUSES = ["Confirmed", "Pending", "Completed"]
BOOKING_STATUSES = ["Confirmed", "Pending", "Completed"]

VALID_CONDITIONS = ["New", "Good", "Fair", "Poor", "Under Repair"]
VALID_AVAILABILITY = ["Available", "Unavailable"]

VALID_USER_TYPES = ["Student", "Teacher"]

RESOURCE_CATEGORIES = [
    "Projector", "Laptop", "Microphone", "Camera", "Speaker",
    "Seminar Hall", "Classroom", "Computer Laboratory",
    "Whiteboard", "Extension Board", "Sports Kit", "Tripod"
]

CAMPUS_LOCATIONS = [
    "Main Building", "Science Block", "Engineering Wing",
    "Library Complex", "Sports Complex", "Auditorium Block",
    "Admin Building", "IT Center", "Arts Block", "Research Center"
]

EQUIPMENT_CATEGORIES = ["Projector", "Laptop", "Microphone", "Camera", "Speaker",
                        "Whiteboard", "Extension Board", "Tripod"]
ROOM_CATEGORIES = ["Seminar Hall", "Classroom", "Computer Laboratory"]
SPORTS_CATEGORIES = ["Sports Kit"]

VALID_STATUS_TRANSITIONS = {
    "Confirmed": ["Pending", "Cancelled", "Completed"],
    "Pending": ["Confirmed", "Cancelled", "Completed"],
    "Cancelled": ["Confirmed", "Pending"],
    "Completed": [],
    "Invalid": [],
    "Conflict": [],
}
