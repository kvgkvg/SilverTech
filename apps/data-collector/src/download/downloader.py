from __future__ import annotations

from pathlib import Path

import httpx


def download_one(client: httpx.Client, url: str, dest: Path) -> dict:
    """Download a single URL to `dest`. Returns a result dict, never raises."""
    try:
        resp = client.get(url, follow_redirects=True)
    except httpx.HTTPError as exc:
        return {"ok": False, "url": url, "reason": f"error_{type(exc).__name__}"}
    if resp.status_code != 200:
        return {"ok": False, "url": url, "reason": f"http_{resp.status_code}"}
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(resp.content)
    return {"ok": True, "url": url, "path": str(dest), "file_size": len(resp.content)}


def download_many(urls_dests: list[tuple[str, Path]], user_agent: str, timeout: int) -> list[dict]:
    """Download a list of (url, dest) pairs sequentially. Returns result dicts."""
    headers = {"User-Agent": user_agent}
    results: list[dict] = []
    with httpx.Client(headers=headers, timeout=timeout) as client:
        for url, dest in urls_dests:
            results.append(download_one(client, url, dest))
    return results
