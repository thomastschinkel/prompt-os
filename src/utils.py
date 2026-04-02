from ddgs import DDGS
from pathlib import Path
import sys

def search_web(query: str, max_results: int = 5) -> str:
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results, safesearch="moderate"):
            title = r.get("title", "")
            url = r.get("href", "")
            snippet = r.get("body", "")
            results.append(f"Title: {title}\n Url: {url}\n Snippet: {snippet}\n")
    return "\n\n".join(results) if results else "No results found."

def resource_path(*parts: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base.joinpath(*parts)

def decode_output(data: bytes) -> str:
    for enc in ("utf-8", "cp850", "cp1252"):
        try:
            return data.decode(enc)
        except Exception:
            continue
    return data.decode("utf-8", errors="replace")