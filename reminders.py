import random
import time

import board
import displayio


##### BEGIN PATCHING #####


from displayio._bitmap import Bitmap
from displayio._colorconverter import ColorConverter
from displayio._ondiskbitmap import OnDiskBitmap
from displayio._palette import Palette
from displayio._structs import (
    InputPixelStruct,
    OutputPixelStruct,
    null_transform,
)
from displayio._colorspace import Colorspace
from displayio._area import Area
import struct


# This is an incredibly hacky solution, which hopefully won't be necessary on the actual device, but it is in the editor.
# Because TileGrid somehow calculates floats for values which are then used in range() and as indices in some weird, random-seeming cases,
# I decided to copy the source of _fill_area from TileGrid, add int(...) to the offending variables (start_x, end_x, start_y, end_y, x_shift, y_shift)
# and replace the actual TileGrid._fill_area with tilegrid_fill_area_patched. This fixes the issue.


def tilegrid_fill_area_patched(
    self,
    colorspace,
    area,
    mask,
    buffer,
) -> bool:
    """Draw onto the image"""
    # pylint: disable=too-many-locals,too-many-branches,too-many-statements

    # If no tiles are present we have no impact
    tiles = self._tiles

    if tiles is None or len(tiles) == 0:
        return False

    if self._hidden_tilegrid or self._hidden_by_parent:
        return False
    overlap = Area()  # area, current_area, overlap
    if not area.compute_overlap(self._current_area, overlap):
        return False
    # else:
    #    print("Checking", area.x1, area.y1, area.x2, area.y2)
    #    print("Overlap", overlap.x1, overlap.y1, overlap.x2, overlap.y2)

    if self._bitmap.width <= 0 or self._bitmap.height <= 0:
        return False

    x_stride = 1
    y_stride = area.width()

    flip_x = self._flip_x
    flip_y = self._flip_y
    if self._transpose_xy != self._absolute_transform.transpose_xy:
        flip_x, flip_y = flip_y, flip_x

    start = 0
    if (self._absolute_transform.dx < 0) != flip_x:
        start += (area.x2 - area.x1 - 1) * x_stride
        x_stride *= -1
    if (self._absolute_transform.dy < 0) != flip_y:
        start += (area.y2 - area.y1 - 1) * y_stride
        y_stride *= -1

    # Track if this layer finishes filling in the given area. We can ignore any remaining
    # layers at that point.
    full_coverage = area == overlap

    transformed = Area()
    area.transform_within(
        flip_x != (self._absolute_transform.dx < 0),
        flip_y != (self._absolute_transform.dy < 0),
        self.transpose_xy != self._absolute_transform.transpose_xy,
        overlap,
        self._current_area,
        transformed,
    )

    start_x = int(transformed.x1 - self._current_area.x1)
    end_x = int(transformed.x2 - self._current_area.x1)
    start_y = int(transformed.y1 - self._current_area.y1)
    end_y = int(transformed.y2 - self._current_area.y1)

    if (self._absolute_transform.dx < 0) != flip_x:
        x_shift = int(area.x2 - overlap.x2)
    else:
        x_shift = int(overlap.x1 - area.x1)
    if (self._absolute_transform.dy < 0) != flip_y:
        y_shift = int(area.y2 - overlap.y2)
    else:
        y_shift = int(overlap.y1 - area.y1)

    # This untransposes x and y so it aligns with bitmap rows
    if self._transpose_xy != self._absolute_transform.transpose_xy:
        x_stride, y_stride = y_stride, x_stride
        x_shift, y_shift = y_shift, x_shift

    pixels_per_byte = 8 // colorspace.depth

    input_pixel = InputPixelStruct()
    output_pixel = OutputPixelStruct()
    # print(input_pixel.y, start_y, end_y)
    for input_pixel.y in range(start_y, end_y):
        row_start = (
            start + (input_pixel.y - start_y + y_shift) * y_stride
        )  # In Pixels
        local_y = input_pixel.y // self._absolute_transform.scale
        #print(input_pixel.x, start_x, end_x, transformed, self._current_area)
        for input_pixel.x in range(start_x, end_x):
            # Compute the destination pixel in the buffer and mask based on the transformations
            offset = (
                row_start + (input_pixel.x - start_x + x_shift) * x_stride
            )  # In Pixels

            # Check the mask first to see if the pixel has already been set
            if mask[offset // 32] & (1 << (offset % 32)):
                continue
            local_x = input_pixel.x // self._absolute_transform.scale
            tile_location = (
                (local_y // self._tile_height + self._top_left_y)
                % self._height_in_tiles
            ) * self._width_in_tiles + (
                local_x // self._tile_width + self._top_left_x
            ) % self._width_in_tiles
            input_pixel.tile = tiles[tile_location]
            input_pixel.tile_x = (
                input_pixel.tile % self._bitmap_width_in_tiles
            ) * self._tile_width + local_x % self._tile_width
            input_pixel.tile_y = (
                input_pixel.tile // self._bitmap_width_in_tiles
            ) * self._tile_height + local_y % self._tile_height

            output_pixel.pixel = 0
            input_pixel.pixel = 0

            # We always want to read bitmap pixels by row first and then transpose into
            # the destination buffer because most bitmaps are row associated.
            if isinstance(self._bitmap, (Bitmap, OnDiskBitmap)):
                input_pixel.pixel = (
                    self._bitmap._get_pixel(  # pylint: disable=protected-access
                        input_pixel.tile_x, input_pixel.tile_y
                    )
                )

            output_pixel.opaque = True
            if self._pixel_shader is None:
                output_pixel.pixel = input_pixel.pixel
            elif isinstance(self._pixel_shader, Palette):
                self._pixel_shader._get_color(  # pylint: disable=protected-access
                    colorspace, input_pixel, output_pixel
                )
            elif isinstance(self._pixel_shader, ColorConverter):
                self._pixel_shader._convert(  # pylint: disable=protected-access
                    colorspace, input_pixel, output_pixel
                )

            if not output_pixel.opaque:
                full_coverage = False
            else:
                mask[offset // 32] |= 1 << (offset % 32)
                if colorspace.depth == 16:
                    struct.pack_into(
                        "H",
                        buffer.cast("B"),
                        offset * 2,
                        output_pixel.pixel,
                    )
                elif colorspace.depth == 32:
                    struct.pack_into(
                        "I",
                        buffer.cast("B"),
                        offset * 4,
                        output_pixel.pixel,
                    )
                elif colorspace.depth == 8:
                    buffer.cast("B")[offset] = output_pixel.pixel & 0xFF
                elif colorspace.depth < 8:
                    # Reorder the offsets to pack multiple rows into
                    # a byte (meaning they share a column).
                    if not colorspace.pixels_in_byte_share_row:
                        width = area.width()
                        row = offset // width
                        col = offset % width
                        # Dividing by pixels_per_byte does truncated division
                        # even if we multiply it back out
                        offset = (
                            col * pixels_per_byte
                            + (row // pixels_per_byte) * pixels_per_byte * width
                            + (row % pixels_per_byte)
                        )
                    shift = (offset % pixels_per_byte) * colorspace.depth
                    if colorspace.reverse_pixels_in_byte:
                        # Reverse the shift by subtracting it from the leftmost shift
                        shift = (pixels_per_byte - 1) * colorspace.depth - shift
                    buffer.cast("B")[offset // pixels_per_byte] |= (
                        output_pixel.pixel << shift
                    )

    return full_coverage
displayio.TileGrid._fill_area = tilegrid_fill_area_patched


##### END PATCHING #####




import framebufferio
import rgbmatrix

import terminalio
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text.bitmap_label import Label
from adafruit_display_text.scrolling_label import ScrollingLabel
import adafruit_minimqtt.adafruit_minimqtt as MQTT

import socket, ssl, os, json

print("starting...")

displayio.release_displays()

matrix = rgbmatrix.RGBMatrix(
    width=64, height=32, bit_depth=24,
    rgb_pins=[board.D6, board.D5, board.D9, board.D11, board.D10, board.D12],
    addr_pins=[board.A5, board.A4, board.A3, board.A2],
    clock_pin=board.D13, latch_pin=board.D0, output_enable_pin=board.D1)
display = framebufferio.FramebufferDisplay(matrix, auto_refresh=False)
group = displayio.Group()
display.root_group = group

FONT = bitmap_font.load_font("spleen-5x8.bdf")


mqtt_client = MQTT.MQTT(
    broker=BROKER_URL,
    username=USERNAME,
    password=PASSWORD,
    port=PORT,
    socket_pool=socket,
    is_ssl=True,
    ssl_context=ssl.create_default_context(),
)

ADD_REMINDERS_TOPIC = "/add_reminder"
GET_REMINDERS_TOPIC = "/get_reminders"
GET_REMINDERS_RESPONSE_TOPIC = "/get_reminders/response"
REMOVE_REMINDER_TOPIC = "/remove_reminder"


ICON_HEIGHT = 7
ICON_WIDTH = 7
class Reminder:
    def __init__(self, text: str, color: int = 0xFFFFFF, icon: list[int] = None, palette: list[int] = None):
        self.text = text
        self.color = color
        self.icon = icon
        self.palette = palette
    def to_json(self):
        return json.dumps({ "text": self.text, "color": self.color, "icon": self.icon, "palette": self.palette })
    def from_json(data):
        return Reminder(
            data["text"],
            (int(data["color"], 16) if isinstance(data["color"], str) else data["color"]) if "color" in data else 0xFFFFFF,
            (data["icon"] if len(data["icon"]) <= (ICON_HEIGHT * ICON_WIDTH) else None) if "icon" in data else None,
            data["palette"] if "palette" in data else None
        )
    def get_bitmap(self):
        if self.icon is None or self.palette is None: return None
        bmp = displayio.Bitmap(ICON_WIDTH, ICON_HEIGHT, 65535)
        for i, val in enumerate(self.icon):
            x = (i // ICON_WIDTH)
            if x < 0 or x >= ICON_WIDTH: continue
            y = (i % ICON_WIDTH)
            if y < 0 or y >= ICON_HEIGHT: continue
            bmp[x, ICON_HEIGHT - y - 1] = val if val is not None else 0
        return bmp
    def get_palette(self):
        if self.icon is None or self.palette is None: return None
        pal = displayio.Palette(65535)
        for i, val in enumerate(self.palette):
            pal[i] = val
        return pal

class Line:
    def __init__(self, text, color, icon=None, pixel_shader=None):
        self.group = displayio.Group()
        self.label = Label(font=FONT, text=text, color=color, x=0 if icon is None else (ICON_WIDTH + 2), base_alignment=True)
        if icon is not None:
            self.icon = displayio.TileGrid(icon, pixel_shader=pixel_shader, x=0, y=-7)
            self.group.append(self.icon)
        else: self.icon = None
        self.group.append(self.label)

lines = [
    Line(" ", 0xFFFFFF),
    Line(" ", 0xFFFFFF),
    Line(" ", 0xFFFFFF),
]
for l in lines: group.append(l.group)

def update_line(i, reminder, xpos=0):
    group.remove(lines[i].group)
    nl = Line(reminder.text, reminder.color if reminder.color is not None else 0xFFFFFF, reminder.get_bitmap(), reminder.get_palette())
    nl.group.x = xpos
    nl.group.y = 8 + i*8 + i*2 + 1
    lines[i] = nl
    group.append(nl.group)

reminders = []
last_reminder_displayed = -1

if os.path.isfile("reminders.json"):
    with open("reminders.json", "r") as f:
        print("loading reminders from disk...")
        reminders = [Reminder.from_json(txt) for txt in f.readlines()]
        print("loaded", len(reminders), "reminders from disk")

def save_reminders():
    with open("reminders.json", "w") as f:
        f.writelines([r.to_json() for r in reminders])
    print("saved", len(reminders), "reminders to disk")



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
        if not message.startswith("{"):
            reminders.append(Reminder(message))
        else:
            msgdata = json.loads(message)
            reminders.append(Reminder.from_json(msgdata))

        print("added new reminder:", reminders[-1].to_json())
        save_reminders()
    elif topic == GET_REMINDERS_TOPIC:
        print("responded with reminders")
        client.publish(GET_REMINDERS_RESPONSE_TOPIC, "\n".join([r.to_json() for r in reminders]))
    elif topic == REMOVE_REMINDER_TOPIC:
        if int(message) < len(reminders) and int(message) >= 0:
            i = int(message)
            print("removed reminder", reminders.pop(i).to_json())
            save_reminders()
    

mqtt_client.on_connect = connected
mqtt_client.on_disconnect = disconnected
mqtt_client.on_message = message

print("connecting...")
mqtt_client.connect()

t = 0
t_end = 0
while True:
    t += 1

    for i, line in enumerate(lines):
        line.group.x -= 1
        if line.group.x < len(line.label.text) * -5 + (-(ICON_WIDTH + 2) if line.icon is not None else 0):
            t_end += 1
            if t_end % 3 == 0: mqtt_client.loop()

            if last_reminder_displayed < len(reminders) - 1:
                last_reminder_displayed += 1
                update_line(i, reminders[last_reminder_displayed], xpos=random.randint(64, 96))
            if last_reminder_displayed >= len(reminders) - 1:
                last_reminder_displayed = -1

    if len(reminders) == 0: mqtt_client.loop()
        
    display.refresh()

    time.sleep(1/20)
