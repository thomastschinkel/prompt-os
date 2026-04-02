from ddgs import DDGS
from pathlib import Path
import sys
import groq
import pyaudio
import numpy as np
import scipy.io.wavfile as wav
import tempfile, os, json

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

def listen():
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    KEYS_PATH = PROJECT_ROOT / "config" / "keys.json"
    samplerate, chunk_size, recorded, silent_chunks, started = 16000, 1600, [], 0, False

    p = pyaudio.PyAudio()
    stream = p.open(rate=samplerate, channels=1, format=pyaudio.paInt16, input=True, frames_per_buffer=chunk_size)
    while True:
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

    with open(KEYS_PATH) as f:
        keys = json.load(f)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav.write(tmp.name, samplerate, np.concatenate(recorded))
        tmp_path = tmp.name

    with open(tmp_path, "rb") as f:
        result = groq.Groq(api_key=keys.get("GROQ_API_KEY")).audio.transcriptions.create(
            model="whisper-large-v3-turbo", file=f
        )
    os.remove(tmp_path)
    return result.text

if __name__ == "__main__":
    print(listen())