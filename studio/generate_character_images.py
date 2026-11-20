#!/usr/bin/env python3
"""Generate one approved master portrait per permanent cast member with Nano Banana."""
from __future__ import annotations
import argparse, base64, json, os, re, sys, time
from pathlib import Path
from google import genai

ROOT = Path(__file__).resolve().parents[1]
CAST_PATH = ROOT / "studio" / "characters" / "cast_11.json"
OUT_DIR = ROOT / "studio" / "characters" / "generated"

def safe_id(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "_", value)

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--character", default="all", help="all or one exact character_id")
    parser.add_argument("--image-size", choices=["1K", "2K", "4K"], default="2K")
    parser.add_argument("--aspect-ratio", default="3:4")
    parser.add_argument("--force", action="store_true", help="Regenerate even if an image already exists")
    args = parser.parse_args()

    # Prefer the user's numbered key pool; retain the legacy single-key fallback.
    api_keys = []
    for key_name in [f"GEMINI_API_KEY_{i}" for i in range(1, 6)] + ["GEMINI_API_KEY"]:
        value = os.getenv(key_name, "").strip()
        if not value:
            continue
        if not value.isascii() or any(ord(ch) < 33 or ord(ch) > 126 for ch in value):
            print(f"Skipping {key_name}: contains whitespace/control/non-ASCII characters.", file=sys.stderr)
            continue
        api_keys.append((key_name, value))
    if not api_keys:
        sys.exit("No usable Gemini key found. Add GEMINI_API_KEY_1 through GEMINI_API_KEY_5 as Repository secrets.")

    model = os.getenv("GEMINI_IMAGE_MODEL", "gemini-nano-banana-2.1").strip()
    cast_data = json.loads(CAST_PATH.read_text(encoding="utf-8"))
    characters = cast_data["cast"]
    if args.character != "all":
        characters = [c for c in characters if c["character_id"] == args.character]
        if not characters:
            sys.exit(f"Unknown character_id: {args.character}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {"model": model, "image_size": args.image_size, "aspect_ratio": args.aspect_ratio, "images": []}

    for index, character in enumerate(characters, start=1):
        character_id = character["character_id"]
        target = OUT_DIR / f"{safe_id(character_id)}.png"
        if target.exists() and not args.force:
            print(f"[{index}/{len(characters)}] SKIP existing: {target.name}")
            manifest["images"].append({"character_id": character_id, "name_ne": character["name_ne"], "file": target.name, "status": "existing"})
            continue

        prompt = (
            character["reference_image_prompt"]
            + "\n\nCAST-WIDE VISUAL RULES: All people are original fictional Nepali characters, not real people. "
            "Photorealistic high-definition portrait, natural skin texture, realistic facial anatomy, natural hands if visible, "
            "lifelike eyes, fine individual hair strands, physically believable light and shadows. "
            "No collage, no contact sheet, no split panels, no captions, no labels, no text, no watermark. "
            "Show exactly one character, centered, head and upper torso fully visible, neutral relaxed pose. "
            "Create a clean master identity reference, not a poster."
            + "\n\nAVOID: " + character["negative_prompt"]
        )
        last_error = None
        for key_name, key_value in api_keys:
            try:
                client = genai.Client(api_key=key_value)
                result = client.interactions.create(
                    model=model,
                    input=prompt,
                    response_format={
                        "type": "image",
                        "mime_type": "image/png",
                        "aspect_ratio": args.aspect_ratio,
                        "image_size": args.image_size,
                    },
                )
                output_image = getattr(result, "output_image", None)
                image_data = getattr(output_image, "data", None) if output_image else None
                if not image_data:
                    raise RuntimeError("Nano Banana returned no output_image data.")
                image_bytes = base64.b64decode(image_data)
                if not image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
                    raise RuntimeError("Returned image is not a valid PNG.")
                target.write_bytes(image_bytes)
                manifest["images"].append({"character_id": character_id, "name_ne": character["name_ne"], "file": target.name, "status": "generated", "bytes": len(image_bytes), "key_slot": key_name})
                print(f"[{index}/{len(characters)}] GENERATED: {target.name} using {key_name} ({len(image_bytes)} bytes)")
                last_error = None
                break
            except Exception as exc:
                last_error = exc
                print(f"{key_name} failed for {character_id}: {exc}", file=sys.stderr)
                continue
        if last_error:
            sys.exit(f"Image generation failed for {character_id}: {last_error}")

    manifest_path = OUT_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + chr(10), encoding="utf-8")
    gallery_lines = ["# ११ स्थायी पात्र — Character Image Gallery", "", f"Model: {model} | Resolution: {args.image_size}", ""]
    for item in manifest["images"]:
        gallery_lines.extend([f"## {item['name_ne']}", f"![{item['name_ne']}]({item['file']})", f"Character ID: `{item['character_id']}`", ""])
    (OUT_DIR / "GALLERY.md").write_text(chr(10).join(gallery_lines), encoding="utf-8")
    print(f"Completed {len(characters)} character image(s). Output: {OUT_DIR}")

if __name__ == "__main__":
    main()
