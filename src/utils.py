from ddgs import DDGS
from pathlib import Path
import sys
import os, json
import trafilatura

def search_web(query: str, max_results: int = 1) -> str:
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results, safesearch="moderate"):
            title = r.get("title", "")
            url = r.get("href", "")
            downloaded = trafilatura.fetch_url(url)
            content = trafilatura.extract(downloaded) if downloaded else ""

            results.append(f"Title: {title}\n Url: {url}\n Content: {content}")
    return "\n\n".join(results) if results else "No results found."

def resource_path(*parts: str) -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS).joinpath(*[p for p in parts if p != ".."])

    base = Path(__file__).resolve().parent.parent
    return base.joinpath(*[p for p in parts if p != ".."])

def decode_output(data: bytes) -> str:
    for enc in ("utf-8", "cp850", "cp1252"):
        try:
            return data.decode(enc)
        except Exception:
            continue
    return data.decode("utf-8", errors="replace")


if __name__ == "__main__":
    print(search_web("weather in sydney", max_results=10))