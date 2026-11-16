import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
import requests

PAIRINGS = {
    'mother_son': ('आमा', 'छोरा', 'चतुर र हाजिरजवाफ', 'आत्मविश्वासी तर सजिलै फस्ने'),
    'father_daughter': ('बुबा', 'छोरी', 'अनुभवी र मायालु', 'आधुनिक र तीक्ष्ण बुद्धि'),
    'husband_wife': ('श्रीमान्', 'श्रीमती', 'ठूलो योजना बनाउने', 'व्यवहारिक र चतुर'),
    'brother_sister': ('दाजु', 'बहिनी', 'आफूलाई ज्ञानी ठान्ने', 'चुलबुले र व्यङ्ग्यात्मक'),
    'two_friends': ('साथी १', 'साथी २', 'अति आत्मविश्वासी', 'तथ्य देखाएर जिस्क्याउने'),
}

def build_prompt(fmt, pairing_id, topic):
    a, b, pa, pb = PAIRINGS[pairing_id]
    duration, ratio, words = ('30–50 seconds', '9:16', '75–115') if fmt == 'short' else ('1–2 minutes', '16:9', '180–280')
    schema = {
        'title': '...', 'logline': '...', 'duration_seconds': 40, 'aspect_ratio': ratio,
        'character_bible': {'A': {'name': a, 'visual_identity': '...', 'wardrobe': '...', 'voice': '...'}, 'B': {'name': b, 'visual_identity': '...', 'wardrobe': '...', 'voice': '...'}},
        'shots': [{'shot_id': 1, 'type': 'wide|two-shot|close-up', 'visual_prompt': 'English cinematic prompt', 'seconds': 5}],
        'dialogue': [{'speaker_id': 'A', 'text': 'नेपाली संवाद', 'emotion': '...', 'action': 'coffee sip', 'shot_id': 1}],
        'subtitles': [{'speaker_id': 'A', 'text': '...', 'start_seconds': 0, 'end_seconds': 2}],
        'audio': {'ambience': '...', 'sfx': ['...'], 'music_mood': '...'},
        'thumbnail_prompt': '...', 'youtube_title': '...', 'description': '...', 'tags': ['...']
    }
    return (f'नेपाली भाषामा मौलिक र अत्यन्तै रमाइलो comedy लेख्नुहोस्। स्थान: हिमाल देखिने नेपाली घरको बाल्कोनी, बिहान, टेबलमा कफी। पात्र A {a} ({pa}), पात्र B {b} ({pb})। विषय: {topic or "दैनिक जीवनको रमाइलो घटना"}। ढाँचा {fmt}, अवधि {duration}, संवाद लक्ष्य {words} शब्द, aspect {ratio}। प्राकृतिक बोलचालको नेपाली देवनागरी, बलियो hook, setup, punchline र callback। दुवै पात्र बराबर बोलून्। हरेक संवादमा speaker_id A/B, emotion, action र shot_id राख्नुहोस्। अनुहार, कपाल, कपडा र आवाजको स्थिर character bible बनाउनुहोस्। अपमानजनक वा घृणायुक्त मजाक नगर्नुहोस्। JSON मात्र फर्काउनुहोस्। Schema: ' + json.dumps(schema, ensure_ascii=False))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--format', choices=['short', 'long'], default='short')
    parser.add_argument('--pairing', choices=PAIRINGS, default='mother_son')
    parser.add_argument('--topic', default='')
    args = parser.parse_args()
    key = os.getenv('GEMINI_API_KEY', '').strip()
    if not key:
        sys.exit('Missing GEMINI_API_KEY Actions secret.')
    model = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash').strip()
    url = f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'
    payload = {'contents': [{'parts': [{'text': build_prompt(args.format, args.pairing, args.topic)}]}], 'generationConfig': {'temperature': 0.95, 'responseMimeType': 'application/json'}}
    response = requests.post(url, headers={'x-goog-api-key': key}, json=payload, timeout=120)
    if not response.ok:
        sys.exit(f'Gemini API HTTP {response.status_code}: {response.text[:1200]}')
    try:
        data = json.loads(response.json()['candidates'][0]['content']['parts'][0]['text'])
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        sys.exit(f'Gemini returned invalid JSON: {exc}')
    required = ['title', 'character_bible', 'shots', 'dialogue', 'subtitles', 'audio', 'thumbnail_prompt']
    missing = [name for name in required if name not in data]
    if missing:
        sys.exit('Missing required fields: ' + ', '.join(missing))
    if not data['shots'] or not data['dialogue']:
        sys.exit('Episode has no shots or dialogue.')
    if {line.get('speaker_id') for line in data['dialogue']} - {'A', 'B'}:
        sys.exit('Invalid speaker_id in dialogue.')
    ratio = '9:16' if args.format == 'short' else '16:9'
    data.update({'format': args.format, 'aspect_ratio': ratio, 'pairing': args.pairing, 'generated_at': datetime.now(timezone.utc).isoformat()})
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
    output = Path('output') / f'{args.format}-{args.pairing}-{stamp}'
    output.mkdir(parents=True, exist_ok=True)
    (output / 'episode.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    lines = [f"# {data['title']}", '', '## संवाद']
    for line in data['dialogue']:
        speaker = data['character_bible'].get(line['speaker_id'], {}).get('name', line['speaker_id'])
        lines.append(f"**{speaker}:** {line['text']}")
    (output / 'episode.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'Generated episode package: {output}')

if __name__ == '__main__':
    main()