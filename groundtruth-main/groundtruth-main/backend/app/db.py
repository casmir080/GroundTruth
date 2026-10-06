from functools import lru_cache

from supabase import Client, create_client

from .config import settings


@lru_cache
def get_client() -> Client:
    return create_client(settings.supabase_url, settings.supabase_service_key)


def fetch_all(build_query, page_size: int = 500) -> list:
    """Fetch every row matching a query, past Supabase's default row cap.

    build_query is a zero-arg callable returning a FRESH, unexecuted query
    each time (filters get reapplied per page) -- e.g.:
        fetch_all(lambda: get_client().table("llm_calls").select("id"))
    Without this, any query over ~1000 rows silently returns a partial
    result instead of erroring, which is worse than a crash.
    """
    rows = []
    offset = 0
    while True:
        page = build_query().range(offset, offset + page_size - 1).execute().data
        rows.extend(page)
        if len(page) < page_size:
            return rows
        offset += page_size
