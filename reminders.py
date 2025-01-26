import random
import time

import board
import displayio
import framebufferio
import rgbmatrix

import terminalio
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text.bitmap_label import Label
from adafruit_display_text.scrolling_label import ScrollingLabel
import adafruit_minimqtt.adafruit_minimqtt as MQTT

import socket, ssl, json, os

displayio.release_displays()

# Fill this with your own information!
MQTT_BROKER = "mqtt.localhost"
MQTT_USER = "neon"
MQTT_PASSWORT = "password"
MQTT_PORT = 8883


matrix = rgbmatrix.RGBMatrix(
    width=64, height=32, bit_depth=24,
    rgb_pins=[board.D6, board.D5, board.D9, board.D11, board.D10, board.D12],
    addr_pins=[board.A5, board.A4, board.A3, board.A2],
    clock_pin=board.D13, latch_pin=board.D0, output_enable_pin=board.D1)
display = framebufferio.FramebufferDisplay(matrix, auto_refresh=False)
SCALE = 1
group = displayio.Group(scale=SCALE)
display.root_group = group

font = bitmap_font.load_font("spleen-5x8.bdf")


lines = [" ", " ", " "]
colors = [0xFFFFFF, 0xFF00FF, 0x00FF00]

labels = [
    Label(
        font=font, text=lines[0],
        base_alignment=True,
    ),
    Label(
        font=font, text=lines[1],
        base_alignment=True,
    ),
    Label(
        font=font, text=lines[2],
        base_alignment=True,
    ),
]

for i, label in enumerate(labels):
    label.x = 0
    label.y = 8 + i*8 + i*2
    group.append(label)

def update_line(i, str, color=None, xpos=0):
    lines[i] = str
    labels[i].x = xpos
    labels[i].text = str
    if color:
        colors[i] = color
        labels[i].color = color

def update_labels():
    for i, str in enumerate(lines):
        update_line(i, str, colors[i])

reminders = []
reminder_colors = []
last_reminder_displayed = -1

if os.path.isfile("reminders.json"):
    with open("reminders.json", "r") as f:
        print("loading reminders from disk...")
        l1, l2 = f.readlines()
        reminders = json.loads(l1)
        reminder_colors = json.loads(l2)
        print("loaded", len(reminders), "reminders from disk")

def save_reminders():
    with open("reminders.json", "w") as f:
        f.writelines([json.dumps(reminders), json.dumps(reminder_colors)])
    print("saved", len(reminders), "reminders to disk")


mqtt_client = MQTT.MQTT(
    broker=MQTT_BROKER,
    username=MQTT_USER,
    password=MQTT_PASSWORD,
    port=MQTT_PORT,
    socket_pool=socket,
    is_ssl=True,
    ssl_context=ssl.create_default_context(),
)

ADD_REMINDERS_TOPIC = "/add_reminder"
GET_REMINDERS_TOPIC = "/get_reminders"
GET_REMINDERS_RESPONSE_TOPIC = "/get_reminders/response"
REMOVE_REMINDER_TOPIC = "/remove_reminder"

def connected(client, userdata, flags, rc):
    print("connected to mqtt server")
    client.subscribe(ADD_REMINDERS_TOPIC)
    client.subscribe(GET_REMINDERS_TOPIC)
    client.subscribe(REMOVE_REMINDER_TOPIC)

def disconnected(client, userdata, rc):
    print("Disconnected from mqtt server - trying to reconnect in 3 sec")
    time.sleep(3)
    client.connect()


def message(client, topic, message):
    if topic == ADD_REMINDERS_TOPIC:
        msg, color = message.split("|")
        print("added new reminder:", msg)
        reminders.append(msg)
        reminder_colors.append(int(color, 16))
        save_reminders()
    elif topic == GET_REMINDERS_TOPIC:
        print("responded with reminders")
        client.publish(GET_REMINDERS_RESPONSE_TOPIC, json.dumps(reminders) + "|" + json.dumps(reminder_colors))
    elif topic == REMOVE_REMINDER_TOPIC:
        if int(message) < len(reminders) and int(message) >= 0:
            print("removed reminder", reminders.pop(int(message)))
            save_reminders()
    

mqtt_client.on_connect = connected
mqtt_client.on_disconnect = disconnected
mqtt_client.on_message = message

mqtt_client.connect()

t = 0
t_end = 0
while True:
    t += 1

    for i, label in enumerate(labels):
        if len(lines[i]) > 0:
            label.x -= 1
            if label.x < len(lines[i]) * -5:                
                t_end += 1
                if t_end % 3 == 0: mqtt_client.loop()
                    
                if last_reminder_displayed < len(reminders) - 1:
                    last_reminder_displayed += 1
                    update_line(i, reminders[last_reminder_displayed], reminder_colors[last_reminder_displayed], random.randint(64, 96))
                if last_reminder_displayed >= len(reminders) - 1:
                    last_reminder_displayed = -1

    if len(reminders) == 0: mqtt_client.loop()
        
    display.refresh()

    time.sleep(1/20)
