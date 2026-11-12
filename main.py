import tkinter as tk
from app.gui import CampusBookingApp


def main():
    root = tk.Tk()
    app = CampusBookingApp(root)
    if app.ready:
        root.mainloop()


if __name__ == "__main__":
    main()

