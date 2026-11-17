# AI Mountain Comedy Studio

This directory contains the Nepali comedy episode workflow. The original Saturday script generator and its workflow are preserved.

## Recurring characters

The permanent character bible lives at `studio/characters/character_profiles.json`. It defines ten original recurring characters across five pairings:

- आमा–छोरा: सुशीला आमा and रोहन
- बुबा–छोरी: हरिप्रसाद and इशा
- श्रीमान्–श्रीमती: विकास and मीना
- दाजु–बहिनी: समीर दाजु and प्रकृति
- दुई साथी: निश्चल and उज्ज्वल

Each profile stores a stable character ID, visual identity, signature wardrobe, personality, mannerisms, Nepali voice description, reference-image prompt and negative prompt. The episode generator now loads these profiles and includes the selected pair's identity details and reference prompts in the generated episode package.

## Generate an episode

Run the GitHub Actions workflow **Build Nepali Comedy Episode** manually. Choose short or long, select a pairing, and optionally provide a topic. Add `GEMINI_API_KEY` as a repository Actions secret first.

- Short: 30–50 seconds, vertical 9:16
- Long: 1–2 minutes, horizontal 16:9

The artifact contains the episode JSON, dialogue Markdown and a pair-specific `thumbnail_prompt.txt`. The thumbnail prompt uses the selected two characters only, their approved identities and episode outfits, a consistent AI Mountain Comedy Studio brand layout, a Nepali headline and an incrementing episode badge. It is a prompt package only: an actual thumbnail image file is not generated yet. The artifact also does not yet contain generated character image files or a rendered MP4.

## Next production stages

Generate and save reference images from the profile prompts, then integrate consistent avatar video, separate Nepali TTS voices, speaker-specific lip-sync and final FFmpeg rendering. These stages require a suitable external API or self-hosted model; costs and free tiers depend on the provider.
