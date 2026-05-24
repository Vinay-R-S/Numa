"""
Google Fit API Client for Numa Health Agent.

Handles OAuth 2.0 authentication and fetches fitness data:
steps, calories, active minutes, distance, sleep (with stages), activities.

Credentials file: server/config/credentials.json  (or GOOGLE_FIT_CREDENTIALS_FILE env)
Token file:       server/config/token.json
"""

import os
import threading
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import AuthorizedSession, Request
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
        72: "sleeping", 100: "yoga", 101: "zumba", 108: "sleep",
        109: "sleep_light", 110: "sleep_deep", 111: "sleep_rem",
        112: "sleep_awake",
    }
    EXCLUDED = {"still", "unknown", "tilting", "automotive", "sleeping"}
    SLEEP_ACTIVITY_TYPES = {
        72: "generic",
        108: "generic",
        109: "light",
        110: "deep",
        111: "rem",
    }
    TRANSIENT_ERROR_MARKERS = (
        "wrong_version_number",
        "[ssl] internal error",
        "ssl: internal error",
        "internal error (_ssl",
        "decryption_failed_or_bad_record_mac",
        "bad record mac",
        "eof occurred in violation of protocol",
        "connection reset",
        "connection aborted",
        "remote end closed connection",
        "transient google fit api",
        "timed out",
        "timeout",
    )

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
        self._http = None
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

    def _get_http_session(self) -> AuthorizedSession:
        if self._http is None:
            self._http = AuthorizedSession(self._authenticate())
        return self._http

    @classmethod
    def _is_transient_google_error(cls, exc: Exception) -> bool:
        text = str(exc).lower()
        return any(marker in text for marker in cls.TRANSIENT_ERROR_MARKERS)

    def _reset_service(self) -> None:
        self._service = None
        self._http = None

    def _request_json(self, method: str, url: str, retries: int = 2, **kwargs) -> dict:
        last_exc = None
        for attempt in range(retries + 1):
            try:
                response = self._get_http_session().request(
                    method,
                    url,
                    timeout=30,
                    **kwargs,
                )
                if response.status_code == 429 or response.status_code >= 500:
                    raise RuntimeError(
                        f"Transient Google Fit API {response.status_code}: {response.text[:500]}"
                    )
                if response.status_code >= 400:
                    raise RuntimeError(f"Google Fit API {response.status_code}: {response.text[:500]}")
                if not response.content:
                    return {}
                return response.json()
            except Exception as exc:
                last_exc = exc
                if not self._is_transient_google_error(exc) or attempt >= retries:
                    raise
                self._reset_service()
                time.sleep(0.35 * (attempt + 1))
        raise last_exc or RuntimeError("Google Fit request failed")

    def _post_aggregate(self, body: dict) -> dict:
        return self._request_json(
            "POST",
            "https://www.googleapis.com/fitness/v1/users/me/dataset:aggregate",
            json=body,
        )

    def _list_sessions(self, start_ms: int, end_ms: int) -> dict:
        return self._request_json(
            "GET",
            "https://www.googleapis.com/fitness/v1/users/me/sessions",
            params={
                "startTime": datetime.fromtimestamp(start_ms / 1000, timezone.utc).isoformat().replace("+00:00", "Z"),
                "endTime": datetime.fromtimestamp(end_ms / 1000, timezone.utc).isoformat().replace("+00:00", "Z"),
            },
        )

    def _execute_google(self, request_builder, retries: int = 2) -> dict:
        last_exc = None
        for attempt in range(retries + 1):
            try:
                return request_builder(self._get_service()).execute()
            except HttpError:
                raise
            except Exception as exc:
                last_exc = exc
                if not self._is_transient_google_error(exc) or attempt >= retries:
                    raise
                self._reset_service()
                time.sleep(0.25 * (attempt + 1))
        raise last_exc or RuntimeError("Google Fit request failed")

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

    @staticmethod
    def _parse_google_time(value: Optional[str]) -> Optional[int]:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return int(parsed.timestamp() * 1000)
        except ValueError:
            return None

    @staticmethod
    def _parse_google_millis(value: Any) -> Optional[int]:
        if value is None:
            return None
        try:
            parsed = int(value)
            return parsed if parsed > 0 else None
        except (TypeError, ValueError):
            return None

    def _session_bounds_ms(self, session: Dict[str, Any]) -> tuple[Optional[int], Optional[int]]:
        start = self._parse_google_millis(session.get("startTimeMillis"))
        if start is None:
            start_nanos = self._parse_google_millis(session.get("startTimeNanos"))
            start = start_nanos // 1_000_000 if start_nanos else None

        end = self._parse_google_millis(session.get("endTimeMillis"))
        if end is None:
            end_nanos = self._parse_google_millis(session.get("endTimeNanos"))
            end = end_nanos // 1_000_000 if end_nanos else None

        if start is None:
            start = self._parse_google_time(session.get("startTime"))
        if end is None:
            end = self._parse_google_time(session.get("endTime"))
        return start, end

    @staticmethod
    def _finalize_sleep_segments(raw_segments: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Convert overlapping Google Fit sleep points into one timeline."""
        valid_segments: List[Dict[str, Any]] = []
        for segment in raw_segments:
            try:
                start = int(segment.get("start_ms") or 0)
                end = int(segment.get("end_ms") or 0)
            except (TypeError, ValueError):
                continue
            if end <= start:
                continue
            stage = str(segment.get("stage") or "generic")
            if stage not in {"generic", "light", "deep", "rem"}:
                stage = "generic"
            valid_segments.append({"start_ms": start, "end_ms": end, "stage": stage})

        if not valid_segments:
            return None

        stage_priority = {"generic": 1, "light": 2, "rem": 3, "deep": 4}
        boundaries = sorted({
            boundary
            for segment in valid_segments
            for boundary in (segment["start_ms"], segment["end_ms"])
        })
        normalized: List[Dict[str, Any]] = []

        for start, end in zip(boundaries, boundaries[1:]):
            if end <= start:
                continue
            covering = [
                segment for segment in valid_segments
                if segment["start_ms"] < end and segment["end_ms"] > start
            ]
            if not covering:
                continue
            chosen = max(covering, key=lambda segment: stage_priority.get(segment["stage"], 1))
            stage = chosen["stage"]
            if normalized and normalized[-1]["stage"] == stage and normalized[-1]["end_ms"] == start:
                normalized[-1]["end_ms"] = end
            else:
                normalized.append({"start_ms": start, "end_ms": end, "stage": stage})

        if not normalized:
            return None

        stages_ms: Dict[str, int] = {"generic": 0, "light": 0, "deep": 0, "rem": 0}
        for segment in normalized:
            stages_ms[segment["stage"]] += segment["end_ms"] - segment["start_ms"]

        total_ms = sum(stages_ms.values())
        if total_ms <= 0:
            return None
        hours = total_ms / (1000 * 60 * 60)
        if hours > 16:
            return None

        ms_to_h = lambda ms: round(ms / (1000 * 60 * 60), 1)
        return {
            "hours": round(hours, 1),
            "start_ms": normalized[0]["start_ms"],
            "end_ms": normalized[-1]["end_ms"],
            "stages": {
                stage: ms_to_h(value)
                for stage, value in stages_ms.items()
                if value > 0
            },
            "segments": [
                {
                    "start_ms": segment["start_ms"],
                    "end_ms": segment["end_ms"],
                    "stage": segment["stage"],
                    "hours": round((segment["end_ms"] - segment["start_ms"]) / (1000 * 60 * 60), 2),
                }
                for segment in normalized
            ],
        }

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
        return self._post_aggregate(body)

    def _aggregate_bucketed(
        self,
        data_type: str,
        start_ms: int,
        end_ms: int,
        bucket_minutes: int,
        source_id: Optional[str] = None,
    ) -> dict:
        agg = {"dataTypeName": data_type}
        if source_id:
            agg["dataSourceId"] = source_id
        body = {
            "aggregateBy": [agg],
            "bucketByTime": {"durationMillis": bucket_minutes * 60 * 1000},
            "startTimeMillis": start_ms,
            "endTimeMillis": end_ms,
        }
        return self._post_aggregate(body)

    def _aggregate_many(
        self,
        aggregate_by: List[Dict[str, str]],
        start_ms: int,
        end_ms: int,
        bucket_minutes: Optional[int] = None,
    ) -> dict:
        body = {
            "aggregateBy": aggregate_by,
            "bucketByTime": {
                "durationMillis": bucket_minutes * 60 * 1000 if bucket_minutes else end_ms - start_ms
            },
            "startTimeMillis": start_ms,
            "endTimeMillis": end_ms,
        }
        return self._post_aggregate(body)

    @staticmethod
    def _bucket_values(response: dict, value_type: str = "float") -> Dict[int, Dict[str, Any]]:
        buckets: Dict[int, Dict[str, Any]] = {}
        for bucket in response.get("bucket", []):
            bucket_start = int(bucket.get("startTimeMillis", 0) or 0)
            bucket_end = int(bucket.get("endTimeMillis", 0) or 0)
            if not bucket_start or not bucket_end:
                continue
            total = 0.0
            found = False
            for dataset in bucket.get("dataset", []):
                for point in dataset.get("point", []):
                    for val in point.get("value", []):
                        if "intVal" in val:
                            total += int(val["intVal"])
                            found = True
                        elif "fpVal" in val:
                            total += float(val["fpVal"])
                            found = True
            buckets[bucket_start] = {
                "start_ms": bucket_start,
                "end_ms": bucket_end,
                "value": int(total) if value_type == "int" else total,
                "found": found,
            }
        return buckets

    @staticmethod
    def _bucket_values_for_type(response: dict, data_type: str, value_type: str = "float") -> Dict[int, Dict[str, Any]]:
        buckets: Dict[int, Dict[str, Any]] = {}
        for bucket in response.get("bucket", []):
            bucket_start = int(bucket.get("startTimeMillis", 0) or 0)
            bucket_end = int(bucket.get("endTimeMillis", 0) or 0)
            if not bucket_start or not bucket_end:
                continue
            total = 0.0
            found = False
            for dataset in bucket.get("dataset", []):
                source_id = str(dataset.get("dataSourceId") or "")
                if data_type not in source_id:
                    continue
                for point in dataset.get("point", []):
                    for val in point.get("value", []):
                        if "intVal" in val:
                            total += int(val["intVal"])
                            found = True
                        elif "fpVal" in val:
                            total += float(val["fpVal"])
                            found = True
            buckets[bucket_start] = {
                "start_ms": bucket_start,
                "end_ms": bucket_end,
                "value": int(total) if value_type == "int" else total,
                "found": found,
            }
        return buckets

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
            resp = self._post_aggregate(body)
            segments: List[Dict[str, Any]] = []
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
                        clipped_start = max(seg_start, start_ms)
                        clipped_end = min(seg_end, end_ms)
                        if clipped_end <= clipped_start:
                            continue
                        dur = clipped_end - clipped_start
                        if dur > 12 * 60 * 60 * 1000:
                            continue
                        segments.append({
                            "start_ms": clipped_start,
                            "end_ms": clipped_end,
                            "stage": {
                                2: "generic",
                                4: "light",
                                5: "deep",
                                6: "rem",
                            }.get(sleep_type, "generic"),
                        })
            sleep_result = self._finalize_sleep_segments(segments)
            if sleep_result:
                return sleep_result

            if not sleep_result:
                session_sleep = self._fetch_sleep_sessions(start_ms, end_ms)
                if session_sleep:
                    return session_sleep
            if not sleep_result:
                activity_sleep = self._fetch_sleep_activity_segments(start_ms, end_ms)
                if activity_sleep:
                    return activity_sleep
            return None
        except HttpError:
            return self._fetch_sleep_sessions(start_ms, end_ms) or self._fetch_sleep_activity_segments(start_ms, end_ms)

    def _fetch_sleep_sessions(self, start_ms: int, end_ms: int) -> Optional[Dict]:
        try:
            resp = self._list_sessions(start_ms, end_ms)
            segments: List[Dict[str, Any]] = []
            for session in resp.get("session", []):
                activity_type = session.get("activityType")
                try:
                    activity_type = int(activity_type)
                except (TypeError, ValueError):
                    activity_type = None
                name = self.ACTIVITY_MAP.get(activity_type, "")
                if activity_type not in self.SLEEP_ACTIVITY_TYPES and name != "sleeping":
                    continue
                seg_start, seg_end = self._session_bounds_ms(session)
                if not (seg_start and seg_end and seg_end > seg_start):
                    continue
                clipped_start = max(seg_start, start_ms)
                clipped_end = min(seg_end, end_ms)
                if clipped_end <= clipped_start:
                    continue
                dur = clipped_end - clipped_start
                if dur > 16 * 60 * 60 * 1000:
                    continue
                segments.append({
                    "start_ms": clipped_start,
                    "end_ms": clipped_end,
                    "stage": "generic",
                })
            return self._finalize_sleep_segments(segments)
        except HttpError:
            return None

    def _fetch_sleep_activity_segments(self, start_ms: int, end_ms: int) -> Optional[Dict]:
        body = {
            "aggregateBy": [{"dataTypeName": "com.google.activity.segment"}],
            "bucketByTime": {"durationMillis": end_ms - start_ms},
            "startTimeMillis": start_ms,
            "endTimeMillis": end_ms,
        }
        try:
            resp = self._post_aggregate(body)
            segments: List[Dict[str, Any]] = []
            for bucket in resp.get("bucket", []):
                for dataset in bucket.get("dataset", []):
                    for point in dataset.get("point", []):
                        values = point.get("value", [])
                        activity_type = values[0].get("intVal") if values else None
                        stage = self.SLEEP_ACTIVITY_TYPES.get(activity_type)
                        if not stage:
                            continue
                        seg_start = int(point.get("startTimeNanos", 0)) // 1_000_000
                        seg_end = int(point.get("endTimeNanos", 0)) // 1_000_000
                        if not (seg_start and seg_end and seg_end > seg_start):
                            continue
                        clipped_start = max(seg_start, start_ms)
                        clipped_end = min(seg_end, end_ms)
                        if clipped_end <= clipped_start:
                            continue
                        dur = clipped_end - clipped_start
                        if dur > 16 * 60 * 60 * 1000:
                            continue
                        segments.append({
                            "start_ms": clipped_start,
                            "end_ms": clipped_end,
                            "stage": stage,
                        })
            return self._finalize_sleep_segments(segments)
        except HttpError:
            return None

    def fetch_activities(self, start_ms: int, end_ms: int) -> Dict[str, int]:
        try:
            resp = self._list_sessions(start_ms, end_ms)
            activities: Dict[str, int] = {}
            for session in resp.get('session', []):
                name = self.ACTIVITY_MAP.get(session.get('activityType', 4), "other")
                if name not in self.EXCLUDED:
                    activities[name] = activities.get(name, 0) + 1
            return activities
        except HttpError:
            return {}

    def fetch_intraday_activity(
        self,
        start_ms: int,
        end_ms: int,
        bucket_minutes: int = 60,
    ) -> List[Dict[str, Any]]:
        with self._request_lock:
            resp = self._aggregate_many(
                [
                    {
                        "dataTypeName": "com.google.step_count.delta",
                        "dataSourceId": "derived:com.google.step_count.delta:com.google.android.gms:estimated_steps",
                    },
                    {"dataTypeName": "com.google.calories.expended"},
                    {"dataTypeName": "com.google.distance.delta"},
                ],
                start_ms,
                end_ms,
                bucket_minutes=bucket_minutes,
            )
            steps = self._bucket_values_for_type(resp, "step_count.delta", "int")
            calories = self._bucket_values_for_type(resp, "calories.expended", "float")
            distance = self._bucket_values_for_type(resp, "distance.delta", "float")
            bucket_ms = bucket_minutes * 60 * 1000
            buckets: List[Dict[str, Any]] = []
            current = start_ms
            while current < end_ms:
                bucket_end = min(current + bucket_ms, end_ms)
                step_count = int(steps.get(current, {}).get("value") or 0)
                calories_count = int(calories.get(current, {}).get("value") or 0)
                distance_km = round(float(distance.get(current, {}).get("value") or 0) / 1000, 2)
                if distance_km == 0 and step_count:
                    distance_km = round((step_count * 0.762) / 1000, 2)
                buckets.append({
                    "start_ms": current,
                    "end_ms": bucket_end,
                    "steps": step_count,
                    "calories": calories_count,
                    "distance_km": distance_km,
                })
                current = bucket_end
            return buckets

    # ── Main entry point ─────────────────────────────────────────────────────

    def fetch_all_data(self, start_ms: int, end_ms: int, include_sleep: bool = True) -> Dict[str, Any]:
        # googleapiclient/httplib2 connections are not safe to share across
        # concurrent requests. Health sync can be triggered by the dashboard,
        # master agent, and background sync at the same time, so serialize all
        # Fit API calls for this user/client.
        with self._request_lock:
            sleep_result = self.fetch_sleep(start_ms, end_ms) if include_sleep else None
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
                "sleep_start_ms": sleep_result.get('start_ms') if sleep_result else None,
                "sleep_end_ms": sleep_result.get('end_ms') if sleep_result else None,
                "heart_rate_bpm": self.fetch_heart_rate(start_ms, end_ms),
                "heart_points": self.fetch_heart_points(start_ms, end_ms),
                "sleep_stages": sleep_result['stages'] if sleep_result else None,
                "sleep_segments": sleep_result.get('segments') if sleep_result else None,
                "activities": self.fetch_activities(start_ms, end_ms),
                "time_range": {
                    "start": datetime.fromtimestamp(start_ms / 1000).strftime('%Y-%m-%d %H:%M'),
                    "end": datetime.fromtimestamp(end_ms / 1000).strftime('%Y-%m-%d %H:%M'),
                },
                "last_updated": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
