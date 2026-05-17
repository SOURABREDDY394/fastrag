import os
from functools import lru_cache

from dotenv import load_dotenv
from fastapi import HTTPException
from supabase import Client, create_client

load_dotenv()


@lru_cache
def get_supabase_client() -> Client:
    supabase_url = os.getenv("SUPABASE_URL")
    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not service_role_key:
        raise HTTPException(
            status_code=500,
            detail=(
                "Missing Supabase configuration. Set SUPABASE_URL and "
                "SUPABASE_SERVICE_ROLE_KEY in the backend .env file."
            ),
        )

    return create_client(supabase_url, service_role_key)
