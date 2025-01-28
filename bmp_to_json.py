def read_bmp(file_path):
    with open(file_path, 'rb') as f:
        header = f.read(54)

        width = int.from_bytes(header[18:22], 'little')
        height = int.from_bytes(header[22:26], 'little')
        color_planes = int.from_bytes(header[26:28], 'little')
        bits_per_pixel = int.from_bytes(header[28:30], 'little')

        print(f"Width: {width}, Height: {height}, Color Planes: {color_planes}, Bits per Pixel: {bits_per_pixel}")

        if bits_per_pixel != 8:
            print("This is not an indexed BMP file.")
            return

        palette_size = 256 * 4
        palette = f.read(palette_size)

        row_size = (width + 3) // 4 * 4
        pixel_data = []
        for y in range(height):
            row = f.read(row_size)
            pixel_data.append(row[:width])

        pal = []
        for i in range(256):
            r = palette[i * 4 + 2]
            g = palette[i * 4 + 1]
            b = palette[i * 4 + 0]
            pal.append(r * 0x010000 + g * 0x0100 + b * 0x01)

        img = []
        for x in range(width):
            for y in range(height):
                img.append(pixel_data[y][x])

        return img, pal[:(max(img) + 1)]

import sys, json

img, pal = read_bmp(sys.argv[1])

#print(json.dumps({"icon": img, "palette": [f"{x:x}" for x in pal]}))
print(json.dumps({"text": "reminder text", "color": "0xFFFFFF", "icon": img, "palette": pal}))
