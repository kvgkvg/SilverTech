from __future__ import annotations

import html as html_lib
import json
import re

# Bing Images carries each result's metadata as an HTML-entity-encoded JSON blob in the
# `m` attribute of an `<a class="iusc" ... m="{&quot;murl&quot;:...}">` anchor. The
# attribute is double-quoted and the inner JSON quotes are `&quot;`, so we capture the
# whole entity-encoded value then html-unescape it before parsing.
_M_ATTR = re.compile(r'<a\b[^>]*\bclass="iusc"[^>]*\bm="([^"]*)"', re.IGNORECASE)
_ALT = re.compile(r'alt="([^"]*)"', re.IGNORECASE)


def extract_bing_candidates(html: str) -> list[dict]:
    """Parse a Bing Images result page into candidate dicts.

    Each dict has: image_url, source_url, alt_text, page_title.
    Anchors without a usable `m` blob are skipped.
    """
    results: list[dict] = []
    for match in _M_ATTR.finditer(html):
        try:
            blob = json.loads(html_lib.unescape(match.group(1)))
        except json.JSONDecodeError:
            continue
        image_url = blob.get("murl", "")
        if not image_url.startswith("http"):
            continue
        # Pair the blob with the nearest alt text that follows the anchor open tag.
        tail = html[match.end():match.end() + 400]
        alt = _ALT.search(tail)
        results.append(
            {
                "image_url": image_url,
                "source_url": blob.get("purl", ""),
                "alt_text": alt.group(1) if alt else "",
                "page_title": blob.get("t", ""),
            }
        )
    return results
