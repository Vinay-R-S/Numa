/**
 * Calendar constants (NUMA-114 P4).
 *
 * Layout and window bounds lifted verbatim out of the old
 * `components/calendar/CalendarView.tsx` so grid maths stays identical.
 */

export const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

export const MONTHS = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
]

/** Day/week grid runs 7 AM - 9 PM. */
export const DAY_START_HOUR = 7
export const HOURS = Array.from({ length: 15 }, (_, index) => index + DAY_START_HOUR)

export const SLOT_HEIGHT = 56

/** Collapsed sidebar rail width, so popups never open underneath it. */
export const SIDEBAR_RAIL_WIDTH = 56

/** Drag/resize clamps, in minutes from midnight. */
export const MIN_EVENT_START_MINUTES = DAY_START_HOUR * 60
export const MAX_EVENT_START_MINUTES = 20 * 60
export const MAX_EVENT_END_MINUTES = 21 * 60
export const MIN_EVENT_DURATION_MINUTES = 15
export const DRAG_SNAP_MINUTES = 15

/** Current-time line is only drawn inside this window. */
export const NOW_LINE_START_MINUTES = DAY_START_HOUR * 60
export const NOW_LINE_END_MINUTES = 22 * 60

export const MOBILE_BREAKPOINT = 640
export const DESKTOP_BREAKPOINT = 1024

export const NOW_TICK_MS = 30_000
export const POPUP_CLOSE_DELAY_MS = 130
export const SSE_RELOAD_DEBOUNCE_MS = 500

export const TIMELINE_SETTINGS_KEY = "numa_timeline_settings"
export const DEFAULT_TIMELINE_INTERVAL_MS = 300_000
export const DEFAULT_WATER_CONFIG = { startHour: 8, endHour: 22, stepMinutes: 60 }
export const DISABLED_WATER_CONFIG = { startHour: 0, endHour: 0, stepMinutes: 60 }
export const DEFAULT_MEAL_TIMES = { breakfast: "08:00", lunch: "13:00", dinner: "20:00" }
