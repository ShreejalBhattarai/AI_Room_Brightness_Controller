import cv2
import requests
import time
import numpy as np
import os

PI_IP = "192.168.1.xxx"
PI_PORT = 5000
CHECK_INTERVAL = 5
CAMERA_INDEX = 1  

def speak(text):
    os.system(f'say "{text}"')

def get_room_brightness():
    cap = cv2.VideoCapture(CAMERA_INDEX)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        print("Could not access camera")
        return None

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return np.mean(gray)

def map_brightness(camera_value):
    # Dark room = bright LED, bright room = dim LED
    return 100 - int((camera_value / 255) * 100)

def set_brightness(level):
    try:
        response = requests.post(
            f"http://{PI_IP}:{PI_PORT}/brightness",
            json={"brightness": level},
            timeout=3
        )
        return response.json()
    except Exception as e:
        print(f"Could not reach Pi: {e}")
        return None

print("📷 Automatic Mode")
print("   Dark room → bright LED")
print("   Bright room → dim LED")
print("   Press Ctrl+C to stop\n")
speak("Automatic mode activated")

last_led_level = -1

try:
    while True:
        brightness = get_room_brightness()

        if brightness is not None:
            led_level = map_brightness(brightness)

            if abs(led_level - last_led_level) > 5:
                result = set_brightness(led_level)
                if result:
                    print(f"  📷 Room: {brightness:.1f}/255 → 💡 LED: {led_level}%")
                    speak(f"Room brightness changed, LED set to {led_level} percent")
                    last_led_level = led_level
            else:
                print(f"  📷 Room: {brightness:.1f}/255 → no change needed")

        time.sleep(CHECK_INTERVAL)

except KeyboardInterrupt:
    print("\n  Stopped automatic mode")
    speak("Automatic mode stopped")
