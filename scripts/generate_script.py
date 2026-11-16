import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


PROMPT = """\
Write an original, funny 4-6 minute Nepali YouTube comedy script for a recurring
show featuring one man and one woman sitting together on a couch in a cozy
Nepali mountain-region setting, drinking coffee.

The pair have playful, mutual flirting and affectionate teasing. Keep the jokes
lighthearted and respectful: no cruel insults, stereotypes, or jokes targeting
protected groups. Give both characters witty lines and let both get the better
of each other sometimes.

Write the dialogue in natural conversational Nepali (Devanagari). Include:
- A catchy episode title and a one-line premise.
- A short opening hook.
- Simple scene/action directions suitable for a fixed avatar, couch, and
  background.
- Clearly labeled dialogue for the two characters.
- A callback or punchline at the end and a brief viewer comment prompt.
- A suggested YouTube title and thumbnail text.

Make this episode feel fresh and self-contained. Do not claim that a real
person said or did anything. Output the script only, using clear headings.
"""


def generate_script(api_key: str, model: str) -> str:
    endpoint = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent"
    )
    payload = {
        "contents": [{"parts": [{"text": PROMPT}]}],
        "generationConfig": {"temperature": 0.9, "maxOutputTokens": 4096},
    }
    request = Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=60) as response:
            result = json.load(response)
    except HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Gemini API returned HTTP {error.code}: {details}"
        ) from error
    except URLError as error:
        raise RuntimeError(f"Could not reach the Gemini API: {error.reason}") from error

    try:
        text = "".join(
            part["text"]
            for part in result["candidates"][0]["content"]["parts"]
            if "text" in part
        ).strip()
    except (KeyError, IndexError, TypeError) as error:
        raise RuntimeError("Gemini returned no usable script text.") from error

    if not text:
        raise RuntimeError("Gemini returned an empty script.")
    return text


def main() -> int:
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("GEMINI_API_KEY is required. Add it as a GitHub Actions secret.", file=sys.stderr)
        return 1

    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash").strip()
    if not model:
        print("GEMINI_MODEL cannot be empty.", file=sys.stderr)
        return 1

    try:
        script = generate_script(api_key, model)
    except RuntimeError as error:
        print(error, file=sys.stderr)
        return 1

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M%S-utc")
    output_path = Path("output") / f"{timestamp}-nepali-comedy-script.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(f"# Nepali Comedy Script\n\n{script}\n", encoding="utf-8")
    print(f"Generated script: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
