"""Download, validate and extract the catalogue PDF. Network and PDF handling live here, parsing elsewhere."""
import hashlib
import shutil
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

MAX_BYTES = 30 * 1024 * 1024
MAX_PAGES = 200


class PdfError(Exception):
    pass


def assert_allowed_url(url: str) -> None:
    u = urlparse(url)
    if u.scheme != "https" or not (u.hostname == "nasa.gov" or (u.hostname or "").endswith(".nasa.gov")):
        raise PdfError(f"Refusing to download from non-NASA or non-HTTPS URL: {url}")


def download(url: str, tries: int = 3, timeout: int = 60, opener=urllib.request.urlopen) -> tuple[bytes, str]:
    assert_allowed_url(url)
    last: Exception | None = None
    for i in range(tries):
        try:
            with opener(urllib.request.Request(url, headers={"User-Agent": "ASTERA-ingest/0.2"}), timeout=timeout) as r:
                ctype = r.headers.get("Content-Type", "")
                data = r.read(MAX_BYTES + 1)
            validate_pdf(data, ctype)
            return data, ctype
        except PdfError:
            raise  # a wrong file will not become right by retrying
        except Exception as e:
            last = e
            time.sleep(min(2 ** i, 8))
    raise PdfError(f"Download failed after {tries} attempts: {last!r}")


def validate_pdf(data: bytes, content_type: str | None = None) -> None:
    if len(data) > MAX_BYTES:
        raise PdfError("File exceeds the size limit.")
    if content_type is not None and "pdf" not in content_type.lower():
        raise PdfError(f"Unexpected content type: {content_type!r}")
    if not data.startswith(b"%PDF"):
        raise PdfError("Content does not start with a PDF header.")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def extract_pages(data: bytes) -> tuple[str, str]:
    """Return (page-delimited text, extractor name). Uses poppler's pdftotext, falling back to pypdf."""
    validate_pdf(data)
    if shutil.which("pdftotext") and shutil.which("pdfinfo"):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d, "c.pdf"); path.write_bytes(data)
            info = subprocess.run(["pdfinfo", str(path)], capture_output=True, text=True, check=True, timeout=60).stdout
            n = int(next(l.split()[1] for l in info.splitlines() if l.startswith("Pages:")))
            if n > MAX_PAGES:
                raise PdfError(f"PDF has {n} pages; limit is {MAX_PAGES}.")
            parts = []
            for i in range(1, n + 1):
                t = subprocess.run(["pdftotext", "-f", str(i), "-l", str(i), str(path), "-"], capture_output=True, text=True, check=True, timeout=60).stdout
                parts.append(f"=== PAGE {i} ===\n{t}")
            return "\n".join(parts), "pdftotext (poppler) per page"
    try:
        import io
        from pypdf import PdfReader
        pages = PdfReader(io.BytesIO(data)).pages
        if len(pages) > MAX_PAGES:
            raise PdfError("Too many pages.")
        return "\n".join(f"=== PAGE {i} ===\n{p.extract_text()}" for i, p in enumerate(pages, 1)), "pypdf"
    except ImportError as e:
        raise PdfError("Neither pdftotext nor pypdf is available.") from e
