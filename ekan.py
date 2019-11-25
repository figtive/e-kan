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
LCD_WIDTH = 240
LCD_HEIGHT = 360

root = None
canvas = None

labels = {}
text_vars = {}
buttons = {}

pump_state = False

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

    text_vars["date_time"].set(f"{datetime.datetime.now():%d/%m %H:%M}")

    text_vars["ap_client"].set(client_count)

    text_vars["water_temp"].set("%.1f" % water_temperature_value + " °C")
    label_color(labels["water_temp"], water_temperature_value, 30, 24)

    set_theme(light_value)
    set_light(light_value)

    text_vars["ambient_temp"].set("%.1f" % ambient_temperature_value + " °C")
    label_color(labels["ambient_temp"], ambient_temperature_value, 30, 24)

    text_vars["ambient_hum"].set("%.1f" % ambient_humidity_value + " hum")
    label_color(labels["ambient_temp"], ambient_humidity_value, 30, 24)

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
    return float(value) / 1000


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


def set_light(value):
    GPIO.output(LIGHT_RELAY_PIN, 0 if value else 1)


def feed():
    servo.ChangeDutyCycle(SERVO_MAX)
    time.sleep(1.3)
    servo.ChangeDutyCycle(SERVO_RESTING)
    time.sleep(2)
    servo.ChangeDutyCycle(0)


def signal_handler(signal, frame):
    GPIO.cleanup()
    sys.exit(0)


def setup_lcd(root):
    global ambient_temperature, ambient_humidity, water_temperature, water_temperature_label, date_time_label, ap_client, canvas

    root.attributes("-fullscreen", True)
    root.bind("<1>", root.quit())
    root.configure(bg="black")

    canvas = tk.Canvas(root, width=LCD_WIDTH, height=LCD_HEIGHT, bg="black")
    canvas.place(x=0, y=0)

    labels["title"] = Label(root, fg="white", bg="black", text="E-Kan", font=("Futura", 25, "bold italic"))
    labels["title"].place(x=2, y=0)

    text_vars["water_temp"] = StringVar()
    text_vars["water_temp"].set("00.0 °C")
    labels["water_temp"] = Label(root, fg="white", bg="black", textvariable=text_vars["water_temp"], font=("Helvetica", 20))
    labels["water_temp"].place(x=2, y=50)

    text_vars["date_time"] = StringVar()
    text_vars["date_time"].set("dd/mm 00:00")
    labels["date_time"] = Label(root, textvariable=text_vars["date_time"], fg="white", bg="black", font=("helvetica", 12))
    labels["date_time"].place(x=2, y=80)

    text_vars["ap_client"] = StringVar()
    text_vars["ap_client"].set("0")
    labels["ap_client"] = Label(root, fg="white", bg="black", textvariable=text_vars["ap_client"], font=("Helvetica", 20))
    labels["ap_client"].place(x=2, y=100)

    buttons["reboot"] = Button(root, text="Reboot", command=reboot)
    buttons["reboot"].place(x=2, y=130)

    buttons["pump"] = Button(root, text="Toggle Pump", command=toggle_pump)
    buttons["pump"].place(x=2, y=160)

    text_vars["ambient_hum"] = StringVar()
    text_vars["ambient_hum"].set("00.0 hum")
    labels["ambient_hum"] = Label(root, fg="white", bg="black", textvariable=text_vars["ambient_hum"], font=("Helvetica", 20))
    labels["ambient_hum"].place(x=2, y=200)

    text_vars["ambient_temp"] = StringVar()
    text_vars["ambient_temp"].set("00.0 °C")
    labels["ambient_temp"] = Label(root, fg="white", bg="black", textvariable=text_vars["ambient_temp"], font=("Helvetica", 20))
    labels["ambient_temp"].place(x=2, y=230)

    buttons["feed"] = Button(root, text="Feed", command=feed)
    buttons["feed"].place(x=2, y=260)


def set_theme(white):
    bg = "white" if not white else "black"
    fg = "white" if white else "black"
    for label in labels:
        if "temp" not in label:
            labels[label].configure(fg=fg)
        labels[label].configure(bg=bg)
    canvas.configure(bg=bg)
    root.configure(bg=bg)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    main()
