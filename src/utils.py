from pathlib import Path
import sys
import os, json

def search_web(query: str, max_results: int = 1) -> str:
    from ddgs import DDGS
    import trafilatura
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results, safesearch="moderate"):
            title = r.get("title", "")
            url = r.get("href", "")
            downloaded = trafilatura.fetch_url(url)
            content = trafilatura.extract(downloaded) if downloaded else ""

            results.append(f"Title: {title}\n Url: {url}\n Content: {content}")
    return "\n\n".join(results) if results else "No results found."

def get_config_path(*parts: str) -> Path:
    if not getattr(sys, "frozen", False):
        return Path(__file__).resolve().parent.parent.joinpath("config", *parts)

    config_dir = Path.home() / ".promptos"
    config_dir.mkdir(parents=True, exist_ok=True)

    config_files = {
        "settings.json": '{"provider": "GitHubAI", "model": "openai/gpt-4o-mini", "mode": "FAST", "ollama_base_url": "http://localhost:11434/v1", "lmstudio_base_url": "http://localhost:1234/v1"}',
        "keys.json": '{"GOOGLE_API_KEY": "", "GROQ_API_KEY": "", "UNCLOSE_API_KEY": "", "OPENROUTE_API_KEY": "", "GITHUB_TOKEN": "", "ANTHROPIC_API_KEY": "", "OPENAI_API_KEY": "", "OLLAMA_API_KEY": "", "LMSTUDIO_API_KEY": ""}',
        "memory.txt": "",
        "prompt.txt": "You are PromptOS, a powerful AI assistant."
    }

    for filename, default_content in config_files.items():
        file_path = config_dir / filename
        if not file_path.exists():
            resource_file = resource_path("config", filename)
            if resource_file.exists():
                try:
                    file_path.write_text(resource_file.read_text(encoding="utf-8"), encoding="utf-8")
                except Exception:
                    file_path.write_text(default_content, encoding="utf-8")
            else:
                file_path.write_text(default_content, encoding="utf-8")
        elif filename == "prompt.txt":
            # Always sync prompt.txt from resources to user home if frozen
            resource_file = resource_path("config", filename)
            if resource_file.exists():
                try:
                    res_content = resource_file.read_text(encoding="utf-8")
                    if file_path.read_text(encoding="utf-8") != res_content:
                        file_path.write_text(res_content, encoding="utf-8")
                except Exception:
                    pass

    return config_dir.joinpath(*parts)

def resource_path(*parts: str) -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        # This is where PyInstaller unpacks data in --onefile mode
        return Path(sys._MEIPASS).joinpath(*parts)

    base = Path(__file__).resolve().parent.parent
    return base.joinpath(*parts)

def decode_output(data: bytes) -> str:
    for enc in ("utf-8", "cp850", "cp1252"):
        try:
            return data.decode(enc)
        except Exception:
            continue
    return data.decode("utf-8", errors="replace")


if __name__ == "__main__":
    print(search_web("weather in sydney", max_results=10))