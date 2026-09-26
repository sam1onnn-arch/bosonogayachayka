# -*- coding: utf-8 -*-
"""cdp.py URL PREFIX [--w 390] [--h 800] [--mobile] [--full] [--tile 1400] [--scroll N]
        [--wait 3] [--step "js"]...  [--shot NAME]...
Шаги --step выполняются по порядку (JS в странице, результат печатается),
--shot NAME делает снимок окна (не всей страницы) сразу после предыдущего шага.
Без --shot и --full делает один снимок окна в конце.
"""
import argparse, base64, json, os, shutil, socket, subprocess, sys, tempfile, time, urllib.request
import websocket
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


class Chrome:
    def __init__(self):
        self.port = free_port()
        self.ud = tempfile.mkdtemp(prefix="cdp_")
        self.proc = subprocess.Popen([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
                                      "--no-default-browser-check", "--remote-debugging-port=%d" % self.port,
                                      "--user-data-dir=" + self.ud, "about:blank"],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        ws = None
        for _ in range(80):
            try:
                data = json.load(urllib.request.urlopen("http://127.0.0.1:%d/json" % self.port, timeout=1))
                pages = [d for d in data if d.get("type") == "page"]
                if pages:
                    ws = pages[0]["webSocketDebuggerUrl"]; break
            except Exception:
                time.sleep(.25)
        self.ws = websocket.create_connection(ws, timeout=90, suppress_origin=True)
        self.n = 0

    def call(self, method, **params):
        self.n += 1
        self.ws.send(json.dumps({"id": self.n, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == self.n:
                return msg.get("result", msg)

    def js(self, expr):
        r = self.call("Runtime.evaluate", expression=expr, returnByValue=True, awaitPromise=True)
        if "exceptionDetails" in r:
            return "EXC: " + json.dumps(r["exceptionDetails"].get("exception", {}).get("description", r["exceptionDetails"]), ensure_ascii=False)
        return r.get("result", {}).get("value", r)

    def close(self):
        try: self.ws.close()
        except Exception: pass
        self.proc.terminate()
        try: self.proc.wait(10)
        except Exception: self.proc.kill()
        shutil.rmtree(self.ud, ignore_errors=True)


ap = argparse.ArgumentParser()
ap.add_argument("url"); ap.add_argument("prefix")
ap.add_argument("--w", type=int, default=1440); ap.add_argument("--h", type=int, default=900)
ap.add_argument("--mobile", action="store_true"); ap.add_argument("--full", action="store_true")
ap.add_argument("--tile", type=int, default=1400); ap.add_argument("--scroll", type=int, default=0)
ap.add_argument("--wait", type=float, default=3.0)
ap.add_argument("--step", action="append", default=[]); ap.add_argument("--shot", action="append", default=[])
ap.add_argument("--dpr", type=float, default=1)
a = ap.parse_args()

c = Chrome()
try:
    c.call("Emulation.setDeviceMetricsOverride", width=a.w, height=a.h, deviceScaleFactor=a.dpr, mobile=a.mobile)
    if a.mobile:
        c.call("Emulation.setTouchEmulationEnabled", enabled=True)
    c.call("Page.enable"); c.call("Runtime.enable")
    c.call("Page.navigate", url=a.url)
    time.sleep(a.wait)
    for _ in range(60):   # скрипт страницы ждёт стили Google Fonts: даём ему до 30 с
        if c.js("!!document.querySelector('#grid .card')") is True: break
        time.sleep(.5)
    c.js('document.documentElement.style.scrollBehavior="auto"')
    if a.scroll:
        c.js("window.scrollTo(0,%d)" % a.scroll); time.sleep(1.0)
    shots = list(a.shot)
    for i, step in enumerate(a.step):
        print("STEP", i, "->", c.js(step))
        time.sleep(.6)
        if i < len(shots):
            r = c.call("Page.captureScreenshot", format="png")
            p = "%s_%s.png" % (a.prefix, shots[i]); open(p, "wb").write(base64.b64decode(r["data"])); print("SHOT", p)
    if a.full:
        H0 = int(c.js("document.documentElement.scrollHeight"))
        y = 0
        while y < H0:
            c.js("window.scrollTo(0,%d)" % y); time.sleep(.35); y += max(300, a.h - 100)
        c.js("window.scrollTo(0,0)"); time.sleep(1.2)
        H = int(c.js("document.documentElement.scrollHeight"))
        r = c.call("Page.captureScreenshot", format="png", captureBeyondViewport=True,
                   clip={"x": 0, "y": 0, "width": a.w, "height": H, "scale": 1})
        raw = a.prefix + "_raw.png"; open(raw, "wb").write(base64.b64decode(r["data"]))
        im = Image.open(raw); n = 0
        for y in range(0, im.height, a.tile):
            im.crop((0, y, im.width, min(im.height, y + a.tile))).save("%s_t%02d.png" % (a.prefix, n)); n += 1
        os.remove(raw); print("FULL", im.size, "tiles", n)
    elif not a.step or len(shots) < 1:
        r = c.call("Page.captureScreenshot", format="png")
        p = a.prefix + "_view.png"; open(p, "wb").write(base64.b64decode(r["data"])); print("SHOT", p)
finally:
    c.close()
