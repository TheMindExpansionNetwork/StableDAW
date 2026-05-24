# Backend card: Elementary Audio live-loop DSP

- **Lane:** realtime framework / local DSP
- **Upstream:** https://github.com/elemaudio/elementary
- **License:** MIT
- **Packages:** `@elemaudio/core`, `@elemaudio/web-renderer`
- **Role:** Browser-local loop-bank, transforms, ducking, delay/filter/gain, and AI-return kill switch.
- **Why:** StableDAW's DAW UI already uses browser Web Audio. Elementary adds a declarative DSP graph that can update from app state while staying low-latency.
- **First safe action:** Add a disabled-by-default `LiveLoopEngine` frontend wrapper that renders a silent graph and exposes a kill switch before any microphone capture.
- **Hardware/cost:** Local browser CPU; no GPU.
- **Risk:** AudioWorklet/mobile browser quirks; needs explicit user gesture for audio start.
- **Closed flags:** starts_gpu=false, starts_paid_api=false, records_audio=false, uploads_private_media=false, publishes_stream=false.
