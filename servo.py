import RPi.GPIO as GPIO
import time

servoPIN = 14
GPIO.setmode(GPIO.BCM)
GPIO.setup(servoPIN, GPIO.OUT)

p = GPIO.PWM(servoPIN, 50)
p.start(0) 

p.ChangeDutyCycle(12.5)
time.sleep(1)
p.ChangeDutyCycle(0)

try:
  while True:
    time.sleep(1)
    p.ChangeDutyCycle(5)
    time.sleep(0.8)
    p.ChangeDutyCycle(12.5)
    time.sleep(1)
    p.ChangeDutyCycle(0)
except KeyboardInterrupt:
  p.stop()
  GPIO.cleanup()

