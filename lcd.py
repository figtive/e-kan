# -*- coding: utf-8 -*-

import os
from tkinter import *
import tkinter as tk
import Adafruit_DHT as dht
import threading
import tkinter.font
from PIL import ImageTk
import RPi.GPIO as GPIO

waterSensorID = "28-031097791088"
waterSensorPin = 4
tempSensorPin = 4
lightSensorPin = 3

GPIO.setmode(GPIO.BCM)
GPIO.setup(lightSensorPin, GPIO.IN)
# GPIO.setup(40, GPIO.OUT)
# GPIO.output(40, GPIO.HIGH)

root = tk.Tk()
# iw ap0 station dump | grep Station | wc -l

#image = PhotoImage(file="background.gif")

#background=Label(root, image=image)
#background.place(x=0,y=0,relwidth=1, relheight=1)

temperature = StringVar()
temperature.set("----"+" °C")		

humidity = StringVar()
humidity.set("----"+"  %")

water = StringVar()
water.set("----"+" °C")	

temperatureLabel = Label(root, fg="black", background="#00dbde", textvariable=temperature, font=("Helvetica", 40, "bold"))
temperatureLabel.place(x=0, y=0)

humidityLabel = Label(root, fg="black", background="#00dbde", textvariable=humidity, font=("Helvetica", 40, "bold"))
humidityLabel.place(x=0, y=80)

humidityLabel = Label(root, fg="black", background="#00dbde", textvariable=water, font=("Helvetica", 40, "bold"))
humidityLabel.place(x=0, y=160)
 
root.attributes("-fullscreen", True)
root.bind("<1>",exit)

def exit(): 
    root.quit()

def readSensor():
    h, t = dht.read(dht.DHT11, 4)
    w = os.popen('cat /sys/bus/w1/devices/%s/w1_slave | tail -n1 | awk \'{print $NF}\' | sed s/t=//' % waterSensorID).read()
    l = GPIO.input(lightSensorPin)
    print(h)
    print(t)
    if t is not None:
        temp = "%.1f" % t
        temperature.set(temp + " °C")
    if h is not None:
        hum = "%.1f" % h
        humidity.set(hum + "  %")
    if w:
        wat = "%.1f" % (int(w)/1000)
        water.set(wat + " °C")
    if l:
        root.configure(background='white')
    else:
        root.configure(background='black')
    root.after(1000, readSensor)
		
root.after(1000, readSensor)

root.mainloop()
