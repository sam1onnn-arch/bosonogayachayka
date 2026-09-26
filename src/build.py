# -*- coding: utf-8 -*-
"""Собирает src/{style.css, body.html, legal.txt, data.js, app.js} в
  ../artifact-source.html — то, что уходит в артефакт (без <html>/<head>/<body>);
  ../index.html          — самостоятельная страница для локального просмотра и GitHub.
Запуск: python build.py  (из папки site/src)
"""
import os
import re
import sys

from legal_build import build_legal

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(os.path.join(HERE, ".."))


def rd(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as fh:
        return fh.read()


# Данные продавца — единственное место. Подставляются в оферту, политику, согласие, подвал и контакты.
# ФИО, ИНН и ОГРНИП сверены с открытым реестром ИП (26.09.2026); в реестре имя записано «Эвелина».
SELLER = {
    "FIO": "Альтман Эвелина Давидовна",
    "FIO_SHORT": "Альтман Э. Д.",
    "INN": "745312232794",
    "OGRNIP": "320745600096958",
    "PHONE": "+7 (921) 982-88-13",
    "PHONE_TEL": "+79219828813",
    "EMAIL": "chaykabn@mail.ru",
    "ADDRESS": "Санкт-Петербург, проспект Елизарова, 36А",
    "HOURS": "пн—сб 10:00—18:00, вс 12:00—18:00",
    "DATE": "26 сентября 2026 г.",
}


def subst(text, where):
    def key(m):
        assert m.group(1) in SELLER, "нет данных продавца %s (%s)" % (m.group(1), where)
        return SELLER[m.group(1)]
    return re.sub(r"\{\{([A-Z_]+)\}\}", key, text)


TITLE = "Босоногая Чайка"
TITLE_PAGE = "Босоногая Чайка — керамика с мезенской росписью, Санкт-Петербург"
FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Neucha'
         '&family=Inter:wght@300;400;500;600&display=swap">')

css = rd("style.css")
body_src = rd("body.html")
assert "<!--LEGAL-->" in body_src, "в body.html нет метки <!--LEGAL-->"
body = subst(body_src.replace("<!--LEGAL-->", build_legal(rd("legal.txt"), SELLER)), "body.html")
js = rd("data.js") + "\n" + rd("app.js")

# Ни одной неразрешённой метки в готовой странице
left = re.findall(r"\{\{[A-Z_]+\}\}|\{[a-z0-9-]+\}", body)
assert not left, "неразрешённые метки: %s" % left[:5]

head_part = "<title>%s</title>\n%s\n<style>\n%s</style>\n" % (TITLE, FONTS, css)
tail = "\n<script>\n%s</script>\n" % js

artifact = head_part + body + tail
with open(os.path.join(OUT, "artifact-source.html"), "w", encoding="utf-8", newline="\n") as fh:
    fh.write(artifact)

FAVICON = ('<link rel="icon" type="image/svg+xml" href="img/favicon.svg">\n'
           '<link rel="icon" type="image/png" sizes="64x64" href="img/favicon-64.png">\n'
           '<link rel="apple-touch-icon" href="img/favicon-180.png">')
DESC = ("Интернет-магазин авторской керамики с мезенской росписью: тарелки, блюда, чашки ручной работы. "
        "Мастерская Лины Альтерман, Санкт-Петербург.")
page = ('<!doctype html>\n<html lang="ru">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        '<meta name="description" content="%s">\n<meta name="theme-color" content="#fbf9f5">\n'
        '<title>%s</title>\n%s\n%s\n<style>\n%s</style>\n</head>\n<body>\n%s%s</body>\n</html>\n'
        % (DESC, TITLE_PAGE, FAVICON, FONTS, css, body, tail))
with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8", newline="\n") as fh:
    fh.write(page)
print("ok", len(artifact), len(page))
