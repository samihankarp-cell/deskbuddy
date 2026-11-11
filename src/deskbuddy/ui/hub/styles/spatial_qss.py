"""Stylesheet pieces for the Spatial look: glass inputs, glass and glowing buttons, translucent
scroll bars and a glass menu. Border + padding add up to Classic's, so nothing shifts. The colours
are the variant's tokens (spatial_tokens.py): dark glass over dusk, or white glass over day."""
from deskbuddy.ui.hub.styles.base import FIELD, FIELD_FOCUS

BLUE_TOP, BLUE_BOTTOM = "#5a76ea", "#3a50c6"   # white type on both stays above 4.5:1


def controls(s) -> str:
    t = s.t
    search, search_edge, search_top, search_focus = t.search
    field, field_edge, field_top, field_bottom, field_focus = t.field
    quiet, quiet_edge, quiet_top, quiet_hot, quiet_down = t.quiet
    menu, menu_edge, menu_pick = t.menu
    blue = f"qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {BLUE_TOP}, stop:1 {BLUE_BOTTOM})"
    blue_hot = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #6c86f2, stop:1 #4760d6)"
    blue_down = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3a50c6, stop:1 #4a63d8)"
    return f"""
    QToolTip {{ background: {t.tip_bg}; color: {t.tip_ink}; border: 1px solid {t.tip_edge};
        padding: 4px 8px; }}

    QLineEdit#search {{ background: {search}; color: {s.side_ink};
        border: 1px solid {search_edge}; border-top-color: {search_top};
        border-radius: 16px; padding: 6px 8px 6px 3px; selection-background-color: {BLUE_TOP};
        selection-color: #ffffff; placeholder-text-color: {s.side_meta}; }}
    QLineEdit#search:focus {{ background: {search_focus}; border: 2px solid {s.accent};
        padding: 5px 7px 5px 2px; }}
    {FIELD} {{ background: {field}; color: {s.ink};
        border: 1px solid {field_edge}; border-top-color: {field_top};
        border-bottom-color: {field_bottom}; border-radius: 12px; padding: 8px 11px;
        selection-background-color: {BLUE_TOP}; selection-color: #ffffff;
        placeholder-text-color: {s.meta}; }}
    {FIELD_FOCUS} {{ background: {field_focus};
        border: 2px solid {s.accent}; padding: 7px 10px; }}
    QLineEdit#composerEdit {{ background: transparent; color: {s.ink}; border: none; padding: 6px 4px;
        font-size: 14px; selection-background-color: {BLUE_TOP}; selection-color: #ffffff;
        placeholder-text-color: {s.meta}; }}
    QDateTimeEdit#field::drop-down {{ border: none; width: 22px; }}

    QPushButton#primary {{ background: {blue}; color: #ffffff; border: 1px solid rgba(255, 255, 255, 70);
        border-top-color: rgba(255, 255, 255, 190); border-radius: 15px; padding: 6px 17px;
        font-weight: 600; }}
    QPushButton#primary:hover {{ background: {blue_hot}; }}
    QPushButton#primary:pressed {{ background: {blue_down}; padding-top: 7px; padding-bottom: 5px; }}
    QPushButton#primary:focus {{ border: 2px solid #ffffff; padding: 5px 16px; }}
    QPushButton#quiet {{ background: {quiet}; color: {s.ink};
        border: 1px solid {quiet_edge}; border-top-color: {quiet_top};
        border-radius: 13px; padding: 4px 12px; font-size: 12px; }}
    QPushButton#quiet:hover {{ background: {quiet_hot}; }}
    QPushButton#quiet:pressed {{ background: {quiet_down}; padding-top: 5px; padding-bottom: 3px; }}
    QPushButton#quiet:focus {{ border: 2px solid {s.accent}; padding: 3px 11px; }}

    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
    QScrollBar::handle:vertical {{ background: {t.sb[0]}; border-radius: 3px; min-height: 36px; }}
    QScrollBar::handle:vertical:hover {{ background: {t.sb[1]}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}

    QMenu {{ background: {menu}; border: 1px solid {menu_edge}; border-radius: 12px; padding: 6px; }}
    QMenu::item {{ padding: 7px 18px; border-radius: 8px; color: {s.ink}; }}
    QMenu::item:selected {{ background: {menu_pick}; color: {s.ink}; }}
    """
