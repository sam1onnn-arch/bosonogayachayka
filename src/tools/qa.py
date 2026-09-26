# -*- coding: utf-8 -*-
"""qa.py URL — проверка страницы: ошибки консоли, горизонтальный скролл на разных ширинах,
логика каталога/корзины/окон."""
import json, shutil, socket, subprocess, sys, tempfile, time, urllib.request
import websocket

sys.stdout.reconfigure(encoding="utf-8")
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
URL = sys.argv[1]


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


port = free_port()
ud = tempfile.mkdtemp(prefix="qa_")
proc = subprocess.Popen([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
                         "--remote-debugging-port=%d" % port, "--user-data-dir=" + ud, "about:blank"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
ws = None
for _ in range(80):
    try:
        data = json.load(urllib.request.urlopen("http://127.0.0.1:%d/json" % port, timeout=1))
        pages = [d for d in data if d.get("type") == "page"]
        if pages:
            ws = pages[0]["webSocketDebuggerUrl"]; break
    except Exception:
        time.sleep(.25)
sock = websocket.create_connection(ws, timeout=90, suppress_origin=True)
n = 0
events = []


def call(method, **params):
    global n
    n += 1
    sock.send(json.dumps({"id": n, "method": method, "params": params}))
    while True:
        msg = json.loads(sock.recv())
        if msg.get("id") == n:
            return msg.get("result", msg)
        if msg.get("method") in ("Runtime.consoleAPICalled", "Runtime.exceptionThrown", "Log.entryAdded"):
            events.append(msg)


def js(expr):
    r = call("Runtime.evaluate", expression=expr, returnByValue=True, awaitPromise=True)
    if "exceptionDetails" in r:
        return "EXC: " + json.dumps(r["exceptionDetails"].get("exception", {}).get("description", ""), ensure_ascii=False)
    return r.get("result", {}).get("value")


call("Page.enable"); call("Runtime.enable"); call("Log.enable")
res = []
try:
    for w, mobile in [(320, True), (390, True), (768, False), (1024, False), (1440, False), (1920, False)]:
        call("Emulation.setDeviceMetricsOverride", width=w, height=900, deviceScaleFactor=1, mobile=mobile)
        call("Page.navigate", url=URL)
        time.sleep(2.5)
        over = js("document.documentElement.scrollWidth - document.documentElement.clientWidth")
        wide = js("""(function(){var W=document.documentElement.clientWidth,bad=[];
          document.querySelectorAll('body *').forEach(function(e){var r=e.getBoundingClientRect();
            if(r.width>0&&(r.right>W+1||r.left<-1)&&getComputedStyle(e).position!=='fixed'&&!e.closest('.tabs,.sprite,.frieze,.hero__media,.hero,.map__frame,.photo__frame,.ovl,.menu,.toast,.skip')){bad.push(e.tagName+'.'+(e.className&&e.className.baseVal!==undefined?e.className.baseVal:e.className)+' '+Math.round(r.left)+'-'+Math.round(r.right))}});
          return bad.slice(0,8)})()""")
        res.append((w, "overflow-x", over, wide))
    call("Emulation.setDeviceMetricsOverride", width=1440, height=900, deviceScaleFactor=1, mobile=False)
    call("Page.navigate", url=URL); time.sleep(2.5)
    for _ in range(60):
        if js("!!document.querySelector('#grid .card')") is True: break
        time.sleep(.5)
    checks = [
        ("cards", "document.querySelectorAll('#grid .card').length"),
        ("tab mezen", "document.querySelector('[data-cat=mezen]').click(); document.querySelectorAll('#grid .card').length"),
        ("tab cups", "document.querySelector('[data-cat=cups]').click(); document.querySelectorAll('#grid .card').length"),
        ("tab all", "document.querySelector('[data-cat=all]').click(); document.querySelectorAll('#grid .card').length"),
        ("sort asc first", "var s=document.querySelector('#sort'); s.value='asc'; s.dispatchEvent(new Event('change')); document.querySelector('#grid .card__price').textContent"),
        ("sort desc first", "var s=document.querySelector('#sort'); s.value='desc'; s.dispatchEvent(new Event('change')); document.querySelector('#grid .card__price').textContent"),
        ("fav add", "document.querySelector('#grid .heart').click(); document.querySelector('#fav-n').textContent"),
        ("fav only", "document.querySelector('#fav-only').click(); document.querySelectorAll('#grid .card').length"),
        ("fav off", "document.querySelector('#fav-only').click(); document.querySelectorAll('#grid .card').length"),
        ("fav persisted", "localStorage.getItem('bch-fav-v1')"),
        ("open modal", "document.querySelector('#grid [data-act=open]').click(); document.querySelector('#ovl-product').hidden"),
        ("modal title", "document.querySelector('.pm__title').textContent"),
        ("zoom on", "document.querySelector('#pm-img').click(); document.querySelector('#pm-img').classList.contains('is-zoom')"),
        ("esc closes", "document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape'})); document.querySelector('#ovl-product').hidden"),
        ("locked after close", "document.documentElement.classList.contains('lock')"),
        ("add plate", "document.querySelector('#grid [data-act=add]').click(); document.querySelector('#cart-n').textContent"),
        ("add again -> qty 2", "document.querySelector('#grid [data-act=add]').click(); document.querySelector('#cart-n').textContent"),
        ("open cart", "document.querySelector('.cartbtn').click(); document.querySelectorAll('.line').length + ' line(s), total ' + document.querySelector('.sum .tot dd').textContent"),
        ("qty +", "document.querySelector('[data-act=qty][data-d=\"1\"]').click(); document.querySelector('.qty output').textContent"),
        ("remove", "document.querySelector('[data-act=remove]').click(); document.querySelector('.cart-empty') ? 'empty state' : 'still has lines'"),
        ("policy modal", "document.querySelector('#ovl-cart .btn--red').click(); 'x'"),
        ("menu", "document.querySelector('[data-act=menu-open]').click(); document.querySelector('#menu').hidden"),
        ("typo nbsp in facts", "(document.querySelector('.facts').textContent.match(/\\u00a0/g)||[]).length"),
        ("typo wj in hours", "(document.querySelector('#contacts').textContent.match(/\\u2060/g)||[]).length"),
        ("docs open", "['offer','policy','consent'].map(function(d){document.querySelector('.ftr [data-doc='+d+']').click();var ok=!document.querySelector('#ovl-'+d).hidden;document.querySelector('#ovl-'+d+' .x').click();return d+':'+ok+'/'+document.querySelector('#ovl-'+d).hidden}).join(' ')"),
        ("docs numbering", "['offer','policy','consent'].map(function(d){var c=document.querySelectorAll('#ovl-'+d+' .c .n');return d+'='+c.length+' first='+c[0].textContent+' last='+c[c.length-1].textContent}).join(' | ')"),
        ("fonts", "[...document.fonts].filter(f=>f.status==='loaded').length"),
        ("imgs broken", "[...document.images].filter(i=>i.complete&&i.naturalWidth===0).map(i=>i.src).length"),
    ]
    for name, expr in checks:
        res.append((name, js(expr)))
        time.sleep(.25)
    errs = [e for e in events if e.get("method") == "Runtime.exceptionThrown" or
            (e.get("method") == "Runtime.consoleAPICalled" and e["params"]["type"] in ("error", "warning")) or
            (e.get("method") == "Log.entryAdded" and e["params"]["entry"]["level"] in ("error", "warning"))]
    for r in res:
        print(r)
    print("CONSOLE PROBLEMS:", len(errs))
    for e in errs[:8]:
        print(json.dumps(e, ensure_ascii=False)[:400])
finally:
    try: sock.close()
    except Exception: pass
    proc.terminate()
    shutil.rmtree(ud, ignore_errors=True)
