"""Stylesheet pieces for the Skeuomorphic look: bevelled buttons, inset wells, metal scroll bars.
Border widths match Classic's sizes (border + padding stay the same total), so nothing shifts.
Colours come from the variant's tokens (skeuo_tokens.py)."""
from deskbuddy.ui.hub.styles.base import FIELD, FIELD_FOCUS


def grad(top: str, bottom: str) -> str:
    return f"qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {top}, stop:1 {bottom})"


def _side(a: str, b: str, c: str) -> str:
    return f"qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {a}, stop:0.5 {b}, stop:1 {c})"


def controls(s) -> str:
    t = s.t
    well, pri = grad(*t.field), grad(*t.primary)
    pri_hot, pri_down = grad(*t.primary_hot), grad(*t.primary_down)
    quiet, quiet_hot, quiet_down = grad(*t.quiet), grad(*t.quiet_hot), grad(*t.quiet_down)
    return f"""
    QLabel#bubbleMeText {{ color: {t.me_ink}; font-size: 13px; }}
    QFrame#preview QLabel#status {{ color: #f0e6cf; font-size: 12px; }}
    QToolTip {{ background: {t.tip_bg}; color: {t.tip_ink}; border: 1px solid {t.tip_edge}; padding: 4px 8px; }}

    QLineEdit#search {{ background: {grad("#24150a", "#3a2415")}; color: {s.side_ink};
        border: 1px solid #170c04; border-bottom-color: #8a6a4a; border-radius: 11px;
        padding: 6px 7px 6px 3px; selection-background-color: #e8cf98; selection-color: #2a1a0c;
        placeholder-text-color: {s.side_meta}; }}
    QLineEdit#search:focus {{ background: {grad("#1c1007", "#322012")}; border: 2px solid #e8cf98;
        padding: 5px 6px 5px 2px; }}
    {FIELD} {{ background: {well}; color: {s.ink};
        border: 1px solid {t.field_edge[0]}; border-top-color: {t.field_edge[1]};
        border-bottom-color: {t.field_edge[2]}; border-radius: 10px; padding: 7px 10px;
        selection-background-color: {t.field_sel[0]}; selection-color: {t.field_sel[1]}; {s.ph(s.meta)} }}
    {FIELD_FOCUS} {{ border: 2px solid {s.accent}; padding: 6px 9px; }}
    QLineEdit#composerEdit {{ background: transparent; color: {s.ink}; border: none; padding: 6px 4px;
        font-size: 14px; {s.ph(s.meta)} }}
    QDateTimeEdit#field::drop-down {{ border: none; width: 22px; }}

    QPushButton#primary {{ background: {pri}; color: {t.primary_ink}; border: 1px solid {t.primary_edge[0]};
        border-top-color: {t.primary_edge[1]}; border-bottom-color: {t.primary_edge[2]}; border-radius: 16px;
        padding: 6px 17px; font-weight: 600; }}
    QPushButton#primary:hover {{ background: {pri_hot}; }}
    QPushButton#primary:pressed {{ background: {pri_down}; padding-top: 7px; padding-bottom: 5px; }}
    QPushButton#primary:focus {{ border: 2px solid {s.accent}; padding: 5px 16px; }}
    QPushButton#quiet {{ background: {quiet}; color: {s.ink}; border: 1px solid {t.quiet_edge[0]};
        border-top-color: {t.quiet_edge[1]}; border-bottom-color: {t.quiet_edge[2]}; border-radius: 12px;
        padding: 4px 12px; font-size: 12px; }}
    QPushButton#quiet:hover {{ background: {quiet_hot}; }}
    QPushButton#quiet:pressed {{ background: {quiet_down}; padding-top: 5px; padding-bottom: 3px;
        border-top-color: {t.quiet_edge[2]}; border-bottom-color: {t.quiet_edge[1]}; }}
    QPushButton#quiet:focus {{ border: 2px solid {s.accent}; padding: 3px 11px; }}

    QScrollBar:vertical {{ background: {t.sb_track}; width: 10px; margin: 2px; border-radius: 5px; }}
    QScrollBar::handle:vertical {{ background: {_side(*t.sb)}; border: 1px solid {t.sb_edge};
        border-radius: 4px; min-height: 36px; }}
    QScrollBar::handle:vertical:hover {{ background: {_side(*t.sb_hot)}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}

    QMenu {{ background: {t.menu}; border: 1px solid {t.menu_edge}; border-radius: 10px; padding: 6px; }}
    QMenu::item {{ padding: 7px 18px; border-radius: 6px; color: {s.ink}; }}
    QMenu::item:selected {{ background: {grad(*t.menu_pick)}; color: {t.menu_pick_ink}; }}
    """
