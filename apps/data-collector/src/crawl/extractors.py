from __future__ import annotations

import json
import re

# Matches the JSON blob carried in the `m` attribute of Bing Images result anchors.
_M_ATTR = re.compile(r"class=\"iusc\"[^>]*\bm='([^']+)'", re.IGNORECASE)
_ALT = re.compile(r"alt=\"([^\"]*)\"", re.IGNORECASE)


def extract_bing_candidates(html: str) -> list[dict]:
    """Parse a Bing Images result page into candidate dicts.

    Each dict has: image_url, source_url, alt_text, page_title.
    Anchors without a usable `m` blob are skipped.
    """
    results: list[dict] = []
    # Split per anchor so we can pair each `m` blob with the nearest alt text.
    for block in re.split(r"<a ", html):
        m = _M_ATTR.search("<a " + block)
        if not m:
            continue
        try:
            blob = json.loads(m.group(1).replace("&quot;", '"'))
        except json.JSONDecodeError:
            continue
        image_url = blob.get("murl", "")
        if not image_url.startswith("http"):
            continue
        alt = _ALT.search(block)
        results.append(
            {
                "image_url": image_url,
                "source_url": blob.get("purl", ""),
                "alt_text": alt.group(1) if alt else "",
                "page_title": blob.get("t", ""),
            }
        )
    return results
