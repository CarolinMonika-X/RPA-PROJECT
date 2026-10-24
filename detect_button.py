
import os
import cv2
import pyautogui
import numpy as np

TEMPLATE_PATH = "templates/save_employee.png"
OUTPUT_PATH = "results/detected_button.png"
THRESHOLD = 0.80

if not os.path.exists(TEMPLATE_PATH):
    raise FileNotFoundError(
        "Button template not found. Run capture_template.py first."
    )

# Load the saved reference image
template = cv2.imread(TEMPLATE_PATH)

if template is None:
    raise ValueError("Could not load the button template.")

template_height, template_width = template.shape[:2]

# Capture the current screen
screenshot = pyautogui.screenshot()
screen = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

# Match the template against the screenshot
result = cv2.matchTemplate(
    screen,
    template,
    cv2.TM_CCOEFF_NORMED
)

_, max_confidence, _, max_location = cv2.minMaxLoc(result)

print(f"Detection confidence: {max_confidence:.2%}")

if max_confidence >= THRESHOLD:
    x, y = max_location

    # Mark the detected button
    cv2.rectangle(
        screen,
        (x, y),
        (x + template_width, y + template_height),
        (0, 255, 0),
        3
    )

    cv2.putText(
        screen,
        f"Save Employee: {max_confidence:.2f}",
        (x, max(25, y - 10)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 0),
        2
    )

    os.makedirs("results", exist_ok=True)
    cv2.imwrite(OUTPUT_PATH, screen)

    print(f"Button detected at x={x}, y={y}")
    print(f"Annotated screenshot saved: {OUTPUT_PATH}")
else:
    print("Button not detected confidently.")
    print("Check the application window and saved template.")
