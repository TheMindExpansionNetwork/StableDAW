"""Modal worker contract for StableDAW GPU power.

This file is intentionally separate from the local FastAPI app. Deploy it only after
explicit approval because Modal GPU calls can spend credits and may download model
weights. The local backend exposes fail-closed planning/status endpoints under
/api/modal-daw without importing this module or starting Modal.

Deploy, after review:
    modal deploy modal/stabledaw_modal_worker.py

Minimal smoke, after deploy:
    modal run modal/stabledaw_modal_worker.py::smoke --prompt "short analog synth stab" --duration 2
"""

from __future__ import annotations

import io
from dataclasses import asdict, dataclass

import modal

APP_NAME = "stabledaw-modal-worker"

image = (
    modal.Image.debian_slim(python_version="3.10")
    .apt_install("ffmpeg", "libsndfile1")
    .pip_install(
        "torch==2.7.1",
        "torchaudio==2.7.1",
        "fastapi>=0.115.0",
        "huggingface-hub>=1.7.1",
        "safetensors>=0.7.0",
        "transformers>=5.8.0",
        "einops>=0.8.2",
        "einops-exts>=0.0.4",
        "numpy>=2.2.6",
        "soundfile>=0.12.0",
        "tqdm>=4.67.3",
    )
    .add_local_dir(".", remote_path="/root/stabledaw")
    .env({"PYTHONPATH": "/root/stabledaw"})
    .workdir("/root/stabledaw")
)

app = modal.App(APP_NAME, image=image)
cache = modal.Volume.from_name("stabledaw-model-cache", create_if_missing=True)


@dataclass
class GenerateRequest:
    prompt: str
    duration: float = 5.0
    model_name: str = "small"
    steps: int = 8
    seed: int = -1
    cfg_scale: float = 1.0
    file_format: str = "wav"


def _clamp_request(req: GenerateRequest) -> GenerateRequest:
    req.duration = max(1.0, min(float(req.duration), 30.0))
    req.steps = max(1, min(int(req.steps), 50))
    if req.file_format not in {"wav", "flac", "ogg"}:
        req.file_format = "wav"
    if req.model_name not in {"small", "medium", "small-rf", "medium-rf"}:
        req.model_name = "small"
    return req


@app.cls(
    gpu="A10G",
    timeout=900,
    scaledown_window=60,
    volumes={"/root/.cache": cache},
    secrets=[],
)
class StableDawWorker:
    @modal.enter()
    def load(self):
        from stable_audio_3.model import StableAudioModel

        self._pipelines = {}
        self._model_cls = StableAudioModel

    def _get_pipeline(self, model_name: str):
        if model_name not in self._pipelines:
            self._pipelines[model_name] = self._model_cls.from_pretrained(model_name)
        return self._pipelines[model_name]

    @modal.method()
    def generate_bytes(self, payload: dict) -> dict:
        import base64
        import torch
        import torchaudio

        req = _clamp_request(GenerateRequest(**payload))
        pipe = self._get_pipeline(req.model_name)
        audio = pipe.generate(
            prompt=req.prompt,
            duration=req.duration,
            steps=req.steps,
            seed=req.seed,
            cfg_scale=req.cfg_scale,
        )
        audio = audio.to(torch.float32).clamp(-1, 1).squeeze(0).cpu()
        sample_rate = int(pipe.model_config.get("sample_rate", 44100))
        buf = io.BytesIO()
        torchaudio.save(buf, audio, sample_rate, format=req.file_format)
        raw = buf.getvalue()
        return {
            "ok": True,
            "request": asdict(req),
            "sample_rate": sample_rate,
            "mime_type": f"audio/{req.file_format}",
            "audio_base64": base64.b64encode(raw).decode("ascii"),
            "bytes": len(raw),
        }


@app.function(timeout=900, gpu="A10G", volumes={"/root/.cache": cache})
def smoke(prompt: str = "short analog synth stab", duration: float = 2.0):
    """Bounded manual smoke entrypoint; not called by local StableDAW automatically."""
    worker = StableDawWorker()
    result = worker.generate_bytes.remote(
        {
            "prompt": prompt,
            "duration": duration,
            "model_name": "small",
            "steps": 4,
            "seed": 1234,
            "file_format": "wav",
        }
    )
    print({k: v for k, v in result.items() if k != "audio_base64"})
