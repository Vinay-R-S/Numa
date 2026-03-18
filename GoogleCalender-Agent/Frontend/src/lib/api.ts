export interface CalendarEvent {
  id: string;
  title: string;
  date: Date;
  startTime: string;
  endTime: string;
  description: string;
  color?: string;
  calendarName?: string;
  readonly?: boolean;
}

export interface CalendarEventPayload {
  title: string;
  date: string;
  startTime: string;
  endTime: string;
  description: string;
}

interface EventsApiResponse {
  events: Array<{
    id: string;
    title: string;
    date: string;
    startTime: string;
    endTime: string;
    description: string;
    color?: string;
    calendarName?: string;
    readonly?: boolean;
  }>;
}

interface AgentApiResponse {
  response: string;
  success?: boolean;
  refreshCalendar?: boolean;
}

export interface AgentChatMessage {
  role: "user" | "assistant";
  content: string;
}

interface DeleteResponse {
  success: boolean;
}

interface BackendHealthResponse {
  status: string;
}

interface WatchStartResponse {
  success: boolean;
}

const API_BASE_URL = (import.meta.env.VITE_BACKEND_API_URL || "http://localhost:8000").replace(/\/$/, "");

async function parseJsonResponse<T>(response: Response, fallbackMessage: string): Promise<T> {
  if (!response.ok) {
    let detail = fallbackMessage;

    try {
      const body = await response.json();
      if (typeof body?.detail === "string") {
        detail = body.detail;
      }
    } catch {
      // Keep fallback message when no JSON body is available.
    }

    throw new Error(detail);
  }

  return response.json() as Promise<T>;
}

export async function fetchEvents(): Promise<CalendarEvent[]> {
  const response = await fetch(`${API_BASE_URL}/events`);
  const data = await parseJsonResponse<EventsApiResponse>(response, "Failed to load events");

  return (data?.events ?? []).map((e) => ({
    ...e,
    date: new Date(e.date),
  }));
}

export async function createCalendarEvent(payload: CalendarEventPayload): Promise<CalendarEvent> {
  const response = await fetch(`${API_BASE_URL}/events`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const data = await parseJsonResponse<EventsApiResponse["events"][number]>(response, "Failed to create event");
  return { ...data, date: new Date(data.date) };
}

export async function updateCalendarEvent(eventId: string, payload: CalendarEventPayload): Promise<CalendarEvent> {
  const response = await fetch(`${API_BASE_URL}/events/${eventId}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const data = await parseJsonResponse<EventsApiResponse["events"][number]>(response, "Failed to update event");
  return { ...data, date: new Date(data.date) };
}

export async function deleteCalendarEvent(eventId: string): Promise<boolean> {
  const response = await fetch(`${API_BASE_URL}/events/${eventId}`, {
    method: "DELETE",
  });
  const data = await parseJsonResponse<DeleteResponse>(response, "Failed to delete event");
  return data.success;
}

export async function checkBackendStatus(): Promise<boolean> {
  const response = await fetch(`${API_BASE_URL}/health`);
  const data = await parseJsonResponse<BackendHealthResponse>(response, "Backend unavailable");
  return data.status === "running";
}

export async function startCalendarWatch(): Promise<boolean> {
  const response = await fetch(`${API_BASE_URL}/watch/start`, {
    method: "POST",
  });
  const data = await parseJsonResponse<WatchStartResponse>(response, "Failed to start calendar watch");
  return data.success;
}

export function subscribeToCalendarUpdates(onUpdate: () => void): () => void {
  const source = new EventSource(`${API_BASE_URL}/events/stream`);

  const handleUpdate = () => {
    onUpdate();
  };

  source.addEventListener("calendar-updated", handleUpdate as EventListener);

  return () => {
    source.removeEventListener("calendar-updated", handleUpdate as EventListener);
    source.close();
  };
}

export async function sendAgentCommand(query: string, history: AgentChatMessage[] = []): Promise<AgentApiResponse> {
  const response = await fetch(`${API_BASE_URL}/agent`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ query, history }),
  });
  const data = await parseJsonResponse<AgentApiResponse>(response, "Agent request failed");

  if (data.success === false) {
    throw new Error(data.response || "Agent request failed");
  }

  return data ?? { response: "No response received." };
}
