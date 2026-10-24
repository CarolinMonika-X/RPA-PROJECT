
import os
import time
import cv2
import pyautogui
import numpy as np

os.makedirs("screenshots", exist_ok=True)
os.makedirs("templates", exist_ok=True)

print("Keep your Employee Management System open.")
print("Make sure the Save Employee button is visible.")
print("Capturing the desktop in 5 seconds...")

time.sleep(5)

# Capture and save screenshot
screenshot = pyautogui.screenshot()
screen = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

cv2.imwrite("screenshots/desktop.png", screen)
print("Screenshot saved.")

# Select the Save Employee button
print("Drag around the Save Employee button.")
print("Press ENTER to confirm your selection.")

x, y, width, height = map(
    int,
    cv2.selectROI(
        "Select Save Employee Button",
        screen,
        showCrosshair=True,
        fromCenter=False
    )
)

cv2.destroyAllWindows()

if width == 0 or height == 0:
    print("No button selected. Please run the script again.")
    raise SystemExit(1)

# Crop and save the selected button
template = screen[y:y + height, x:x + width]

template_path = os.path.abspath("templates/save_employee.png")
success = cv2.imwrite(template_path, template)

if success:
    print("Template successfully saved:")
    print(template_path)
else:
    print("Failed to save template.")
