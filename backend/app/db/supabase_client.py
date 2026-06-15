import os
from functools import lru_cache

from dotenv import load_dotenv
from fastapi import HTTPException
from supabase import Client, create_client

load_dotenv()


@lru_cache
def get_supabase_client() -> Client:
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        raise HTTPException(
            status_code=500,
            detail=(
                "Missing Supabase configuration. Set SUPABASE_URL and "
                "either SUPABASE_SERVICE_ROLE_KEY or SUPABASE_KEY in the "
                "backend .env file."
            ),
        )

    return create_client(supabase_url, supabase_key)
