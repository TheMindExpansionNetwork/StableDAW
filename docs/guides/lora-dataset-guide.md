# LoRA Dataset Preparation Guide

**Derived from:** Direct reading of `stable_audio_3/data/dataset.py`, `scripts/pre_encode_dataset.py`, `scripts/train_lora.py`, `stable_audio_3/training/diffusion.py`, and `docs/workflows/lora.md`.
**Not assumptions — everything here is verifiable in those files.**

---

## What the pipeline actually does with your audio

The training pipeline (`SampleDataset`) accepts any audio file, resamples it to 44.1kHz stereo, then crops or zero-pads it to a fixed length (default: ~380 seconds). The padding mask tracks where real audio ends — padded regions don't corrupt gradient signal. Short files are fine; they just have a larger proportion of masked padding. The caption in the matching `.txt` file is passed raw to T5Gemma via `txt.read_text().strip()` — plain text, no special format.

**The model learns to associate the caption text with the audio content.** Dataset quality is entirely about how accurately and specifically that pairing describes what is heard.

---

## Mixed songs vs. stems vs. one-shots

The code is format-agnostic. The answer depends on what you want the LoRA to learn:

| Goal | Audio type | Why |
|---|---|---|
| Genre / vibe / aesthetic | Full mixes | Model hears the gestalt and learns overall texture |
| Specific instrument sound | **Stems only** | Full mix corrupts the signal — model hears irrelevant content alongside the target |
| Drum kit character | Stems or one-shots (200+) | One-shots are heavily padded; you need many for a meaningful signal |
| Synthesis texture | Solo recordings | Same as stems — isolation lets the caption match exactly what is heard |
| Producer style | Full mixes | Style = everything together |

**Rule:** The caption must describe exactly what the model hears. If the caption says "punchy 808 kick" but the file is a full mix with cymbals, snare, and bass, training signal is corrupted and the LoRA will learn poorly or inconsistently.

---

## Caption format and granularity

### Format

Plain text. One file, same name as the audio, `.txt` extension. The loader does:

```python
txt.read_text().strip()  # scripts/pre_encode_dataset.py:42
```

No tags format. No JSON. T5Gemma handles natural language, comma-separated descriptors, or a mix of both. Match the style the base model was trained on: describe what you hear.

### Minimum viable caption

Enough words to distinguish this clip from:
1. Everything else in your own dataset
2. The base model's existing knowledge of that sound

If every file in your dataset has the same caption, the LoRA overfits to that audio regardless of prompt. If the caption is too vague ("kick drum"), the LoRA competes with everything SA3 already knows about kick drums.

**Practical minimum: ~8–15 words covering instruments, key sonic characteristic, and genre context.**

| Quality | Example |
|---|---|
| Too vague | `kick drum` |
| Minimal OK | `kick drum, punchy, 808 style` |
| Good | `808 kick drum, deep sub, punchy attack, tight short decay, trap production` |
| Best | `808 kick drum, deep sub thump, sharp transient attack, tight 50ms decay, dry, no reverb, trap / drill production` |

### The `seconds_total` conditioner trap

On small datasets, the model can latch onto duration numbers instead of text. The docs (`docs/workflows/lora.md`) explicitly recommend:

```
--exclude seconds_total
```

for small datasets to prevent conditioner hijacking.

---

## Dataset size and step count

The training math:

```
effective_epochs ≈ steps / num_samples
```

Default: `--steps 10000`, `--batch_size 1`.

| Samples | Recommended steps | Effective epochs | Notes |
|---|---|---|---|
| 10–20 | 500–1,000 | ~50 | Very small — risk of overfit; use `--exclude seconds_total` |
| 50 | 2,000–3,000 | ~50 | Small but workable with coherent, well-captioned data |
| 80–150 | 5,000–10,000 | ~65–100 | Sweet spot for most LoRAs |
| 200–500 | 10,000–20,000 | ~50 | Solid; may need more steps to see full effect |
| One-shots (200+) | 5,000–10,000 | ~25–50 | One-shots are short; more files needed vs. loops |

**One-shot caveat:** A 0.1s one-shot at 44.1kHz is 4,410 samples out of a 12,582,912-sample window — 99.97% of the training example is masked padding. You need many one-shots of the same type to accumulate a meaningful gradient.

---

## Pre-encoding (recommended for repeated training runs)

Running `scripts/pre_encode_dataset.py` converts raw audio to SAME autoencoder latents once, saving `.npy` + `.json` pairs. Training then skips on-the-fly encoding, which is faster and reduces VRAM pressure.

```
encoded/
  000000000000.npy     ← latent tensor [channels, latent_length]
  000000000000.json    ← {"prompt": "...", "seconds_total": ..., "padding_mask": [...]}
  silence.npy          ← silence latent used for variable-length padding
```

Use `same-s` for CPU/low-VRAM encode; `same-l` for faster encoding on GPU (requires ~6GB+ VRAM).

---

## Automating caption work

The only required manual work per file is writing the caption. Strategies to minimize this:

1. **Filename parsing** — if files are named `909_kick_punchy_dry.wav`, strip extension, replace separators with spaces, optionally run through a small LLM to flesh out into a sentence
2. **Folder templates** — files organized by type (kicks/, basses/, pads/) get a per-folder template; only outliers need individual editing
3. **Batch apply + per-file override** — apply one caption to all, then edit the minority that differ
4. **AI audio captioning** — run a music description model on the audio first, review outputs

The real time cost is **audio curation** (finding/recording 100 coherent stems), not captioning.

---

## Recommended dataset layouts

### Style LoRA (full mixes)
```
my_style/
  track_01.wav          (3–5 min full mix)
  track_01.txt          "dark ambient electronic, slow evolving pads, granular texture, no percussion, deep low rumble"
  track_02.wav
  track_02.txt
  ...  (30–80 tracks)
```

### Instrument LoRA (stems)
```
my_bass/
  bass_01.wav           (8–60s stem recording)
  bass_01.txt           "reese bass stem, detuned sawtooth, heavy low-mid, growling texture, 140bpm, UK drill"
  bass_02.wav
  bass_02.txt
  ...  (80–200 stems)
```

### One-shot pack LoRA
```
my_kit/
  kick_01.wav           (0.05–0.5s)
  kick_01.txt           "808 kick drum, deep sub thump, punchy transient, tight decay, trap"
  kick_02.wav
  kick_02.txt
  ...  (200+ one-shots)
```
Use `--exclude seconds_total` and reduce steps proportionally.
