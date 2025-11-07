#!/usr/bin/env python3
import os, time, shutil, base64, random
from io import BytesIO
from PIL import Image, ImageOps
from cairosvg import svg2png

# === CONFIG ===
WALLE_PATH = os.path.expanduser("~/walle/walle.svg")
BG_PATH = os.path.expanduser("~/walle/bg.jpg")
BASE_ORIENTATION = "left"

# Image IDs for Kitty protocol
BG_IMAGE_ID = 1
WALLE_IMAGE_ID = 2

# === DUST ===
class DustParticle:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.life = random.uniform(0.8, 1.4)
        self.x_drift = random.uniform(-0.2, 0.2)
        self.y_drift = random.uniform(-0.4, 0.1)
        self.char = random.choice(['·', '˙', '•', '∙'])
        self.born = time.time()

    def update(self, dt):
        self.x += self.x_drift
        self.y += self.y_drift
        return (time.time() - self.born) < self.life

    def draw(self):
        age = time.time() - self.born
        alpha = 1.0 - (age / self.life)
        if alpha > 0.7:
            color = "\033[38;5;180m"  # warm beige
        elif alpha > 0.4:
            color = "\033[38;5;137m"
        else:
            color = "\033[38;5;94m"
        return f"{color}\033[{int(self.y)};{int(self.x)}H{self.char}\033[0m"

# === IMAGE HELPERS ===
def svg_to_png_data(svg_path, width, flip=False):
    png = svg2png(url=svg_path, output_width=width)
    img = Image.open(BytesIO(png)).convert("RGBA")
    if flip:
        img = ImageOps.mirror(img)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def kitty_display_image(png_data, x, y, image_id, zindex=0):
    b64 = base64.b64encode(png_data).decode("ascii")
    # Use direct mode (a=d) instead of transmit mode to avoid visual artifacts
    print(f"\033[{y};{x}H\033_Ga=T,z={zindex},i={image_id},f=100,q=2;{b64}\033\\", end="", flush=True)

def kitty_clear_image(image_id):
    """Clear a specific image by ID"""
    print(f"\033_Ga=d,d=i,i={image_id}\033\\", end="", flush=True)

def display_background():
    """Force background visible and scaled to terminal"""
    cols, rows = shutil.get_terminal_size()
    target_width = cols * 9
    target_height = rows * 18

    with Image.open(BG_PATH) as bg:
        bg = bg.convert("RGB").resize((target_width, target_height))
        # Slight blur/dim for cinematic effect
        bg = bg.point(lambda p: int(p * 0.8))
        buf = BytesIO()
        bg.save(buf, format="JPEG")
        data = base64.b64encode(buf.getvalue()).decode("ascii")
        # Display with ID and z-index at back, suppress responses with q=2
        print(f"\033[1;1H\033_Gf=100,a=T,i={BG_IMAGE_ID},z=-1,q=2;{data}\033\\", end="", flush=True)

def build_oriented_images(width_chars):
    if BASE_ORIENTATION == "left":
        img_left = svg_to_png_data(WALLE_PATH, width_chars * 10, flip=False)
        img_right = svg_to_png_data(WALLE_PATH, width_chars * 10, flip=True)
    else:
        img_left = svg_to_png_data(WALLE_PATH, width_chars * 10, flip=True)
        img_right = svg_to_png_data(WALLE_PATH, width_chars * 10, flip=False)
    return img_left, img_right

# === MAIN LOOP ===
def main():
    cols, rows = shutil.get_terminal_size()
    w = 45
    # Position Wall-E at the bottom (accounting for his height ~18 rows)
    y = max(1, rows - 18)
    img_left, img_right = build_oriented_images(w)

    direction = -1
    x = cols - w
    current_img = img_left
    particles = []
    last_time = time.time()
    spawn_timer = 0

    print("\033[2J\033[H\033[?25l", end="")
    display_background()  # draw bg once with ID

    try:
        while True:
            now = time.time()
            dt = now - last_time
            last_time = now

            cols, rows = shutil.get_terminal_size()
            right_bound, left_bound = max(1, cols - w), 1
            # Update y position if terminal resizes
            y = max(1, rows - 18)

            spawn_timer += dt
            if spawn_timer > 0.08:
                spawn_timer = 0
                spawn_x = x if direction == 1 else x + w
                spawn_y = y + random.randint(12, 16)
                for _ in range(random.randint(1, 3)):
                    particles.append(DustParticle(
                        spawn_x + random.uniform(-2, 2),
                        spawn_y + random.uniform(-1, 1)
                    ))

            new_particles = []
            for p in particles:
                print(f"\033[{int(p.y)};{int(p.x)}H ", end="")
                if p.update(dt):
                    new_particles.append(p)
            particles = new_particles

            for p in particles:
                print(p.draw(), end="")

            # Only clear Wall-E's image, not the background
            kitty_clear_image(WALLE_IMAGE_ID)
            kitty_display_image(current_img, x, y, WALLE_IMAGE_ID, zindex=5)

            if direction == -1:
                x -= 1
                if x <= left_bound:
                    direction = 1
                    current_img = img_right
            else:
                x += 1
                if x >= right_bound:
                    direction = -1
                    current_img = img_left

            time.sleep(0.05)

    except KeyboardInterrupt:
        pass
    finally:
        kitty_clear_image(WALLE_IMAGE_ID)
        kitty_clear_image(BG_IMAGE_ID)
        print(f"\033[2J\033[{y + 18};1H\033[?25h", end="")

if __name__ == "__main__":
    main()
