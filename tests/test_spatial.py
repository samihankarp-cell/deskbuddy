"""The Spatial look: floating panes that Classic and Skeuomorphic give back, and cached glass."""
from test_hub import classic_again, dash, memory  # noqa: F401  (the hub's fixtures)

from deskbuddy.ui.hub import styles


def test_spatial_floats_the_panes_and_other_looks_put_them_back(dash):
    def edges():
        m = dash.root.contentsMargins()
        return (m.left(), m.top(), m.right(), m.bottom()), dash.root.spacing()

    dash.set_style("spatial")
    look = styles.active()
    assert all(side > 0 for side in look.window_margins) and look.pane_gap > 0
    assert edges() == (look.window_margins, look.pane_gap)
    for other in ("skeuo", "spatial", "classic"):
        dash.set_style(other)
    assert edges() == ((0, 0, 0, 0), 0)


def test_spatial_backdrop_frost_and_panes_are_cached_not_rebuilt_on_refresh(dash, memory):
    dash.set_style("spatial")
    dash.grab()
    names = ("sp_back", "sp_frost", "sp_scene", "sp_pane_sidebar", "sp_pane_centre", "sp_pane_right")
    cache = styles.active()._cache
    before = [cache[name][1] for name in names]
    memory.add_message("buddy", "Done: something new.")
    dash.refresh()
    dash.grab()
    assert all(cache[name][1] is old for name, old in zip(names, before))
