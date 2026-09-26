# -*- coding: utf-8 -*-
"""Проверка: страница работает, когда localStorage и clipboard недоступны (как в песочнице артефакта)."""
import json, shutil, socket, subprocess, sys, tempfile, time, urllib.request
import websocket

sys.stdout.reconfigure(encoding="utf-8")
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
URL = sys.argv[1]
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
ud = tempfile.mkdtemp(prefix="qa2_")
proc = subprocess.Popen([CHROME, "--headless=new", "--disable-gpu", "--no-first-run", "--remote-debugging-port=%d" % port,
                         "--user-data-dir=" + ud, "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
ws = None
for _ in range(80):
    try:
        d = json.load(urllib.request.urlopen("http://127.0.0.1:%d/json" % port, timeout=1))
        p = [x for x in d if x.get("type") == "page"]
        if p:
            ws = p[0]["webSocketDebuggerUrl"]; break
    except Exception:
        time.sleep(.25)
sock = websocket.create_connection(ws, timeout=60, suppress_origin=True)
n = 0
events = []


def call(m, **pr):
    global n
    n += 1
    sock.send(json.dumps({"id": n, "method": m, "params": pr}))
    while True:
        msg = json.loads(sock.recv())
        if msg.get("id") == n:
            return msg.get("result", msg)
        if msg.get("method") in ("Runtime.exceptionThrown", "Runtime.consoleAPICalled"):
            events.append(msg)


def js(e):
    r = call("Runtime.evaluate", expression=e, returnByValue=True, awaitPromise=True)
    if "exceptionDetails" in r:
        return "EXC " + str(r["exceptionDetails"].get("exception", {}).get("description"))
    return r.get("result", {}).get("value")


try:
    call("Page.enable"); call("Runtime.enable")
    call("Page.addScriptToEvaluateOnNewDocument", source="""
      Object.defineProperty(window,'localStorage',{get:function(){throw new DOMException('blocked','SecurityError')}});
      Object.defineProperty(navigator,'clipboard',{get:function(){return undefined}});
    """)
    call("Emulation.setDeviceMetricsOverride", width=1280, height=900, deviceScaleFactor=1, mobile=False)
    call("Page.navigate", url=URL); time.sleep(3)
    for _ in range(60):
        if js("!!document.querySelector('#grid .card')") is True: break
        time.sleep(.5)
    print("cards", js("document.querySelectorAll('#grid .card').length"))
    print("add", js("document.querySelector('#grid [data-act=add]').click(); document.querySelector('#cart-n').textContent"))
    print("fav", js("document.querySelector('#grid .heart').click(); document.querySelector('#fav-n').textContent"))
    print("cart", js("document.querySelector('.cartbtn').click(); document.querySelectorAll('.line').length"))
    print("form", js("document.querySelector('[data-act=checkout]').click(); !!document.querySelector('#order-form')"))
    print("submit", js("var n=document.querySelector('#f-name');n.value='Анна';var p=document.querySelector('#f-phone');p.value='9001234567';p.dispatchEvent(new Event('input',{bubbles:true}));document.querySelector('#f-offer').click();document.querySelector('#f-consent').click();document.querySelector('#order-form').requestSubmit();!!document.querySelector('#order-text')"))
    print("copy", js("document.querySelector('[data-act=copy-order]').click(); 'clicked'"))
    time.sleep(.5)
    print("toast", js("document.querySelector('#toast').textContent"))
    errs = [e for e in events if e.get("method") == "Runtime.exceptionThrown"]
    print("EXCEPTIONS:", len(errs))
    for e in errs[:5]:
        print(json.dumps(e["params"]["exceptionDetails"].get("exception", {}).get("description", ""), ensure_ascii=False)[:300])
finally:
    try: sock.close()
    except Exception: pass
    proc.terminate(); shutil.rmtree(ud, ignore_errors=True)
