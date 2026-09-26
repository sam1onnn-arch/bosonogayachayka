# -*- coding: utf-8 -*-
"""Собирает юридические документы сайта из legal.txt в HTML-окна.

Разметка legal.txt (одна строка = один пункт):
  @doc offer            начало документа (id окна: ovl-offer)
  @name / @title / @sub / @date / @flat yes    метаданные
  ## Название раздела   раздел (нумеруется автоматически)
  ## [метка] Название   раздел с меткой для ссылок
  Текст пункта          пункт 3.1, 3.2 ... (в документе @flat yes: 1, 2 ...)
  [метка] Текст пункта  пункт с меткой
  - элемент списка      тире-список под предыдущим пунктом
  // комментарий        игнорируется
В тексте:
  {{KEY}}               данные продавца из словаря SELLER
  {метка}               номер пункта или раздела с этой меткой
  [[doc|текст]]         ссылка на другое окно (offer, policy, consent)
  **слово**             полужирный
Пропущенная метка или ключ — ошибка сборки, а не молчаливая пустота.
"""
import re


def parse(src):
    docs, cur = [], None
    for raw in src.split("\n"):
        line = raw.strip()
        if not line or line.startswith("//"):
            continue
        if line.startswith("@doc "):
            cur = {"id": line[5:].strip(), "meta": {}, "items": []}
            docs.append(cur)
            continue
        assert cur is not None, "текст до первого @doc: " + line[:40]
        if line.startswith("@"):
            key, _, val = line[1:].partition(" ")
            cur["meta"][key] = val.strip()
        elif line.startswith("## "):
            cur["items"].append(["sec", line[3:].strip()])
        elif line.startswith("- "):
            cur["items"].append(["li", line[2:].strip()])
        else:
            cur["items"].append(["cl", line])
    return docs


def number(doc):
    """Проставляет номера и собирает метки: [(kind, num, text)], {метка: номер}."""
    flat = doc["meta"].get("flat") == "yes"
    sec = cl = 0
    labels, out = {}, []
    for kind, text in doc["items"]:
        lab = None
        m = re.match(r"\[([a-z0-9-]+)\]\s+(.*)$", text)
        if m and kind != "li":
            lab, text = m.group(1), m.group(2)
        if kind == "sec":
            sec, cl = sec + 1, 0
            num, ref = "%d." % sec, "%d" % sec
        elif kind == "cl":
            cl += 1
            if flat:
                num, ref = "%d." % cl, "%d" % cl
            else:
                assert sec, "пункт до первого раздела: " + text[:40]
                num, ref = "%d.%d." % (sec, cl), "%d.%d" % (sec, cl)
        else:
            num, ref = None, None
        if lab:
            assert lab not in labels, "метка повторяется: " + lab
            labels[lab] = ref
        out.append((kind, num, text))
    return out, labels


def fill(text, seller, labels, where):
    def key(m):
        k = m.group(1)
        assert k in seller, "нет данных продавца: %s (%s)" % (k, where)
        v = seller[k]
        # телефон и почту не разрываем на две строки
        return '<span class="nw">%s</span>' % v if k in ("PHONE", "EMAIL") else v

    def lab(m):
        k = m.group(1)
        assert k in labels, "нет метки {%s} (%s)" % (k, where)
        return labels[k]

    def link(m):
        return '<a href="#%s" data-act="doc-open" data-doc="%s">%s</a>' % (m.group(1), m.group(1), m.group(2))

    text = re.sub(r"\{\{([A-Z_]+)\}\}", key, text)
    text = re.sub(r"\{([a-z0-9-]+)\}", lab, text)
    text = re.sub(r"\[\[([a-z]+)\|([^\]]+)\]\]", link, text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    return text


def render(doc, seller):
    meta = doc["meta"]
    for k in ("name", "title", "sub", "date"):
        assert k in meta, "у документа %s нет @%s" % (doc["id"], k)
    items, labels = number(doc)
    flat = meta.get("flat") == "yes"
    f = lambda t: fill(t, seller, labels, doc["id"])
    h = []
    h.append('<div class="ovl ovl--doc" id="ovl-%s" role="dialog" aria-modal="true" aria-label="%s" hidden>' % (doc["id"], f(meta["title"])))
    h.append('<div class="dlg dlg--doc">')
    h.append('<div class="doc__bar"><span class="doc__name">%s</span>'
             '<button class="x x--bar" type="button" data-act="close" aria-label="Закрыть">'
             '<svg class="ic" aria-hidden="true"><use href="#i-x"/></svg></button></div>' % f(meta["name"]))
    h.append('<article class="doc">')
    h.append('<h2 class="doc__title">%s</h2>' % f(meta["title"]))
    h.append('<p class="doc__sub">%s</p>' % f(meta["sub"]))
    h.append('<p class="doc__date">%s</p>' % f(meta["date"]))
    open_sec = open_ul = False
    if flat:
        h.append("<section>")
        open_sec = True
    for kind, num, text in items:
        if kind != "li" and open_ul:
            h.append("</ul>")
            open_ul = False
        if kind == "sec":
            if open_sec:
                h.append("</section>")
            h.append('<section><h3><span class="n">%s</span><span>%s</span></h3>' % (num, f(text)))
            open_sec = True
        elif kind == "cl":
            h.append('<p class="c"><span class="n">%s</span><span class="t">%s</span></p>' % (num, f(text)))
        else:
            if not open_ul:
                h.append('<ul class="dash">')
                open_ul = True
            h.append("<li>%s</li>" % f(text))
    if open_ul:
        h.append("</ul>")
    if open_sec:
        h.append("</section>")
    h.append('<div class="doc__end"><button class="btn btn--line btn--sm" type="button" data-act="close">Закрыть</button></div>')
    h.append("</article></div></div>")
    return "\n".join(h)


def build_legal(src, seller):
    docs = parse(src)
    ids = [d["id"] for d in docs]
    assert len(ids) == len(set(ids)), "повторяется @doc"
    return "\n".join(render(d, seller) for d in docs)
