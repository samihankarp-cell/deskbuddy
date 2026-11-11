"""The two alert switches in Settings. Both default to on; the app asks here before alerting."""

SUGGESTIONS = "alert_suggestions"
REMINDER_TOASTS = "alert_reminder_toasts"


def alert_on(memory, key: str) -> bool:
    return memory.get(key, "1") != "0"


def set_alert(memory, key: str, on: bool) -> None:
    memory.set(key, "1" if on else "0")
