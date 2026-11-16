# Production pipeline status

## Implemented
- Short (30–50 seconds, 9:16) and long (1–2 minutes, 16:9) choices.
- Five selectable Nepali character pairings.
- Gemini-generated character bible, shot prompts, speaker-labelled dialogue, subtitle cues, audio notes, thumbnail prompt and metadata.
- Downloadable GitHub Actions artifacts.

## Remaining before MP4
1. Persistent character reference images.
2. Separate Nepali TTS voices and timing for both speakers.
3. Consistent avatar video generation per shot.
4. Speaker-specific lip-sync using each character's own audio.
5. FFmpeg assembly, subtitles, ambience, SFX and MP4 export.
6. Automated video/audio/subtitle quality checks.

GitHub Actions orchestrates services; it does not itself generate realistic talking-avatar footage. The remaining stages need external APIs or self-hosted models and may cost money. Store credentials only as Actions secrets. Never report an MP4 as ready until it is rendered and checked.
