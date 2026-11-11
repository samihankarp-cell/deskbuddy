"""The moods Desk Buddy can be in, and the colour that shows each one."""
from enum import Enum


class BuddyState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    WORKING = "working"
    ASKING = "asking"
    DONE = "done"
    COULDNT = "couldnt"


STATE_COLORS: dict[BuddyState, str] = {
    BuddyState.IDLE: "#ff7a59",
    BuddyState.LISTENING: "#3db8ff",
    BuddyState.THINKING: "#b388ff",
    BuddyState.WORKING: "#ffb347",
    BuddyState.ASKING: "#ffd23f",
    BuddyState.DONE: "#35c8a0",
    BuddyState.COULDNT: "#8a94a6",
}
