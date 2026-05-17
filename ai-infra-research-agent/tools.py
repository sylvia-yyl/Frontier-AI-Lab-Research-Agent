from google import genai
from google.genai import types
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))


def search_web(query: str) -> tuple[str, list[str], list[str]]:
    """
    Search using Gemini + Google Search grounding.
    Returns (text, source_labels, source_urls).
    source_labels are domain/title strings used for tier classification.
    source_urls are the full URIs for clickable links.
    """
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=query,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())]
        )
    )

    text = response.text if response.text else "No results found"

    sources = []
    source_urls = []
    try:
        candidate = response.candidates[0]
        chunks = candidate.grounding_metadata.grounding_chunks
        for chunk in chunks:
            if hasattr(chunk, "web") and chunk.web:
                label = chunk.web.title or chunk.web.uri or ""
                url = chunk.web.uri or ""
                if label:
                    sources.append(label)
                    source_urls.append(url)
    except Exception:
        pass

    return text, sources, source_urls


if __name__ == "__main__":
    text, sources, source_urls = search_web("DeepSeek AI latest research 2026")
    print(text[:300])
    print(f"\nSources found: {len(sources)}")
    for label, url in zip(sources[:8], source_urls[:8]):
        print(f"  {label} — {url}")
