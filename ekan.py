import datetime
import os
import signal
import sys
import time
import tkinter.font
import Adafruit_DHT as dht
import RPi.GPIO as GPIO
import tkinter as tk
from PIL import ImageTk
from tkinter import *


WATER_TEMPERATURE_SENSOR_ID = "28-031097791088"
WATER_TEMPERATURE_SENSOR_PIN = 4
AMBIENT_TEMPERATURE_SENSOR_PIN = 4
LIGHT_SENSOR_PIN = 16
LIGHT_RELAY_PIN = 20
PUMP_RELAY_PIN = 21
SERVO_PIN = 14
SERVO_RESTING = 12.5
SERVO_MAX = 6.55

root = None
water_temperature = None
ambient_temperature = None
ambient_humidity = None
ap_client = None
servo = None

water_temperature_label = None
ambient_temperature_label = None
ambient_humidity_label = None
date_time_label = None

pump_state = False
# light_state = False

def main():
    global root

    root = tk.Tk()
    setup_gpio()
    setup_lcd(root)
    setup_servo()
    root.after(500, sensor_loop)
    root.mainloop()


def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(LIGHT_SENSOR_PIN, GPIO.IN)
    GPIO.setup(LIGHT_RELAY_PIN, GPIO.OUT)
    GPIO.setup(PUMP_RELAY_PIN, GPIO.OUT)
    GPIO.setup(SERVO_PIN, GPIO.OUT)


def setup_lcd(root):
    global ambient_temperature, ambient_humidity, water_temperature, water_temperature_label, date_time_label, ap_client

    root.attributes("-fullscreen", True)
    root.bind("<1>", root.quit())
    root.configure(bg="black")

    title_label = Label(root, fg="white", bg="red", text="E-Kan", font=("Futura", 25, "bold italic"))
    title_label.place(x=2, y=0)

    water_temperature = StringVar()
    water_temperature.set("00.0 °C")
    water_temperature_label = Label(root, fg="white", bg="black", textvariable=water_temperature, font=("Helvetica", 20))
    water_temperature_label.place(x=2, y=50)

    date_time_label = Label(root, text=f"{datetime.datetime.now():%d/%m %H:%M}", fg="white", bg="black", font=("helvetica", 12))
    date_time_label.place(x=2, y=80)

    ap_client = StringVar()
    ap_client.set("0")
    ap_client_label = Label(root, fg="white", bg="black", textvariable=ap_client, font=("Helvetica", 20))
    ap_client_label.place(x=2, y=100)

    reboot_button = Button(root, text="Reboot", command=reboot)
    reboot_button.place(x=2, y=130)

    pump_button = Button(root, text="Toggle Pump", command=toggle_pump)
    pump_button.place(x=2, y=160)

    # light_button = Button(root, text="Toggle Light", command=toggle_light)
    # light_button.place(x=2, y=200)

    ambient_humidity = StringVar()
    ambient_humidity_label = Label(root, fg="white", bg="black", textvariable=ambient_humidity, font=("Helvetica", 20))
    ambient_humidity_label.place(x=2, y=200)

    ambient_temperature = StringVar()
    ambient_temperature_label = Label(root, fg="white", bg="black", textvariable=ambient_temperature, font=("Helvetica", 20))
    ambient_temperature_label.place(x=2, y=230)

    feed_button = Button(root, text="Feed", command=feed)
    feed_button.place(x=2, y=260)


def setup_servo():
    global servo

    servo = GPIO.PWM(SERVO_PIN, 50)
    servo.start(0) 
    servo.ChangeDutyCycle(SERVO_RESTING)
    time.sleep(1)
    servo.ChangeDutyCycle(0)


def sensor_loop():
    light_value = get_light_value()
    water_temperature_value = get_water_temperature()
    ambient_temperature_value = get_ambient_temperature()
    ambient_humidity_value = get_ambient_humidity()
    client_count = get_ap_client_count()

    date_time_label.configure(text=f"{datetime.datetime.now():%d/%m %H:%M}")

    ap_client.set(client_count)

    water_temperature.set("%.1f" % water_temperature_value + " °C")
    label_color(water_temperature_label, water_temperature_value, 30, 24)

    if light_value:
        root.configure(bg="black")
        set_light(False)
    else:
        root.configure(bg="white")
        set_light()

    ambient_humidity.set("%.1f" % ambient_temperature_value + " °C")

    ambient_temperature.set("%.1f" % ambient_temperature_value + " hum")

    root.after(500, sensor_loop)


def label_color(label, value, upper, lower):
    if value >= upper:
        label.configure(fg="orange")
    elif value <= lower:
        label.configure(fg="cyan")
    else:
        label.configure(fg="white")


def get_ap_client_count():
    return os.popen('iw ap0 station dump | grep Station | wc -l').read()


def get_water_temperature():
    value = os.popen('cat /sys/bus/w1/devices/%s/w1_slave | tail -n1 | awk \'{print $NF}\' | sed s/t=//' % WATER_TEMPERATURE_SENSOR_ID).read()
    return int(value) / 1000


def get_ambient_temperature():
    # value = dht.read(dht.DHT11, 4)[1]
    # print(f"ambient temp {value}")
    # return value if value else 0
    return 20


def get_ambient_humidity():
    # value = dht.read(dht.DHT11, 4)[0]
    # print(f"ambient hum {value}")
    # return value if value else 0
    return 20


def get_light_value():
    return GPIO.input(LIGHT_SENSOR_PIN)


def reboot():
    os.popen('sudo reboot')


def toggle_pump():
    global pump_state
    pump_state = not pump_state
    GPIO.output(PUMP_RELAY_PIN, pump_state)


# def toggle_light():
#     global light_state
#     light_state = not light_state
#     GPIO.output(LIGHT_RELAY_PIN, light_state)


def set_light(value=True):
    GPIO.output(LIGHT_RELAY_PIN, value)


def feed():
    servo.ChangeDutyCycle(SERVO_MAX)
    time.sleep(1.3)
    servo.ChangeDutyCycle(SERVO_RESTING)
    time.sleep(2)
    servo.ChangeDutyCycle(0)


def signal_handler(signal, frame):
    GPIO.cleanup()
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    main()
 
