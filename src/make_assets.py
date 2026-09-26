# -*- coding: utf-8 -*-
"""Готовит картинки сайта из исходников в ceramic_shop/ -> site/img/.
Запуск: python make_assets.py   (из папки site/src)
"""
import glob
import math
import os
import sys
import time
import urllib.request
from io import BytesIO

from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.abspath(os.path.join(HERE, "..", ".."))          # ceramic_shop
OUT = os.path.abspath(os.path.join(HERE, "..", "img"))
os.makedirs(OUT, exist_ok=True)


def save(im, name, q=84):
    path = os.path.join(OUT, name)
    im.convert("RGB").save(path, "JPEG", quality=q, optimize=True, progressive=True)
    print(name, im.size, os.path.getsize(path) // 1024, "KB")


# --- главный экран и мастер -------------------------------------------------
chat = sorted(glob.glob(os.path.join(SRC, "*.png")))
chat = [f for f in chat if "ChatGPT" in f]
hero_src, lina_src = chat[0], chat[1]          # 09_03 — главный экран, 09_31 — мастер
hero = Image.open(hero_src).convert("RGB")
lina = Image.open(lina_src).convert("RGB")
print("hero", hero.size, "lina", lina.size)

save(hero, "hero.jpg", 86)
# мобильный кадр: тарелка целиком, без пустой левой половины
save(hero.crop((790, 0, 1570, 941)), "hero-m.jpg", 86)
save(lina, "lina.jpg", 84)

# цвета фона главного экрана для подложки
px = hero.load()
for (x, y) in [(40, 40), (300, 120), (620, 60), (60, 480), (300, 480), (60, 900), (400, 900), (1640, 900), (1640, 500)]:
    print("hero px", (x, y), px[x, y])
top = hero.crop((790, 0, 1570, 30)).resize((1, 1), Image.LANCZOS).getpixel((0, 0))
print("mobile crop top avg", top)
plate_red = hero.crop((1120, 460, 1230, 500)).resize((1, 1), Image.LANCZOS).getpixel((0, 0))
print("plate red-ish avg", plate_red)

# --- каталог ------------------------------------------------------------------
cards = sorted(glob.glob(os.path.join(SRC, "catalog_cards", "[0-9][0-9].png")))
for f in cards:
    n = os.path.splitext(os.path.basename(f))[0]
    over = glob.glob(os.path.join(SRC, "catalog_cards", n + "-*.png"))   # 11-fish.png заменяет 11.png
    im = Image.open(over[0] if over else f).convert("RGB")
    save(im.resize((1200, 1200), Image.LANCZOS), "p%s.jpg" % n, 82)
    save(im.resize((640, 640), Image.LANCZOS), "p%s-s.jpg" % n, 80)

# --- карта из тайлов OpenStreetMap -----------------------------------------------
LAT, LON, Z = 59.891196, 30.404577, 16
COLS, ROWS = 5, 3


def tile_xy(lat, lon, z):
    n = 2 ** z
    x = (lon + 180.0) / 360.0 * n
    y = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
    return x, y


fx, fy = tile_xy(LAT, LON, Z)
tx0 = int(fx) - COLS // 2
ty0 = int(fy) - ROWS // 2
print("tile float", fx, fy, "origin", tx0, ty0)
mp = Image.new("RGB", (256 * COLS, 256 * ROWS), (230, 228, 224))
ok = 0
for j in range(ROWS):
    for i in range(COLS):
        url = "https://tile.openstreetmap.org/%d/%d/%d.png" % (Z, tx0 + i, ty0 + j)
        req = urllib.request.Request(url, headers={"User-Agent": "bosonogaya-chayka-site-mockup/1.0 (static map, 15 tiles)"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                t = Image.open(BytesIO(r.read())).convert("RGB")
            mp.paste(t, (256 * i, 256 * j))
            ok += 1
        except Exception as e:
            print("tile fail", url, e)
        time.sleep(0.4)
print("tiles ok", ok, "of", COLS * ROWS)
# положение метки в пикселях карты
pin_x = (fx - tx0) * 256
pin_y = (fy - ty0) * 256
print("pin px", pin_x, pin_y, "of", mp.size)
save(mp, "map.jpg", 86)
