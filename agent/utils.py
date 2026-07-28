"""Shared retry utility for Morph API rate limits (5 req/min on free tier)."""


import sys
import time
import functools


def with_retry(fn, max_attempts=5, base_wait=15):
    """Call fn, retrying on 429 with exponential backoff.

    Daily-quota errors (tokens per day) fail immediately instead of retrying —
    a short backoff can never fix a 24h quota, and burning minutes on retries
    risks the MCP client timing out and cancelling the call mid-wait, which
    crashes the whole server when we try to respond to an already-cancelled
    request.
    """
    for attempt in range(max_attempts):
        try:
            return fn()
        except Exception as e:
            msg = str(e)
            if "tokens per day" in msg.lower() or "tpd" in msg.lower():
                raise RuntimeError(
                    "This provider's daily token quota is exhausted. Retrying won't "
                    "help right now — it resets on a rolling basis (usually within an "
                    f"hour). Original error: {msg}"
                ) from None
            if "429" in msg or "rate_limit" in msg.lower() or "Rate limit" in msg:
                wait = base_wait * (attempt + 1)
                print(f"  [rate limit] waiting {wait}s before retry {attempt+1}/{max_attempts}...", file=sys.stderr)
                time.sleep(wait)
            else:
                raise
    raise RuntimeError(f"Failed after {max_attempts} attempts due to rate limits.")


def call_with_fallback(primary_fn, fallback_fn, max_attempts=5, base_wait=15):
    """Try primary_fn (e.g. Kimi); if its daily quota is exhausted, silently
    retry with fallback_fn (e.g. Groq) instead of failing outright. Different
    providers' daily caps rarely run out at the same time."""
    try:
        return with_retry(primary_fn, max_attempts=max_attempts, base_wait=base_wait)
    except RuntimeError as e:
        if "quota" in str(e).lower() or "rate limit" in str(e).lower():
            print("  [fallback] Primary provider's quota is exhausted — trying the fallback provider...", file=sys.stderr)
            return with_retry(fallback_fn, max_attempts=max_attempts, base_wait=base_wait)
        raise
