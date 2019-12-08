import asyncio
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
from threading import Thread
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
AMBIENT_STATE_DELAY = 10
BUTTON_NAME = ["light", "pump", "feed", "reboot"]


class Ekan(tk.Tk):
    def __init__(self, loop, interval=1 / 120):
        super().__init__()
        self.loop = loop
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.tasks = []
        self.tasks.append(loop.create_task(self.updater(interval)))
        self.tasks.append(loop.create_task(self.sensor_loop(0.2)))

        self.canvas = None
        self.servo = None

        self.labels = {}
        self.text_vars = {}
        self.lines = []
        self.buttons = {}
        self.button_texts = {}

        self.pump_state = True
        self.light_mode = 0
        self.is_feeding = False
        self.ambient_state = False
        self.ambient_counter = 0
        self.next_feed = datetime.datetime.now() + datetime.timedelta(hours=9)

        self.sensor_values = {
            "light_value": 0,
            "water_temperature_value": .0,
            "ambient_temperature_value": .0,
            "ambient_humidity_value": .0,
            "client_count": 0
        }

        self.setup_gpio()
        self.setup_lcd()
        self.setup_servo()

        self.sensor_process = Thread(target=self.read_sensors)
        self.feed_process = Thread(target=self.feed_callback)

    def setup_gpio(self):
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
        GPIO.output(LED_PUMP, 1)
        GPIO.add_event_detect(LIGHT_SENSOR_PIN, GPIO.BOTH, callback=self.light_swap, bouncetime=250)

    def setup_servo(self):
        self.servo = GPIO.PWM(SERVO_PIN, 50)
        self.servo.start(0)
        self.servo.ChangeDutyCycle(SERVO_RESTING)
        time.sleep(1)
        self.servo.ChangeDutyCycle(0)

    def light_swap(self, chan):
        time.sleep(0.225)
        self.sensor_values["light_value"] = self.get_light_value()
        if self.light_mode == 0:
            self.set_light(self.sensor_values["light_value"])

    def read_sensors(self):
        self.sensor_values["water_temperature_value"] = self.get_water_temperature()
        self.sensor_values["ambient_temperature_value"] = self.get_ambient_temperature()
        self.sensor_values["ambient_humidity_value"] = self.get_ambient_humidity()
        self.sensor_values["client_count"] = self.get_ap_client_count()

    async def sensor_loop(self, interval):
        while True:
            self.sensor_process = Thread(target=self.read_sensors)
            self.sensor_process.start()
            await asyncio.sleep(interval)

    def label_color(self, label, value, upper, lower, white):
        fg = "white" if white else "black"
        if value >= upper:
            label.configure(fg="orange")
        elif value <= lower:
            label.configure(fg="cyan")
        else:
            label.configure(fg=fg)

    def get_ap_client_count(self):
        count = os.popen('iw ap0 station dump | grep Station | wc -l').read()
        if int(count) > 0:
            GPIO.output(LED_AP, 1)
        else:
            GPIO.output(LED_AP, 0)
        return int(count)

    def get_water_temperature(self):
        value = float(os.popen(
            'cat /sys/bus/w1/devices/%s/w1_slave | tail -n1 | awk \'{print $NF}\' | sed s/t=//' % WATER_TEMPERATURE_SENSOR_ID).read())
        if value / 1000 < 25 or value / 1000 > 29:
            GPIO.output(LED_TEMP, 1)
        else:
            GPIO.output(LED_TEMP, 0)
        return value / 1000

    def get_ambient_temperature(self):
        value = dht.read(dht.DHT11, 4)[1]
        print(f"ambient temp {value}")
        return value if value else 0

    def get_ambient_humidity(self):
        value = dht.read(dht.DHT11, 4)[0]
        print(f"ambient hum {value}")
        return value if value else 0

    def get_light_value(self):
        return GPIO.input(LIGHT_SENSOR_PIN)

    def reboot(self, event):
        os.popen('sudo reboot')

    def toggle_pump(self, event):
        self.pump_state = not self.pump_state
        GPIO.output(LED_PUMP, self.pump_state)
        GPIO.output(PUMP_RELAY_PIN, not self.pump_state)

    def toggle_light_mode(self, event=None):
        if self.light_mode == 0:
            self.light_mode += 1
            self.canvas.itemconfigure(self.button_texts["light"], text="Light On")
        elif self.light_mode == 1:
            self.light_mode += 1
            self.canvas.itemconfigure(self.button_texts["light"], text="Light Off")
        else:
            self.light_mode = 0
            self.canvas.itemconfigure(self.button_texts["light"], text="Light Auto")
        self.set_light(self.get_light_value())

    def set_light(self, light):
        if self.light_mode == 0:
            GPIO.output(LIGHT_RELAY_PIN, 0 if light else 1)
            GPIO.output(LED_LIGHT, 1 if light else 0)
        elif self.light_mode == 1:
            GPIO.output(LIGHT_RELAY_PIN, 0)
            GPIO.output(LED_LIGHT, 1)
        elif self.light_mode == 2:
            GPIO.output(LIGHT_RELAY_PIN, 1)
            GPIO.output(LED_LIGHT, 0)

    def feed_callback(self):
        self.is_feeding = True
        GPIO.output(LED_FEED, 1)
        self.servo.ChangeDutyCycle(SERVO_MAX)
        time.sleep(2)
        self.servo.ChangeDutyCycle(SERVO_RESTING)
        GPIO.output(LED_FEED, 0)
        time.sleep(2)
        self.servo.ChangeDutyCycle(0)
        self.is_feeding = False

    def feed(self, event):
        if not self.is_feeding:
            self.feed_process = Thread(target=self.feed_callback)
            self.feed_process.start()

    def set_theme(self, white):
        bg = "white" if not white else "black"
        fg = "white" if white else "black"
        for label in self.labels:
            self.labels[label].configure(fg=fg)
            self.labels[label].configure(bg=bg)
        for i in range(len(self.lines)):
            self.canvas.itemconfigure(self.lines[i], fill=fg)
        for button in BUTTON_NAME:
            self.canvas.itemconfigure(self.buttons[button], fill=bg)
            if button != "reboot":
                self.canvas.itemconfigure(self.button_texts[button], fill=fg)
        self.canvas.configure(bg=bg)
        self.configure(bg=bg)

    def setup_lcd(self):
        self.attributes("-fullscreen", True)
        self.bind("<1>", self.quit())
        self.configure(bg="black")

        self.canvas = tk.Canvas(self, width=LCD_WIDTH, height=LCD_HEIGHT, bg="black")
        self.canvas.place(x=-1, y=-1)

        self.labels["title"] = Label(self, fg="white", bg="black", text="E-Kan", font=("Futura", 25, "bold italic"))

        self.labels["water_temp_desc"] = Label(self, fg="white", bg="black", text="Water", font=("Helvetica", 11))
        self.text_vars["water_temp"] = StringVar()
        self.text_vars["water_temp"].set("00.0 °C")
        self.labels["water_temp"] = Label(self, fg="white", bg="black", textvariable=self.text_vars["water_temp"],
                                          font=("Helvetica", 20))
        self.labels["ambient_desc"] = Label(self, fg="white", bg="black", text="Ambient", font=("Helvetica", 11))
        self.text_vars["ambient"] = StringVar()
        self.text_vars["ambient"].set("00.0 °C")
        self.labels["ambient"] = Label(self, fg="white", bg="black", textvariable=self.text_vars["ambient"],
                                       font=("Helvetica", 20))

        self.text_vars["time"] = StringVar()
        self.text_vars["time"].set("00:00")
        self.labels["time"] = Label(self, textvariable=self.text_vars["time"], fg="white", bg="black",
                                    font=("helvetica", 30))
        self.text_vars["day"] = StringVar()
        self.text_vars["day"].set("Mon")
        self.labels["day"] = Label(self, textvariable=self.text_vars["day"], fg="white", bg="black",
                                   font=("helvetica", 12))
        self.text_vars["date"] = StringVar()
        self.text_vars["date"].set("dd/mm")
        self.labels["date"] = Label(self, textvariable=self.text_vars["date"], fg="white", bg="black",
                                    font=("helvetica", 12))

        self.labels["feed_desc"] = Label(self, fg="white", bg="black", text="Feed in", font=("Helvetica", 11))
        self.text_vars["feed"] = StringVar()
        self.text_vars["feed"].set("00:00")
        self.labels["feed"] = Label(self, fg="white", bg="black", textvariable=self.text_vars["feed"],
                                    font=("Helvetica", 20))
        self.labels["ap_client_desc"] = Label(self, fg="white", bg="black", text="AP Client", font=("Helvetica", 11))
        self.text_vars["ap_client"] = StringVar()
        self.text_vars["ap_client"].set("0")
        self.labels["ap_client"] = Label(self, fg="white", bg="black", textvariable=self.text_vars["ap_client"],
                                         font=("Helvetica", 20))

        self.labels["title"].place(x=60, y=0)
        self.buttons["reboot"] = self.canvas.create_rectangle(190, 0, 240, 44, fill="black", tags="reboot_button",
                                                              outline="")
        self.canvas.tag_bind("reboot_button", "<Button-1>", self.reboot)

        self.lines.append(self.canvas.create_line(0, 45, 240, 45, fill="white"))

        self.labels["water_temp_desc"].place(x=25, y=50)
        self.labels["water_temp"].place(x=10, y=68)
        self.lines.append(self.canvas.create_line(120, 45, 120, 105, fill="white"))
        self.labels["ambient_desc"].place(x=145, y=50)
        self.labels["ambient"].place(x=135, y=68)

        self.lines.append(self.canvas.create_line(0, 105, 240, 105, fill="white"))

        self.labels["time"].place(x=30, y=108)
        self.labels["day"].place(x=150, y=113)
        self.labels["date"].place(x=150, y=133)

        self.lines.append(self.canvas.create_line(0, 163, 240, 163, fill="white"))

        self.labels["feed_desc"].place(x=25, y=167)
        self.labels["feed"].place(x=15, y=185)
        self.lines.append(self.canvas.create_line(120, 163, 120, 225, fill="white"))
        self.labels["ap_client_desc"].place(x=145, y=167)
        self.labels["ap_client"].place(x=170, y=185)

        self.lines.append(self.canvas.create_line(0, 225, 240, 225, fill="white"))

        self.buttons["feed"] = self.canvas.create_rectangle(0, 226, 240, 275, fill="black", tags="feed_button",
                                                            outline="")
        self.button_texts["feed"] = self.canvas.create_text(120, 250, text="Feed", font=("Futura", 25, "italic"),
                                                            fill="white", tags="feed_text")
        self.canvas.tag_bind("feed_button", "<Button-1>", self.feed)
        self.canvas.tag_bind("feed_text", "<Button-1>", self.feed)

        self.lines.append(self.canvas.create_line(0, 275, 240, 275, fill="white"))

        self.buttons["pump"] = self.canvas.create_rectangle(0, 276, 119, 320, fill="black", tags="pump_button",
                                                            outline="")
        self.button_texts["pump"] = self.canvas.create_text(55, 300, text="Pump", font=("Helvetica", 14), fill="white",
                                                            tags="pump_text")
        self.canvas.tag_bind("pump_button", "<Button-1>", self.toggle_pump)
        self.canvas.tag_bind("pump_text", "<Button-1>", self.toggle_pump)
        self.lines.append(self.canvas.create_line(120, 275, 120, 320, fill="white"))
        self.buttons["light"] = self.canvas.create_rectangle(121, 276, 240, 320, fill="black", tags="light_button",
                                                             outline="")
        self.button_texts["light"] = self.canvas.create_text(180, 300, text="Light Auto", font=("Helvetica", 14),
                                                             fill="white", tags="light_text")
        self.canvas.tag_bind("light_button", "<Button-1>", self.toggle_light_mode)
        self.canvas.tag_bind("light_text", "<Button-1>", self.toggle_light_mode)

    async def updater(self, interval):
        while True:
            self.set_theme(self.sensor_values["light_value"])

            self.text_vars["water_temp"].set("%2.1f" % self.sensor_values["water_temperature_value"] + " °C")
            self.label_color(self.labels["water_temp"], self.sensor_values["water_temperature_value"], 30, 24,
                             self.sensor_values["light_value"])

            value = self.sensor_values["ambient_temperature_value"] if self.ambient_state else self.sensor_values[
                "ambient_humidity_value"]
            unit = " °C" if self.ambient_state else " %"
            ambient_text = "%2.1f" % value + unit
            self.text_vars["ambient"].set(ambient_text)
            self.label_color(self.labels["ambient"], value, 30, 24, self.sensor_values["light_value"])
            if self.ambient_counter > AMBIENT_STATE_DELAY:
                self.ambient_state = not self.ambient_state
                self.ambient_counter = 0
            else:
                self.ambient_counter += 1

            self.text_vars["time"].set(f"{datetime.datetime.now():%H:%M}")
            self.text_vars["day"].set(f"{datetime.datetime.now():%a}")
            self.text_vars["date"].set(f"{datetime.datetime.now():%d/%m}")

            temp = self.next_feed - datetime.datetime.now()
            self.text_vars["feed"].set(str(temp)[0:-10])
            self.text_vars["ap_client"].set(self.sensor_values["client_count"])

            if datetime.datetime.now() > self.next_feed:
                self.next_feed = datetime.datetime.now() + datetime.timedelta(hours=9)
                self.feed(None)

            self.update()
            await asyncio.sleep(interval)

    def close(self):
        for task in self.tasks:
            task.cancel()
        self.loop.stop()
        self.destroy()


def signal_handler(signal, frame):
    GPIO.cleanup()
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    loop = asyncio.get_event_loop()
    app = Ekan(loop)
    loop.run_forever()
