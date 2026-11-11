// Desk Buddy add-on. Connects to the Desk Buddy app on this PC and runs its requests in tabs.
const PORT = 8765;
let ws = null;
const recentTabs = []; // tabs opened lately, so a click that opens a new tab can be followed

function browserName() {
  const ua = navigator.userAgent;
  const brands = (navigator.userAgentData?.brands || []).map((b) => b.brand).join(" ");
  if (ua.includes("Firefox")) return "Firefox";
  if (/Comet/i.test(brands + ua)) return "Comet";
  if (/Brave/i.test(brands) || navigator.brave) return "Brave";
  if (/Edg\//.test(ua)) return "Edge";
  return "Chrome";
}

function send(obj) {
  if (ws && ws.readyState === 1) ws.send(JSON.stringify(obj));
}

function connect() {
  if (ws && ws.readyState <= 1) return;
  try {
    ws = new WebSocket(`ws://127.0.0.1:${PORT}`);
  } catch (e) {
    ws = null;
    return;
  }
  ws.onopen = () => send({ hello: browserName() });
  ws.onmessage = async (event) => {
    const msg = JSON.parse(event.data);
    if (msg.id === undefined) return;
    try {
      const result = await handle(msg.method, msg.params || {});
      send({ id: msg.id, ok: true, result });
    } catch (e) {
      send({ id: msg.id, ok: false, error: String(e?.message || e) });
    }
  };
  ws.onclose = () => { ws = null; setTimeout(connect, 2000); };
  ws.onerror = () => { try { ws.close(); } catch (e) {} };
}

// Keep the connection (and this background worker) alive.
chrome.alarms.create("deskbuddy-keepalive", { periodInMinutes: 0.5 });
chrome.alarms.onAlarm.addListener(connect);
chrome.runtime.onStartup.addListener(connect);
chrome.runtime.onInstalled.addListener(connect);
setInterval(() => send({ keepalive: 1 }), 20000);
connect();

// Tell Desk Buddy when this browser is the one being used.
chrome.tabs.onActivated.addListener(() => send({ active: 1 }));
chrome.windows.onFocusChanged.addListener((id) => { if (id !== chrome.windows.WINDOW_ID_NONE) send({ active: 1 }); });
chrome.tabs.onCreated.addListener((tab) => {
  recentTabs.push({ id: tab.id, opener: tab.openerTabId, at: Date.now() });
  while (recentTabs.length > 20) recentTabs.shift();
});

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function waitLoaded(tabId, ms = 15000) {
  const end = Date.now() + ms;
  let tab = await chrome.tabs.get(tabId);
  while (tab.status !== "complete" && Date.now() < end) {
    await sleep(250);
    tab = await chrome.tabs.get(tabId);
  }
  return tab;
}

const info = (tab) => ({ tabId: tab.id, url: tab.url || tab.pendingUrl || "", title: tab.title || "", windowId: tab.windowId, active: tab.active });

async function inPage(tabId, func, args = []) {
  const results = await chrome.scripting.executeScript({ target: { tabId }, func, args });
  const value = results && results[0] ? results[0].result : null;
  if (value && value.error) throw new Error(value.error);
  return value;
}

async function handle(method, p) {
  switch (method) {
    case "list":
      return (await chrome.tabs.query({})).map(info);
    case "active": {
      const [tab] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
      if (!tab) throw new Error("no tab is open");
      return info(tab);
    }
    case "open": {
      let tab;
      if (p.newWindow) {
        const win = await chrome.windows.create(p.url ? { url: p.url, focused: true } : { focused: true });
        tab = win.tabs[0];
      } else {
        tab = await chrome.tabs.create(p.url ? { url: p.url, active: true } : { active: true });
      }
      return info(await waitLoaded(tab.id));
    }
    case "navigate":
      await chrome.tabs.update(p.tabId, { url: p.url });
      await sleep(300);
      return info(await waitLoaded(p.tabId));
    case "back":
      await chrome.tabs.goBack(p.tabId);
      await sleep(400);
      return info(await waitLoaded(p.tabId));
    case "close":
      await chrome.tabs.remove(p.tabId);
      return { closed: true };
    case "activate": {
      const tab = await chrome.tabs.update(p.tabId, { active: true });
      await chrome.windows.update(tab.windowId, { focused: true });
      return info(tab);
    }
    case "info":
      return info(await chrome.tabs.get(p.tabId));
    case "wait":
      return info(await waitLoaded(p.tabId, p.ms || 15000));
    case "look":
      return inPage(p.tabId, pageLook, [p.max || 120]);
    case "click": {
      const before = Date.now();
      const result = await inPage(p.tabId, pageClick, [p.id]);
      await sleep(900);
      const opened = recentTabs.filter((t) => t.at >= before && t.opener === p.tabId).pop();
      const tab = await waitLoaded(opened ? opened.id : p.tabId, 12000);
      return { ...result, ...info(tab), newTab: Boolean(opened) };
    }
    case "type": {
      const result = await inPage(p.tabId, pageType, [p.id, p.text, Boolean(p.enter)]);
      if (p.enter) { await sleep(900); await waitLoaded(p.tabId, 12000); }
      return { ...result, ...info(await chrome.tabs.get(p.tabId)) };
    }
    case "scroll":
      return inPage(p.tabId, pageScroll, [p.direction]);
    case "text":
      return inPage(p.tabId, (max) => ({ url: location.href, title: document.title, text: (document.body?.innerText || "").slice(0, max) }), [p.max || 8000]);
    case "media":
      return inPage(p.tabId, pageMedia, [p.sampleMs || 1200]);
    case "play":
      return inPage(p.tabId, pagePlay, []);
    case "ytfirst":
      return inPage(p.tabId, () => {
        const link = document.querySelector("ytd-video-renderer a#video-title, ytd-rich-item-renderer a#video-title-link");
        return link ? { href: link.href, title: (link.title || link.innerText || "").trim() } : { href: null };
      }, []);
    default:
      throw new Error(`unknown request: ${method}`);
  }
}

// ---- functions below run inside the web page ------------------------------

function pageLook(max) {
  const selector = 'a[href],button,input,textarea,select,summary,[role=button],[role=link],[role=tab],[role=menuitem],[role=option],[role=checkbox],[role=textbox],[role=searchbox],[role=combobox],[contenteditable=""],[contenteditable=true],[onclick]';
  document.querySelectorAll("[data-deskbuddy]").forEach((e) => e.removeAttribute("data-deskbuddy"));
  const out = [];
  const vh = innerHeight, vw = innerWidth;
  for (const el of document.querySelectorAll(selector)) {
    const r = el.getBoundingClientRect();
    if (r.width < 4 || r.height < 4) continue;
    if (r.bottom < -vh || r.top > vh * 2.5 || r.right < 0 || r.left > vw) continue;
    const st = getComputedStyle(el);
    if (st.visibility === "hidden" || st.display === "none" || el.disabled || el.type === "hidden") continue;
    const label = (el.getAttribute("aria-label") || el.placeholder || el.name || el.title || "").slice(0, 60);
    const text = (el.innerText || el.value || el.alt || "").replace(/\s+/g, " ").trim().slice(0, 90);
    if (!text && !label) continue;
    el.setAttribute("data-deskbuddy", String(out.length));
    out.push({ id: out.length, tag: el.tagName.toLowerCase(), type: el.type || el.getAttribute("role") || "", text, label, inView: r.top >= 0 && r.bottom <= vh });
    if (out.length >= max) break;
  }
  return { url: location.href, title: document.title, scrollY: Math.round(scrollY), pageHeight: document.documentElement.scrollHeight, viewHeight: vh, elements: out };
}

function pageClick(id) {
  const el = document.querySelector(`[data-deskbuddy="${id}"]`);
  if (!el) return { error: `element ${id} is no longer on the page; look again` };
  el.scrollIntoView({ block: "center" });
  if (el.focus) el.focus();
  el.click();
  return { clicked: (el.innerText || el.value || el.getAttribute("aria-label") || "").trim().slice(0, 80) };
}

function pageType(id, text, enter) {
  const el = document.querySelector(`[data-deskbuddy="${id}"]`);
  if (!el) return { error: `element ${id} is no longer on the page; look again` };
  if (el.type === "password") return { error: "that is a password box; Desk Buddy never types passwords" };
  el.scrollIntoView({ block: "center" });
  el.focus();
  if (el.isContentEditable) {
    document.execCommand("selectAll", false, null);
    document.execCommand("insertText", false, text);
  } else if (el.tagName === "SELECT") {
    const want = text.toLowerCase();
    const option = [...el.options].find((o) => o.text.toLowerCase().includes(want) || o.value.toLowerCase() === want);
    if (!option) return { error: `no option like "${text}" in that list` };
    el.value = option.value;
    el.dispatchEvent(new Event("change", { bubbles: true }));
  } else {
    const proto = el.tagName === "TEXTAREA" ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    const setter = Object.getOwnPropertyDescriptor(proto, "value")?.set;
    if (setter) setter.call(el, text); else el.value = text;
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
  }
  const value = el.isContentEditable ? el.innerText : (el.tagName === "SELECT" ? el.options[el.selectedIndex].text : el.value);
  if (enter) {
    const opts = { key: "Enter", code: "Enter", keyCode: 13, which: 13, bubbles: true, cancelable: true };
    const notCancelled = el.dispatchEvent(new KeyboardEvent("keydown", opts));
    el.dispatchEvent(new KeyboardEvent("keypress", opts));
    el.dispatchEvent(new KeyboardEvent("keyup", opts));
    if (notCancelled && el.form) { if (el.form.requestSubmit) el.form.requestSubmit(); else el.form.submit(); }
  }
  return { value };
}

function pageScroll(direction) {
  const before = scrollY;
  const step = innerHeight * 0.85;
  if (direction === "top") scrollTo(0, 0);
  else if (direction === "bottom") scrollTo(0, document.documentElement.scrollHeight);
  else scrollBy(0, direction === "up" ? -step : step);
  return new Promise((resolve) => setTimeout(() => resolve({ before: Math.round(before), after: Math.round(scrollY), pageHeight: document.documentElement.scrollHeight }), 350));
}

async function pageMedia(sampleMs) {
  const media = [...document.querySelectorAll("video,audio")].sort((a, b) => (b.duration || 0) - (a.duration || 0))[0];
  if (!media) return null;
  const start = media.currentTime;
  await new Promise((r) => setTimeout(r, sampleMs));
  const advanced = media.currentTime > start;
  return { paused: media.paused, playing: !media.paused && advanced, currentTime: Math.round(media.currentTime * 10) / 10, muted: media.muted, title: document.title };
}

async function pagePlay() {
  const media = [...document.querySelectorAll("video,audio")].sort((a, b) => (b.duration || 0) - (a.duration || 0))[0];
  if (!media) return { error: "there is no video or audio on this page" };
  try { await media.play(); } catch (e) {
    const button = document.querySelector(".ytp-play-button, [aria-label*='Play' i]");
    if (button) button.click();
  }
  return { paused: media.paused };
}
