"""Browser tool safety: what asks the user first, and that clicks use the per-look token."""
from types import SimpleNamespace

import pytest

from deskbuddy.browser import tools as bt


def el(id, text="", label="", tag="button", type="", inView=True):
    return {"id": id, "tag": tag, "type": type, "text": text, "label": label, "inView": inView}


def ctx_with(*elements, token="abc123"):
    return SimpleNamespace(elements={e["id"]: e for e in elements}, look_token=token)


# ---- Enter ----------------------------------------------------------------

def test_enter_in_message_box_asks():
    ctx = ctx_with(el(1, text="", label="Message", tag="textarea"))
    ask = bt._type_risk(ctx, {"id": 1, "text": "hello", "press_enter": True})
    assert ask and "hello" in ask and "Message" in ask and "Enter" in ask


@pytest.mark.parametrize("e", [
    el(1, label="Search", tag="input", type="text"),
    el(1, label="", tag="input", type="search"),
    el(1, label="", tag="div", type="searchbox"),
    el(1, label="Find a product", tag="input"),
    el(1, label="q", tag="input"),
    el(1, text="Query", tag="input"),
])
def test_enter_in_search_box_does_not_ask(e):
    assert bt._type_risk(ctx_with(e), {"id": 1, "text": "cats", "press_enter": True}) is None


def test_no_enter_does_not_ask():
    ctx = ctx_with(el(1, label="Message", tag="textarea"))
    assert bt._type_risk(ctx, {"id": 1, "text": "hello"}) is None
    assert bt._type_risk(ctx, {"id": 1, "text": "hello", "press_enter": False}) is None


# ---- click wording ----------------------------------------------------------

@pytest.mark.parametrize("text", [
    "Delete forever", "Remove", "Empty trash", "Close account", "Deactivate", "Uninstall",
    "Jetzt kaufen", "Zur Kasse", "Comprar", "Acheter", "Acquista", "खरीदें", "Bezahlen", "Pagar",
    "Enviar", "Envoyer", "Senden", "Invia", "भेजें", "Absenden",
    "Supprimer", "Löschen", "Eliminar", "Excluir", "Elimina", "हटाएं", "Entfernen",
    "Iniciar sesión", "Se connecter", "Anmelden", "Accedi", "साइन इन", "Entrar",
    "Send message", "Buy now", "Sign in",
])
def test_risky_clicks_ask(text):
    assert bt._click_risk(ctx_with(el(1, text=text)), {"id": 1}), text


@pytest.mark.parametrize("text", ["Sent items", "Search", "Next", "Settings", "Home", "Menu"])
def test_harmless_clicks_do_not_ask(text):
    assert bt._click_risk(ctx_with(el(1, text=text)), {"id": 1}) is None


def test_delete_wording():
    assert "deletes" in bt._click_risk(ctx_with(el(1, text="Delete forever")), {"id": 1})


def test_label_matches_too():
    assert bt._click_risk(ctx_with(el(1, text="", label="Supprimer")), {"id": 1})


# ---- token ------------------------------------------------------------------

class FakeBridge:
    connected = True
    browser = "Chrome"

    def __init__(self):
        self.calls = []

    def call(self, method, **kw):
        self.calls.append((method, kw))
        if method == "active":
            return {"tabId": 7}
        if method == "text":
            return {"url": "https://x.test", "title": "t", "text": "same"}
        if method == "look":
            return {"url": "https://x.test", "title": "t", "scrollY": 0, "pageHeight": 10, "token": "feedbeef",
                    "elements": [el(0, text="Go")]}
        if method == "click":
            return {"url": "https://x.test", "title": "t"}
        if method == "type":
            return {"value": kw["text"], "url": "https://x.test", "title": "t"}
        return {}


def make_ctx(bridge):
    return SimpleNamespace(bridge=bridge, tab_id=None, elements={}, look_token="", places=set(),
                           step=lambda s: None)


def test_look_stores_token_and_click_type_send_it():
    bridge = FakeBridge()
    ctx = make_ctx(bridge)
    bt.browser_look(ctx)
    assert ctx.look_token == "feedbeef"
    ctx.elements[1] = el(1, tag="input", label="Name")
    bt.browser_click(ctx, id=0)
    bt.browser_type(ctx, id=1, text="Bob")
    sent = {m: kw for m, kw in bridge.calls if m in ("click", "type")}
    assert sent["click"]["token"] == "feedbeef"
    assert sent["type"]["token"] == "feedbeef"
