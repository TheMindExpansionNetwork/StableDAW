# Live looping framework/model add-on: Elementary Audio + ACE-Step

## Pick

**Framework:** [Elementary Audio](https://github.com/elemaudio/elementary) — MIT JavaScript DSP framework with `@elemaudio/core` and `@elemaudio/web-renderer` for browser audio apps.

**Model lane:** [ACE-Step / ACE-Step v1.5](https://github.com/ace-step/ACE-Step) — Apache-2.0 music generation model family suitable as an async next-phrase / remix / accompaniment worker.

## Why this fits StableDAW

StableDAW already has browser timeline editing, sequencer, piano roll, Web Audio playback, analyzer, and a FastAPI generation backend. For live looping, the missing layer is a **responsive local DSP bus** that can answer immediately while bigger models render the next section in the background.

Elementary Audio is a better live-looping add than another backend-only model because it can own the browser-local performance graph:

- loop-bank playback
- gain and mute/kill switch
- delay/reverb/filter/pan transforms
- ducking under human input
- deterministic graph updates from app state
- future native/plugin portability

ACE-Step is the next model lane because it is faster/controllable for music phrase generation and can live behind the existing Modal GPU bridge as an async generator. It should not be used for instant note-by-note response; it should generate the next 8-30 second phrase while the Elementary loop-bank keeps the room playable.

## Target bus shape

```text
room_input_bus
  -> short-window analyzer
  -> response scheduler
  -> elementary_dsp_loop_bus       # immediate local call-response
  -> ai_return_bus                 # selected/transformed/generated phrase
  -> stream_monitor_bus            # local monitor mix, limiter, kill switch

modal_ace_step_next_phrase_worker  # async; refills loop bank / next section
```

## Added backend contract

This fork adds a fail-closed module:

```text
backend/modules/live_loop/
```

Endpoints:

```text
GET /api/live-loop/status
GET /api/live-loop/bus-plan
```

These are plan/status endpoints only. They do not open the microphone, call Modal, start a GPU, record audio, upload private media, or publish a stream.

## Integration plan

1. Add `@elemaudio/core` and `@elemaudio/web-renderer` to the frontend when ready.
2. Create a browser `LiveLoopEngine` wrapper around the existing Web Audio player/analyzer.
3. Route StableDAW clips/library items into a loop bank.
4. Let the short-window analyzer pick loop-bank responses based on RMS, brightness, onset density, and silence gates.
5. Add an operator-visible kill switch and return-gain meter before mic capture.
6. Connect ACE-Step behind the Modal worker as a `next_phrase` lane:
   - prompt from analyzer/window state
   - cap duration to 8-30 seconds
   - return WAV/FLAC + metadata
   - import into Library/timeline/loop bank
7. Only after local loop-bank proof feels playable, move the room primitive to WebRTC/LiveKit.

## Truth labels

- Current status: **offline smoke verified, live room not started**.
- No real WebRTC room yet.
- No browser microphone opened by the new endpoint.
- No GPU spend by default.
- Generated proof audio is deterministic synthetic bus simulation, not a live human room.
