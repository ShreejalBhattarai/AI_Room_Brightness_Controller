import requests
import speech_recognition as sr
import json
import re
import os
import time

PI_IP = "192.168.1.115"
PI_PORT = 5000
OLLAMA_MODEL = "mistral"

def speak(text):
    os.system(f'say "{text}"')

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

def listen():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print(" Listening... (speak now)")
        r.adjust_for_ambient_noise(source, duration=1)
        audio = r.listen(source, timeout=5)
    try:
        text = r.recognize_google(audio)
        print(f"  You said: {text}")
        return text
    except sr.UnknownValueError:
        print(" Could not understand audio")
        return None
    except sr.RequestError:
        print(" Google Speech Recognition unavailable")
        return None

def ask_ollama(user_input):
    prompt = f"""
You are an LED brightness controller. Follow instructions EXACTLY.
The user said: "{user_input}"

Rules:
- If single brightness: {{"brightness": X}} where X is EXACTLY what user said
- If multiple levels: {{"brightness_list": [X, Y, Z]}} with EXACTLY the number of steps user asked for
- List order must match user's direction (off to bright = low to high, bright to off = high to low)
- All values integers 0-100. 0=off, 100=full brightness, 50=half
- No markdown, no backticks, no explanation. Raw JSON only.

Examples:
"50%" -> {{"brightness": 50}}
"3 levels off to bright" -> {{"brightness_list": [0, 50, 100]}}
"4 levels bright to dim" -> {{"brightness_list": [100, 66, 33, 0]}}
"turn off" -> {{"brightness": 0}}
"full brightness" -> {{"brightness": 100}}
"""
    response = requests.post("http://localhost:11434/api/generate", json={
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False
    })
    return response.json()["response"].strip()

def extract_brightness(ai_response):
    clean = re.sub(r"```[a-zA-Z]*\n?", "", ai_response)
    clean = clean.replace("```", "").strip()
    match = re.search(r"\{.*\}", clean, re.DOTALL)
    if not match:
        raise ValueError("No JSON found in response")
    return json.loads(match.group())

def handle_response(data):
    if "brightness_list" in data:
        levels = data["brightness_list"]
        print(f"  Running sequence: {levels}")
        speak("Running light sequence")
        for level in levels:
            level = max(0, min(100, int(level)))
            set_brightness(level)
            print(f"  💡 Brightness → {level}%")
            time.sleep(1)
        speak("Sequence complete")
        print()
    elif "brightness" in data:
        level = max(0, min(100, int(data["brightness"])))
        set_brightness(level)
        print(f" Brightness set to {level}%\n")
        speak(f"LED set to {level} percent")

print("🎤 Manual Mode")
print("   Speak your commands after pressing Enter")
print("   Say 'quit' to exit\n")
speak("Manual mode activated")

while True:
    input("  Press Enter to speak...")
    text = listen()

    if not text:
        continue

    if text.lower() in ("quit", "exit"):
        speak("Goodbye")
        break

    try:
        ai_raw = ask_ollama(text)
        print(f"  AI interpreted: {ai_raw}")
        data = extract_brightness(ai_raw)
        handle_response(data)
    except Exception as e:
        print(f" Error: {e}\n")
