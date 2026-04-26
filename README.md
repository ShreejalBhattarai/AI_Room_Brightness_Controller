# AI Room Brightness Controller 

Control a Raspberry Pi 3B+ LED using voice commands powered by a local AI model, or automatically via Mac camera brightness detection. Everything runs locally.

---

## Table of Contents
1. [Project Overview](#project-overview)
2. [Hardware Setup](#hardware-setup)
3. [Architecture](#architecture)
4. [Part 1: Raspberry Pi Setup](#part-1-raspberry-pi-setup)
5. [Part 2: Mac Setup](#part-2-mac-setup)
6. [Part 3: Running the Project](#part-3-running-the-project)
7. [File Structure](#file-structure)
8. [Technical Details](#technical-details)

---

## Project Overview

This project connects a Mac running a local LLM (Mistral via Ollama) to a Raspberry Pi 3B+ over WiFi. You can:

- **Manual Mode** — speak natural language commands ("make it really bright", "dim it a little") and the AI interprets them and adjusts the LED brightness
- **Automatic Mode** — the Mac camera continuously reads room brightness and automatically adjusts the LED inversely (dark room = bright LED, bright room = dim LED)

---

## Hardware Setup

### Components
- Raspberry Pi 3B+ (Broadcom BCM2837B0, Cortex-A53, ARMv7, 1GB LPDDR2)
- 1x LED
- 1x 330Ω resistor 
- 2x jumper wires
- MacBook Air (Mac camera used for automatic mode)

### Wiring

```
Pi GPIO18 (Pin 12) → 330Ω resistor → LED long leg (+) → LED short leg (-) → Pi GND (Pin 14)
```

### Pin Reference
```
[Pin 11 - GP17]  [Pin 12 - GP18]  ← GPIO18 (PWM signal to LED)
[Pin 13 - GP27]  [Pin 14 - GND ]  ← Ground
```

### Why a resistor?
The LED would draw too much current without it and burn out. The 330Ω resistor limits current to a safe level.

### Why GPIO18?
GPIO18 is one of the Pi's hardware PWM pins. PWM (Pulse Width Modulation) rapidly switches the pin on and off to simulate variable brightness — at 75% duty cycle the LED appears 75% bright.

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│                    MacBook Air                  │
│                                                 │
│  control.py → manual.py  → Ollama (Mistral)     │
│            ↘ automatic.py → OpenCV (camera)     │
│                    │                            │
│            HTTP POST /brightness                │
└────────────────────┼────────────────────────────┘
                     │ WiFi (same network)
┌────────────────────┼────────────────────────────┐
│           Raspberry Pi 3B+                      │
│                    │                            │
│            led_server.py (Flask)                │
│                    │                            │
│            RPi.GPIO (PWM)                       │
│                    │                            │
│            GPIO18 → LED                         │
└─────────────────────────────────────────────────┘
```

---

## Part 1: Raspberry Pi Setup

All Pi steps were done via SSH from Mac terminal and all files were created using `nano`.

### 1.1 Enable SSH on Pi

SSH was enabled using `raspi-config` directly on the Pi:

```bash
sudo raspi-config
# Interface Options → SSH → Enable → Finish
```

### 1.2 Find Pi IP Address

```bash
hostname -I
# Returns something like: 192.168.1.xxx
```

### 1.3 SSH from Mac

```bash
ssh shreejal17@192.168.1.xxx
```

### 1.4 Create Python Virtual Environment on Pi

The Pi was running Raspberry Pi OS Bookworm which enforces externally managed Python environments. Installing packages system-wide with `pip3` throws:

```
error: externally-managed-environment
```

To work around this cleanly, a virtual environment was created:

```bash
# Create the virtual environment
python3 -m venv ~/led_env

# Activate it (must do this every session)
source ~/led_env/bin/activate

# Prompt changes to show:
# (led_env) shreejal17@shreejal:~ $
```

### 1.5 Install Flask and RPi.GPIO

Inside the activated venv:

```bash
pip install flask RPi.GPIO
```

- **Flask** — lightweight Python web framework used to create a REST API on the Pi
- **RPi.GPIO** — library to control the Pi's GPIO pins from Python

### 1.6 Create the Flask Server

The file was created using `nano` inside the venv directory:

```bash
nano ~/led_server.py
```

The server exposes two endpoints:
- `GET /status` — health check
- `POST /brightness` — accepts JSON `{"brightness": 0-100}` and sets PWM duty cycle

After writing the file, it was saved with `Ctrl + O`, confirmed with `Enter`, and exited with `Ctrl + X`.

### 1.7 GPIO and PWM Configuration

Inside `led_server.py`, GPIO was configured as follows:

```python
import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)      # Use BCM pin numbering (GPIO18, not physical pin 12)
GPIO.setup(18, GPIO.OUT)    # Set GPIO18 as output
pwm = GPIO.PWM(18, 1000)    # 1000Hz PWM frequency on GPIO18
pwm.start(0)                # Start at 0% duty cycle (LED off)
```

**BCM vs BOARD numbering:**
- `GPIO.BCM` uses the Broadcom chip numbering (GPIO18)
- `GPIO.BOARD` uses the physical pin number (Pin 12)
- BCM was used because it matches standard Pi pinout diagrams

**PWM frequency:**
- 1000Hz means the pin switches on/off 1000 times per second
- At this frequency the LED appears to change brightness smoothly to the human eye
- `ChangeDutyCycle(75)` means the pin is HIGH for 75% of each cycle = 75% brightness

### 1.8 Run the Server

```bash
source ~/led_env/bin/activate
python ~/led_server.py
```

Server output:
```
* Running on http://0.0.0.0:5000
```

`host='0.0.0.0'` means the server listens on all network interfaces — not just localhost — so the Mac can reach it over WiFi on port 5000.

### 1.9 Auto-start on Boot (optional)

To start the Flask server automatically when the Pi boots:

```bash
crontab -e
# Add this line:
@reboot source /home/shreejal17/led_env/bin/activate && python /home/shreejal17/led_server.py &
```

---

## Part 2: Mac Setup

All Mac steps were done in Terminal (zsh) and files were created using `nano`.

### 2.1 Install Ollama

Ollama is a tool that runs large language models locally on your Mac. Downloaded and installed from [ollama.com](https://ollama.com).

```bash
# Verify installation
ollama --version

# Start the Ollama server
ollama serve
# Runs on http://localhost:11434
```

### 2.2 Download Mistral Model

Several models were tested:

```bash
# First tried phi3 — too small, poor instruction following
ollama pull phi3

# Deleted phi3
ollama rm phi3:latest

# Downloaded mistral — much better instruction following
ollama pull mistral
```

**Why Mistral over phi3:**
- phi3 (3.8B parameters) struggled to follow precise JSON formatting instructions
- Mistral (7B parameters) follows instructions reliably and outputs clean JSON
- Mistral is fast enough to run on MacBook Air without GPU

### 2.3 Create Python Virtual Environment on Mac

A separate venv was created on the Mac for the controller scripts:

```bash
# Create venv
python3 -m venv ~/voice_led_env

# Activate it
source ~/voice_led_env/bin/activate

# Prompt changes to show:
# (voice_led_env) (base) shreejalbhattarai@MacBookAir ~ %
```

Note: The Mac was also running conda (base environment). Both conda and venv were active simultaneously — `voice_led_env` took precedence for package resolution.

### 2.4 Install Mac Dependencies

```bash
pip install SpeechRecognition pyaudio requests opencv-python
```

If `pyaudio` fails due to missing PortAudio:
```bash
brew install portaudio
pip install pyaudio
```

**Libraries used:**
- `SpeechRecognition` — captures audio from microphone and transcribes via Google Speech Recognition API
- `pyaudio` — low level audio I/O library required by SpeechRecognition to access the microphone
- `requests` — sends HTTP POST requests to the Pi Flask server
- `opencv-python` — accesses Mac camera and processes frames to calculate room brightness

### 2.5 Text-to-Speech Engine

**Mac's built-in `say` command** was used for text-to-speech — no extra library needed:

```python
import os
os.system('say "LED set to 75 percent"')
```

The `say` command is part of macOS and uses the system's built-in speech synthesis. It was called via Python's `os.system()`. No installation required.

To list available voices:
```bash
say -v '?'
```

To use a specific voice:
```python
os.system('say -v Samantha "LED activated"')
```

### 2.6 Create Project Files

All files were created using `nano` in the project directory:

```bash
mkdir ~/Desktop/raspberry_pi_mistral_project
cd ~/Desktop/raspberry_pi_mistral_project

nano control.py
nano manual.py
nano automatic.py
```

Each file was saved with `Ctrl + O` → `Enter` and exited with `Ctrl + X`.

### 2.7 Sensitive Configuration

The Pi's IP address was stored separately in `config.py` which is excluded from version control:

```bash
nano config.py
```

```python
PI_IP = "YOUR_PI_IP_HERE"
PI_PORT = 5000
OLLAMA_MODEL = "mistral"
```

```bash
echo "config.py" >> .gitignore
```

A `config.example.py` is included in the repo as a template.

---

## Part 3: Running the Project

### 3.1 Start Flask Server on Pi

SSH into Pi and run:

```bash
ssh shreejal17@<pi-ip>
source ~/led_env/bin/activate
python ~/led_server.py
```

Leave this running.

### 3.2 Test Connection from Mac

```bash
curl http://<pi-ip>:5000/status
# Expected: {"status": "running"}

curl -X POST http://<pi-ip>:5000/brightness \
  -H "Content-Type: application/json" \
  -d '{"brightness": 50}'
# Expected: {"status": "ok", "brightness": 50}
```

### 3.3 Start Ollama on Mac

```bash
ollama serve
```

### 3.4 Run the Controller

```bash
cd ~/Desktop/raspberry_pi_mistral_project
source ~/voice_led_env/bin/activate
python control.py
```

```
╔══════════════════════════════════╗
║        LED AI Controller         ║
║                                  ║
║  1 → Manual Mode (voice)         ║
║  2 → Automatic Mode (camera)     ║
║  q → Quit                        ║
╚══════════════════════════════════╝

Select mode (1/2/q):
```

### 3.5 Manual Mode

Select `1`. Press Enter when prompted, then speak:

```
You: make it really bright     → LED: 100%
You: dim it a little           → LED: 30%
You: give me 3 levels off to bright → LED: 0% → 50% → 100%
You: turn off                  → LED: 0%
```

The AI (Mistral via Ollama) interprets the command and returns JSON:
```json
{"brightness": 75}
```
or for sequences:
```json
{"brightness_list": [0, 50, 100]}
```

Mac speaks the response aloud using `say`.

### 3.6 Automatic Mode

Select `2`. The Mac camera captures a frame every 5 seconds, converts it to grayscale, calculates average pixel brightness (0-255), and maps it inversely to LED brightness (0-100%).

```
Dark room (low lux)  → high LED brightness
Bright room (high lux) → low LED brightness
```

Only updates LED if brightness changes by more than 5% to avoid constant flickering.

---

## File Structure

```
raspberry_pi_mistral_project/
├── control.py          # Main menu — launches manual or automatic mode
├── manual.py           # Voice + AI controlled LED (runs on Mac)
├── automatic.py        # Camera brightness controlled LED (runs on Mac)
├── led_server.py       # Flask REST API server (runs on Pi)
├── .gitignore          # Excludes config.py, venvs, cache
└── README.md           # This file
```

---

## Technical Details

### PWM Brightness Control
PWM (Pulse Width Modulation) simulates analog brightness on a digital pin. At 1000Hz with 75% duty cycle, the LED is on for 0.75ms and off for 0.25ms per millisecond — the human eye averages this as 75% brightness.

### Virtual Address to GPIO
The Flask server runs in Python userspace. `RPi.GPIO` uses `/dev/gpiomem` to memory-map GPIO registers without requiring root access.

### AI Prompt Engineering
Mistral is prompted with strict JSON-only output instructions and examples. The response is cleaned of markdown code fences using regex before JSON parsing:

```python
clean = re.sub(r"```[a-zA-Z]*\n?", "", ai_response)
match = re.search(r"\{.*\}", clean, re.DOTALL)
```

### Camera Brightness Calculation
OpenCV captures a single frame, converts BGR to grayscale, and takes the mean pixel value (0-255). This is mapped to LED brightness with an inverse linear function:

```python
led_level = 100 - int((camera_value / 255) * 100)
```

### Speech Recognition
Google's Speech Recognition API is used via the `SpeechRecognition` library. The microphone input is captured with `pyaudio`, ambient noise is calibrated for 1 second before each recording, and the audio is sent to Google's API for transcription.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `externally-managed-environment` on Pi | Use venv: `python3 -m venv ~/led_env` |
| `No module named RPi` | `pip install RPi.GPIO` inside venv |
| `raspberrypi.local` not resolving | Use IP address directly |
| Flask not reachable from Mac | Check `host='0.0.0.0'` in `led_server.py` |
| Wrong camera in automatic mode | Change `CAMERA_INDEX = 1` to `0` or `2` |
| Ollama JSON parse error | Mistral handles this better than phi3 |
| `pyaudio` install fails | `brew install portaudio` first |

---

## Dependencies

### Raspberry Pi
```
flask
RPi.GPIO
```

### Mac
```
SpeechRecognition
pyaudio
requests
opencv-python
ollama (mistral model)
```
