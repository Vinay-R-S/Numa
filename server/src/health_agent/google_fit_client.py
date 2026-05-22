"""
Google Fit API Client for Numa Health Agent.

Handles OAuth 2.0 authentication and fetches fitness data:
steps, calories, active minutes, distance, sleep (with stages), activities.

Credentials file: server/config/credentials.json  (or GOOGLE_FIT_CREDENTIALS_FILE env)
Token file:       server/config/token.json
"""

import os
import threading
from datetime import datetime
from typing import Optional, Dict, Any, List

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class GoogleFitClient:

    SCOPES = [
        'https://www.googleapis.com/auth/fitness.activity.read',
        'https://www.googleapis.com/auth/fitness.sleep.read',
        'https://www.googleapis.com/auth/fitness.location.read',
        'https://www.googleapis.com/auth/fitness.heart_rate.read',
    ]

    ACTIVITY_MAP = {
        7: "walking", 8: "running", 1: "biking", 3: "still", 4: "unknown",
        6: "tilting", 9: "automotive", 16: "gym_workout", 35: "hiking",
        82: "swimming", 97: "yoga", 98: "meditation", 80: "strength_training",
        72: "sleeping", 100: "yoga", 101: "zumba",
    }
    EXCLUDED = {"still", "unknown", "tilting", "automotive", "sleeping"}

    def __init__(self, credentials_file: str = None, token_file: str = None, user_id: str = None):
        config_dir = os.path.join(os.path.dirname(__file__), '..', 'config')
        default_creds = os.getenv('GOOGLE_FIT_CREDENTIALS_FILE', 'credentials.json')
        if not os.path.isabs(default_creds):
            default_creds = os.path.join(config_dir, default_creds)
        self.credentials_file = credentials_file or default_creds
        default_token = os.getenv('GOOGLE_FIT_TOKEN_FILE', 'token.json')
        if not os.path.isabs(default_token):
            default_token = os.path.join(config_dir, default_token)
        self.token_file = self._normalize_token_file(token_file or default_token)
        self.user_id = user_id
        self._service = None
        self._request_lock = threading.RLock()

    @staticmethod
    def _normalize_token_file(path: str) -> str:
        path = os.path.expanduser(path.strip().strip("\"'"))
        if os.path.isdir(path) or path.endswith((os.sep, "/", "\\")):
            return os.path.join(path, "google_fit_token.json")
        return path

    def _client_config_from_env(self) -> Optional[dict]:
        client_id = os.getenv("GOOGLE_FIT_CLIENT_ID", "").strip()
        client_secret = os.getenv("GOOGLE_FIT_CLIENT_SECRET", "").strip()
        if not client_id or not client_secret:
            return None

        return {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost"],
            }
        }

    def _authenticate(self) -> Credentials:
        if self.user_id:
            try:
                from ..calendar.service import get_credentials
                return get_credentials(user_id=self.user_id)
            except RuntimeError as exc:
                raise RuntimeError(
                    "Google Fit is not connected for this user. Reconnect Google from Calendar so the token includes Fitness scopes."
                ) from exc

        creds = None
        if os.path.isfile(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, self.SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_file):
                    client_config = self._client_config_from_env()
                    if not client_config:
                        raise FileNotFoundError(
                            f"'{self.credentials_file}' not found and GOOGLE_FIT_CLIENT_ID/GOOGLE_FIT_CLIENT_SECRET are not set. "
                            "Add Google Fit credentials in Settings or download OAuth credentials from Google Cloud Console."
                        )
                    flow = InstalledAppFlow.from_client_config(client_config, self.SCOPES)
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, self.SCOPES)
                creds = flow.run_local_server(port=0)
            os.makedirs(os.path.dirname(self.token_file), exist_ok=True)
            with open(self.token_file, 'w') as f:
                f.write(creds.to_json())
        return creds

    def _get_service(self):
        if not self._service:
            creds = self._authenticate()
            self._service = build('fitness', 'v1', credentials=creds, cache_discovery=False)
        return self._service

    # ── Extraction helpers ───────────────────────────────────────────────────

    @staticmethod
    def _extract_int(response: dict) -> Optional[int]:
        total, found = 0, False
        for bucket in response.get('bucket', []):
            for dataset in bucket.get('dataset', []):
                for point in dataset.get('point', []):
                    for val in point.get('value', []):
                        if 'intVal' in val:
                            total += val['intVal']; found = True
                        elif 'fpVal' in val:
                            total += int(val['fpVal']); found = True
        return total if found else None

    @staticmethod
    def _extract_float(response: dict) -> Optional[float]:
        total, found = 0.0, False
        for bucket in response.get('bucket', []):
            for dataset in bucket.get('dataset', []):
                for point in dataset.get('point', []):
                    for val in point.get('value', []):
                        if 'fpVal' in val:
                            total += val['fpVal']; found = True
                        elif 'intVal' in val:
                            total += float(val['intVal']); found = True
        return total if found else None

    @staticmethod
    def _extract_average_float(response: dict) -> Optional[float]:
        total, count = 0.0, 0
        for bucket in response.get('bucket', []):
            for dataset in bucket.get('dataset', []):
                for point in dataset.get('point', []):
                    for val in point.get('value', []):
                        if 'fpVal' in val:
                            total += float(val['fpVal']); count += 1
                        elif 'intVal' in val:
                            total += float(val['intVal']); count += 1
        return round(total / count, 1) if count else None

    def _aggregate(self, data_type: str, start_ms: int, end_ms: int,
                   source_id: Optional[str] = None) -> dict:
        agg = {"dataTypeName": data_type}
        if source_id:
            agg["dataSourceId"] = source_id
        body = {
            "aggregateBy": [agg],
            "bucketByTime": {"durationMillis": end_ms - start_ms},
            "startTimeMillis": start_ms,
            "endTimeMillis": end_ms,
        }
        try:
            return self._get_service().users().dataset().aggregate(userId="me", body=body).execute()
        except HttpError:
            return {}

    # ── Data fetchers ────────────────────────────────────────────────────────

    def fetch_steps(self, start_ms: int, end_ms: int) -> Optional[int]:
        resp = self._aggregate(
            "com.google.step_count.delta", start_ms, end_ms,
            "derived:com.google.step_count.delta:com.google.android.gms:estimated_steps",
        )
        return self._extract_int(resp)

    def fetch_active_minutes(self, start_ms: int, end_ms: int) -> Optional[int]:
        return self._extract_int(self._aggregate("com.google.active_minutes", start_ms, end_ms))

    def fetch_calories(self, start_ms: int, end_ms: int) -> Optional[int]:
        r = self._extract_float(self._aggregate("com.google.calories.expended", start_ms, end_ms))
        return int(r) if r is not None else None

    def fetch_distance(self, start_ms: int, end_ms: int) -> Optional[float]:
        r = self._extract_float(self._aggregate("com.google.distance.delta", start_ms, end_ms))
        return round(r / 1000, 2) if r is not None else None

    def fetch_heart_rate(self, start_ms: int, end_ms: int) -> Optional[float]:
        return self._extract_average_float(self._aggregate("com.google.heart_rate.bpm", start_ms, end_ms))

    def fetch_heart_points(self, start_ms: int, end_ms: int) -> Optional[float]:
        r = self._extract_float(self._aggregate("com.google.heart_minutes", start_ms, end_ms))
        return round(r, 1) if r is not None else None

    def fetch_sleep(self, start_ms: int, end_ms: int) -> Optional[Dict]:
        """Fetch sleep data with stage breakdown."""
        SLEEP_TYPES = {2, 4, 5, 6}
        body = {
            "aggregateBy": [{"dataTypeName": "com.google.sleep.segment"}],
            "bucketByTime": {"durationMillis": end_ms - start_ms},
            "startTimeMillis": start_ms,
            "endTimeMillis": end_ms,
        }
        try:
            resp = self._get_service().users().dataset().aggregate(userId="me", body=body).execute()
            stages_ms: Dict[int, int] = {2: 0, 4: 0, 5: 0, 6: 0}
            total_ms = 0
            for bucket in resp.get('bucket', []):
                for dataset in bucket.get('dataset', []):
                    for point in dataset.get('point', []):
                        seg_start = int(point.get('startTimeNanos', 0)) // 1_000_000
                        seg_end = int(point.get('endTimeNanos', 0)) // 1_000_000
                        if not (seg_start and seg_end and seg_end > seg_start):
                            continue
                        values = point.get('value', [])
                        sleep_type = values[0].get('intVal', 2) if values else 2
                        if sleep_type not in SLEEP_TYPES:
                            continue
                        dur = seg_end - seg_start
                        if dur > 12 * 60 * 60 * 1000:
                            continue
                        stages_ms[sleep_type] = stages_ms.get(sleep_type, 0) + dur
                        total_ms += dur
            if total_ms <= 0:
                return None
            hours = total_ms / (1000 * 60 * 60)
            if hours > 16:
                return None
            ms_to_h = lambda ms: round(ms / (1000 * 60 * 60), 1)
            return {
                'hours': round(hours, 1),
                'stages': {
                    'deep': ms_to_h(stages_ms.get(5, 0)),
                    'light': ms_to_h(stages_ms.get(4, 0)),
                    'rem': ms_to_h(stages_ms.get(6, 0)),
                    'generic': ms_to_h(stages_ms.get(2, 0)),
                },
            }
        except HttpError:
            return None

    def fetch_activities(self, start_ms: int, end_ms: int) -> Dict[str, int]:
        try:
            resp = self._get_service().users().sessions().list(
                userId="me",
                startTime=datetime.fromtimestamp(start_ms / 1000).isoformat() + "Z",
                endTime=datetime.fromtimestamp(end_ms / 1000).isoformat() + "Z",
            ).execute()
            activities: Dict[str, int] = {}
            for session in resp.get('session', []):
                name = self.ACTIVITY_MAP.get(session.get('activityType', 4), "other")
                if name not in self.EXCLUDED:
                    activities[name] = activities.get(name, 0) + 1
            return activities
        except HttpError:
            return {}

    # ── Main entry point ─────────────────────────────────────────────────────

    def fetch_all_data(self, start_ms: int, end_ms: int) -> Dict[str, Any]:
        # googleapiclient/httplib2 connections are not safe to share across
        # concurrent requests. Health sync can be triggered by the dashboard,
        # master agent, and background sync at the same time, so serialize all
        # Fit API calls for this user/client.
        with self._request_lock:
            sleep_result = self.fetch_sleep(start_ms, end_ms)
            distance = self.fetch_distance(start_ms, end_ms)
            steps = self.fetch_steps(start_ms, end_ms)

            if distance is None and steps:
                distance = round((steps * 0.762) / 1000, 2)

            return {
                "steps": steps,
                "active_minutes": self.fetch_active_minutes(start_ms, end_ms),
                "calories": self.fetch_calories(start_ms, end_ms),
                "distance_km": distance,
                "sleep_hours": sleep_result['hours'] if sleep_result else None,
                "heart_rate_bpm": self.fetch_heart_rate(start_ms, end_ms),
                "heart_points": self.fetch_heart_points(start_ms, end_ms),
                "sleep_stages": sleep_result['stages'] if sleep_result else None,
                "activities": self.fetch_activities(start_ms, end_ms),
                "time_range": {
                    "start": datetime.fromtimestamp(start_ms / 1000).strftime('%Y-%m-%d %H:%M'),
                    "end": datetime.fromtimestamp(end_ms / 1000).strftime('%Y-%m-%d %H:%M'),
                },
                "last_updated": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
