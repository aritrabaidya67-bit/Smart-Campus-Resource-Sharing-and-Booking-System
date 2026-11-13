import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from pathlib import Path

from app.config import (
    VALID_CONDITIONS, VALID_AVAILABILITY, VALID_USER_TYPES,
    RESOURCE_CATEGORIES, CAMPUS_LOCATIONS,
    DATE_FORMAT, TIME_FORMAT, DISPLAY_DATE_FORMAT, DISPLAY_TIME_FORMAT,
    ACTIVE_STATUSES
)
from app.storage import (
    save_resources_to_file, load_resources_from_file,
    save_users_to_file, load_users_from_file,
    save_bookings_to_file, load_bookings_from_file,
    save_booking_attempts_to_file, load_booking_attempts_from_file
)
from app.resource_service import (
    add_resource, display_resources, validate_resource_data,
    search_resource, search_resource_recursively,
    register_user, display_users, get_next_resource_id, get_next_user_id,
    validate_user_data, delete_resource, delete_user, update_resource_status
)
from app.booking_service import (
    book_resource, cancel_booking, display_user_bookings,
    update_booking_status, check_availability, delete_booking,
    complete_past_bookings, sync_booking_counts
)
from app.report_service import (
    generate_resource_report, format_report_text, save_generated_report,
    validate_report_filter
)
from app.analytics import display_statistics, create_single_graph, GRAPH_TITLES
from app.models import BookingManager


class CampusBookingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Smart Campus Resource Sharing and Booking System")
        self.root.geometry("1100x700")
        self.root.minsize(900, 600)

        logo_path = Path(__file__).resolve().parent.parent / "logo" / "Campus Booking Calendar Icon.png"
        if logo_path.exists():
            self._app_icon = tk.PhotoImage(file=str(logo_path))
            self.root.iconphoto(True, self._app_icon)

        self._load_errors = set()
        self.resources = self._load_data(load_resources_from_file, "resources")
        self.users = self._load_data(load_users_from_file, "users")
        self.bookings = self._load_data(load_bookings_from_file, "bookings")
        self.booking_attempts = self._load_data(load_booking_attempts_from_file, "booking attempts")
        if self._load_errors:
            messagebox.showerror(
                "Application Not Started",
                "One or more data files could not be read. Repair the original file using its backup, then restart the application."
            )
            self.root.destroy()
            self.ready = False
            return
        self.ready = True
        self.booking_manager = BookingManager(
            self.bookings, self.booking_attempts, self.resources, self.users
        )
        attempts_migrated = self.booking_manager.migrate_booking_attempt_ids()
        counts_reconciled = sync_booking_counts(self.resources, self.bookings)
        if attempts_migrated or counts_reconciled:
            self._save_all_data()
        self._submission_in_progress = False

        self._auto_complete_past_bookings()
        self._setup_styles()
        self._build_layout()
        self._show_dashboard()
        self._schedule_auto_complete()

    def _load_data(self, loader_func, data_name):
        try:
            return loader_func()
        except ValueError as e:
            self._load_errors.add(data_name)
            messagebox.showwarning(
                "Data Warning",
                f"Problem loading {data_name}: {e}\n\nThe original file will be kept unchanged until it is repaired."
            )
            return []

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"), padding=5)
        style.configure("Heading.TLabel", font=("Segoe UI", 12, "bold"), padding=3)
        style.configure("TButton", font=("Segoe UI", 10), padding=5)
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"))
        style.configure("Nav.TButton", font=("Segoe UI", 9), padding=4)
        style.configure("Treeview", font=("Segoe UI", 9), rowheight=25)
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))
        style.configure("Card.TLabelframe", padding=10)
        style.configure("BigNum.TLabel", font=("Segoe UI", 20, "bold"))

    def _build_layout(self):
        header = ttk.Frame(self.root, padding=5)
        header.pack(fill=tk.X)
        ttk.Label(header, text="Smart Campus Resource Sharing & Booking", style="Title.TLabel").pack(side=tk.LEFT)
        ttk.Label(header, text="Created by one and only Aritra Kumar Baidya (BWU/BCA/25/055)", font=("Segoe UI", 9)).pack(side=tk.RIGHT)
        main_pane = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        nav_frame = ttk.Frame(main_pane, padding=5)
        main_pane.add(nav_frame, weight=0)

        self.content_frame = ttk.Frame(main_pane, padding=5)
        main_pane.add(self.content_frame, weight=1)

        buttons = [
            ("Dashboard", self._show_dashboard),
            ("Add Resource", self._show_add_resource),
            ("Display Resources", self._show_display_resources),
            ("Update Resource Status", self._show_update_resource_status),
            ("Register User", self._show_register_user),
            ("Display Users", self._show_display_users),
            ("Book Resource", self._show_book_resource),
            ("Search Resource", self._show_search_resource),
            ("Check Availability", self._show_check_availability),
            ("Cancel Booking", self._show_cancel_booking),
            ("Display Bookings", self._show_display_bookings),
            ("Update Booking Status", self._show_update_status),
            ("Generate Report", self._show_generate_report),
            ("Display Statistics", self._show_statistics),
            ("Generate Graphs", self._generate_graphs),
            ("Exit", self._exit_app),
        ]

        for text, command in buttons:
            ttk.Button(nav_frame, text=text, command=command, style="Nav.TButton", width=22).pack(fill=tk.X, pady=2)

    def _clear_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def _format_date(self, date_str):
        try:
            return datetime.strptime(date_str, DATE_FORMAT).strftime(DISPLAY_DATE_FORMAT)
        except (ValueError, TypeError):
            return date_str

    def _format_time(self, time_str):
        try:
            return datetime.strptime(time_str, TIME_FORMAT).strftime(DISPLAY_TIME_FORMAT)
        except (ValueError, TypeError):
            return time_str

    def _save_all_data(self):
        try:
            if "resources" not in self._load_errors:
                save_resources_to_file(self.resources)
            if "users" not in self._load_errors:
                save_users_to_file(self.users)
            if "bookings" not in self._load_errors:
                save_bookings_to_file(self.bookings)
            if "booking attempts" not in self._load_errors:
                save_booking_attempts_to_file(self.booking_attempts)
            return True
        except (OSError, TypeError, ValueError) as error:
            messagebox.showerror("Save Error", f"Changes could not be fully saved: {error}")
            return False

    def _auto_complete_past_bookings(self):
        if complete_past_bookings(self.bookings):
            self._save_all_data()

    def _schedule_auto_complete(self):
        self._auto_complete_past_bookings()
        self.root.after(60000, self._schedule_auto_complete)

    def _show_dashboard(self):
        self._clear_content()
        frame = ttk.LabelFrame(self.content_frame, text="Dashboard", padding=15)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        stats_frame = ttk.Frame(frame)
        stats_frame.pack(fill=tk.X, pady=(0, 10))

        total_res = len(self.resources)
        total_users = len(self.users)
        total_bookings = len(self.bookings)
        confirmed = sum(1 for b in self.bookings if b.get("status") == "Confirmed")
        pending = sum(1 for b in self.bookings if b.get("status") == "Pending")
        cancelled = sum(1 for b in self.bookings if b.get("status") == "Cancelled")
        completed = sum(1 for b in self.bookings if b.get("status") == "Completed")

        cards = [
            ("Total Resources", total_res),
            ("Total Users", total_users),
            ("Total Bookings", total_bookings),
            ("Confirmed", confirmed),
            ("Pending", pending),
            ("Cancelled", cancelled),
            ("Completed", completed),
        ]

        for i, (label, value) in enumerate(cards):
            row, col = divmod(i, 4)
            card = ttk.LabelFrame(stats_frame, text=label, style="Card.TLabelframe")
            card.grid(row=row, column=col, padx=8, pady=5, sticky="nsew")
            ttk.Label(card, text=str(value), style="BigNum.TLabel").pack(padx=10, pady=5)
            stats_frame.columnconfigure(col, weight=1)

        ttk.Label(frame, text="Recent Bookings", style="Heading.TLabel").pack(anchor=tk.W, pady=(10, 5))

        cols = ("ID", "User", "Resource", "Date", "Time", "Status")
        tree_frame = ttk.Frame(frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=8)
        col_widths = {"ID": 70, "User": 80, "Resource": 80, "Date": 90, "Time": 130, "Status": 80}
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=col_widths.get(col, 80), minwidth=50)

        recent = sorted(self.bookings, key=lambda x: x.get("created_at", ""), reverse=True)[:10]
        for b in recent:
            tree.insert("", tk.END, values=(
                b.get("booking_id"), b.get("user_id"), b.get("resource_id"),
                self._format_date(b.get("booking_date")),
                f"{self._format_time(b.get('start_time'))} - {self._format_time(b.get('end_time'))}",
                b.get("status")
            ))

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _show_add_resource(self):
        self._clear_content()
        frame = ttk.LabelFrame(self.content_frame, text="Add New Resource", padding=15)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        fields = {}
        row = 0

        ttk.Label(frame, text="Resource ID:").grid(row=row, column=0, sticky=tk.W, pady=3)
        next_id = get_next_resource_id(self.resources)
        id_var = tk.StringVar(value=next_id)
        ttk.Entry(frame, textvariable=id_var, width=30).grid(row=row, column=1, pady=3, padx=5)
        fields["resource_id"] = id_var
        row += 1

        ttk.Label(frame, text="Name:").grid(row=row, column=0, sticky=tk.W, pady=3)
        name_var = tk.StringVar()
        ttk.Entry(frame, textvariable=name_var, width=30).grid(row=row, column=1, pady=3, padx=5)
        fields["name"] = name_var
        row += 1

        ttk.Label(frame, text="Category:").grid(row=row, column=0, sticky=tk.W, pady=3)
        cat_var = tk.StringVar()
        ttk.Combobox(frame, textvariable=cat_var, values=RESOURCE_CATEGORIES, width=28, state="readonly").grid(row=row, column=1, pady=3, padx=5)
        fields["category"] = cat_var
        row += 1

        ttk.Label(frame, text="Location:").grid(row=row, column=0, sticky=tk.W, pady=3)
        loc_var = tk.StringVar()
        ttk.Combobox(frame, textvariable=loc_var, values=CAMPUS_LOCATIONS, width=28, state="readonly").grid(row=row, column=1, pady=3, padx=5)
        fields["location"] = loc_var
        row += 1

        ttk.Label(frame, text="Quantity:").grid(row=row, column=0, sticky=tk.W, pady=3)
        qty_var = tk.StringVar(value="1")
        ttk.Entry(frame, textvariable=qty_var, width=30).grid(row=row, column=1, pady=3, padx=5)
        fields["quantity"] = qty_var
        row += 1

        ttk.Label(frame, text="Condition:").grid(row=row, column=0, sticky=tk.W, pady=3)
        cond_var = tk.StringVar()
        ttk.Combobox(frame, textvariable=cond_var, values=VALID_CONDITIONS, width=28, state="readonly").grid(row=row, column=1, pady=3, padx=5)
        fields["condition"] = cond_var
        row += 1

        ttk.Label(frame, text="Availability:").grid(row=row, column=0, sticky=tk.W, pady=3)
        avail_var = tk.StringVar(value="Available")
        ttk.Combobox(frame, textvariable=avail_var, values=VALID_AVAILABILITY, width=28, state="readonly").grid(row=row, column=1, pady=3, padx=5)
        fields["availability"] = avail_var
        row += 1

        def submit():
            raw = {k: v.get().strip() for k, v in fields.items()}
            errors = validate_resource_data(
                raw.get("name", ""), raw.get("category", ""),
                raw.get("location", ""), raw.get("quantity", ""),
                raw.get("condition", ""), raw.get("availability", "")
            )
            if errors:
                messagebox.showerror("Validation Error", "\n".join(errors))
                return
            data = {
                "resource_id": raw.get("resource_id", ""),
                "name": raw["name"],
                "category": raw["category"],
                "location": raw["location"],
                "quantity": int(raw["quantity"]),
                "condition": raw["condition"],
                "availability": raw["availability"],
                "booking_count": 0
            }
            success, messages = add_resource(self.resources, data)
            if success:
                if not self._save_all_data():
                    return
                messagebox.showinfo("Success", messages[0])
                self._show_add_resource()
            else:
                messagebox.showerror("Error", "\n".join(messages))

        ttk.Button(frame, text="Add Resource", command=submit, style="Accent.TButton").grid(row=row, column=0, columnspan=2, pady=15)

    def _show_display_resources(self):
        self._clear_content()
        frame = ttk.LabelFrame(self.content_frame, text="All Resources", padding=10)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        cols = ("ID", "Name", "Category", "Location", "Qty", "Condition", "Availability", "Bookings")
        tree_frame = ttk.Frame(frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=18)

        col_widths = {"ID": 70, "Name": 150, "Category": 120, "Location": 120, "Qty": 50, "Condition": 80, "Availability": 90, "Bookings": 70}
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=col_widths.get(col, 100), minwidth=50)

        resources_sorted = sorted(display_resources(self.resources), key=lambda x: x.get("booking_count", 0), reverse=True)
        for r in resources_sorted:
            tree.insert("", tk.END, values=(
                r.get("resource_id"), r.get("name"), r.get("category"),
                r.get("location"), r.get("quantity"), r.get("condition"),
                r.get("availability"), r.get("booking_count", 0)
            ))

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=8)

        def do_delete():
            selected = tree.selection()
            if not selected:
                messagebox.showinfo("Info", "Select a resource to delete.")
                return
            vals = tree.item(selected[0], "values")
            rid = vals[0]
            if not messagebox.askyesno("Confirm", f"Delete resource {rid} - {vals[1]}?"):
                return
            ok, msg = delete_resource(self.resources, self.bookings, rid)
            if ok:
                if not self._save_all_data():
                    return
                messagebox.showinfo("Deleted", msg)
                self._show_display_resources()
            else:
                messagebox.showerror("Error", msg)

        ttk.Button(btn_frame, text="Delete Selected Resource", command=do_delete, style="Accent.TButton").pack(side=tk.RIGHT, padx=5)

    def _show_update_resource_status(self):
        self._clear_content()
        frame = ttk.LabelFrame(self.content_frame, text="Update Resource Status", padding=15)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        if not self.resources:
            ttk.Label(frame, text="No resources available.", font=("Segoe UI", 11)).pack(pady=20)
            return

        resource_display = [
            f"{r.get('resource_id')} - {r.get('name')} ({r.get('category')})"
            for r in self.resources if isinstance(r, dict)
        ]

        ttk.Label(frame, text="Select Resource:").grid(row=0, column=0, sticky=tk.W, pady=3)
        res_var = tk.StringVar()
        res_combo = ttk.Combobox(frame, textvariable=res_var, values=resource_display, width=45, state="readonly")
        res_combo.grid(row=0, column=1, pady=3, padx=5)

        info_frame = ttk.LabelFrame(frame, text="Current Status", padding=10)
        info_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=10, padx=5)

        current_avail_label = ttk.Label(info_frame, text="Availability: -")
        current_avail_label.grid(row=0, column=0, sticky=tk.W, padx=10, pady=2)
        current_qty_label = ttk.Label(info_frame, text="Quantity: -")
        current_qty_label.grid(row=0, column=1, sticky=tk.W, padx=10, pady=2)
        current_cond_label = ttk.Label(info_frame, text="Condition: -")
        current_cond_label.grid(row=0, column=2, sticky=tk.W, padx=10, pady=2)
        current_bookings_label = ttk.Label(info_frame, text="Active Bookings: -")
        current_bookings_label.grid(row=0, column=3, sticky=tk.W, padx=10, pady=2)

        ttk.Label(frame, text="New Availability:").grid(row=2, column=0, sticky=tk.W, pady=3)
        avail_var = tk.StringVar()
        ttk.Combobox(frame, textvariable=avail_var, values=VALID_AVAILABILITY, width=28, state="readonly").grid(row=2, column=1, pady=3, padx=5)

        ttk.Label(frame, text="New Quantity:").grid(row=3, column=0, sticky=tk.W, pady=3)
        qty_var = tk.StringVar()
        ttk.Entry(frame, textvariable=qty_var, width=30).grid(row=3, column=1, pady=3, padx=5)

        ttk.Label(frame, text="New Condition:").grid(row=4, column=0, sticky=tk.W, pady=3)
        cond_var = tk.StringVar()
        ttk.Combobox(frame, textvariable=cond_var, values=VALID_CONDITIONS, width=28, state="readonly").grid(row=4, column=1, pady=3, padx=5)

        def on_resource_selected(event=None):
            sel = res_var.get()
            if not sel:
                return
            resource_id = sel.split(" - ")[0].strip()
            resource = search_resource_recursively(self.resources, 0, resource_id)
            if resource is None:
                return
            current_avail_label.config(text=f"Availability: {resource.get('availability', '-')}")
            current_qty_label.config(text=f"Quantity: {resource.get('quantity', '-')}")
            current_cond_label.config(text=f"Condition: {resource.get('condition', '-')}")
            active_count = sum(
                1 for b in self.bookings
                if isinstance(b, dict) and b.get("resource_id") == resource_id and b.get("status") in ACTIVE_STATUSES
            )
            current_bookings_label.config(text=f"Active Bookings: {active_count}")
            avail_var.set(resource.get("availability", ""))
            qty_var.set(str(resource.get("quantity", "")))
            cond_var.set(resource.get("condition", ""))

        res_combo.bind("<<ComboboxSelected>>", on_resource_selected)

        def submit():
            sel = res_var.get()
            if not sel:
                messagebox.showerror("Error", "Please select a resource.")
                return
            resource_id = sel.split(" - ")[0].strip()
            new_avail = avail_var.get().strip() or None
            new_qty = qty_var.get().strip() or None
            new_cond = cond_var.get().strip() or None
            if new_avail is None and new_qty is None and new_cond is None:
                messagebox.showerror("Error", "Please set at least one field to update.")
                return
            success, message = update_resource_status(
                self.resources, self.bookings, resource_id,
                new_availability=new_avail,
                new_quantity=new_qty,
                new_condition=new_cond
            )
            if success:
                if not self._save_all_data():
                    return
                messagebox.showinfo("Success", message)
                self._show_update_resource_status()
            else:
                messagebox.showerror("Error", message)

        ttk.Button(frame, text="Update Resource", command=submit, style="Accent.TButton").grid(row=5, column=0, columnspan=2, pady=15)

    def _show_register_user(self):
        self._clear_content()
        frame = ttk.LabelFrame(self.content_frame, text="Register New User", padding=15)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        fields = {}
        row = 0

        ttk.Label(frame, text="User ID:").grid(row=row, column=0, sticky=tk.W, pady=3)
        uid_var = tk.StringVar(value=get_next_user_id(self.users))
        ttk.Entry(frame, textvariable=uid_var, width=30).grid(row=row, column=1, pady=3, padx=5)
        fields["user_id"] = uid_var
        row += 1

        ttk.Label(frame, text="Name:").grid(row=row, column=0, sticky=tk.W, pady=3)
        name_var = tk.StringVar()
        ttk.Entry(frame, textvariable=name_var, width=30).grid(row=row, column=1, pady=3, padx=5)
        fields["name"] = name_var
        row += 1

        ttk.Label(frame, text="User Type:").grid(row=row, column=0, sticky=tk.W, pady=3)
        type_var = tk.StringVar()
        ttk.Combobox(frame, textvariable=type_var, values=VALID_USER_TYPES, width=28, state="readonly").grid(row=row, column=1, pady=3, padx=5)
        fields["user_type"] = type_var
        row += 1

        ttk.Label(frame, text="Department:").grid(row=row, column=0, sticky=tk.W, pady=3)
        dept_var = tk.StringVar()
        ttk.Entry(frame, textvariable=dept_var, width=30).grid(row=row, column=1, pady=3, padx=5)
        fields["department"] = dept_var
        row += 1

        ttk.Label(frame, text="Semester:").grid(row=row, column=0, sticky=tk.W, pady=3)
        sem_var = tk.StringVar()
        ttk.Entry(frame, textvariable=sem_var, width=30).grid(row=row, column=1, pady=3, padx=5)
        fields["semester"] = sem_var
        row += 1

        ttk.Label(frame, text="Contact Number:").grid(row=row, column=0, sticky=tk.W, pady=3)
        contact_var = tk.StringVar()
        ttk.Entry(frame, textvariable=contact_var, width=30).grid(row=row, column=1, pady=3, padx=5)
        fields["contact_number"] = contact_var
        row += 1

        ttk.Label(frame, text="Email:").grid(row=row, column=0, sticky=tk.W, pady=3)
        email_var = tk.StringVar()
        ttk.Entry(frame, textvariable=email_var, width=30).grid(row=row, column=1, pady=3, padx=5)
        fields["email"] = email_var
        row += 1

        def submit():
            raw = {k: v.get().strip() for k, v in fields.items()}
            errors = validate_user_data(
                raw.get("user_id", ""), raw.get("name", ""),
                raw.get("user_type", ""), raw.get("department", ""),
                raw.get("contact_number", ""), raw.get("email", ""),
                raw.get("semester", "")
            )
            if errors:
                messagebox.showerror("Validation Error", "\n".join(errors))
                return
            data = dict(raw)
            success, messages = register_user(self.users, data)
            if success:
                if not self._save_all_data():
                    return
                messagebox.showinfo("Success", messages[0])
                self._show_register_user()
            else:
                messagebox.showerror("Error", "\n".join(messages))

        ttk.Button(frame, text="Register User", command=submit, style="Accent.TButton").grid(row=row, column=0, columnspan=2, pady=15)

    def _show_display_users(self):
        self._clear_content()
        frame = ttk.LabelFrame(self.content_frame, text="All Users", padding=10)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        cols = ("ID", "Name", "Type", "Department", "Semester", "Contact", "Email")
        tree_frame = ttk.Frame(frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=18)
        col_widths = {"ID": 70, "Name": 130, "Type": 80, "Department": 120, "Semester": 70, "Contact": 110, "Email": 180}
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=col_widths.get(col, 100), minwidth=50)

        for u in display_users(self.users):
            tree.insert("", tk.END, values=(
                u.get("user_id"), u.get("name"), u.get("user_type"),
                u.get("department"), u.get("semester", ""),
                u.get("contact_number"), u.get("email")
            ))

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=8)

        def do_delete():
            selected = tree.selection()
            if not selected:
                messagebox.showinfo("Info", "Select a user to delete.")
                return
            vals = tree.item(selected[0], "values")
            uid = vals[0]
            if not messagebox.askyesno("Confirm", f"Delete user {uid} - {vals[1]}?"):
                return
            ok, msg = delete_user(self.users, self.bookings, uid)
            if ok:
                if not self._save_all_data():
                    return
                messagebox.showinfo("Deleted", msg)
                self._show_display_users()
            else:
                messagebox.showerror("Error", msg)

        ttk.Button(btn_frame, text="Delete Selected User", command=do_delete, style="Accent.TButton").pack(side=tk.RIGHT, padx=5)

    def _show_book_resource(self):
        self._clear_content()
        frame = ttk.LabelFrame(self.content_frame, text="Book a Resource", padding=15)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        row = 0

        ttk.Label(frame, text="User:").grid(row=row, column=0, sticky=tk.W, pady=3)
        user_ids = [f"{u.get('user_id')} - {u.get('name')}" for u in self.users]
        user_var = tk.StringVar()
        ttk.Combobox(frame, textvariable=user_var, values=user_ids, width=35, state="readonly").grid(row=row, column=1, pady=3, padx=5)
        row += 1

        ttk.Label(frame, text="Resource:").grid(row=row, column=0, sticky=tk.W, pady=3)
        resource_ids = [f"{r.get('resource_id')} - {r.get('name')} ({r.get('category')})" for r in self.resources if r.get("availability") == "Available"]
        res_var = tk.StringVar()
        ttk.Combobox(frame, textvariable=res_var, values=resource_ids, width=35, state="readonly").grid(row=row, column=1, pady=3, padx=5)
        row += 1

        ttk.Label(frame, text="Date (YYYY-MM-DD):").grid(row=row, column=0, sticky=tk.W, pady=3)
        date_var = tk.StringVar(value=datetime.now().strftime(DATE_FORMAT))
        ttk.Entry(frame, textvariable=date_var, width=37).grid(row=row, column=1, pady=3, padx=5)
        row += 1

        ttk.Label(frame, text="Start Time (HH:MM, 00:00 to 23:59):").grid(row=row, column=0, sticky=tk.W, pady=3)
        start_var = tk.StringVar(value="09:00")
        ttk.Entry(frame, textvariable=start_var, width=37).grid(row=row, column=1, pady=3, padx=5)
        row += 1

        ttk.Label(frame, text="End Time (HH:MM, 00:00 to 23:59):").grid(row=row, column=0, sticky=tk.W, pady=3)
        end_var = tk.StringVar(value="10:00")
        ttk.Entry(frame, textvariable=end_var, width=37).grid(row=row, column=1, pady=3, padx=5)
        row += 1

        ttk.Label(frame, text="Quantity:").grid(row=row, column=0, sticky=tk.W, pady=3)
        qty_var = tk.StringVar(value="1")
        ttk.Entry(frame, textvariable=qty_var, width=37).grid(row=row, column=1, pady=3, padx=5)
        row += 1

        ttk.Label(frame, text="Purpose:").grid(row=row, column=0, sticky=tk.W, pady=3)
        purpose_var = tk.StringVar()
        ttk.Entry(frame, textvariable=purpose_var, width=37).grid(row=row, column=1, pady=3, padx=5)
        row += 1

        def submit():
            if self._submission_in_progress:
                return
            self._submission_in_progress = True
            try:
                user_sel = user_var.get()
                res_sel = res_var.get()
                if not user_sel or not res_sel:
                    messagebox.showerror("Error", "Please select both a user and a resource.")
                    return

                qty_str = qty_var.get().strip()
                try:
                    qty_val = int(qty_str)
                except (ValueError, TypeError):
                    messagebox.showerror("Validation Error", "Quantity must be a valid positive integer.")
                    return

                user_id = user_sel.split(" - ")[0].strip()
                resource_id = res_sel.split(" - ")[0].strip()
                booking_id = self.booking_manager.get_next_booking_id()

                data = {
                    "booking_id": booking_id,
                    "user_id": user_id,
                    "resource_id": resource_id,
                    "booking_date": date_var.get().strip(),
                    "start_time": start_var.get().strip(),
                    "end_time": end_var.get().strip(),
                    "purpose": purpose_var.get().strip(),
                    "quantity_requested": qty_val,
                }

                success, status, message = book_resource(
                    self.resources, self.users, self.bookings,
                    self.booking_attempts, data
                )
                saved = self._save_all_data()
                if not saved:
                    return

                if success:
                    start_display = self._format_time(data["start_time"])
                    end_display = self._format_time(data["end_time"])
                    messagebox.showinfo("Booking Confirmed", f"{message}\nBooking ID: {booking_id}\nTime: {start_display} - {end_display}")
                    self._show_book_resource()
                else:
                    messagebox.showwarning(f"Booking {status}", message)
            finally:
                self._submission_in_progress = False

        ttk.Button(frame, text="Book Resource", command=submit, style="Accent.TButton").grid(row=row, column=0, columnspan=2, pady=15)

    def _show_search_resource(self):
        self._clear_content()
        frame = ttk.LabelFrame(self.content_frame, text="Search Resources", padding=15)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        search_frame = ttk.Frame(frame)
        search_frame.pack(fill=tk.X, pady=5)

        ttk.Label(search_frame, text="Search By:").grid(row=0, column=0, sticky=tk.W, pady=3)
        mode_var = tk.StringVar(value="Name")
        ttk.Combobox(search_frame, textvariable=mode_var, values=["Name", "Category", "Location", "Availability", "Condition", "Resource ID"], width=15, state="readonly").grid(row=0, column=1, padx=5)

        ttk.Label(search_frame, text="Value:").grid(row=0, column=2, padx=5)
        search_var = tk.StringVar()
        ttk.Entry(search_frame, textvariable=search_var, width=25).grid(row=0, column=3, padx=5)

        cols = ("ID", "Name", "Category", "Location", "Qty", "Condition", "Availability")
        tree_frame = ttk.Frame(frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=15)
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=100, minwidth=50)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        def do_search():
            for item in tree.get_children():
                tree.delete(item)
            mode = mode_var.get()
            val = search_var.get().strip()
            if not val:
                messagebox.showinfo("Info", "Please enter a search value.")
                return

            results = []
            if mode == "Resource ID":
                found = search_resource_recursively(self.resources, 0, val)
                if found:
                    results = [found]
            elif mode == "Name":
                results = search_resource(self.resources, name=val)
            elif mode == "Category":
                results = search_resource(self.resources, category=val)
            elif mode == "Location":
                results = search_resource(self.resources, location=val)
            elif mode == "Availability":
                results = search_resource(self.resources, availability=val)
            elif mode == "Condition":
                results = search_resource(self.resources, condition=val)

            if not results:
                messagebox.showinfo("No Results", "No matching resources found.")
                return

            for r in results:
                tree.insert("", tk.END, values=(
                    r.get("resource_id"), r.get("name"), r.get("category"),
                    r.get("location"), r.get("quantity"), r.get("condition"),
                    r.get("availability")
                ))

        ttk.Button(search_frame, text="Search", command=do_search).grid(row=0, column=4, padx=10)

    def _show_check_availability(self):
        self._clear_content()
        frame = ttk.LabelFrame(self.content_frame, text="Check Resource Availability", padding=15)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        row = 0
        ttk.Label(frame, text="Resource:").grid(row=row, column=0, sticky=tk.W, pady=3)
        resource_ids = [f"{r.get('resource_id')} - {r.get('name')}" for r in self.resources]
        res_var = tk.StringVar()
        ttk.Combobox(frame, textvariable=res_var, values=resource_ids, width=35, state="readonly").grid(row=row, column=1, pady=3, padx=5)
        row += 1

        ttk.Label(frame, text="Date (YYYY-MM-DD):").grid(row=row, column=0, sticky=tk.W, pady=3)
        date_var = tk.StringVar(value=datetime.now().strftime(DATE_FORMAT))
        ttk.Entry(frame, textvariable=date_var, width=37).grid(row=row, column=1, pady=3, padx=5)
        row += 1

        ttk.Label(frame, text="Start Time (HH:MM):").grid(row=row, column=0, sticky=tk.W, pady=3)
        start_var = tk.StringVar(value="09:00")
        ttk.Entry(frame, textvariable=start_var, width=37).grid(row=row, column=1, pady=3, padx=5)
        row += 1

        ttk.Label(frame, text="End Time (HH:MM):").grid(row=row, column=0, sticky=tk.W, pady=3)
        end_var = tk.StringVar(value="10:00")
        ttk.Entry(frame, textvariable=end_var, width=37).grid(row=row, column=1, pady=3, padx=5)
        row += 1

        ttk.Label(frame, text="Quantity:").grid(row=row, column=0, sticky=tk.W, pady=3)
        qty_var = tk.StringVar(value="1")
        ttk.Entry(frame, textvariable=qty_var, width=37).grid(row=row, column=1, pady=3, padx=5)
        row += 1

        result_label = ttk.Label(frame, text="", font=("Segoe UI", 11))
        result_label.grid(row=row + 1, column=0, columnspan=2, pady=10)

        def do_check():
            res_sel = res_var.get()
            if not res_sel:
                messagebox.showerror("Error", "Please select a resource.")
                return
            resource_id = res_sel.split(" - ")[0].strip()
            available, msg = check_availability(
                self.resources, self.bookings, resource_id,
                date_var.get().strip(), start_var.get().strip(),
                end_var.get().strip(), qty_var.get().strip()
            )
            if available:
                result_label.config(text=f"AVAILABLE: {msg}", foreground="green")
            else:
                result_label.config(text=f"NOT AVAILABLE: {msg}", foreground="red")

        ttk.Button(frame, text="Check Availability", command=do_check, style="Accent.TButton").grid(row=row, column=0, columnspan=2, pady=10)

    def _show_cancel_booking(self):
        self._clear_content()
        frame = ttk.LabelFrame(self.content_frame, text="Cancel Booking", padding=15)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        active_bookings = [b for b in self.bookings if b.get("status") in ACTIVE_STATUSES]

        if not active_bookings:
            ttk.Label(frame, text="No active bookings to cancel.", font=("Segoe UI", 11)).pack(pady=20)
            return

        booking_display = [f"{b.get('booking_id')} - {b.get('resource_id')} ({b.get('booking_date')} {b.get('start_time')}-{b.get('end_time')})" for b in active_bookings]

        ttk.Label(frame, text="Select Booking:").grid(row=0, column=0, sticky=tk.W, pady=3)
        bk_var = tk.StringVar()
        ttk.Combobox(frame, textvariable=bk_var, values=booking_display, width=50, state="readonly").grid(row=0, column=1, pady=3, padx=5)

        def submit():
            sel = bk_var.get()
            if not sel:
                messagebox.showerror("Error", "Please select a booking.")
                return
            booking_id = sel.split(" - ")[0].strip()
            success, message = cancel_booking(self.bookings, booking_id, self.resources)
            if success:
                if not self._save_all_data():
                    return
                messagebox.showinfo("Success", message)
                self._show_cancel_booking()
            else:
                messagebox.showerror("Error", message)

        ttk.Button(frame, text="Cancel Booking", command=submit, style="Accent.TButton").grid(row=1, column=0, columnspan=2, pady=15)

    def _show_display_bookings(self):
        self._clear_content()
        frame = ttk.LabelFrame(self.content_frame, text="Display Bookings", padding=10)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        filter_frame = ttk.Frame(frame)
        filter_frame.pack(fill=tk.X, pady=5)

        ttk.Label(filter_frame, text="Filter by User:").pack(side=tk.LEFT, padx=5)
        user_ids = ["All"] + [f"{u.get('user_id')} - {u.get('name')}" for u in self.users]
        user_var = tk.StringVar(value="All")
        ttk.Combobox(filter_frame, textvariable=user_var, values=user_ids, width=30, state="readonly").pack(side=tk.LEFT, padx=5)

        cols = ("ID", "User", "Resource", "Date", "Start", "End", "Qty", "Purpose", "Status")
        tree_frame = ttk.Frame(frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=16)
        col_widths = {"ID": 70, "User": 70, "Resource": 70, "Date": 90, "Start": 70, "End": 70, "Qty": 40, "Purpose": 150, "Status": 80}
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=col_widths.get(col, 80), minwidth=40)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        def refresh():
            for item in tree.get_children():
                tree.delete(item)
            sel = user_var.get()
            if sel == "All":
                data = sorted(self.bookings, key=lambda x: (x.get("booking_date", ""), x.get("start_time", "")))
            else:
                uid = sel.split(" - ")[0].strip()
                data = display_user_bookings(self.bookings, uid)

            if not data:
                return

            for b in data:
                tree.insert("", tk.END, values=(
                    b.get("booking_id"), b.get("user_id"), b.get("resource_id"),
                    self._format_date(b.get("booking_date")),
                    self._format_time(b.get("start_time")),
                    self._format_time(b.get("end_time")),
                    b.get("quantity_requested"), b.get("purpose"), b.get("status")
                ))

        ttk.Button(filter_frame, text="Refresh", command=refresh).pack(side=tk.LEFT, padx=10)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=8)

        def do_delete():
            selected = tree.selection()
            if not selected:
                messagebox.showinfo("Info", "Select a booking to delete.")
                return
            vals = tree.item(selected[0], "values")
            bid = vals[0]
            if not messagebox.askyesno("Confirm", f"Permanently delete booking {bid}?"):
                return
            ok, msg = delete_booking(self.bookings, bid, self.resources)
            if ok:
                if not self._save_all_data():
                    return
                messagebox.showinfo("Deleted", msg)
                refresh()
            else:
                messagebox.showerror("Error", msg)

        ttk.Button(btn_frame, text="Delete Selected Booking", command=do_delete, style="Accent.TButton").pack(side=tk.RIGHT, padx=5)

        refresh()

    def _show_update_status(self):
        self._clear_content()
        frame = ttk.LabelFrame(self.content_frame, text="Update Booking Status", padding=15)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        booking_display = [f"{b.get('booking_id')} - {b.get('status')} ({b.get('booking_date')})" for b in self.bookings]

        if not booking_display:
            ttk.Label(frame, text="No bookings available.", font=("Segoe UI", 11)).pack(pady=20)
            return

        ttk.Label(frame, text="Select Booking:").grid(row=0, column=0, sticky=tk.W, pady=3)
        bk_var = tk.StringVar()
        ttk.Combobox(frame, textvariable=bk_var, values=booking_display, width=45, state="readonly").grid(row=0, column=1, pady=3, padx=5)

        ttk.Label(frame, text="New Status:").grid(row=1, column=0, sticky=tk.W, pady=3)
        status_var = tk.StringVar()
        allowed_statuses = ["Confirmed", "Pending", "Cancelled", "Completed"]
        ttk.Combobox(frame, textvariable=status_var, values=allowed_statuses, width=28, state="readonly").grid(row=1, column=1, pady=3, padx=5)

        def submit():
            sel = bk_var.get()
            new_status = status_var.get()
            if not sel or not new_status:
                messagebox.showerror("Error", "Please select a booking and a new status.")
                return
            booking_id = sel.split(" - ")[0].strip()
            success, message = update_booking_status(
                self.bookings, self.resources, self.users, booking_id, new_status
            )
            if success:
                if not self._save_all_data():
                    return
                messagebox.showinfo("Success", message)
                self._show_update_status()
            else:
                messagebox.showerror("Error", message)

        ttk.Button(frame, text="Update Status", command=submit, style="Accent.TButton").grid(row=2, column=0, columnspan=2, pady=15)

    def _show_generate_report(self):
        self._clear_content()
        frame = ttk.LabelFrame(self.content_frame, text="Generate Report", padding=15)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        filter_frame = ttk.Frame(frame)
        filter_frame.pack(fill=tk.X, pady=5)

        ttk.Label(filter_frame, text="Filter:").pack(side=tk.LEFT, padx=5)
        filter_type_var = tk.StringVar(value="All")
        ttk.Combobox(filter_frame, textvariable=filter_type_var, values=["All", "Daily", "Monthly"], width=10, state="readonly").pack(side=tk.LEFT, padx=5)

        ttk.Label(filter_frame, text="Value (YYYY-MM-DD or YYYY-MM):").pack(side=tk.LEFT, padx=5)
        filter_val_var = tk.StringVar()
        ttk.Entry(filter_frame, textvariable=filter_val_var, width=15).pack(side=tk.LEFT, padx=5)

        text_widget = tk.Text(frame, wrap=tk.WORD, font=("Consolas", 10), height=25)
        text_scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=text_scroll.set)
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=10)
        text_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=10)

        def generate():
            ft = filter_type_var.get()
            fv = filter_val_var.get().strip()

            valid, err_msg = validate_report_filter(ft, fv)
            if not valid:
                messagebox.showerror("Filter Error", err_msg)
                return

            date_f = fv if ft == "Daily" and fv else None
            month_f = fv if ft == "Monthly" and fv else None

            report = generate_resource_report(self.resources, self.bookings, self.users, date_f, month_f)

            report_text = format_report_text(report)
            text_widget.delete("1.0", tk.END)
            text_widget.insert(tk.END, report_text)

            if date_f:
                report_filename = f"report_daily_{date_f}.txt"
            elif month_f:
                report_filename = f"report_monthly_{month_f}.txt"
            else:
                report_filename = "report_full_overview.txt"
            try:
                filepath = save_generated_report(report, report_filename)
            except (OSError, TypeError, ValueError) as error:
                messagebox.showerror("Report Save Error", f"The report was generated but could not be saved: {error}")
                return
            messagebox.showinfo("Report Saved", f"Report saved to:\n{filepath}")

        ttk.Button(filter_frame, text="Generate", command=generate).pack(side=tk.LEFT, padx=10)

    def _show_statistics(self):
        self._clear_content()
        frame = ttk.LabelFrame(self.content_frame, text="Booking Statistics", padding=15)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        stats = display_statistics(self.resources, self.bookings, self.users)

        text_widget = tk.Text(frame, wrap=tk.WORD, font=("Consolas", 11), height=25)
        text_widget.pack(fill=tk.BOTH, expand=True)

        lines = []
        lines.append("=" * 50)
        lines.append("BOOKING STATISTICS")
        lines.append("=" * 50)
        lines.append(f"Total Resources: {stats.get('total_resources', 0)}")
        lines.append(f"Total Users: {stats.get('total_users', 0)}")
        lines.append(f"Total Bookings: {stats.get('total_bookings', 0)}")
        lines.append("-" * 50)
        lines.append(f"Total Booking Hours (NumPy): {stats.get('total_booking_hours', 0):.2f}")
        lines.append(f"Average Booking Duration (NumPy): {stats.get('average_booking_duration', 0):.2f} hours")
        lines.append(f"Max Booking Duration (NumPy): {stats.get('max_booking_duration', 0):.2f} hours")
        lines.append(f"Min Booking Duration (NumPy): {stats.get('min_booking_duration', 0):.2f} hours")
        std_val = stats.get("std_dev_booking_duration", "N/A")
        if isinstance(std_val, float):
            lines.append(f"Std Dev of Duration (SciPy): {std_val:.2f} hours")
        else:
            lines.append(f"Std Dev of Duration (SciPy): {std_val}")
        lines.append("-" * 50)
        lines.append(f"Avg Resource Usage (NumPy): {stats.get('avg_resource_usage', 0):.2f}")
        lines.append(f"Max Resource Usage (NumPy): {stats.get('max_resource_usage', 0)}")
        lines.append(f"Min Resource Usage (NumPy): {stats.get('min_resource_usage', 0)}")
        lines.append("-" * 50)
        lines.append("Bookings by Status:")
        for status, count in stats.get("bookings_by_status", {}).items():
            lines.append(f"  {status}: {count}")
        lines.append("=" * 50)

        text_widget.insert(tk.END, "\n".join(lines))
        text_widget.config(state=tk.DISABLED)

    def _generate_graphs(self):
        if not self.bookings:
            messagebox.showinfo("No Data", "No booking data available for graphs.")
            return
        try:
            self._clear_content()
            frame = ttk.LabelFrame(self.content_frame, text="Booking Analytics Graphs", padding=10)
            frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

            current_index = [0]
            canvas_holder = [None]
            toolbar_holder = [None]

            nav_frame = ttk.Frame(frame)
            nav_frame.pack(fill=tk.X, pady=(0, 5))

            prev_btn = ttk.Button(nav_frame, text="\u25C0  Previous", style="Nav.TButton")
            prev_btn.pack(side=tk.LEFT, padx=5)

            graph_label = ttk.Label(nav_frame, text="", style="Heading.TLabel")
            graph_label.pack(side=tk.LEFT, expand=True)

            next_btn = ttk.Button(nav_frame, text="Next  \u25B6", style="Nav.TButton")
            next_btn.pack(side=tk.RIGHT, padx=5)

            counter_label = ttk.Label(nav_frame, text="", font=("Segoe UI", 9))
            counter_label.pack(side=tk.RIGHT, padx=10)

            chart_frame = ttk.Frame(frame)
            chart_frame.pack(fill=tk.BOTH, expand=True)

            def show_graph(idx):
                current_index[0] = idx

                if toolbar_holder[0]:
                    toolbar_holder[0].destroy()
                if canvas_holder[0]:
                    canvas_holder[0].get_tk_widget().destroy()

                fig = create_single_graph(self.resources, self.bookings, idx)

                canvas = FigureCanvasTkAgg(fig, master=chart_frame)
                canvas.draw()

                toolbar = NavigationToolbar2Tk(canvas, chart_frame)
                toolbar.update()
                toolbar.pack(side=tk.BOTTOM, fill=tk.X)

                canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

                canvas_holder[0] = canvas
                toolbar_holder[0] = toolbar

                graph_label.config(text=GRAPH_TITLES[idx])
                counter_label.config(text=f"{idx + 1} / {len(GRAPH_TITLES)}")
                prev_btn.config(state=tk.NORMAL if idx > 0 else tk.DISABLED)
                next_btn.config(state=tk.NORMAL if idx < len(GRAPH_TITLES) - 1 else tk.DISABLED)

            def go_prev():
                if current_index[0] > 0:
                    show_graph(current_index[0] - 1)

            def go_next():
                if current_index[0] < len(GRAPH_TITLES) - 1:
                    show_graph(current_index[0] + 1)

            prev_btn.config(command=go_prev)
            next_btn.config(command=go_next)

            show_graph(0)
        except Exception as e:
            messagebox.showerror("Graph Error", f"Could not generate graphs: {e}")

    def _exit_app(self):
        if not self._save_all_data():
            return
        self.root.quit()
        self.root.destroy()
