import numpy as np
from app.booking_service import calculate_booking_duration
from app.config import USAGE_STATUSES

try:
    from scipy.stats import tstd as scipy_tstd
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


def _get_booking_durations(bookings, statuses=None):
    durations = []
    if not isinstance(bookings, list):
        return durations
    for b in bookings:
        if not isinstance(b, dict):
            continue
        if statuses and b.get("status") not in statuses:
            continue
        d = calculate_booking_duration(b.get("start_time", ""), b.get("end_time", ""))
        if d > 0:
            durations.append(d)
    return durations


def display_statistics(resources, bookings, users):
    resources = resources if isinstance(resources, list) else []
    bookings = bookings if isinstance(bookings, list) else []
    users = users if isinstance(users, list) else []
    stats = {}
    usage_statuses = USAGE_STATUSES
    durations = _get_booking_durations(bookings, statuses=usage_statuses)
    duration_array = np.array(durations) if durations else np.array([])

    if duration_array.size > 0:
        stats["total_booking_hours"] = float(np.sum(duration_array))
        stats["average_booking_duration"] = float(np.mean(duration_array))
        stats["max_booking_duration"] = float(np.max(duration_array))
        stats["min_booking_duration"] = float(np.min(duration_array))
    else:
        stats["total_booking_hours"] = 0.0
        stats["average_booking_duration"] = 0.0
        stats["max_booking_duration"] = 0.0
        stats["min_booking_duration"] = 0.0

    if SCIPY_AVAILABLE and len(durations) >= 2:
        stats["std_dev_booking_duration"] = float(scipy_tstd(durations))
    elif len(durations) < 2:
        stats["std_dev_booking_duration"] = "Not enough data (need at least 2 bookings)"
    else:
        stats["std_dev_booking_duration"] = "SciPy not available"

    resource_usage = {}
    for b in bookings:
        if not isinstance(b, dict) or b.get("status") not in usage_statuses:
            continue
        rid = b.get("resource_id", "")
        rid = rid if isinstance(rid, str) else str(rid)
        resource_usage[rid] = resource_usage.get(rid, 0) + 1

    usage_array = np.array([
        resource_usage.get(
            resource.get("resource_id") if isinstance(resource.get("resource_id"), str)
            else str(resource.get("resource_id", "")),
            0
        )
        for resource in resources
        if isinstance(resource, dict)
    ])
    if usage_array.size > 0:
        stats["avg_resource_usage"] = float(np.mean(usage_array))
        stats["max_resource_usage"] = int(np.max(usage_array))
        stats["min_resource_usage"] = int(np.min(usage_array))
    else:
        stats["avg_resource_usage"] = 0.0
        stats["max_resource_usage"] = 0
        stats["min_resource_usage"] = 0

    stats["total_resources"] = sum(isinstance(resource, dict) for resource in resources)
    stats["total_users"] = sum(isinstance(user, dict) for user in users)
    stats["total_bookings"] = sum(isinstance(booking, dict) for booking in bookings)

    status_counts = {}
    for b in bookings:
        if not isinstance(b, dict):
            continue
        status = b.get("status", "Unknown")
        status = status if isinstance(status, str) else "Unknown"
        status_counts[status] = status_counts.get(status, 0) + 1
    stats["bookings_by_status"] = status_counts

    return stats


def _collect_graph_data(resources, bookings):
    resources = resources if isinstance(resources, list) else []
    bookings = bookings if isinstance(bookings, list) else []
    resource_names = {}
    resource_locations = {}
    for r in resources:
        if not isinstance(r, dict):
            continue
        resource_id = r.get("resource_id", "")
        resource_id = resource_id if isinstance(resource_id, str) else str(resource_id)
        resource_names[resource_id] = str(r.get("name", "Unknown"))
        resource_locations[resource_id] = str(r.get("location", "Unknown"))

    usage_statuses = USAGE_STATUSES
    resource_booking_counts = {}
    location_booking_counts = {}
    daily_counts = {}
    status_counts = {}
    durations = []

    for b in bookings:
        if not isinstance(b, dict):
            continue
        rid = b.get("resource_id", "")
        status = b.get("status", "")
        bdate = b.get("booking_date", "")

        if not isinstance(status, str):
            status = "Unknown"
        if not isinstance(rid, str):
            rid = str(rid)
        if not isinstance(bdate, str):
            bdate = "Unknown"
        if status in usage_statuses:
            rname = f"{resource_names.get(rid, rid)} ({rid})"
            resource_booking_counts[rname] = resource_booking_counts.get(rname, 0) + 1

            loc = resource_locations.get(rid, "Unknown")
            location_booking_counts[loc] = location_booking_counts.get(loc, 0) + 1

            daily_counts[bdate] = daily_counts.get(bdate, 0) + 1

            d = calculate_booking_duration(b.get("start_time", ""), b.get("end_time", ""))
            if d > 0:
                durations.append(d)

        status_counts[status] = status_counts.get(status, 0) + 1

    return {
        "resource_booking_counts": resource_booking_counts,
        "location_booking_counts": location_booking_counts,
        "daily_counts": daily_counts,
        "status_counts": status_counts,
        "durations": durations,
    }


GRAPH_TITLES = [
    "Resource-wise Bookings (Top 10)",
    "Location-wise Bookings",
    "Daily Booking Trend",
    "Booking Status Distribution",
    "Booking Duration Distribution",
]


def _draw_graph_on_axis(data, graph_index, ax, detailed=False):
    if graph_index == 0:
        rbc = data["resource_booking_counts"]
        if rbc:
            items = sorted(rbc.items(), key=lambda x: x[1], reverse=True)[:10]
            max_label = 15 if not detailed else 30
            names = [item[0][:max_label] for item in items]
            counts = [item[1] for item in items]
            bars = ax.barh(names, counts, color="#4A90D9", edgecolor="#3570A9", height=0.6)
            ax.set_xlabel("Number of Bookings", fontsize=11 if detailed else 9)
            ax.set_title("Resource-wise Bookings (Top 10)", fontsize=13 if detailed else 10, fontweight="bold")
            ax.invert_yaxis()
            if detailed:
                for bar, count in zip(bars, counts):
                    ax.text(bar.get_width() + 0.05, bar.get_y() + bar.get_height() / 2,
                            str(count), va="center", fontsize=9, fontweight="bold")
        else:
            ax.text(0.5, 0.5, "No booking data", ha="center", va="center",
                    transform=ax.transAxes, fontsize=14, color="gray")
            ax.set_title("Resource-wise Bookings", fontsize=13 if detailed else 10, fontweight="bold")

    elif graph_index == 1:
        lbc = data["location_booking_counts"]
        if lbc:
            locs = list(lbc.keys())
            max_label = 12 if not detailed else 20
            counts = [lbc[loc] for loc in locs]
            bars = ax.bar(range(len(locs)), counts, color="#50C878", edgecolor="#3AA85E", width=0.6)
            ax.set_xticks(range(len(locs)))
            ax.set_xticklabels([loc[:max_label] for loc in locs], rotation=30, ha="right", fontsize=9 if detailed else 7)
            ax.set_ylabel("Number of Bookings", fontsize=11 if detailed else 9)
            ax.set_title("Location-wise Bookings", fontsize=13 if detailed else 10, fontweight="bold")
            if detailed:
                for bar, count in zip(bars, counts):
                    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.1,
                            str(count), ha="center", fontsize=9, fontweight="bold")
        else:
            ax.text(0.5, 0.5, "No booking data", ha="center", va="center",
                    transform=ax.transAxes, fontsize=14, color="gray")
            ax.set_title("Location-wise Bookings", fontsize=13 if detailed else 10, fontweight="bold")

    elif graph_index == 2:
        dc = data["daily_counts"]
        if dc:
            sorted_dates = sorted(dc.keys())
            date_labels = list(map(lambda d: d[5:], sorted_dates))
            values = [dc[d] for d in sorted_dates]
            ax.plot(range(len(date_labels)), values, marker="o", color="#E74C3C",
                    linewidth=2.5 if detailed else 2, markersize=7 if detailed else 5,
                    markerfacecolor="white", markeredgewidth=2)
            if detailed:
                ax.fill_between(range(len(date_labels)), values, alpha=0.15, color="#E74C3C")
            ax.set_xticks(range(len(date_labels)))
            ax.set_xticklabels(date_labels, rotation=45, ha="right", fontsize=8 if detailed else 6)
            ax.set_ylabel("Number of Bookings", fontsize=11 if detailed else 9)
            ax.set_title("Daily Booking Trend", fontsize=13 if detailed else 10, fontweight="bold")
            ax.grid(axis="y", alpha=0.3)
        else:
            ax.text(0.5, 0.5, "No booking data", ha="center", va="center",
                    transform=ax.transAxes, fontsize=14, color="gray")
            ax.set_title("Daily Booking Trend", fontsize=13 if detailed else 10, fontweight="bold")

    elif graph_index == 3:
        sc = data["status_counts"]
        if sc:
            labels = list(sc.keys())
            sizes = list(sc.values())
            colors = ["#4A90D9", "#E74C3C", "#F39C12", "#95A5A6", "#50C878", "#9B59B6"]
            wedges, texts, autotexts = ax.pie(
                sizes, labels=labels, autopct="%1.1f%%",
                colors=[colors[i % len(colors)] for i in range(len(labels))], startangle=140,
                textprops={"fontsize": 10 if detailed else 8}
            )
            if detailed:
                for at in autotexts:
                    at.set_fontweight("bold")
            ax.set_title("Booking Status Distribution", fontsize=13 if detailed else 10, fontweight="bold")
        else:
            ax.text(0.5, 0.5, "No booking data", ha="center", va="center",
                    transform=ax.transAxes, fontsize=14, color="gray")
            ax.set_title("Booking Status Distribution", fontsize=13 if detailed else 10, fontweight="bold")

    elif graph_index == 4:
        dur = data["durations"]
        if dur:
            ax.hist(dur, bins=min(10, len(set(dur))),
                    color="#9B59B6", edgecolor="white", linewidth=1.2, rwidth=0.85)
            ax.set_xlabel("Duration (hours)", fontsize=11 if detailed else 9)
            ax.set_ylabel("Frequency", fontsize=11 if detailed else 9)
            ax.set_title("Booking Duration Distribution", fontsize=13 if detailed else 10, fontweight="bold")
            ax.grid(axis="y", alpha=0.3)
        else:
            ax.text(0.5, 0.5, "No booking data", ha="center", va="center",
                    transform=ax.transAxes, fontsize=14, color="gray")
            ax.set_title("Booking Duration Distribution", fontsize=13 if detailed else 10, fontweight="bold")


def create_single_graph(resources, bookings, graph_index):
    return generate_graphs(resources, bookings, graph_index)


def generate_graphs(resources, bookings, graph_index=None):
    from matplotlib.figure import Figure
    data = _collect_graph_data(resources, bookings)

    if graph_index is not None:
        if graph_index < 0 or graph_index >= len(GRAPH_TITLES):
            raise ValueError("Invalid graph number.")
        fig = Figure(figsize=(8, 5), dpi=100)
        ax = fig.add_subplot(1, 1, 1)
        _draw_graph_on_axis(data, graph_index, ax, detailed=True)
        fig.tight_layout(pad=2.0)
        return fig

    figures = []
    for index in range(len(GRAPH_TITLES)):
        fig = Figure(figsize=(8, 5), dpi=100)
        ax = fig.add_subplot(1, 1, 1)
        _draw_graph_on_axis(data, index, ax, detailed=True)
        fig.tight_layout(pad=2.0)
        figures.append(fig)
    return figures
