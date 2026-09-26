/* Логика магазина: каталог, карточка, корзина, оформление, отзывы, меню.
   Невидимые символы пишем эскейпами (\xa0), а не самими знаками. */
(function () {
  "use strict";

  var NB = "\xa0";
  var WJ = String.fromCharCode(0x2060);   // word joiner: не даёт перенести строку внутри «10:00—18:00»
  var KEY_CART = "bch-cart-v1";
  var KEY_FAV = "bch-fav-v1";

  /* ---------- утилиты ---------- */
  function $(s, r) { return (r || document).querySelector(s); }
  function $$(s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); }
  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c];
    });
  }
  function byId(list, id) {
    for (var i = 0; i < list.length; i++) if (list[i].id === id) return list[i];
    return null;
  }
  var nf = new Intl.NumberFormat("ru-RU");
  function money(n) { return nf.format(n).replace(/\s/g, NB) + NB + "₽"; }
  function plural(n, f) {
    var m10 = n % 10, m100 = n % 100;
    if (m10 === 1 && m100 !== 11) return f[0];
    if (m10 >= 2 && m10 <= 4 && (m100 < 10 || m100 >= 20)) return f[1];
    return f[2];
  }
  function load(key, def) {
    try {
      var v = JSON.parse(localStorage.getItem(key));
      return v == null ? def : v;
    } catch (e) { return def; }
  }
  function save(key, val) {
    try { localStorage.setItem(key, JSON.stringify(val)); } catch (e) { /* хранилище недоступно */ }
  }

  /* ---------- русская типографика ---------- */
  var PREP = "в|во|к|ко|с|со|у|о|об|от|до|по|на|за|из|без|при|про|над|под|для|и|а|но|да|не|ни";
  /* пробелы правим только обычные и неразрывные: перенос строки не трогаем */
  var RE_PREP = new RegExp("(^|[ \\xa0(«„\\u2014])(" + PREP + ")[ ]+(?=[^\\s])", "gi");
  var RE_PART = /[ ]+(же|бы|ли)(?=[\s,.;:!?)]|$)/gi;
  var RE_DASH = /[ \xa0]+([—])/g;
  var RE_RANGE = /([0-9A-Za-zЀ-ӿ])—([0-9A-Za-zЀ-ӿ])/g;
  var RE_NUM =/(\d)[ ]+(?=[A-Za-zЀ-ӿ₽%°])/g;
  /* «ст. 26.1», «п. 4», «№ 2463»: сокращение и число не разрываем */
  var RE_ABBR = /(^|[ \xa0(«])(ст\.|п\.|пп\.|ч\.|№|§)[ ]+(?=\d)/g;
  var RE_DATE = /(\d{1,2})[ \xa0](января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)[ \xa0](\d{4})[ \xa0]г\./g;
  function typo(s) {
    if (!s || s.length < 3) return s;
    return s
      .replace(/\s-\s/g, NB + "— ")
      .replace(RE_DASH, NB + "$1")
      .replace(RE_RANGE, "$1" + WJ + "—" + WJ + "$2")
      .replace(RE_PREP, function (m, a, b) { return a + b + NB; })
      .replace(RE_PREP, function (m, a, b) { return a + b + NB; })
      .replace(RE_PART, NB + "$1")
      .replace(RE_ABBR, function (m, a, b) { return a + b + NB; })
      .replace(RE_DATE, "$1" + NB + "$2" + NB + "$3" + NB + "г.")
      .replace(RE_NUM, "$1" + NB);
  }
  function typoTree(root) {
    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode: function (n) {
        var p = n.parentNode;
        if (!p) return NodeFilter.FILTER_REJECT;
        var t = p.nodeName;
        if (t === "SCRIPT" || t === "STYLE" || t === "TEXTAREA" || t === "TITLE" || t === "PRE") return NodeFilter.FILTER_REJECT;
        return n.nodeValue.length > 2 ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
      }
    });
    var nodes = [], n;
    while ((n = walker.nextNode())) nodes.push(n);
    nodes.forEach(function (node) {
      var v = typo(node.nodeValue);
      if (v !== node.nodeValue) node.nodeValue = v;
    });
  }

  /* ---------- состояние ---------- */
  var S = {
    cat: "all",
    sort: "def",
    favOnly: false,
    cart: load(KEY_CART, []).filter(function (l) { return l && byId(PRODUCTS, l.id) && l.q > 0; }),
    fav: load(KEY_FAV, []).filter(function (id) { return byId(PRODUCTS, id); }),
    openId: null,
    variant: null,
    step: "cart",
    order: null
  };
  var stack = [];       // открытые окна, верхнее — последнее
  var lastFocus = null;

  /* ---------- каталог ---------- */
  function visible() {
    var a = PRODUCTS.filter(function (p) {
      return (S.cat === "all" || p.cat === S.cat) && (!S.favOnly || S.fav.indexOf(p.id) > -1);
    });
    if (S.sort === "asc") a = a.slice().sort(function (x, y) { return x.price - y.price; });
    if (S.sort === "desc") a = a.slice().sort(function (x, y) { return y.price - x.price; });
    return a;
  }
  function heartBtn(id, on) {
    return '<button class="heart" type="button" data-act="fav" data-id="' + id + '" aria-pressed="' + on + '" aria-label="' +
      (on ? "Убрать из избранного" : "В избранное") + '"><svg class="ic" aria-hidden="true"><use href="#i-heart"/></svg></button>';
  }
  function cardHTML(p) {
    var on = S.fav.indexOf(p.id) > -1;
    var hasV = p.variants && p.variants.length;
    return '<li class="card">' +
      '<div class="card__media">' +
        '<button class="card__img" type="button" data-act="open" data-id="' + p.id + '" aria-label="Смотреть «' + esc(p.name) + '»">' +
          '<img src="img/' + p.id + '-s.jpg" srcset="img/' + p.id + '-s.jpg 640w, img/' + p.id + '.jpg 1200w" sizes="(max-width:900px) 46vw, 380px" alt="' + esc(p.alt) + '" width="640" height="640" loading="lazy" decoding="async">' +
        '</button>' + heartBtn(p.id, on) +
      '</div>' +
      '<h3 class="card__name"><button type="button" data-act="open" data-id="' + p.id + '">«' + esc(p.name) + '»</button></h3>' +
      '<p class="card__kind">' + esc(p.kind) + '</p>' +
      '<p class="card__price">' + (hasV ? "" : "") + money(p.price) + (p.unit ? "<small>" + esc(p.unit) + "</small>" : "") + '</p>' +
      '<div class="card__row">' +
        (hasV
          ? '<button class="btn btn--line btn--sm" type="button" data-act="open" data-id="' + p.id + '">Выбрать<span class="lg"> рисунок</span></button>'
          : '<button class="btn btn--red btn--sm" type="button" data-act="add" data-id="' + p.id + '">В корзину</button>') +
      '</div></li>';
  }
  function renderTabs() {
    $("#tabs").innerHTML = CATS.map(function (c) {
      var sel = c.id === S.cat;
      return '<button class="tab" type="button" data-act="tab" data-cat="' + c.id + '" aria-pressed="' + sel + '">' + esc(c.name) + '</button>';
    }).join("");
  }
  function renderGrid() {
    var list = visible();
    var html = list.map(cardHTML).join("");
    if (!list.length) {
      html = '<li class="empty">' + (S.favOnly
        ? "В избранном пока пусто. Отметьте сердечком вещи, которые понравились."
        : "В этом разделе пока ничего нет.") + "</li>";
    }
    var g = $("#grid");
    g.innerHTML = html;
    typoTree(g);
    $("#count").textContent = list.length + NB + plural(list.length, ["работа", "работы", "работ"]);
    var fb = $("#fav-only");
    fb.setAttribute("aria-pressed", String(S.favOnly));
    $("#fav-n").textContent = S.fav.length ? "(" + S.fav.length + ")" : "";
  }

  /* ---------- избранное ---------- */
  function toggleFav(id) {
    var i = S.fav.indexOf(id);
    if (i > -1) S.fav.splice(i, 1); else S.fav.push(id);
    save(KEY_FAV, S.fav);
    if (S.favOnly && !S.fav.length) S.favOnly = false;
    renderGrid();
    if (S.openId === id) renderProduct(id, true);
  }

  /* ---------- окна ---------- */
  var FOCUSABLE = 'a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])';
  function lockScroll(on) { document.documentElement.classList.toggle("lock", on); }
  function openOverlay(el) {
    if (!stack.length) lastFocus = document.activeElement;
    if (stack.indexOf(el) === -1) stack.push(el);
    el.hidden = false;
    el.scrollTop = 0;
    lockScroll(true);
    var first = $(".x", el) || $(FOCUSABLE, el);
    if (first) first.focus({preventScroll: true});
  }
  function closeOverlay(el) {
    el = el || stack[stack.length - 1];
    if (!el) return;
    el.hidden = true;
    var i = stack.indexOf(el);
    if (i > -1) stack.splice(i, 1);
    if (el.id === "ovl-product") S.openId = null;
    if (!stack.length) {
      lockScroll(false);
      if (lastFocus && document.contains(lastFocus)) lastFocus.focus({preventScroll: true});
    } else {
      var top = stack[stack.length - 1];
      var f = $(".x", top) || $(FOCUSABLE, top);
      if (f) f.focus({preventScroll: true});
    }
  }
  document.addEventListener("keydown", function (e) {
    var menu = $("#menu");
    if (e.key === "Escape") {
      if (stack.length) { closeOverlay(); e.preventDefault(); }
      else if (!menu.hidden) { closeMenu(); e.preventDefault(); }
      return;
    }
    if (e.key === "Tab") {
      var top = stack.length ? stack[stack.length - 1] : (!menu.hidden ? menu : null);
      if (!top) return;
      var items = $$(FOCUSABLE, top).filter(function (n) { return n.offsetParent !== null; });
      if (!items.length) return;
      var first = items[0], last = items[items.length - 1];
      if (e.shiftKey && document.activeElement === first) { last.focus(); e.preventDefault(); }
      else if (!e.shiftKey && document.activeElement === last) { first.focus(); e.preventDefault(); }
    }
  });
  $$(".ovl").forEach(function (o) {
    o.addEventListener("mousedown", function (e) { if (e.target === o) closeOverlay(o); });
  });

  function openMenu() {
    var m = $("#menu");
    m.hidden = false;
    lockScroll(true);
    $$('[data-act="menu-open"]').forEach(function (b) { b.setAttribute("aria-expanded", "true"); });
    var b = $(".burger", m);
    if (b) b.focus({preventScroll: true});
  }
  function closeMenu() {
    var m = $("#menu");
    if (m.hidden) return;
    m.hidden = true;
    if (!stack.length) lockScroll(false);
    $$('[data-act="menu-open"]').forEach(function (b) { b.setAttribute("aria-expanded", "false"); });
  }

  /* ---------- уведомление ---------- */
  var toastTimer = null;
  function toast(msg, actLabel, actFn) {
    var t = $("#toast");
    t.innerHTML = "<span></span>" + (actLabel ? '<button type="button">' + esc(actLabel) + "</button>" : "");
    $("span", t).textContent = msg;
    if (actLabel) $("button", t).addEventListener("click", function () { t.classList.remove("is-on"); actFn(); });
    t.classList.add("is-on");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { t.classList.remove("is-on"); }, actLabel ? 4200 : 2600);
  }

  /* ---------- карточка товара ---------- */
  function related(p) {
    var same = PRODUCTS.filter(function (x) { return x.id !== p.id && x.cat === p.cat; });
    var rest = PRODUCTS.filter(function (x) { return x.id !== p.id && x.cat !== p.cat; });
    return same.concat(rest).slice(0, 3);
  }
  function renderProduct(id, keepZoom) {
    var p = byId(PRODUCTS, id);
    var on = S.fav.indexOf(id) > -1;
    var zoomed = keepZoom && $(".pm__img") && $(".pm__img").classList.contains("is-zoom");
    var v = "";
    if (p.variants) {
      v = '<div class="var"><h3 id="var-h">Рисунок</h3><div class="chips" role="radiogroup" aria-labelledby="var-h">' +
        p.variants.map(function (name) {
          var sel = name === S.variant;
          return '<button class="chip" type="button" role="radio" data-act="variant" data-v="' + esc(name) + '" aria-checked="' + sel + '">' + esc(name) + "</button>";
        }).join("") + "</div></div>";
    }
    var specs = '<dl class="spec">' + p.spec.map(function (r) {
      return "<div><dt>" + esc(r[0]) + "</dt><dd>" + esc(r[1]) + "</dd></div>";
    }).join("") + (p.unit ? "<div><dt>Цена</dt><dd>" + esc(p.unit) + "</dd></div>" : "") + "</dl>";
    var rel = related(p).map(function (r) {
      return '<li><button class="mini" type="button" data-act="open" data-id="' + r.id + '"><img src="img/' + r.id + '-s.jpg" alt="' + esc(r.alt) + '" width="640" height="640" loading="lazy"><b>«' + esc(r.name) + "»</b><span>" + money(r.price) + (r.unit ? " " + esc(r.unit) : "") + "</span></button></li>";
    }).join("");
    $("#pm-view").innerHTML =
      '<div class="pm">' +
        '<div class="pm__img' + (zoomed ? " is-zoom" : "") + '" id="pm-img"><img src="img/' + p.id + '.jpg" alt="' + esc(p.alt) + '" width="1200" height="1200"><span class="pm__hint">Нажмите, чтобы рассмотреть роспись</span></div>' +
        '<div class="pm__info">' +
          '<h2 class="pm__title">«' + esc(p.name) + "»</h2>" +
          '<p class="pm__kind">' + esc(p.kind) + "</p>" +
          '<p class="pm__desc">' + esc(p.desc) + "</p>" +
          specs + v +
          '<div class="pm__buy">' +
            '<span class="pm__price">' + money(p.price) + (p.unit ? "<small>" + esc(p.unit) + "</small>" : "") + "</span>" +
            heartBtn(p.id, on) +
            '<button class="btn btn--red" type="button" data-act="add" data-id="' + p.id + '">В корзину</button>' +
          "</div>" +
          '<p class="pm__note">Рисунок и оттенок глазури у каждой вещи чуть отличаются от фото. Наличие подтвердит мастер, когда получит заказ.</p>' +
        "</div>" +
        '<div class="more"><h3>Вас может заинтересовать</h3><ul>' + rel + "</ul></div>" +
      "</div>";
    typoTree($("#pm-view"));
  }
  function openProduct(id) {
    var p = byId(PRODUCTS, id);
    if (!p) return;
    S.openId = id;
    S.variant = p.variants ? p.variants[0] : null;
    renderProduct(id);
    var ov = $("#ovl-product");
    if (stack.indexOf(ov) === -1) openOverlay(ov);
    else { ov.scrollTop = 0; }
  }
  document.addEventListener("pointermove", function (e) {
    var box = e.target.closest && e.target.closest(".pm__img.is-zoom");
    if (!box) return;
    var r = box.getBoundingClientRect();
    box.firstElementChild.style.transformOrigin = ((e.clientX - r.left) / r.width * 100) + "% " + ((e.clientY - r.top) / r.height * 100) + "%";
  });

  /* ---------- корзина ---------- */
  function lineKey(l) { return l.id + "|" + (l.v || ""); }
  function cartCount() { return S.cart.reduce(function (s, l) { return s + l.q; }, 0); }
  function cartTotal() {
    return S.cart.reduce(function (s, l) { return s + byId(PRODUCTS, l.id).price * l.q; }, 0);
  }
  function saveCart() {
    save(KEY_CART, S.cart);
    var n = cartCount();
    var b = $("#cart-n");
    b.textContent = n;
    b.hidden = !n;
    $(".cartbtn").setAttribute("aria-label", n ? "Корзина, " + n + " " + plural(n, ["товар", "товара", "товаров"]) : "Корзина");
  }
  function addToCart(id, variant) {
    var p = byId(PRODUCTS, id);
    if (!p) return;
    var v = p.variants ? (variant || p.variants[0]) : "";
    var found = null;
    S.cart.forEach(function (l) { if (l.id === id && (l.v || "") === v) found = l; });
    if (found) found.q += 1; else S.cart.push({id: id, v: v, q: 1});
    saveCart();
    toast("«" + p.name + "»" + (v ? ", " + v.toLowerCase() : "") + " — в корзине", "Корзина", function () { openCart("cart"); });
  }
  function changeQty(key, d) {
    S.cart.forEach(function (l) { if (lineKey(l) === key) l.q = Math.max(1, Math.min(99, l.q + d)); });
    saveCart();
    renderCart();
    var again = $$('[data-act="qty"]').filter(function (b) {
      return b.getAttribute("data-key") === key && parseInt(b.getAttribute("data-d"), 10) === d;
    })[0];
    if (again) again.focus({preventScroll: true});
  }
  function removeLine(key) {
    S.cart = S.cart.filter(function (l) { return lineKey(l) !== key; });
    saveCart();
    renderCart();
  }
  function openCart(step) {
    var pm = $("#ovl-product");
    if (stack.indexOf(pm) > -1) closeOverlay(pm);
    $("#toast").classList.remove("is-on");
    S.step = step || "cart";
    if (!S.cart.length) S.step = "cart";
    renderCart();
    var ov = $("#ovl-cart");
    if (stack.indexOf(ov) === -1) openOverlay(ov); else ov.scrollTop = 0;
    closeMenu();
  }

  function linesHTML() {
    return '<ul class="lines">' + S.cart.map(function (l) {
      var p = byId(PRODUCTS, l.id);
      var key = esc(lineKey(l));
      return '<li class="line">' +
        '<img src="img/' + p.id + '-s.jpg" alt="" width="76" height="76">' +
        '<div class="line__t"><b>«' + esc(p.name) + "»</b><span>" + esc(p.kind) + "</span>" + (l.v ? "<span>Рисунок: " + esc(l.v) + "</span>" : "") + "</div>" +
        '<div class="qty"><button type="button" data-act="qty" data-d="-1" data-key="' + key + '" aria-label="Меньше"><svg class="ic" aria-hidden="true"><use href="#i-minus"/></svg></button>' +
          "<output aria-live=\"polite\">" + l.q + '</output><button type="button" data-act="qty" data-d="1" data-key="' + key + '" aria-label="Больше"><svg class="ic" aria-hidden="true"><use href="#i-plus"/></svg></button></div>' +
        '<div class="line__p">' + money(p.price * l.q) + "</div>" +
        '<button class="line__x" type="button" data-act="remove" data-key="' + key + '" aria-label="Убрать из корзины"><svg class="ic" aria-hidden="true"><use href="#i-trash"/></svg></button>' +
      "</li>";
    }).join("") + "</ul>";
  }
  function renderCart() {
    var box = $("#cart-view");
    if (S.step === "form" && S.cart.length) { renderForm(box); }
    else if (S.step === "done" && S.order) { renderDone(box); }
    else if (!S.cart.length) {
      box.innerHTML = '<h2 class="sheet__title" id="cart-title">Корзина</h2>' +
        '<div class="cart-empty"><svg viewBox="0 0 64 64" aria-hidden="true"><use href="#i-gull"/></svg>' +
        "<p>Пока пусто. Загляните в каталог: там кони с Мезени и звери из бестиария.</p>" +
        '<a class="btn btn--red" href="#catalog" data-act="close-all">В каталог</a></div>';
    } else {
      var total = cartTotal();
      box.innerHTML = '<h2 class="sheet__title" id="cart-title">Корзина</h2>' + linesHTML() +
        '<dl class="sum">' +
          "<div><dt>Стоимость товаров</dt><dd>" + money(total) + "</dd></div>" +
          "<div><dt>Доставка</dt><dd>согласуем при подтверждении</dd></div>" +
          '<div class="tot"><dt>Итого</dt><dd>' + money(total) + "</dd></div>" +
        "</dl>" +
        '<div class="sheet__cta"><button class="btn btn--red" type="button" data-act="checkout">Оформить заказ</button>' +
        '<button class="link" type="button" data-act="close-all">Продолжить покупки</button></div>' +
        '<p class="sheet__note">Оплаты на сайте нет. Мастер подтвердит наличие и сроки, а способ оплаты и стоимость доставки согласует с вами лично.</p>';
    }
    typoTree(box);
  }

  function renderForm(box) {
    var total = cartTotal();
    box.innerHTML = '<h2 class="sheet__title" id="cart-title">Оформление заказа</h2>' +
      '<form class="frame" id="order-form" novalidate>' +
        "<h3>Как с вами связаться</h3>" +
        '<div class="row2">' +
          '<label class="field" id="w-name"><span class="sr">Имя</span><input id="f-name" name="name" type="text" autocomplete="name" placeholder="Имя" maxlength="60"></label>' +
          '<label class="field" id="w-phone"><span class="sr">Телефон</span><input id="f-phone" name="phone" type="tel" inputmode="tel" autocomplete="tel" placeholder="+7 (___) ___-__-__" maxlength="18"></label>' +
        "</div>" +
        "<h3>Как получить заказ</h3>" +
        '<div class="seg" role="radiogroup" aria-label="Способ получения">' +
          '<label><input type="radio" name="dlv" value="pickup" checked><span>Самовывоз из мастерской</span></label>' +
          '<label><input type="radio" name="dlv" value="ship"><span>Отправка по России</span></label>' +
        "</div>" +
        '<p class="hint" id="dlv-hint">Мастерская: проспект Елизарова, 36А. Пн—сб 10:00—18:00, вс 12:00—18:00. Когда заказ будет готов, мастер напишет или позвонит.</p>' +
        '<div class="row2" id="ship-box" hidden>' +
          '<label class="field" id="w-city"><span class="sr">Город</span><input id="f-city" name="city" type="text" autocomplete="address-level2" placeholder="Город"></label>' +
          '<label class="field" id="w-addr"><span class="sr">Адрес доставки</span><input id="f-addr" name="addr" type="text" autocomplete="street-address" placeholder="Улица, дом, квартира"></label>' +
        "</div>" +
        "<h3>Комментарий к заказу</h3>" +
        '<label class="field"><span class="sr">Комментарий</span><textarea id="f-comment" name="comment" placeholder="Пожелания по рисунку, подарочная упаковка, удобное время для звонка"></textarea></label>' +
        '<label class="chk" id="w-offer"><input type="checkbox" id="f-offer"><span>Принимаю условия <a href="#offer" data-act="doc-open" data-doc="offer">публичной оферты</a></span></label>' +
        '<label class="chk" id="w-consent"><input type="checkbox" id="f-consent"><span>Даю <a href="#consent" data-act="doc-open" data-doc="consent">согласие на обработку персональных данных</a>. Как они используются, описано в <a href="#policy" data-act="doc-open" data-doc="policy">политике конфиденциальности</a></span></label>' +
        '<div class="err" id="f-err" role="alert"></div>' +
        '<div class="frame__cta"><button class="btn btn--red" type="submit">Подтвердить заказ · ' + money(total) + "</button>" +
        '<button class="link" type="button" data-act="back-cart">Вернуться в корзину</button></div>' +
      "</form>";
    typoTree(box);
    $("#f-phone").addEventListener("input", function (e) {
      var el = e.target, d = el.value.replace(/\D/g, "");
      if (!d) { el.value = ""; return; }
      el.value = fmtPhone(d);
    });
    $$('input[name="dlv"]').forEach(function (r) {
      r.addEventListener("change", function () {
        var ship = $('input[name="dlv"]:checked').value === "ship";
        $("#ship-box").hidden = !ship;
        $("#dlv-hint").hidden = ship;
      });
    });
    $("#order-form").addEventListener("submit", submitOrder);
    var n = $("#f-name");
    if (n) n.focus({preventScroll: true});
  }
  function fmtPhone(d) {
    if (d[0] === "8") d = "7" + d.slice(1);
    if (d[0] !== "7") d = "7" + d;
    d = d.slice(0, 11);
    var out = "+7";
    if (d.length > 1) out += " (" + d.slice(1, 4);
    if (d.length >= 4) out += ")";
    if (d.length > 4) out += " " + d.slice(4, 7);
    if (d.length > 7) out += "-" + d.slice(7, 9);
    if (d.length > 9) out += "-" + d.slice(9, 11);
    return out;
  }
  function mark(id, bad) { var w = $(id); if (w) w.classList.toggle("is-bad", !!bad); }
  function submitOrder(e) {
    e.preventDefault();
    var name = $("#f-name").value.trim();
    var phone = $("#f-phone").value.trim();
    var ship = $('input[name="dlv"]:checked').value === "ship";
    var city = ship ? $("#f-city").value.trim() : "";
    var addr = ship ? $("#f-addr").value.trim() : "";
    var comment = $("#f-comment").value.trim();
    var ok = $("#f-consent").checked;
    var offer = $("#f-offer").checked;
    var digits = phone.replace(/\D/g, "");
    var bad = [];
    mark("#w-name", name.length < 2); if (name.length < 2) bad.push("имя");
    mark("#w-phone", digits.length < 11); if (digits.length < 11) bad.push("телефон полностью");
    mark("#w-city", ship && !city); mark("#w-addr", ship && !addr);
    if (ship && (!city || !addr)) bad.push("город и адрес");
    mark("#w-offer", !offer);
    mark("#w-consent", !ok);
    var err = $("#f-err");
    if (bad.length) { err.textContent = "Укажите " + bad.join(", ") + "."; return; }
    if (!offer || !ok) {
      err.textContent = !offer && !ok ? "Нужно принять условия оферты и дать согласие на обработку персональных данных."
        : (!offer ? "Нужно принять условия оферты." : "Нужно согласие на обработку персональных данных.");
      return;
    }
    err.textContent = "";
    var lines = S.cart.map(function (l, i) {
      var p = byId(PRODUCTS, l.id);
      return (i + 1) + ". «" + p.name + "»" + (l.v ? " (" + l.v.toLowerCase() + ")" : "") + " — " + l.q + " × " + money(p.price) + " = " + money(p.price * l.q);
    });
    var text = "Здравствуйте! Хочу заказать:\n" + lines.join("\n") + "\nИтого: " + money(cartTotal()) + "\n\n" +
      "Имя: " + name + "\nТелефон: " + phone + "\n" +
      "Получение: " + (ship ? "отправка по России, " + city + ", " + addr : "самовывоз из мастерской") +
      (comment ? "\nКомментарий: " + comment : "") +
      "\n\nУсловия оферты принимаю. Согласие на обработку персональных данных даю.";
    S.order = text;
    S.step = "done";
    renderCart();
    $("#ovl-cart").scrollTop = 0;
  }
  function renderDone(box) {
    var link = "https://wa.me/" + CONTACT.wa + "?text=" + encodeURIComponent(S.order);
    box.innerHTML = '<div class="done"><h2 class="sheet__title" id="cart-title">Заказ собран</h2>' +
      "<p>Пока он никуда не отправлен. Самый быстрый способ&nbsp;— отправить текст мастеру в WhatsApp. Можно и скопировать его, чтобы написать в другом мессенджере.</p>" +
      '<pre class="order" id="order-text"></pre>' +
      '<div class="done__act"><a class="btn btn--red" href="' + link + '" target="_blank" rel="noopener">Отправить в WhatsApp</a>' +
      '<button class="btn btn--line" type="button" data-act="copy-order">Скопировать текст</button></div>' +
      '<p class="hint hint--call">Или позвоните мастеру:</p>' +
      '<a class="tel" href="tel:+' + CONTACT.wa + '">' + CONTACT.phone + "</a>" +
      '<div class="sheet__cta"><button class="link" type="button" data-act="clear-cart">Очистить корзину и закрыть</button>' +
      '<button class="link" type="button" data-act="back-cart">Изменить заказ</button></div></div>';
    $("#order-text").textContent = S.order;
    typoTree(box);
  }
  function copyOrder() {
    var el = $("#order-text");
    function sel() {
      try {
        var r = document.createRange(); r.selectNodeContents(el);
        var s = window.getSelection(); s.removeAllRanges(); s.addRange(r);
        return document.execCommand("copy");
      } catch (e) { return false; }
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(S.order).then(function () { toast("Текст заказа скопирован"); },
        function () { toast(sel() ? "Текст заказа скопирован" : "Текст выделен: скопируйте его (Ctrl+C)"); });
    } else {
      toast(sel() ? "Текст заказа скопирован" : "Текст выделен: скопируйте его (Ctrl+C)");
    }
  }

  /* ---------- отзывы ---------- */
  function renderReviews() {
    var box = $("#rev-list");
    box.innerHTML = REVIEWS.map(function (r) {
      return '<figure class="q"><blockquote>' + esc(r.text) + "</blockquote>" +
        '<figcaption><span class="who">' + esc(r.who) + '</span><span class="when">' + esc(r.when) + "</span></figcaption></figure>";
    }).join("");
    typoTree(box);
  }

  /* ---------- действия ---------- */
  document.addEventListener("click", function (e) {
    var t = e.target.closest("[data-act]");
    if (!t) {
      var z = e.target.closest("#pm-img");
      if (z) z.classList.toggle("is-zoom");
      return;
    }
    var act = t.getAttribute("data-act"), id = t.getAttribute("data-id");
    switch (act) {
      case "tab":
        S.cat = t.getAttribute("data-cat");
        renderTabs(); renderGrid();
        var sel = $('.tab[aria-pressed="true"]'); if (sel) sel.focus({preventScroll: true});
        break;
      case "open": openProduct(id); break;
      case "add":
        addToCart(id, id === S.openId ? S.variant : null);
        break;
      case "variant":
        S.variant = t.getAttribute("data-v");
        $$(".chip").forEach(function (c) { c.setAttribute("aria-checked", String(c === t)); });
        break;
      case "fav": toggleFav(id); break;
      case "fav-filter":
        S.favOnly = !S.favOnly;
        if (S.favOnly && !S.fav.length) toast("Отметьте сердечком вещи, которые понравились");
        renderGrid();
        break;
      case "cart-open": openCart("cart"); break;
      case "close": closeOverlay(t.closest(".ovl")); break;
      case "close-all":
        while (stack.length) closeOverlay();
        break;
      case "qty": changeQty(t.getAttribute("data-key"), parseInt(t.getAttribute("data-d"), 10)); break;
      case "remove": removeLine(t.getAttribute("data-key")); break;
      case "checkout": S.step = "form"; renderCart(); $("#ovl-cart").scrollTop = 0; break;
      case "back-cart": S.step = "cart"; renderCart(); $("#ovl-cart").scrollTop = 0; break;
      case "copy-order": copyOrder(); break;
      case "clear-cart":
        S.cart = []; S.order = null; S.step = "cart"; saveCart();
        while (stack.length) closeOverlay();
        toast("Корзина очищена");
        break;
      case "doc-open": e.preventDefault(); openOverlay($("#ovl-" + t.getAttribute("data-doc"))); break;
      case "menu-open": openMenu(); break;
      case "menu-close": closeMenu(); break;
    }
    if ((act === "close-all") && t.tagName === "A") { /* переход к #catalog выполнит браузер */ }
  });
  $("#sort").addEventListener("change", function (e) { S.sort = e.target.value; renderGrid(); });
  /* ---------- старт ---------- */
  renderTabs();
  renderGrid();
  renderReviews();
  saveCart();
  typoTree($("#main"));
  typoTree($(".ftr"));
  typoTree($("#menu"));
  ["offer", "policy", "consent"].forEach(function (d) { typoTree($("#ovl-" + d)); });
})();
