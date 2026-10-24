
import tkinter as tk
from tkinter import messagebox
from datetime import datetime
import csv
import os

# Store employee records inside the project
RESULTS_DIR = "results"
os.makedirs(RESULTS_DIR, exist_ok=True)

CSV_FILE = os.path.join(RESULTS_DIR, "employees.csv")


def save_employee():
    employee_id = id_entry.get().strip()
    name = name_entry.get().strip()
    department = department_entry.get().strip()

    if not employee_id or not name or not department:
        messagebox.showwarning(
            "Validation Error",
            "Please fill in all employee fields."
        )
        return

    file_exists = os.path.exists(CSV_FILE)

    with open(CSV_FILE, "a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        if not file_exists:
            writer.writerow(
                ["Employee ID", "Name", "Department", "Created At"]
            )

        writer.writerow([
            employee_id,
            name,
            department,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ])

    status_label.config(text="Status: Employee saved successfully")
    messagebox.showinfo(
        "Success",
        f"Employee {name} saved successfully!"
    )


def clear_fields():
    id_entry.delete(0, tk.END)
    name_entry.delete(0, tk.END)
    department_entry.delete(0, tk.END)
    status_label.config(text="Status: Fields cleared")


# Main application window
root = tk.Tk()
root.title("Legacy Employee Management System")
root.geometry("650x430")
root.resizable(False, False)
root.configure(bg="#d4d0c8")

# Header
header = tk.Label(
    root,
    text="EMPLOYEE MANAGEMENT SYSTEM",
    font=("Arial", 16, "bold"),
    bg="#000080",
    fg="white",
    pady=12
)
header.pack(fill="x")

# Form area
form = tk.Frame(root, bg="#d4d0c8", padx=35, pady=25)
form.pack(fill="both", expand=True)

tk.Label(
    form, text="Employee ID:",
    font=("Arial", 11), bg="#d4d0c8"
).grid(row=0, column=0, sticky="w", pady=10)

id_entry = tk.Entry(form, width=35, font=("Arial", 11))
id_entry.grid(row=0, column=1, pady=10, padx=15)

tk.Label(
    form, text="Employee Name:",
    font=("Arial", 11), bg="#d4d0c8"
).grid(row=1, column=0, sticky="w", pady=10)

name_entry = tk.Entry(form, width=35, font=("Arial", 11))
name_entry.grid(row=1, column=1, pady=10, padx=15)

tk.Label(
    form, text="Department:",
    font=("Arial", 11), bg="#d4d0c8"
).grid(row=2, column=0, sticky="w", pady=10)

department_entry = tk.Entry(form, width=35, font=("Arial", 11))
department_entry.grid(row=2, column=1, pady=10, padx=15)

# Buttons
button_frame = tk.Frame(form, bg="#d4d0c8")
button_frame.grid(row=3, column=0, columnspan=2, pady=20)

save_button = tk.Button(
    button_frame,
    text="Save Employee",
    width=16,
    font=("Arial", 10, "bold"),
    command=save_employee
)
save_button.pack(side="left", padx=10)

clear_button = tk.Button(
    button_frame,
    text="Clear Fields",
    width=16,
    font=("Arial", 10),
    command=clear_fields
)
clear_button.pack(side="left", padx=10)

# Status bar
status_label = tk.Label(
    root,
    text="Status: Ready",
    anchor="w",
    relief="sunken",
    bg="#eeeeee",
    padx=10
)
status_label.pack(fill="x", side="bottom")
id_entry.focus_set()
root.mainloop()
