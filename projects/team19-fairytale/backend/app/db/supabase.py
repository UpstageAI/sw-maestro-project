from functools import lru_cache

from supabase import Client, create_client

from app.config import settings


@lru_cache
def get_supabase_admin_client() -> Client:
    url = settings.resolved_supabase_url
    key = settings.supabase_service_role_key or settings.supabase_anon_key

    if not url or not key:
        raise RuntimeError("Supabase URL and API key must be configured.")

    return create_client(url, key)
