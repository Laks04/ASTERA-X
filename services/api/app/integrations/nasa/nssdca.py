"""Conservative NASA mission-page retrieval adapter.

This adapter fetches only registered NASA hosts, records provenance and extracts
page metadata/text for subsequent human review. It does not infer mission fields.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from html.parser import HTMLParser
from urllib.parse import urlparse
from datetime import datetime, timezone
import re

import httpx

ALLOWED_HOSTS = {"nssdc.gsfc.nasa.gov", "science.nasa.gov"}
USER_AGENT = "ASTERA-research-client/1.0 (NASA mission metadata; contact: project maintainer)"


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.title: list[str] = []
        self.description = ""
        self._in_title = False
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_d = dict(attrs)
        if tag == "title": self._in_title = True
        if tag in {"script", "style", "noscript", "svg"}: self._skip += 1
        if tag == "meta" and attrs_d.get("name", "").lower() in {"description", "og:description"}:
            self.description = attrs_d.get("content") or self.description

    def handle_endtag(self, tag: str) -> None:
        if tag == "title": self._in_title = False
        if tag in {"script", "style", "noscript", "svg"} and self._skip: self._skip -= 1

    def handle_data(self, data: str) -> None:
        value = re.sub(r"\s+", " ", data).strip()
        if not value: return
        if self._in_title: self.title.append(value)
        if not self._skip: self.parts.append(value)


@dataclass
class MissionPageSnapshot:
    source_url: str
    final_url: str
    retrieved_at: str
    http_status: int
    content_type: str
    sha256: str
    page_title: str | None
    meta_description: str | None
    extracted_text: str
    extraction_note: str


def validate_nasa_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError("Only HTTPS URLs on registered NASA hosts are allowed")


def fetch_mission_page(url: str, timeout: float = 25.0) -> MissionPageSnapshot:
    validate_nasa_url(url)
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"}
    with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
        response = client.get(url)
    validate_nasa_url(str(response.url))
    response.raise_for_status()
    content_type = response.headers.get("content-type", "")
    if "html" not in content_type.lower():
        raise ValueError(f"Expected HTML from NASA mission page, received {content_type!r}")
    raw = response.content
    parser = _TextExtractor()
    parser.feed(response.text)
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(parser.parts)).strip()
    return MissionPageSnapshot(
        source_url=url, final_url=str(response.url), retrieved_at=datetime.now(timezone.utc).isoformat(),
        http_status=response.status_code, content_type=content_type, sha256=sha256(raw).hexdigest(),
        page_title=" ".join(parser.title).strip() or None, meta_description=parser.description or None,
        extracted_text=text[:100_000],
        extraction_note="HTML text extraction only; no mission fields are asserted or auto-verified. Human review required.",
    )
