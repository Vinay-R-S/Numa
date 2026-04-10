# Google Calendar Database Schema

> Format: DBML (dbdiagram.io)
> Scope: Calendar data only

---

## Tables

| Name | Type | Purpose |
|---|---|---|
| users | Table | Google-authenticated user profile |
| calendars | Table | Calendars linked to a user |
| events | Table | Calendar events |
| attendees | Table | Event attendees |
| watch_channels | Table | Google Calendar push watch channels |

---

## Schema (DBML)

```dbml
// Use DBML to define your database structure
// Docs: https://dbml.dbdiagram.io/docs

Table users {
  id integer [pk, increment]
  google_id varchar(255) [not null, unique, note: 'Google account subject id']
  email varchar(320) [not null, unique]
  display_name varchar(255)
  timezone varchar(64) [not null, default: 'Asia/Kolkata']
  created_at timestamp [default: `CURRENT_TIMESTAMP`]
  updated_at timestamp [default: `CURRENT_TIMESTAMP`]
}

Table calendars {
  id integer [pk, increment]
  user_id integer [not null]
  google_cal_id varchar(512) [not null]
  name varchar(255) [not null]
  access_role varchar(16) [not null, default: 'owner', note: 'owner | writer | reader']
  is_primary boolean [not null, default: 0]
  sync_token text
  last_synced_at timestamp
  created_at timestamp [default: `CURRENT_TIMESTAMP`]
  updated_at timestamp [default: `CURRENT_TIMESTAMP`]

  indexes {
    (user_id, google_cal_id) [unique]
    user_id
  }
}

Table events {
  id integer [pk, increment]
  calendar_id integer [not null]
  google_event_id varchar(512) [not null]
  title varchar(512) [not null, default: '(No title)']
  description text
  location varchar(512)
  start_datetime timestamp [not null]
  end_datetime timestamp [not null]
  is_all_day boolean [not null, default: 0]
  status varchar(16) [not null, default: 'confirmed', note: 'confirmed | tentative | cancelled']
  etag varchar(255)
  recurring_event_id varchar(512)
  deleted_at timestamp
  created_at timestamp [default: `CURRENT_TIMESTAMP`]
  updated_at timestamp [default: `CURRENT_TIMESTAMP`]

  indexes {
    (calendar_id, google_event_id) [unique]
    (calendar_id, start_datetime)
    recurring_event_id
  }
}

Table attendees {
  id integer [pk, increment]
  event_id integer [not null]
  email varchar(320) [not null]
  display_name varchar(255)
  response_status varchar(16) [not null, default: 'needsAction', note: 'needsAction | accepted | declined | tentative']
  is_organizer boolean [not null, default: 0]
  is_self boolean [not null, default: 0]
  optional boolean [not null, default: 0]
  created_at timestamp [default: `CURRENT_TIMESTAMP`]
  updated_at timestamp [default: `CURRENT_TIMESTAMP`]

  indexes {
    (event_id, email) [unique]
    (event_id, response_status)
  }
}

Table watch_channels {
  id integer [pk, increment]
  user_id integer [not null]
  calendar_id integer [not null]
  channel_uuid varchar(64) [not null, unique]
  google_resource_id varchar(255)
  status varchar(16) [not null, default: 'active', note: 'active | expired | stopped']
  expires_at timestamp
  registered_at timestamp [default: `CURRENT_TIMESTAMP`]
  last_notification_at timestamp
  created_at timestamp [default: `CURRENT_TIMESTAMP`]
  updated_at timestamp [default: `CURRENT_TIMESTAMP`]

  indexes {
    user_id
    calendar_id
    status
    expires_at
  }
}

Ref calendars_user: calendars.user_id > users.id
Ref events_calendar: events.calendar_id > calendars.id
Ref attendees_event: attendees.event_id > events.id
Ref watch_channels_user: watch_channels.user_id > users.id
Ref watch_channels_calendar: watch_channels.calendar_id > calendars.id
```

---

## Relationships

```text
users -> calendars -> events -> attendees
users -> watch_channels
calendars -> watch_channels
```

---

## Overview

This schema is designed for a calendar-first backend with Google Calendar sync support.
It avoids agent/chat/email concerns and focuses only on data required to:

1. Store users and their connected calendars.
2. Persist events with recurrence and sync metadata.
3. Track attendees and RSVP status.
4. Track Google watch channels for push-based updates.

The core design is normalized and read-friendly:

1. One user can own many calendars.
2. One calendar can contain many events.
3. One event can have many attendees.
4. One calendar can have many watch channels over time.

---

## Table Details

### users

Purpose:

1. Stores a unique Google identity for each app user.
2. Stores profile and timezone metadata needed for calendar rendering.

Important columns:

1. google_id: immutable Google subject id and main identity anchor.
2. email: unique contact/login identity.
3. timezone: default timezone used for display and parsing.

Design notes:

1. google_id and email are unique to prevent duplicate user records.
2. created_at and updated_at support auditing and change tracking.

### calendars

Purpose:

1. Represents every Google calendar connected to a user account.
2. Stores sync checkpoints and access permissions.

Important columns:

1. google_cal_id: Google calendar id from the API.
2. access_role: indicates read/write capability.
3. sync_token: incremental sync cursor from Google.
4. last_synced_at: timestamp of most recent successful sync.

Design notes:

1. Unique index on (user_id, google_cal_id) prevents duplicate linked calendars.
2. user_id index speeds up listing calendars for the current user.

### events

Purpose:

1. Stores calendar events as the main operational dataset.
2. Supports deduplication, recurrence linking, and soft delete semantics.

Important columns:

1. google_event_id: source event id from Google.
2. start_datetime and end_datetime: authoritative time range.
3. recurring_event_id: links instance events to a recurring parent.
4. etag: useful for conflict detection and incremental updates.
5. deleted_at: soft delete marker for sync-safe deletion.

Design notes:

1. Unique index on (calendar_id, google_event_id) blocks duplicate event imports.
2. (calendar_id, start_datetime) index helps range queries for month/day views.
3. recurring_event_id index helps fetch all recurrence instances quickly.

### attendees

Purpose:

1. Stores invitees and RSVP state for each event.
2. Supports organizer/self flags and optional attendees.

Important columns:

1. email: attendee identity.
2. response_status: RSVP state.
3. is_organizer and is_self: role indicators from Google data.

Design notes:

1. Unique index on (event_id, email) prevents duplicate attendee rows.
2. (event_id, response_status) index helps RSVP summary queries.

### watch_channels

Purpose:

1. Persists Google push notification channel registrations.
2. Tracks channel lifecycle for renewals and reliability.

Important columns:

1. channel_uuid: app-generated unique channel id.
2. google_resource_id: Google resource binding for webhook validation.
3. status: active, expired, or stopped lifecycle state.
4. expires_at: renewal planning timestamp.

Design notes:

1. user_id and calendar_id indexes support per-user/per-calendar channel lookups.
2. expires_at index helps schedule renewal jobs.

---

## Data Flow Mapping

1. User connects account.
2. calendars rows are created/updated from CalendarList API.
3. events are synced per calendar using sync_token.
4. attendees are upserted per event from event attendee payload.
5. watch_channels rows are created when watch is registered and updated on renewal.

---

## Query Patterns Supported

1. List all calendars for a user: filter calendars by user_id.
2. Fetch a calendar range: filter events by calendar_id and start_datetime.
3. Resolve recurring chain: filter events by recurring_event_id.
4. Compute RSVP stats: group attendees by response_status for a given event_id.
5. Find channels to renew: filter watch_channels by status and expires_at.

---

## Notes

1. The DBML block is kept exactly as your current working schema.
2. Explanations are intentionally verbose so this can be used as project documentation.
3. For dbdiagram rendering, paste only the DBML code block if markdown wrapper causes confusion.
4. If needed, I can add an SQL migration section aligned to SQLite or Postgres.
