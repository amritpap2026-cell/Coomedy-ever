# Production pipeline status

## Implemented

- Short (30–50 seconds, 9:16) and long (1–2 minutes, 16:9) choices.
- Five selectable Nepali character pairings.
- Ten original recurring character profiles in `studio/characters/character_profiles.json`.
- Stable character IDs, appearance, signature clothing, personality, mannerisms, Nepali voice descriptions, reference-image prompts and negative prompts.
- Episode generation loads the selected permanent profiles and includes their identity and image-prompt data in each episode JSON.
- Gemini-generated shot prompts, speaker-labelled dialogue, subtitle cues, audio notes, thumbnail prompt and metadata.
- Downloadable GitHub Actions artifacts.

## Not yet implemented

1. Actual character reference-image files generated and saved in the repository or asset storage.
2. Separate Nepali TTS audio files for both speakers.
3. Consistent avatar video generation per shot.
4. Speaker-specific lip-sync using each character's own audio.
5. FFmpeg assembly, subtitles, ambience, SFX and MP4 export.
6. Automated video/audio/subtitle quality checks.

GitHub Actions orchestrates services; it does not itself generate realistic talking-avatar footage. The remaining stages need external APIs or self-hosted models and may cost money. Store credentials only as Actions secrets. Never report an MP4 as ready until it is rendered and checked.
