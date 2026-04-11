from ddgs import DDGS
from pathlib import Path
import sys
import groq
import pyaudio
import numpy as np
import scipy.io.wavfile as wav
import tempfile, os, json
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

def listen(stop_event=None):
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    KEYS_PATH = PROJECT_ROOT / "config" / "keys.json"
    samplerate, chunk_size, recorded, silent_chunks, started = 16000, 1600, [], 0, False

    p = pyaudio.PyAudio()
    stream = p.open(rate=samplerate, channels=1, format=pyaudio.paInt16, input=True, frames_per_buffer=chunk_size)
    while True:
        if stop_event and stop_event.is_set():
            break
        chunk = np.frombuffer(stream.read(chunk_size), dtype='int16')
        recorded.append(chunk)
        if np.abs(chunk).mean() > 500:
            started, silent_chunks = True, 0
        elif started:
            silent_chunks += 1
            if silent_chunks >= 15:
                break
    stream.stop_stream()
    stream.close()
    p.terminate()

    if not recorded:
        return ""

    with open(KEYS_PATH) as f:
        groq_key = json.load(f).get("GROQ_API_KEY")

    if not groq_key:
        return ""

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav.write(tmp.name, samplerate, np.concatenate(recorded))
        tmp_path = tmp.name

    try:
        with open(tmp_path, "rb") as f:
            result = groq.Groq(api_key=groq_key).audio.transcriptions.create(
                model="whisper-large-v3-turbo", file=f
            )
        return result.text
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
    
    return ""

if __name__ == "__main__":
    print(search_web("weather in sydney", max_results=10))