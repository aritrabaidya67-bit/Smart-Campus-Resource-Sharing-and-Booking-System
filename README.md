# Smart Campus Resource Sharing and Booking System

<p align="center">
  <img src="logo/Campus Booking Calendar Icon.png" alt="Smart Campus Logo" width="150" />
</p>

<p align="center">
  A desktop application for university campus resource management built with <strong>Python</strong> and <strong>Tkinter</strong>.
  <br />
  Supports booking projectors, laptops, microphones, cameras, speakers, seminar halls, classrooms, computer labs, whiteboards, extension boards, sports kits, tripods, and other shared resources.
</p>

<p align="center">
  Created by <strong>Aritra Kumar Baidya</strong> (BWU/BCA/25/055)
</p>

---

## Features

- **User Management** — Register students and teachers with full validation (email, contact, semester)
- **Resource Management** — Add resources across 12 categories and 10 campus locations
- **Update Resource Status** — Change availability, quantity, and condition of any resource with business-rule enforcement
- **Smart Booking** — Book resources with full conflict detection, capacity management, and user overlap prevention
- **Availability Checker** — Check real-time availability for a specific resource, date, time, and quantity
- **Search** — Find resources by name, category, location, availability, condition, or ID (including recursive search)
- **Booking Lifecycle** — Cancel, reactivate, and update booking status with transition rules
- **Auto-Completion** — Past bookings are automatically marked as Completed
- **Dashboard** — Summary cards (total resources, users, bookings, status counts) and recent bookings table
- **Reports** — Generate comprehensive reports with All / Daily / Monthly filters, auto-saved to disk
- **Statistics** — View booking analytics powered by NumPy and SciPy
- **Graphs** — 5 interactive Matplotlib chart types with navigation
- **Data Safety** — JSON persistence with atomic writes; corrupted files are backed up, never overwritten
- **Custom App Icon** — Branded window icon in the title bar and taskbar

---

## Python Version

Python **3.10** or later recommended.

## Installation

```bash
pip install -r requirements.txt
```

**Dependencies:** `numpy`, `scipy`, `matplotlib` (plus Python standard library including `tkinter`).

## How to Run

```bash
python main.py
```

---

## Project Structure

```
smart_campus_booking/
├── main.py                     Application entry point
├── requirements.txt            Python dependencies
├── README.md                   This file
├── logo/
│   └── Campus Booking Calendar Icon.png
├── app/
│   ├── __init__.py
│   ├── config.py               Configuration constants and status transitions
│   ├── models.py               Data classes (User, Resource, Equipment, Room,
│   │                           SportsResource, Booking, BookingManager, ReportGenerator)
│   ├── storage.py              JSON file persistence with atomic writes
│   ├── resource_service.py     Resource/user management + update resource status
│   ├── booking_service.py      Booking logic, validation, conflict detection
│   ├── report_service.py       Report generation and formatting
│   ├── analytics.py            NumPy/SciPy statistics and Matplotlib graphs
│   └── gui.py                  Tkinter GUI (dashboard + 16 sections)
├── data/
│   ├── resources.json          24 resources across 12 categories
│   ├── users.json              30 registered users
│   ├── bookings.json           40 booking records
│   └── booking_attempts.json   32 failed attempt records
└── reports/                    Generated report files (28+ reports)
```

---

## Data File Locations

| File | Purpose |
|------|---------|
| `data/resources.json` | All campus resources (24 resources) |
| `data/users.json` | Registered users (30 users) |
| `data/bookings.json` | Confirmed, pending, cancelled, and completed bookings (40 bookings) |
| `data/booking_attempts.json` | Failed booking attempts — conflicts and invalid entries (32 records) |
| `reports/` | Auto-saved report files as `.txt` (28+ reports) |

---

## Booking Rules

1. User ID must exist in the system
2. Resource ID must exist, be marked **Available**, and not be **Under Repair**
3. Booking date cannot be in the past
4. Start time cannot be in the past (for today's date)
5. Start time must be before end time
6. Requested quantity must be a positive integer not exceeding total resource quantity
7. No resource capacity conflict at any point during the requested time slot
8. Same user cannot have overlapping bookings (even for different resources)
9. Booking duration must not exceed **8 hours** (configurable in `app/config.py`)
10. Booking purpose is required

### Capacity Conflict Detection

The system uses a **time-point sweep algorithm** to calculate peak simultaneous resource usage during a requested interval. A new booking is accepted only when:

```
peak existing usage + requested quantity <= total resource quantity
```

This correctly handles non-overlapping existing bookings. For example, with a resource of quantity 2:
- Booking A: 09:00–10:00, quantity 1
- Booking B: 10:00–11:00, quantity 1
- New request: 09:00–11:00, quantity 1 → **Accepted** (peak usage is 1, not 2)

---

## Booking Statuses

| Status | Meaning |
|--------|---------|
| **Confirmed** | Valid booking with capacity reserved |
| **Pending** | Valid booking waiting for approval (reserves capacity) |
| **Conflict** | Attempted booking that violates scheduling rules |
| **Invalid** | Attempted booking with invalid data |
| **Cancelled** | Previously active booking that was cancelled |
| **Completed** | Booking whose scheduled end time has passed |

Failed Conflict and Invalid attempts are stored in `booking_attempts.json` and do **not** reserve capacity. Successful bookings use `BK` IDs, while failed attempts use separate `BA` IDs.

### Status Transitions

| Current Status | Allowed Transitions |
|----------------|---------------------|
| Confirmed | Pending, Cancelled, Completed |
| Pending | Confirmed, Cancelled, Completed |
| Cancelled | Confirmed, Pending (after revalidation) |
| Completed | None |

- Reactivating a cancelled booking rechecks date, resource condition/availability, the 8-hour duration limit, capacity, and user conflicts
- A booking cannot be marked Completed before its scheduled end time
- Confirmed and Pending bookings are automatically completed after their end time passes

---

## Update Resource Status

The **Update Resource Status** section allows modifying a resource's availability, quantity, and condition. Business rules enforced:

| Rule | Description |
|------|-------------|
| Under Repair → Unavailable | A resource under repair must be marked as Unavailable |
| Active booking protection | Cannot set Unavailable or Under Repair if the resource has active (Confirmed/Pending) bookings |
| Quantity floor | Cannot reduce quantity below what active bookings require (checks peak concurrent usage) |
| No-op detection | Returns a clear message if values are identical to current |
| Change summary | Success message shows exactly what changed (e.g., `Quantity: 5 → 10`) |

---

## Class Hierarchy

```
User                          stores user information

Resource                      base resource class
├── Equipment(Resource)       projectors, laptops, microphones, cameras, speakers,
│                             whiteboards, extension boards, tripods
├── Room(Resource)            seminar halls, classrooms, computer laboratories
└── SportsResource(Resource)  sports kits

Booking                       stores booking data with time_range() returning a tuple
BookingManager                manages booking/attempt ID generation and lookup
ReportGenerator               builds category statistics with optional filtered bookings
```

---

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

### Additional Functions

| Function | Module |
|----------|--------|
| `check_booking_status()` | booking_service.py |
| `check_availability()` | booking_service.py |
| `search_resource_recursively()` | resource_service.py |
| `update_resource_status()` | resource_service.py |

---

## Key Implementation Details

| Concept | Implementation |
|---------|----------------|
| **Recursive search** | `search_resource_recursively(resources, index, resource_id)` in resource_service.py |
| **Lambda sorts** | Resources sorted by `booking_count` descending; bookings sorted by date and start_time |
| **Tuples** | `Booking.time_range()` returns `(start_time, end_time)` tuple |
| **Nested dictionaries** | Category statistics use `{category: {total, available, booked}}` |
| **NumPy** | `np.sum`, `np.mean`, `np.max`, `np.min` for booking duration analytics |
| **SciPy** | `scipy.stats.tstd` for standard deviation of booking durations |
| **Matplotlib** | 5 chart types — horizontal bar, vertical bar, line, pie, histogram |
| **Overlap formula** | `new_start < existing_end AND new_end > existing_start` |
| **Capacity algorithm** | Peak simultaneous usage via time-point sweep |
| **Atomic writes** | Files written to `.tmp` then renamed to prevent corruption |
| **Under Repair rule** | Resources marked Under Repair cannot be Available or booked |
| **Auto-completion** | Background timer marks past Confirmed/Pending bookings as Completed |
| **Booking count sync** | Resource booking counts are recalculated from booking records after every change |

---

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

---

## How to Generate Reports

1. Click **Generate Report** in the sidebar
2. Select filter type: **All**, **Daily**, or **Monthly**
3. Enter a date value if needed (`YYYY-MM-DD` for daily, `YYYY-MM` for monthly)
4. Click **Generate**
5. Reports are saved automatically to the `reports/` folder

---

## License

This project was developed as a university assignment for the BCA program at Brainware University.
