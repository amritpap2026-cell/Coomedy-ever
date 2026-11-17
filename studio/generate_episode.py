import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
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



CALENDAR_BASE_URL = "https://trisambat.com/api/v1"


def load_nepali_calendar(date_override=""):
    """Load BS date and festival events; continue safely if the calendar API is unavailable."""
    try:
        if date_override:
            parsed = datetime.strptime(date_override, "%Y-%m-%d").date()
            url = f"{CALENDAR_BASE_URL}/ad/{parsed.year}/{parsed.month:02d}.json"
            response = requests.get(url, timeout=20)
            response.raise_for_status()
            payload = response.json()
            days = payload.get("days", []) if isinstance(payload, dict) else payload
            day = next((item for item in days if item.get("ad") == parsed.isoformat()), None)
            if not day:
                raise ValueError("No calendar record for " + parsed.isoformat())
        else:
            response = requests.get(f"{CALENDAR_BASE_URL}/today.json", timeout=20)
            response.raise_for_status()
            day = response.json()

        bs_year = day.get("bs", {}).get("year")
        if not bs_year:
            raise ValueError("Calendar response has no BS year.")
        holiday_response = requests.get(f"{CALENDAR_BASE_URL}/holidays/{bs_year}.json", timeout=20)
        holiday_response.raise_for_status()
        holiday_payload = holiday_response.json()
        entries = holiday_payload.get("days", holiday_payload.get("holidays", [])) if isinstance(holiday_payload, dict) else holiday_payload
        ad_date = day.get("ad") or date_override
        events = list(day.get("events", []))
        if isinstance(entries, list):
            for item in entries:
                if isinstance(item, dict) and (item.get("ad") or item.get("date") or item.get("gregorian")) == ad_date:
                    if item not in events:
                        events.append(item)
        return {
            "available": True,
            "ad_date": ad_date,
            "bs_date": day.get("text", {}).get("bs", {}).get("ne", ""),
            "weekday": day.get("weekday"),
            "events": events,
            "is_holiday": day.get("holiday", False),
            "source": "Trisambat Nepali Calendar API (beta)",
        }
    except Exception as exc:
        print("WARNING: Nepali calendar unavailable; using a regular-day script. " + str(exc), file=sys.stderr)
        return {
            "available": False,
            "ad_date": date_override or datetime.now(ZoneInfo("Asia/Kathmandu")).date().isoformat(),
            "bs_date": "",
            "weekday": None,
            "events": [],
            "is_holiday": False,
            "source": "unavailable",
            "warning": str(exc),
        }


def calendar_event_names(calendar):
    result = []
    for event in calendar.get("events", []):
        if isinstance(event, str):
            result.append(event)
        elif isinstance(event, dict):
            name = event.get("nameNe") or event.get("name_ne") or event.get("name") or event.get("title") or event.get("festival")
            if name:
                result.append(str(name))
    return list(dict.fromkeys(result))


def build_prompt(fmt, pairing_id, topic, profiles, calendar, series_state):
    pairing = profiles["pairings"][pairing_id]
    characters = pairing["characters"]
    next_episode_number = int(series_state.get("episode_number", 0)) + 1
    selected_outfits = {
        speaker_id: characters[speaker_id]["outfit_options"][(next_episode_number - 1) % len(characters[speaker_id]["outfit_options"])]
        for speaker_id in ("A", "B")
    }
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
                "wardrobe": selected_outfits[speaker_id]["description"],
                "outfit_id": selected_outfits[speaker_id]["outfit_id"],
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
        "series_continuity": {"story_elapsed_years": 0, "timeline_summary": "...", "previous_episode_recap": "...", "current_situation": "...", "character_state": {}, "ongoing_story_arcs": [], "unresolved_threads": [], "running_gags": [], "new_episode_hook": "..."},
        "comedy_quality_check": {"hook_strength": "...", "main_satirical_target": "...", "escalation": "...", "final_punchline": "...", "callback": "..."},
    }
    child_identity_block = {child_id: {k: v for k, v in child.items() if k not in ("reference_image_prompt", "negative_prompt")} for child_id, child in supporting.items()}
    child_reference_prompts = {child_id: {"reference_image_prompt": child["reference_image_prompt"], "negative_prompt": child["negative_prompt"]} for child_id, child in supporting.items()}
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
    creative_seed = hashlib.sha256((str(calendar.get("ad_date")) + "|" + pairing_id + "|" + (topic or "daily")).encode("utf-8")).hexdigest()[:12]
    calendar_context = {
        "ad_date": calendar.get("ad_date"),
        "bs_date_ne": calendar.get("bs_date"),
        "special_events_today": calendar_event_names(calendar),
        "public_holiday": calendar.get("is_holiday", False),
        "calendar_available": calendar.get("available", False),
        "creative_seed": creative_seed,
    }
    return (
        "नेपाली भाषामा मौलिक, अत्यन्तै रमाइलो र स्वाभाविक comedy लेख्नुहोस्। "
        "स्थान: हिमाल देखिने नेपाली घरको बाल्कोनी, बिहान, टेबलमा कफी। "
        f"विषय: {topic or 'दैनिक जीवनको रमाइलो घटना'}। ढाँचा {fmt}, अवधि {duration}, "
        f"संवाद लक्ष्य {words} शब्द, aspect {ratio}। "
        "प्राकृतिक, जीवन्त, बोलिचालीको नेपाली देवनागरी प्रयोग गर्नुहोस्—किताबी वा अनुवाद-जस्तो भाषा होइन। "
        "यो साधारण जोकको सूची होइन; दर्शकलाई पेट मिची-मिची हँसाउने, धारिलो तर बुद्धिमानी नेपाली व्यंग्य-कथा हुनुपर्छ। "
        "पहिलो 1–2 सेकेन्डमै चाखलाग्दो hook दिनुहोस्। त्यसपछि वास्तविक नेपाली जीवनको चिनिने समस्या, ढोंग वा विरोधाभास "
        "छान्नुहोस्; पात्रहरूको फरक सोचबाट ठट्टा सुरु गर्नुहोस् र हरेक संवादसँग हास्यको स्तर बढाउनुहोस्। "
        "कम्तीमा 3 वटा बलिया laugh beats, एउटा अप्रत्याशित तर तर्क मिल्ने twist र अन्त्यमा सबैभन्दा बलियो, "
        "छोटो र याद रहने punchline दिनुहोस्। सुरुको शब्द, वस्तु वा कुरा अन्त्यमा नयाँ अर्थमा फर्काएर callback गर्नुहोस्। "
        "संवाद छोटा, timing मिल्ने र एकअर्कालाई जिस्क्याउने स्वाभाविक शैलीका होऊन्। "
        "व्यंग्य सामाजिक बानी, देखावटीपन, महँगी, मोबाइल, अफिस, पढाइ, सार्वजनिक प्रशासनिक व्यवहार, परिवारका "
        "विरोधाभास वा पर्वका वास्तविक चलनमा केन्द्रित हुन सक्छ। गाली, अश्लीलता वा कमजोरमाथि प्रहारलाई हास्य नबनाउनुहोस्। "
        "जात, धर्म, लिङ्ग, अपाङ्गता वा समुदायलाई होच्याएर हँसाउने काम नगर्नुहोस्; व्यंग्य व्यवहार र शक्तिको दुरुपयोगमाथि होस्। "
        "फजुल filler, घिसेपिटे चुट्किला, जबर्जस्ती rhyme र व्याख्या गर्नुपर्ने punchline नलेख्नुहोस्। "
        "हरेक episode नयाँ premise भए पनि एउटै निरन्तर series को भाग हुनुपर्छ। अघिल्लो episode को घटना र परिणामबाटै आजको कथा अघि बढाउनुहोस्। कथा कहिल्यै reset वा समाप्त नगर्नुहोस्। पात्रले पुराना घटना सम्झनुपर्छ; सम्बन्ध, निर्णय र समस्याहरू समयसँगै विकसित हुनुपर्छ। एउटा मुख्य कथा-धागो लामो समय चलाउनुहोस्, सबै समस्या एउटै भागमा समाधान नगर्नुहोस्। हरेक भागमा बलियो punchline सँगै अर्को भागतर्फ तान्ने cliffhanger वा खुला hook राख्नुहोस्। अघिल्लो घटनासँग नमिल्ने कुरा नलेख्नुहोस्। "
        "दुवै पात्रलाई अर्थपूर्ण र हास्यास्पद भूमिका दिनुहोस्। "
        "तलका character profiles स्थायी canon हुन्: अनुहार, उमेर, छाला, कपाल, चिनारी, व्यक्तित्व वा आवाज नबदल्नुहोस्। "
        "हरेक नयाँ episode मा कथाअनुसार नयाँ पोसाक छान्न सकिन्छ; तर एउटै episode का सबै shot र angle मा "
        "त्यही पोसाक, रंग र सामान निरन्तर राख्नुहोस्। हरेक shot prompt मा सम्बन्धित character_id कायम राख्नुहोस्। "
        "Speaker A/B कहिल्यै नसाट्नुहोस्। "
        "प्रत्येक संवादमा speaker_id, emotion, action र shot_id अनिवार्य राख्नुहोस्। "
        "आजको नेपाली पात्रोअनुसार विशेष पर्व वा दिवस छ भने त्यसको संस्कृति, खानपान, चलन र पारिवारिक परिवेशलाई कथामा स्वाभाविक रूपमा समेट्नुहोस्। पर्वको नाम मात्र उल्लेख नगर्नुहोस्; त्यसैअनुसार मौलिक punchline बनाउनुहोस्। आज विशेष पर्व छैन भने जबर्जस्ती पर्व नथप्नुहोस्। पात्रोमा नभएका मिति वा सांस्कृतिक तथ्य नबनाउनुहोस्। अपमानजनक वा घृणायुक्त मजाक नगर्नुहोस्। JSON मात्र फर्काउनुहोस्.\n"
        "NEPALI CALENDAR CONTEXT: " + json.dumps(calendar_context, ensure_ascii=False) + "\n"
        "SERIES MEMORY — continue this exact timeline: " + json.dumps(series_state, ensure_ascii=False) + "\n"
        "SELECTED OUTFITS FOR THIS EPISODE (must remain identical in every shot): "
        + json.dumps(selected_outfits, ensure_ascii=False)
        + "\nPERMANENT CHARACTER CANON: "
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
    parser.add_argument("--date", default="", help="Optional AD date YYYY-MM-DD; defaults to today in Nepal.")
    args = parser.parse_args()

    profiles = load_profiles()
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        sys.exit("Missing GEMINI_API_KEY Actions secret.")
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    calendar = load_nepali_calendar(args.date)
    state_path = ROOT / "series_state.json"
    series_state = json.loads(state_path.read_text(encoding="utf-8"))
    prompt = build_prompt(args.format, args.pairing, args.topic, profiles, calendar, series_state)
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

    next_state = data.get("series_continuity")
    required_state = ("timeline_summary", "previous_episode_recap", "current_situation", "character_state", "ongoing_story_arcs", "unresolved_threads", "running_gags", "new_episode_hook")
    if not isinstance(next_state, dict) or any(k not in next_state for k in required_state):
        sys.exit("Missing complete series_continuity; refusing disconnected episode.")
    next_state["episode_number"] = int(series_state.get("episode_number", 0)) + 1
    next_state["story_elapsed_years"] = max(elapsed_years, float(next_state.get("story_elapsed_years", elapsed_years)))
    next_state["story_day"] = int(series_state.get("story_day", 0)) + 1
    next_state["last_episode_date_ad"] = calendar.get("ad_date", "")
    next_state["last_episode_title"] = data.get("title", "")
    next_state["last_pairing"] = args.pairing
    next_state["series_title"] = series_state.get("series_title", "हिमालको बाल्कोनी — कहिल्यै नसकिने गफ")
    recent = list(series_state.get("recent_premises", []))
    recent.append(data.get("logline", data.get("title", "")))
    next_state["recent_premises"] = recent[-30:]
    state_path.write_text(json.dumps(next_state, ensure_ascii=False, indent=2) + chr(10), encoding="utf-8")
    data["series_continuity"] = next_state
    data["series_episode_number"] = next_state["episode_number"]
    data["series_title"] = next_state["series_title"]

    # Attach the authoritative character identities and image prompts to every episode package.
    selected = profiles["pairings"][args.pairing]["characters"]
    data["studio_character_profiles"] = {
        speaker_id: selected[speaker_id] for speaker_id in ("A", "B")
    }
    data["selected_outfits"] = {
        speaker_id: {
            **selected_outfits[speaker_id],
            "character_id": selected[speaker_id]["character_id"],
            "character_name": selected[speaker_id]["name"],
        }
        for speaker_id in ("A", "B")
    }
    data["recurring_children"] = {
        child_id: {
            **child,
            "current_age_years": child["starting_age_years"] + int(next_state["story_elapsed_years"]),
            "selected_outfit": child_outfits[child_id],
        }
        for child_id, child in supporting.items()
    }
    data["selected_outfits"] = {speaker_id: {**selected_outfits[speaker_id], "character_id": selected[speaker_id]["character_id"], "character_name": selected[speaker_id]["name"]} for speaker_id in ("A", "B")}
    data["nepali_calendar"] = calendar
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
    lines = [f"# {data['title']}", "", "## नेपाली पात्रो"]
    lines.append(f"- मिति: {calendar.get('bs_date') or calendar.get('ad_date')}")
    names = calendar_event_names(calendar)
    lines.append("- विशेष दिन/पर्व: " + (", ".join(names) if names else "आज पात्रोमा विशेष पर्व भेटिएन"))
    lines.extend(["", "## स्थायी पात्र"])
    for speaker_id in ("A", "B"):
        character = selected[speaker_id]
        lines.append(
            f"- **{character['name']}** ({character['character_id']}): "
            f"{character['apparent_age']}; Outfit: {selected_outfits[speaker_id]['name']} — {selected_outfits[speaker_id]['description']}"
        )
    lines.extend(["", "## स्थायी बाल पात्र"])
    for child_id, child in supporting.items():
        lines.append(f"- **{child['name']}**: {child['starting_age_years'] + int(next_state['story_elapsed_years'])} वर्ष; Outfit: {child_outfits[child_id]['name']} — {child_outfits[child_id]['description']}")
    lines.extend(["", "## संवाद"])
    for line in data["dialogue"]:
        speaker = selected[line["speaker_id"]]["name"]
        lines.append(f"**{speaker}:** {line['text']}")
    (output / "episode.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Generated episode package: {output}")


if __name__ == "__main__":
    main()
