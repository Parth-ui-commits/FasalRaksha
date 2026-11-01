"""Resilient HTTP layer: retries, TTL cache, stale-on-error fallback, provenance.
Every upstream call returns a Result so callers (and the LLM) always know
where data came from, when, and whether it is degraded."""
import hashlib, json, threading, time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import requests

_CACHE: dict = {}
_LOCK = threading.Lock()
HEADERS = {"User-Agent": "FasalRaksha/1.0 (hackathon prototype)"}


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Result:
    ok: bool
    source: str
    data: object = None
    error: str | None = None
    fetched_at: str = ""
    from_cache: bool = False

    def to_dict(self):
        return asdict(self)


def fetch_json(source, url, params=None, ttl=600, retries=3, timeout=20):
    key = hashlib.sha1(f"{url}|{json.dumps(params, sort_keys=True, default=str)}".encode()).hexdigest()
    with _LOCK:
        hit = _CACHE.get(key)
    if hit and time.time() - hit[0] < ttl:
        r = hit[1]
        return Result(True, r.source, r.data, None, r.fetched_at, True)
    last = None
    for i in range(retries):
        try:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
            if resp.status_code == 429 or resp.status_code >= 500:
                raise RuntimeError(f"HTTP {resp.status_code}")
            resp.raise_for_status()
            res = Result(True, source, resp.json(), None, _now())
            with _LOCK:
                _CACHE[key] = (time.time(), res)
            return res
        except Exception as e:  # noqa: BLE001
            last = f"{type(e).__name__}: {e}"
            time.sleep(0.6 * 2 ** i)
    if hit:  # real data fetched earlier, clearly flagged as stale
        r = hit[1]
        return Result(True, r.source, r.data, f"stale (live fetch failed: {last})", r.fetched_at, True)
    return Result(False, source, None, last, _now())
