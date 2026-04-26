from flask import Flask, request, jsonify
import RPi.GPIO as GPIO

app = Flask(__name__)
GPIO.setmode(GPIO.BCM)
GPIO.setup(18, GPIO.OUT)
pwm = GPIO.PWM(18, 1000)
pwm.start(0)


@app.route('/brightness', methods = ['POST'])
def set_brightness():
	data = request.json
	level = int(data.get('brightness', 0))
	level = max(0, min(100, level))
	pwm.ChangeDutyCycle(level)
	return jsonify({"status": "ok", "brightness": level})

@app.route('/status', methods=['GET'])
def status():
	return jsonify({"status": "running"})


if __name__ == '__main__':
	try:
		app.run(host='0.0.0.0', port = 5000)
	except:
		pwm.stop()
		GPIO.cleanup()
