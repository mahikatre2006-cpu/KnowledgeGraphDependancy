import os
from typing import Dict, Any, List, Optional, Tuple
import httpx


class SupabaseClient:
    """
    Direct REST API Client for Supabase using HTTPX.
    Communicates with Supabase PostgREST endpoints using Service Role Key.
    """

    @classmethod
    def get_config(cls) -> Tuple[str, str]:
        url = os.getenv("SUPABASE_URL", "https://zowwjzwrwxoawvfsuuoy.supabase.co").rstrip("/")
        service_key = os.getenv(
            "SUPABASE_SERVICE_ROLE_KEY",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inpvd3dqendyd3hvYXd2ZnN1dW95Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4ODUxMjMwMCwiZXhwIjoyMTA0MDg4MzAwfQ.a2t3YEDX-EXLtz1PuIZlbH43pRqNpTey6bu0excUJFs"
        )
        return url, service_key

    @classmethod
    def get_headers(cls) -> Dict[str, str]:
        _, service_key = cls.get_config()
        return {
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }

    @classmethod
    def save_user_progress(cls, user_id: str, known_concept_ids: List[str]) -> List[Dict[str, Any]]:
        """Saves user progress records directly to Supabase via REST API."""
        url, _ = cls.get_config()
        headers = cls.get_headers()

        # Delete existing progress for user
        try:
            httpx.delete(
                f"{url}/rest/v1/user_progress?user_id=eq.{user_id}",
                headers=headers,
                timeout=10
            )
        except Exception:
            pass

        # Insert new progress records
        records = [
            {
                "id": f"prog_{user_id}_{cid}",
                "user_id": user_id,
                "concept_id": cid,
                "status": "known"
            }
            for cid in known_concept_ids
        ]

        if not records:
            return []

        try:
            resp = httpx.post(
                f"{url}/rest/v1/user_progress",
                json=records,
                headers=headers,
                timeout=10
            )
            if resp.status_code in [200, 201]:
                return resp.json()
        except Exception:
            pass

        return records
