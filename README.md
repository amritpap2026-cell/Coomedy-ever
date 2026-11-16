# Coomedy-ever
A nepali comedy

## Automatic script generation

The `Generate Nepali comedy script` GitHub Actions workflow generates an
original Nepali couch-comedy script with the Gemini API every Saturday at
18:00 Nepal Time. You can also start it manually from the repository's
**Actions** tab using **Run workflow**.

Before running it:

1. Add a repository Actions secret named `GEMINI_API_KEY` with your Gemini API
   key. Never put the key in this repository.
2. Optionally add a repository Actions variable named `GEMINI_MODEL` to choose
   a Gemini model. The default is `gemini-2.5-flash`.
3. After the run completes, download the `nepali-comedy-script-<run id>`
   artifact from the workflow run's **Artifacts** section. Artifacts are kept
   for 30 days.

This first phase generates scripts only. Video rendering and YouTube uploading
are not configured yet; add those after choosing a renderer and setting up
YouTube authorization.
