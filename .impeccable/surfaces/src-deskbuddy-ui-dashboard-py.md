---
version: 1
slug: "src-deskbuddy-ui-dashboard-py"
primary_target: "src/deskbuddy/ui/dashboard.py"
related_targets: []
---

# Dashboard surface brief

Scope: the Desk Buddy dashboard window (src/deskbuddy/ui/dashboard.py), Operate mode. Native Qt window, about 980x680, opened on demand from the robot or tray.

Task: give an order; see each job and its honest verdict; manage reminders; see and correct memory; connect services. Glanced at for seconds between browser tasks, often in the evening under a desk lamp.

Decided without the owner (they asked for no questions): direction taken as rolled, not chosen from a hand.

## Direction contract

THESIS: Desk Buddy's dashboard is its card file: every job, reminder, fact and connector is a typed index card filed behind a coloured pressboard divider. It refuses the category default of a dark sidebar, metric tiles and a chat log.

OWN-WORLD: Dark steel drawer ground (#1f2b2a) with a darker drawer face header. Pressboard dividers in saturated, flat colours, one per section: ultramarine, vermilion, ochre, teal, violet. Cool white card stock (#f2f4f7) with square-ish 3px corners and a 2px rule under the card title in its section's divider colour. Segoe UI for all reading text; Bahnschrift SemiBold for divider labels and counts. Verdicts are stamped words, never colour alone.

STORY: The visitor opens the drawer, sees which divider is pulled forward and what each one holds by its count, reads the newest cards first, and acts with the order card at the top or a button on a card.

FIRST VIEWPORT: Drawer face across the top: Kettle at 40px, "Desk Buddy", live status line with a state dot, Settings on the right. Under it, the divider tab row: Today, Activity, Reminders, Memory, Connectors, each a pressboard tab with its live count; the active tab stands taller in full colour and joins the open panel, the others sit back a step. The open panel's top edge carries the active divider colour. Today: a blank order card with its input and Send, then the conversation as cards, newest first.

FORM: Tabbed index-card file, position 6 of 7 on the ordered list. seed:853619edc3dcfd33. Raised from declined challengers: from the acetate tab board, each divider carries its section's live count (extent on the tab); from labanotation, state is never colour alone (stamped word plus colour); from the streaming wall, the active divider lifts and the rest sit back. Kept from the jet-age ticket wallet (competitive): nothing disappears, it cancels: shown reminders stay filed, marked Shown.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
