# -*- coding: utf-8 -*-
"""Рисует бесшовный тайл орнамента (кольцо с крестом на волне между двумя полосами)
по присланному образцу «Узор.png» и пишет site/img/frieze.svg + frieze-test.html.
Параметры подобраны по замерам образца: кольцо 33x29 при периоде 48, полосы 10 и 9,
красная «печать» сдвинута вниз на 4-5 единиц.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(os.path.join(HERE, "..", "img"))

INK = "#1b1516"
RED = "#c8281e"

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="48" height="72" viewBox="0 0 48 72">
<g fill="{RED}">
<rect x="0" y="6" width="48" height="9"/>
<rect x="0" y="63" width="48" height="9"/>
</g>
<g fill="{INK}">
<rect x="0" y="2" width="48" height="10"/>
<rect x="0" y="58" width="48" height="9"/>
</g>
<g fill="none" stroke="{INK}" stroke-linecap="round" stroke-linejoin="round">
<ellipse cx="31" cy="35" rx="14.3" ry="12.4" stroke-width="4.4"/>
<path d="M25.6 35H36.4M31 29.6V40.4" stroke-width="3.1" stroke-linecap="butt"/>
<path d="M40 43.2Q44.6 46.8 48 47M0 47L20.4 26.6" stroke-width="3.2"/>
</g>
</svg>
'''
with open(os.path.join(OUT, "frieze.svg"), "w", encoding="utf-8", newline="\n") as fh:
    fh.write(svg)

# светлый вариант для тёмного подвала: полосы и кольцо цвета глазури, красная «печать» чуть ярче
light = svg.replace(INK, "#efe7de").replace(RED, "#d8392d")
with open(os.path.join(OUT, "frieze-light.svg"), "w", encoding="utf-8") as fh:
    fh.write(light)

# значок вкладки здесь не рисуем: img/favicon.svg — чайка, присланная заказчиком
# (ceramic_shop/mezen-gull-from-image-favicon (1).svg), её не перезаписывать.

print("ok")
