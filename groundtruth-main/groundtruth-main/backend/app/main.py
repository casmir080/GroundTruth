from typing import Literal, Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .auth import require_api_key
from .config import settings
from .dashboard import router as dashboard_router
from .db import get_client
from .llm import logged_completion

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="GroundTruth", version="0.1.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_methods=["GET"],
    allow_headers=["*"],
)
app.include_router(dashboard_router)


@app.get("/")
def root():
    return {"service": "GroundTruth", "docs": "/docs"}


@app.get("/health")
def health():
    return {"ok": True}


class ChatRequest(BaseModel):
    prompt: str
    source: Literal["live", "benchmark"] = "live"
    query_type: Optional[str] = None
    system: Optional[str] = None


@app.post("/v1/chat", dependencies=[Depends(require_api_key)])
@limiter.limit("10/minute")
def chat(request: Request, req: ChatRequest):
    """Send a prompt to the LLM; the call is logged to Supabase either way."""
    try:
        return logged_completion(
            req.prompt,
            source=req.source,
            query_type=req.query_type,
            system=req.system,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/v1/calls", dependencies=[Depends(require_api_key)])
def recent_calls(limit: int = 20, source: Optional[str] = None):
    q = (
        get_client()
        .table("llm_calls")
        .select("*")
        .order("created_at", desc=True)
        .limit(min(limit, 100))
    )
    if source:
        q = q.eq("source", source)
    return q.execute().data


@app.get("/v1/status", dependencies=[Depends(require_api_key)])
def status():
    db = get_client()

    def count(source: Optional[str] = None) -> int:
        q = db.table("llm_calls").select("id", count="exact")
        if source:
            q = q.eq("source", source)
        return q.limit(1).execute().count

    return {
        "total_calls": count(),
        "live_calls": count("live"),
        "benchmark_calls": count("benchmark"),
    }
