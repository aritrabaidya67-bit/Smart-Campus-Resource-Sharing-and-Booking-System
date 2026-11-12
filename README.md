# Smart Campus Resource Sharing and Booking System

A desktop application for university campus resource management built with Python and Tkinter. Supports booking projectors, laptops, microphones, cameras, speakers, seminar halls, classrooms, computer labs, whiteboards, extension boards, sports kits, tripods, and other shared resources.

Created by one and only Aritra Kumar Baidya (BWU/BCA/25/055)

## Features

- Register users (Students and Teachers)
- Add and manage campus resources across 12 categories and 10 locations
- Book resources with full conflict detection and capacity management
- Prevent duplicate resource, user, and booking IDs
- Search resources by name, category, location, availability, condition, or ID
- Check real-time availability for specific date/time/quantity
- Cancel bookings with history preservation
- Update booking status (Confirmed, Pending, Completed, Cancelled)
- Automatic completion of past bookings
- Dashboard with summary statistics and recent bookings
- Generate comprehensive reports with daily and monthly filters
- View booking statistics with NumPy and SciPy analytics
- Visualize data with 5 Matplotlib graph types
- All data persisted in local JSON files with atomic writes
- Damaged JSON files are backed up, and the application stops rather than overwriting unreadable data

## Python Version

Python 3.10 or later recommended.

## Installation

```bash
pip install -r requirements.txt
```

Dependencies: numpy, scipy, matplotlib (plus Python standard library including tkinter).

## How to Run

From the project root directory:

```bash
python main.py
```

## How to Generate Reports

From the GUI: click "Generate Report", select filter type (All, Daily, or Monthly), enter a date value if needed, and click "Generate". Reports are saved automatically to the `reports/` folder.

## Data File Locations

| File | Purpose |
|------|---------|
| `data/resources.json` | All campus resources (24 resources) |
| `data/users.json` | Registered users (30 users) |
| `data/bookings.json` | Confirmed, pending, cancelled, and completed bookings (40 bookings) |
| `data/booking_attempts.json` | Failed booking attempts (conflicts and invalid) |

## Report File Location

Generated reports are saved to the `reports/` folder as `.txt` files.

## Booking Rules

1. User ID must exist in the system
2. Resource ID must exist, be marked Available, and not be Under Repair
3. Booking date cannot be in the past
4. Start time cannot be in the past (for today's date)
5. Start time must be before end time
6. Requested quantity must be a positive integer not exceeding total resource quantity
7. No resource capacity conflict at any point during the requested time slot
8. Same user cannot have overlapping bookings (even for different resources)
9. Booking duration must not exceed 8 hours (configurable in `app/config.py`)
10. Booking purpose is required

### Capacity Conflict Detection

The system uses a time-point sweep algorithm to calculate the peak simultaneous resource usage during a requested interval. A new booking is accepted only when:

```
peak existing usage + requested quantity <= total resource quantity
```

This correctly handles non-overlapping existing bookings. For example, with a resource of quantity 2:
- Booking A: 09:00-10:00, quantity 1
- Booking B: 10:00-11:00, quantity 1
- New request: 09:00-11:00, quantity 1 → Accepted (peak usage is 1, not 2)

## Booking Statuses

| Status | Meaning |
|--------|---------|
| Confirmed | Valid booking with capacity reserved |
| Pending | Valid booking waiting for approval (reserves capacity) |
| Conflict | Attempted booking that violates scheduling rules |
| Invalid | Attempted booking with invalid data |
| Cancelled | Previously active booking that was cancelled |
| Completed | Booking whose scheduled end time has passed |

Failed Conflict and Invalid attempts are stored in `booking_attempts.json` and do not reserve capacity.
Successful bookings use `BK` IDs, while failed attempts use separate `BA` IDs. Failed attempts do not advance the booking ID sequence. Older failed-attempt records are automatically migrated to `BA` IDs when the application starts.

### Status Transitions

| Current Status | Allowed Transitions |
|----------------|---------------------|
| Confirmed | Pending, Cancelled, Completed |
| Pending | Confirmed, Cancelled, Completed |
| Cancelled | Confirmed, Pending (after revalidation) |
| Completed | None |

- Reactivating a cancelled booking rechecks date, resource condition and availability, the eight-hour duration limit, capacity, and user conflicts.
- A booking cannot be marked Completed before its scheduled end time.
- Confirmed and Pending bookings are automatically completed after their end time passes, releasing their reserved capacity.

## Project Structure

```
smart_campus_booking/
    main.py                  - Application entry point
    requirements.txt         - Python dependencies
    README.md                - This file
    app/
        __init__.py
        config.py            - Configuration constants and status transitions
        models.py            - Data classes (User, Resource, Equipment, Room,
                               SportsResource, Booking, BookingManager, ReportGenerator)
        storage.py           - JSON file persistence with atomic writes
        resource_service.py  - Resource and user management functions
        booking_service.py   - Booking logic, validation, conflict detection
        report_service.py    - Report generation and formatting
        analytics.py         - NumPy/SciPy statistics and Matplotlib graphs
        gui.py               - Tkinter GUI with dashboard
    data/
        resources.json       - 24 resources across 12 categories
        users.json           - 30 registered users
        bookings.json        - 40 booking records
        booking_attempts.json - 32 failed attempt records
    reports/                 - Generated report files
```

## Required Function Names (20)

All implemented as module-level functions:

| Function | Module |
|----------|--------|
| `add_resource()` | resource_service.py |
| `display_resources()` | resource_service.py |
| `validate_resource_data()` | resource_service.py |
| `register_user()` | resource_service.py |
| `display_users()` | resource_service.py |
| `search_resource()` | resource_service.py |
| `book_resource()` | booking_service.py |
| `check_booking_conflict()` | booking_service.py |
| `validate_booking_time()` | booking_service.py |
| `calculate_booking_duration()` | booking_service.py |
| `cancel_booking()` | booking_service.py |
| `display_user_bookings()` | booking_service.py |
| `update_booking_status()` | booking_service.py |
| `generate_resource_report()` | report_service.py |
| `save_resources_to_file()` | storage.py |
| `load_resources_from_file()` | storage.py |
| `save_bookings_to_file()` | storage.py |
| `load_bookings_from_file()` | storage.py |
| `display_statistics()` | analytics.py |
| `generate_graphs()` | analytics.py |

Additional assignment functions:

| Function | Module |
|----------|--------|
| `check_booking_status()` | booking_service.py |
| `check_availability()` | booking_service.py |
| `search_resource_recursively()` | resource_service.py |

## Class Hierarchy

- `User` - stores user information
- `Resource` - base resource class
  - `Equipment(Resource)` - projectors, laptops, microphones, etc.
  - `Room(Resource)` - seminar halls, classrooms, labs
  - `SportsResource(Resource)` - sports kits
- `Booking` - stores booking data with `time_range()` returning a tuple
- `BookingManager` - manages booking ID generation and lookup
- `ReportGenerator` - builds category statistics with optional filtered bookings

## Key Implementation Details

- **Recursive search**: `search_resource_recursively(resources, index, resource_id)` in resource_service.py
- **Lambda sorts**: Resources sorted by booking_count descending; bookings sorted by date and start_time; graph data sorted by value
- **Tuples**: `Booking.time_range()` returns `(start_time, end_time)` tuple
- **Nested dictionaries**: Category statistics in reports use nested dicts `{category: {total, available, booked}}`
- **NumPy**: Total hours (`np.sum`), average duration (`np.mean`), max/min duration (`np.max`, `np.min`)
- **SciPy**: Standard deviation of booking durations (`scipy.stats.tstd`)
- **Matplotlib**: 5 chart types - resource-wise horizontal bar, location-wise bar, daily trend line, status pie, duration histogram
- **Overlap formula**: `new_start < existing_end AND new_end > existing_start`
- **Capacity**: Peak simultaneous usage via time-point sweep algorithm
- **Data consistency**: Resource booking counts are recalculated from booking records after changes and reconciled at startup
- **Atomic writes**: Files written to `.tmp` then renamed to prevent corruption
- **Repair-state validation**: Resources marked Under Repair cannot be marked Available or booked
- **Historical reports**: Completed bookings are included in booked-unit and category usage totals
- **Auto-completion**: Confirmed and Pending bookings are automatically marked Completed after their end datetime passes

## Dataset Summary

| Category | Count | Minimum Required |
|----------|-------|------------------|
| Resources | 24 | 20 |
| Users | 30 | 30 |
| Bookings | 40 | 40 |
| Categories | 12 | 8 |
| Locations | 10 | 10 |
| Conflict attempts | 7+ | 5 |
| Invalid attempts | 25+ | 5 |
| Report files | 28+ | 10 |
