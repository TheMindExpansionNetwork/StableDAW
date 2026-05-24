# Modal realtime DAW bridge

StableDAW is already a strong browser DAW: the timeline, sequencer, piano roll, waveform editing, spectral analyzer, and audition transport run locally in the browser. The right Modal integration is **not** to put the whole DAW in the cloud. Keep the playable DAW local and route expensive render jobs to scale-to-zero GPU workers.

## Status in this fork

This fork adds a fail-closed bridge scaffold:

- Local backend module: `backend/modules/modal_daw/`
- Status endpoint: `GET /api/modal-daw/status`
- Safe preflight endpoint: `GET /api/modal-daw/preflight`
- Plan-only endpoint: `POST /api/modal-daw/plan-render`
- Modal worker contract: `modal/stabledaw_modal_worker.py`

The local endpoints **do not call Modal, start GPUs, upload audio, record audio, or publish streams**. They only expose the routing plan and approval state.

## Realtime strategy

For a playable DAW feel:

1. **Local realtime layer**
   - Browser Web Audio transport
   - Timeline edits, clip moves/cuts/fades
   - Sequencer and piano roll playback
   - Analyzer and meters
   - Short loop-bank previews

2. **Modal power layer**
   - Stable Audio 3 text-to-audio render jobs
   - Audio-to-audio and continuation jobs from selected bounced clips
   - Inpainting selected regions
   - Batch effects/stems where FFmpeg/local CPU is not enough
   - LoRA training from approved datasets

3. **Return path**
   - Modal returns WAV/FLAC plus metadata
   - StableDAW imports the artifact into the browser Library
   - User drags it onto the timeline or accepts it into an inpaint/continuation slot

This is closer to an Ableton-style workflow: local session stays responsive while cloud workers render the next phrase, fill, stem, or style pack.

## Approval gates

Default environment:

```bash
STABLEDAW_MODAL_ENABLE=false
STABLEDAW_MODAL_ENDPOINT_URL=
```

Before any live Modal GPU use, a human should approve:

- Modal deploy target and GPU size
- model choice (`small` first; `medium` only after smoke)
- max duration
- max steps
- whether private audio may be uploaded
- whether generated artifacts may be saved locally or pushed anywhere

## Manual deploy path

Only after approval:

```bash
modal deploy modal/stabledaw_modal_worker.py
export STABLEDAW_MODAL_ENABLE=true
export STABLEDAW_MODAL_ENDPOINT_URL=<deployed endpoint URL>
uv run uvicorn backend.server:app --host 0.0.0.0 --port 8600 --reload
```

Bounded smoke, after deploy:

```bash
modal run modal/stabledaw_modal_worker.py::smoke --prompt "short analog synth stab" --duration 2
```

## API shape to connect next

The current upstream frontend submits local jobs to `/api/generate-jobs` and polls `/api/jobs/{id}`. The clean next implementation is:

- Add `generation_backend = local | modal` in the Create panel.
- If `local`, keep the current `/api/generate-jobs` path.
- If `modal`, create a local job record with `backend: modal`, forward a bounded payload to the Modal endpoint, then populate the same `JOBS[job_id].result` shape when Modal returns.
- Reuse the existing Library/IndexedDB import and spectrogram paths so the UI does not need a second artifact system.

## Why this is safe for now

`GET /api/modal-daw/preflight` returns:

- `safe: No Modal network call or GPU start was made by this preflight.`
- `starts_gpu: false`
- `starts_paid_api: false`
- `records_audio: false`
- `uploads_private_media: false`
- `publishes_stream: false`

That keeps the fork reviewable and runnable without accidentally spending credits.
