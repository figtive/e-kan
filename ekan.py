import datetime
import os
import random
import signal
import sys
import time
import tkinter.font
import Adafruit_DHT as dht
import RPi.GPIO as GPIO
import tkinter as tk
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
LCD_HEIGHT = 320
LED_PUMP = 5
LED_LIGHT = 6
LED_TEMP = 13
LED_FEED = 19
LED_AP = 26

root = None
canvas = None
servo = None

labels = {}
text_vars = {}
buttons = {}

pump_state = False
light_mode = 0

def main():
    global root

    root = tk.Tk()
    setup_gpio()
    setup_lcd(root)
    setup_servo()
    root.after(5000, sensor_loop)
    root.mainloop()


def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(LIGHT_SENSOR_PIN, GPIO.IN)
    GPIO.setup(LIGHT_RELAY_PIN, GPIO.OUT)
    GPIO.setup(AMBIENT_TEMPERATURE_SENSOR_PIN, GPIO.IN)
    GPIO.setup(PUMP_RELAY_PIN, GPIO.OUT)
    GPIO.setup(SERVO_PIN, GPIO.OUT)
    GPIO.setup(LED_FEED, GPIO.OUT)
    GPIO.setup(LED_LIGHT, GPIO.OUT)
    GPIO.setup(LED_PUMP, GPIO.OUT)
    GPIO.setup(LED_TEMP, GPIO.OUT)
    GPIO.setup(LED_AP, GPIO.OUT)
    GPIO.output(PUMP_RELAY_PIN, 1)

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

    text_vars["time"].set(f"{datetime.datetime.now():%H:%M}")
    text_vars["day"].set(f"{datetime.datetime.now():%a}")
    text_vars["date"].set(f"{datetime.datetime.now():%d/%m}")

    text_vars["ap_client"].set(client_count)

    text_vars["water_temp"].set("%2.1f" % water_temperature_value + " °C")
    label_color(labels["water_temp"], water_temperature_value, 30, 24, light_value)

    set_theme(light_value)
    set_light()

    text_vars["ambient_temp"].set("%2.1f" % ambient_temperature_value + " °C")
    label_color(labels["ambient_temp"], ambient_temperature_value, 30, 24, light_value)

    text_vars["ambient_hum"].set("%2.1f" % ambient_humidity_value + " %")
    label_color(labels["ambient_hum"], ambient_humidity_value, 30, 24, light_value)

    root.after(1000, sensor_loop)


def label_color(label, value, upper, lower, white):
    fg = "white" if white else "black"
    if value >= upper:
        label.configure(fg="orange")
    elif value <= lower:
        label.configure(fg="cyan")
    else:
        label.configure(fg=fg)


def get_ap_client_count():
    count =  os.popen('iw ap0 station dump | grep Station | wc -l').read()
    if int(count) > 0:
        GPIO.output(LED_AP, 1)
    else:
        GPIO.output(LED_AP, 0)
    return int(count)


def get_water_temperature():
    value = float(os.popen('cat /sys/bus/w1/devices/%s/w1_slave | tail -n1 | awk \'{print $NF}\' | sed s/t=//' % WATER_TEMPERATURE_SENSOR_ID).read())
    if value / 1000 < 25 or value/1000 > 29:
        GPIO.output(LED_TEMP, 1)
    else:
        GPIO.output(LED_TEMP, 0)
    return value / 1000


def get_ambient_temperature():
    # value = dht.read(dht.DHT11, 4)[1]
    # print(f"ambient temp {value}")
    # return value if value else 0
    return 0


def get_ambient_humidity():
    # value = dht.read(dht.DHT11, 4)[0]
    # print(f"ambient hum {value}")
    # return value if value else 0
    return 0


def get_light_value():
    return GPIO.input(LIGHT_SENSOR_PIN)


# def reboot():
#     os.popen('sudo reboot')


def toggle_pump():
    global pump_state
    pump_state = not pump_state
    GPIO.output(LED_PUMP, pump_state)
    GPIO.output(PUMP_RELAY_PIN, not pump_state)


def toggle_light_mode():
    global light_mode
    if light_mode == 0:
        light_mode += 1
    elif light_mode == 1:
        light_mode += 1
    else:
        light_mode = 0
    set_light()

def set_light():
    light = get_light_value()
    if light_mode == 0:
        GPIO.output(LIGHT_RELAY_PIN, 0 if light else 1)
        GPIO.output(LED_LIGHT, 1 if light else 0)
    elif light_mode == 1:
        GPIO.output(LIGHT_RELAY_PIN, 0)
        GPIO.output(LED_LIGHT, 1)
    else:
        GPIO.output(LIGHT_RELAY_PIN, 1)
        GPIO.output(LED_LIGHT, 0)

def feed():
    GPIO.output(LED_FEED, 1)
    servo.ChangeDutyCycle(SERVO_MAX)
    time.sleep(1.3)
    servo.ChangeDutyCycle(SERVO_RESTING)
    GPIO.output(LED_FEED, 0)
    time.sleep(2)
    servo.ChangeDutyCycle(0)

def signal_handler(signal, frame):
    GPIO.cleanup()
    sys.exit(0)

def setup_lcd(root):
    global canvas

    root.attributes("-fullscreen", True)
    root.bind("<1>", root.quit())
    root.configure(bg="black")

    canvas = tk.Canvas(root, width=LCD_WIDTH, height=LCD_HEIGHT, bg="black")
    canvas.place(x=-1, y=-1)


    labels["title"] = Label(root, fg="white", bg="black", text="E-Kan", font=("Futura", 25, "bold italic"))

    labels["water_temp_desc"] = Label(root, fg="white", bg="black", text="Water", font=("Helvetica", 11))
    text_vars["water_temp"] = StringVar()
    text_vars["water_temp"].set("00.0 °C")
    labels["water_temp"] = Label(root, fg="white", bg="black", textvariable=text_vars["water_temp"], font=("Helvetica", 20))

    text_vars["time"] = StringVar()
    text_vars["time"].set("00:00")
    labels["time"] = Label(root, textvariable=text_vars["time"], fg="white", bg="black", font=("helvetica", 30))
    text_vars["day"] = StringVar()
    text_vars["day"].set("Mon")
    labels["day"] = Label(root, textvariable=text_vars["day"], fg="white", bg="black", font=("helvetica", 12))
    text_vars["date"] = StringVar()
    text_vars["date"].set("dd/mm")
    labels["date"] = Label(root, textvariable=text_vars["date"], fg="white", bg="black", font=("helvetica", 12))

    labels["ap_client_desc"] = Label(root, fg="white", bg="black", text="AP Client", font=("Helvetica", 11))
    text_vars["ap_client"] = StringVar()
    text_vars["ap_client"].set("0")
    labels["ap_client"] = Label(root, fg="white", bg="black", textvariable=text_vars["ap_client"], font=("Helvetica", 20))

    # buttons["reboot"] = Button(root, text="Reboot", command=reboot)
    buttons["light"] = Button(root, text="Toggle Light", command=toggle_light_mode)

    buttons["pump"] = Button(root, text="Toggle Pump", command=toggle_pump)

    buttons["feed"] = Button(root, text="Feed", command=feed, width=26, height=2)

    labels["ambient_hum_desc"] = Label(root, fg="white", bg="black", text="Humidity", font=("Helvetica", 11))
    text_vars["ambient_hum"] = StringVar()
    text_vars["ambient_hum"].set("00.0 %")
    labels["ambient_hum"] = Label(root, fg="white", bg="black", textvariable=text_vars["ambient_hum"], font=("Helvetica", 20))

    labels["ambient_temp_desc"] = Label(root, fg="white", bg="black", text="Ambient", font=("Helvetica", 11))
    text_vars["ambient_temp"] = StringVar()
    text_vars["ambient_temp"].set("00.0 °C")
    labels["ambient_temp"] = Label(root, fg="white", bg="black", textvariable=text_vars["ambient_temp"], font=("Helvetica", 20))

    labels["title"].place(x=60, y=0)

    canvas.create_line(0, 45, 240, 45, fill="white")
    
    labels["water_temp_desc"].place(x=25, y=50)
    labels["water_temp"].place(x=10, y=68)
    canvas.create_line(120, 45, 120, 105, fill="white")
    labels["ambient_temp_desc"].place(x=145, y=50)
    labels["ambient_temp"].place(x=135, y=68)

    canvas.create_line(0, 105, 240, 105, fill="white")

    labels["time"].place(x=30, y=108)
    labels["day"].place(x=150, y=113)
    labels["date"].place(x=150, y=133)

    canvas.create_line(0, 163, 240, 163, fill="white")

    labels["ambient_hum_desc"].place(x=18, y=167)
    labels["ambient_hum"].place(x=15, y=185)
    canvas.create_line(120, 163, 120, 225, fill="white")
    labels["ap_client_desc"].place(x=145, y=167)
    labels["ap_client"].place(x=170, y=185)

    canvas.create_line(0, 225, 240, 225, fill="white")
    
    buttons["feed"].place(x=0, y=225)

    canvas.create_line(0, 275, 240, 275, fill="white")

    buttons["pump"].place(x=0, y=275)
    canvas.create_line(120, 275, 120, 320, fill="white")
    buttons["light"].place(x=120, y=275)
    # buttons["reboot"].place(x=2, y=130)


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
