"""The dashboard window now lives in the hub package; this keeps the old import working."""
from deskbuddy.ui.hub.window import Dashboard

__all__ = ["Dashboard"]
