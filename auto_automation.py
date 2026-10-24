
import os
import time
import csv
import cv2
import pyautogui
import numpy as np
import pygetwindow as gw

APP_TITLE = "Legacy Employee Management System"
TEMPLATE_PATH = "templates/save_employee.png"
CSV_PATH = "results/employees.csv"
OUTPUT_PATH = "results/automation_result.png"

# Test record
EMPLOYEE_ID = "EMP002"
EMPLOYEE_NAME = "Automation Test"
DEPARTMENT = "IT"

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.5


def find_save_button():
    """Locate the Save Employee button using OpenCV."""

    template = cv2.imread(TEMPLATE_PATH)

    if template is None:
        raise FileNotFoundError(
            "Button template missing. Run capture_template.py first."
        )

    screenshot = pyautogui.screenshot()
    screen = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

    match = cv2.matchTemplate(
        screen, template, cv2.TM_CCOEFF_NORMED
    )

    _, confidence, _, location = cv2.minMaxLoc(match)

    print(f"Save button confidence: {confidence:.2%}")

    if confidence < 0.80:
        raise RuntimeError(
            "Save button not detected confidently. "
            "Check the window and template."
        )

    height, width = template.shape[:2]
    x, y = location

    # Save a screenshot showing the detection
    os.makedirs("results", exist_ok=True)

    cv2.rectangle(
        screen, (x, y), (x + width, y + height),
        (0, 255, 0), 3
    )

    cv2.imwrite(OUTPUT_PATH, screen)

    return x + width // 2, y + height // 2


def main():
    if not os.path.exists(TEMPLATE_PATH):
        raise FileNotFoundError(
            "Missing templates/save_employee.png"
        )

    windows = gw.getWindowsWithTitle(APP_TITLE)

    if not windows:
        raise RuntimeError(
            "Employee application is not open. Run python main.py."
        )

    app = windows[0]

    if app.isMinimized:
        app.restore()

    app.activate()
    time.sleep(1)

    # Focus was set to Employee ID in main.py
    pyautogui.write(EMPLOYEE_ID, interval=0.08)
    pyautogui.press("tab")

    pyautogui.write(EMPLOYEE_NAME, interval=0.05)
    pyautogui.press("tab")

    pyautogui.write(DEPARTMENT, interval=0.08)

    print("Employee fields filled.")

    # Detect the button from the current screen
    button_x, button_y = find_save_button()

    print(f"Clicking detected button at ({button_x}, {button_y})")

    # Ask for confirmation before clicking Save
    answer = input(
        "Review the form. Type YES to click Save Employee: "
    )

    if answer.strip().upper() != "YES":
        print("Save cancelled by user.")
        return

    # Save using the detected image location
    pyautogui.click(button_x, button_y)
    time.sleep(1)

    # The sample app displays a success dialog.
    # Press Enter to dismiss it.
    pyautogui.press("enter")
    time.sleep(1)

    # Verify the saved record in the CSV
    if not os.path.exists(CSV_PATH):
        raise RuntimeError("Employee CSV file was not created.")

    with open(CSV_PATH, newline="", encoding="utf-8") as file:
        records = list(csv.DictReader(file))

    found = any(
        row["Employee ID"] == EMPLOYEE_ID
        and row["Name"] == EMPLOYEE_NAME
        and row["Department"] == DEPARTMENT
        for row in records
    )

    if found:
        print("SUCCESS: Employee record verified in CSV.")
    else:
        print("FAILED: Employee record was not found in CSV.")


if __name__ == "__main__":
    main()
