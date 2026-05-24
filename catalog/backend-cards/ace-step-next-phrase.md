# Backend card: ACE-Step async next phrase

- **Lane:** async music generation / next phrase
- **Upstream:** https://github.com/ace-step/ACE-Step
- **License:** Apache-2.0
- **Model family:** ACE-Step / ACE-Step v1.5
- **Role:** Generate the next 8-30 second phrase, fill, accompaniment, remix, or loop-bank refill while the local loop-bank keeps playback responsive.
- **Why:** ACE-Step is a music-generation model family focused on speed, coherence, controllability, lyric/song support, remixing, and audio-to-audio style workflows. It fits behind the Modal worker better than direct browser execution.
- **First safe action:** Add a Modal worker lane named `ace_step_next_phrase` that accepts a capped prompt + optional local bounce and returns WAV/FLAC + metadata. Start with a 2-5 second smoke only after approval.
- **Hardware/cost:** Modal GPU; scale-to-zero; duration and steps capped.
- **Risk:** Not instant note-level response; use it asynchronously for the next section. Confirm model license/weights terms before public/commercial release.
- **Closed flags:** starts_gpu=false until human approval, starts_paid_api=false until human approval, records_audio=false, uploads_private_media=false unless explicitly approved, publishes_stream=false.
