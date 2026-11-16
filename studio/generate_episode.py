import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
PROFILE_PATH = ROOT / "characters" / "character_profiles.json"

# Keep these IDs aligned with the manual workflow inputs.
PAIRINGS = {
    "mother_son": ("आमा", "छोरा"),
    "father_daughter": ("बुबा", "छोरी"),
    "husband_wife": ("श्रीमान्", "श्रीमती"),
    "brother_sister": ("दाजु", "बहिनी"),
    "two_friends": ("साथी १", "साथी २"),
}


def load_profiles():
    if not PROFILE_PATH.is_file():
        sys.exit(f"Missing character profile file: {PROFILE_PATH}")
    try:
        profiles = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        sys.exit(f"Could not read character profiles: {exc}")
    if profiles.get("schema_version") != 1:
        sys.exit("Unsupported character profile schema_version.")
    for pairing_id in PAIRINGS:
        pairing = profiles.get("pairings", {}).get(pairing_id)
        if not pairing or not all(k in pairing.get("characters", {}) for k in ("A", "B")):
            sys.exit(f"Character profiles are incomplete for {pairing_id}.")
        for speaker_id in ("A", "B"):
            character = pairing["characters"][speaker_id]
            for field in ("character_id", "name", "reference_image_prompt", "negative_prompt", "voice_ne"):
                if not character.get(field):
                    sys.exit(f"Missing {field} for {pairing_id}/{speaker_id}.")
    return profiles


def build_prompt(fmt, pairing_id, topic, profiles):
    pairing = profiles["pairings"][pairing_id]
    characters = pairing["characters"]
    duration, ratio, words = (
        ("30–50 seconds", "9:16", "75–115")
        if fmt == "short"
        else ("1–2 minutes", "16:9", "180–280")
    )
    schema = {
        "title": "...",
        "logline": "...",
        "duration_seconds": 40 if fmt == "short" else 90,
        "aspect_ratio": ratio,
        "character_bible": {
            speaker_id: {
                "character_id": characters[speaker_id]["character_id"],
                "name": characters[speaker_id]["name"],
                "visual_identity": "Use the supplied permanent profile without changing it.",
                "wardrobe": characters[speaker_id]["wardrobe"],
                "voice": characters[speaker_id]["voice_ne"],
            }
            for speaker_id in ("A", "B")
        },
        "shots": [
            {
                "shot_id": 1,
                "type": "wide|two-shot|close-up",
                "speaker_focus": "A|B|both",
                "visual_prompt": "English cinematic prompt; preserve selected character identities.",
                "seconds": 5,
            }
        ],
        "dialogue": [
            {
                "speaker_id": "A",
                "text": "नेपाली संवाद",
                "emotion": "...",
                "action": "coffee sip",
                "shot_id": 1,
            }
        ],
        "subtitles": [
            {"speaker_id": "A", "text": "...", "start_seconds": 0, "end_seconds": 2}
        ],
        "audio": {"ambience": "...", "sfx": ["..."], "music_mood": "..."},
        "thumbnail_prompt": "...",
        "youtube_title": "...",
        "description": "...",
        "tags": ["..."],
    }
    identity_block = {
        speaker_id: {
            key: value
            for key, value in characters[speaker_id].items()
            if key not in ("reference_image_prompt", "negative_prompt")
        }
        for speaker_id in ("A", "B")
    }
    reference_prompts = {
        speaker_id: {
            "reference_image_prompt": characters[speaker_id]["reference_image_prompt"],
            "negative_prompt": characters[speaker_id]["negative_prompt"],
        }
        for speaker_id in ("A", "B")
    }
    return (
        "नेपाली भाषामा मौलिक, अत्यन्तै रमाइलो र स्वाभाविक comedy लेख्नुहोस्। "
        "स्थान: हिमाल देखिने नेपाली घरको बाल्कोनी, बिहान, टेबलमा कफी। "
        f"विषय: {topic or 'दैनिक जीवनको रमाइलो घटना'}। ढाँचा {fmt}, अवधि {duration}, "
        f"संवाद लक्ष्य {words} शब्द, aspect {ratio}। "
        "प्राकृतिक बोलचालको नेपाली देवनागरी, सुरुमा बलियो hook, त्यसपछि setup, "
        "अन्त्यमा बलियो punchline र सम्भव भए callback। दुवै पात्रलाई अर्थपूर्ण संवाद दिनुहोस्। "
        "तलका character profiles स्थायी canon हुन्: अनुहार, उमेर, छाला, कपाल, चिनारी, "
        "लुगा, व्यक्तित्व वा आवाज नबदल्नुहोस्। हरेक shot prompt मा सम्बन्धित character_id "
        "र उही दृश्य पहिचान कायम राख्ने निर्देशन समावेश गर्नुहोस्। एउटै पात्रलाई फरक अनुहार "
        "वा फरक कपडामा नदेखाउनुहोस्। Speaker A/B कहिल्यै नसाट्नुहोस्। "
        "प्रत्येक संवादमा speaker_id, emotion, action र shot_id अनिवार्य राख्नुहोस्। "
        "अपमानजनक, घृणायुक्त वा लक्षित समूहलाई होच्याउने मजाक नगर्नुहोस्। JSON मात्र फर्काउनुहोस्.\n"
        "PERMANENT CHARACTER CANON: "
        + json.dumps(identity_block, ensure_ascii=False)
        + "\nREFERENCE IMAGE PROMPTS: "
        + json.dumps(reference_prompts, ensure_ascii=False)
        + "\nOUTPUT JSON SCHEMA: "
        + json.dumps(schema, ensure_ascii=False)
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--format", choices=["short", "long"], default="short")
    parser.add_argument("--pairing", choices=PAIRINGS, default="mother_son")
    parser.add_argument("--topic", default="")
    args = parser.parse_args()

    profiles = load_profiles()
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        sys.exit("Missing GEMINI_API_KEY Actions secret.")
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    prompt = build_prompt(args.format, args.pairing, args.topic, profiles)
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.95,
            "responseMimeType": "application/json",
        },
    }
    response = requests.post(
        url, headers={"x-goog-api-key": key}, json=payload, timeout=120
    )
    if not response.ok:
        sys.exit(f"Gemini API HTTP {response.status_code}: {response.text[:1200]}")
    try:
        data = json.loads(response.json()["candidates"][0]["content"]["parts"][0]["text"])
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        sys.exit(f"Gemini returned invalid JSON: {exc}")

    required = [
        "title", "character_bible", "shots", "dialogue",
        "subtitles", "audio", "thumbnail_prompt",
    ]
    missing = [name for name in required if name not in data]
    if missing:
        sys.exit("Missing required fields: " + ", ".join(missing))
    if not data["shots"] or not data["dialogue"]:
        sys.exit("Episode has no shots or dialogue.")
    if {line.get("speaker_id") for line in data["dialogue"]} - {"A", "B"}:
        sys.exit("Invalid speaker_id in dialogue.")

    # Attach the authoritative character identities and image prompts to every episode package.
    selected = profiles["pairings"][args.pairing]["characters"]
    data["studio_character_profiles"] = {
        speaker_id: selected[speaker_id] for speaker_id in ("A", "B")
    }
    data.update({
        "format": args.format,
        "aspect_ratio": "9:16" if args.format == "short" else "16:9",
        "pairing": args.pairing,
        "pairing_label_ne": profiles["pairings"][args.pairing]["label_ne"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    })

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    output = Path("output") / f"{args.format}-{args.pairing}-{stamp}"
    output.mkdir(parents=True, exist_ok=True)
    (output / "episode.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = [f"# {data['title']}", "", "## स्थायी पात्र"]
    for speaker_id in ("A", "B"):
        character = selected[speaker_id]
        lines.append(
            f"- **{character['name']}** ({character['character_id']}): "
            f"{character['apparent_age']}; {character['wardrobe']}"
        )
    lines.extend(["", "## संवाद"])
    for line in data["dialogue"]:
        speaker = selected[line["speaker_id"]]["name"]
        lines.append(f"**{speaker}:** {line['text']}")
    (output / "episode.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Generated episode package: {output}")


if __name__ == "__main__":
    main()
