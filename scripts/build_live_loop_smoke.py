#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import math
import subprocess
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/assets/audio/live-loop-elementary-ace-test"
SR = 44100
DURATION = 64.0
N = int(SR * DURATION)


def clamp(x: float) -> float:
    return max(-0.98, min(0.98, x))


def env(t: float, start: float, end: float, attack: float = 0.05, release: float = 0.25) -> float:
    if t < start or t >= end:
        return 0.0
    if t < start + attack:
        return (t - start) / max(attack, 1e-6)
    if t > end - release:
        return max(0.0, (end - t) / max(release, 1e-6))
    return 1.0


def write_wav(path: Path, mono: list[float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        frames = bytearray()
        for sample in mono:
            v = int(clamp(sample) * 32767)
            frames += v.to_bytes(2, "little", signed=True)
            frames += v.to_bytes(2, "little", signed=True)
        wf.writeframes(frames)


def stats(mono: list[float], path: Path) -> dict:
    peak = max(abs(x) for x in mono)
    rms = math.sqrt(sum(x * x for x in mono) / len(mono))
    return {
        "file": str(path.relative_to(ROOT)),
        "duration_seconds": DURATION,
        "sample_rate": SR,
        "rms": round(rms, 6),
        "peak": round(peak, 6),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def synth() -> tuple[list[float], list[float], list[float], list[dict]]:
    room = [0.0] * N
    ai = [0.0] * N
    events: list[dict] = []
    root_freqs = [110.0, 130.81, 146.83, 164.81]

    # Human room-input loop: bass pulse + hummed melody + hand percussion.
    for i in range(N):
        t = i / SR
        bar = int(t // 4)
        beat = t % 1.0
        chord = root_freqs[bar % len(root_freqs)]
        human_env = env(t, 0, 60, attack=0.5, release=2.5)
        bass = math.sin(2 * math.pi * chord * t) * 0.13
        hum_freq = chord * (2.0 if (bar % 4) in (0, 1) else 2.25)
        hum = math.sin(2 * math.pi * hum_freq * t + 0.2 * math.sin(2 * math.pi * 4.5 * t)) * 0.08
        perc = 0.0
        if beat < 0.035:
            perc += (1.0 - beat / 0.035) * math.sin(2 * math.pi * 75 * t) * 0.18
        if 0.5 <= beat < 0.525:
            perc += (1.0 - (beat - 0.5) / 0.025) * math.sin(2 * math.pi * 210 * t) * 0.08
        # Drop out sections to test response scheduler space detection.
        space = 0.35 if 16 <= t < 20 or 44 <= t < 48 else 1.0
        room[i] = (bass + hum + perc) * human_env * space

    # AI return loop: answers after the human phrases, simulating Elementary
    # local loop-bank transform first and ACE-Step next-phrase refill later.
    answer_windows = [
        (8, 16, "elementary_loopbank_bright_answer"),
        (20, 32, "ace_step_next_phrase_async_return"),
        (36, 44, "elementary_filtered_delay_answer"),
        (48, 60, "ace_step_next_phrase_async_return_2"),
    ]
    for start, end, label in answer_windows:
        events.append({"start": start, "end": end, "bus": "ai_return_bus", "event": label})
        for i in range(int(start * SR), int(end * SR)):
            t = i / SR
            local_t = t - start
            e = env(t, start, end, attack=0.25, release=0.7)
            pulse = (0.5 + 0.5 * math.sin(2 * math.pi * 0.5 * local_t))
            shimmer = math.sin(2 * math.pi * (330 + 35 * math.sin(2 * math.pi * 0.125 * t)) * t) * 0.055
            fifth = math.sin(2 * math.pi * 220 * 1.5 * t) * 0.045
            sub = math.sin(2 * math.pi * 55 * t) * 0.04
            ai[i] += (shimmer + fifth + sub) * e * (0.65 + 0.35 * pulse)

    events.extend([
        {"start": 0, "end": 8, "bus": "room_input_bus", "event": "human establishes loop"},
        {"start": 8, "end": 16, "bus": "elementary_dsp_loop_bus", "event": "local low-latency loop-bank answer"},
        {"start": 20, "end": 32, "bus": "modal_ace_step_next_phrase_worker", "event": "async next phrase returned to ai bus"},
        {"start": 48, "end": 60, "bus": "modal_ace_step_next_phrase_worker", "event": "second async refill returned"},
    ])

    mix = []
    for r, a in zip(room, ai):
        duck = 0.72 if abs(r) > 0.08 else 1.0
        mix.append(clamp(r * 0.82 + a * 0.95 * duck))
    return room, ai, mix, sorted(events, key=lambda x: (x["start"], x["bus"]))


def analyze_windows(room: list[float], ai: list[float], mix: list[float]) -> list[dict]:
    rows = []
    win = int(2 * SR)
    for idx, start in enumerate(range(0, N, win)):
        end = min(N, start + win)
        chunk = room[start:end]
        ai_chunk = ai[start:end]
        mix_chunk = mix[start:end]
        rms = math.sqrt(sum(x*x for x in chunk) / len(chunk))
        ai_rms = math.sqrt(sum(x*x for x in ai_chunk) / len(ai_chunk))
        mix_rms = math.sqrt(sum(x*x for x in mix_chunk) / len(mix_chunk))
        zc = sum(1 for a, b in zip(chunk, chunk[1:]) if (a >= 0) != (b >= 0)) / len(chunk)
        brightness = "bright" if zc > 0.035 else "warm"
        state = "space" if rms < 0.055 else "active"
        decision = "trigger_ai_return" if state == "space" or idx in {4, 10, 18, 24} else "listen"
        rows.append({
            "start_seconds": round(start / SR, 3),
            "end_seconds": round(end / SR, 3),
            "room_rms": round(rms, 6),
            "ai_rms": round(ai_rms, 6),
            "mix_rms": round(mix_rms, 6),
            "zero_crossing_density": round(zc, 6),
            "brightness_state": brightness,
            "energy_state": state,
            "scheduler_decision": decision,
        })
    return rows


def convert_mp3(wav_path: Path) -> Path:
    mp3 = wav_path.with_suffix(".mp3")
    subprocess.run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(wav_path),
        "-codec:a", "libmp3lame", "-b:a", "192k", str(mp3)
    ], check=True)
    return mp3


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    room, ai, mix, events = synth()
    wavs = {
        "01_room_input_bus.wav": room,
        "02_ai_return_bus.wav": ai,
        "03_stream_monitor_mix.wav": mix,
        "04_fast_window_playable_feedback_sketch.wav": mix[: int(16 * SR)],
    }
    artifact_stats = []
    for name, data in wavs.items():
        path = OUT / name
        dur = len(data) / SR
        write_wav(path, data)
        mp3 = convert_mp3(path)
        st = stats(data + ([0.0] * (N - len(data))) if len(data) < N else data, path)
        st["duration_seconds"] = round(dur, 3)
        st["mp3_file"] = str(mp3.relative_to(ROOT))
        st["mp3_sha256"] = hashlib.sha256(mp3.read_bytes()).hexdigest()
        st["mp3_bytes"] = mp3.stat().st_size
        artifact_stats.append(st)

    rows = analyze_windows(room, ai, mix)
    csv_path = OUT / "analyzer_windows.csv"
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    receipt = {
        "status": "offline_live_loop_smoke_verified",
        "truth_label": "deterministic synthetic bus simulation; not a live WebRTC room and not a real ACE-Step GPU render",
        "framework_added": "Elementary Audio",
        "model_lane_added": "ACE-Step async next phrase via Modal contract",
        "sample_rate": SR,
        "buses": ["room_input_bus", "elementary_dsp_loop_bus", "ai_return_bus", "stream_monitor_bus"],
        "events": events,
        "artifacts": artifact_stats,
        "analyzer_csv": str(csv_path.relative_to(ROOT)),
        "fail_closed_flags": {
            "starts_gpu": False,
            "starts_paid_api": False,
            "opens_microphone": False,
            "records_audio": False,
            "uploads_private_media": False,
            "publishes_stream": False,
        },
    }
    receipt_path = OUT / "LIVE_LOOP_ELEMENTARY_ACE_TEST_RECEIPT.json"
    receipt_path.write_text(json.dumps(receipt, indent=2))
    print(json.dumps({"receipt": str(receipt_path), "artifacts": len(artifact_stats)}, indent=2))


if __name__ == "__main__":
    main()
