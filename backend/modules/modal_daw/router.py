import os
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(tags=["modal-daw"])


class ModalDawFlags(BaseModel):
    starts_gpu: bool = False
    starts_paid_api: bool = False
    publishes_stream: bool = False
    records_audio: bool = False
    uploads_private_media: bool = False
    requires_human_approval: bool = True


class ModalDawStatus(BaseModel):
    status: Literal["closed_until_human_yes", "operator_armed"]
    adapter: Literal["modal_gpu_worker_contract"] = "modal_gpu_worker_contract"
    modal_app: str = "stabledaw-modal-worker"
    endpoint_env: str = "STABLEDAW_MODAL_ENDPOINT_URL"
    enable_env: str = "STABLEDAW_MODAL_ENABLE"
    token_env: str = "MODAL_TOKEN_ID / MODAL_TOKEN_SECRET or modal profile"
    first_safe_action: str = "Run local health/preflight, then deploy the Modal worker only after explicit approval."
    realtime_strategy: list[str] = Field(default_factory=list)
    lanes: list[dict] = Field(default_factory=list)
    flags: ModalDawFlags = Field(default_factory=ModalDawFlags)


def _enabled() -> bool:
    return os.getenv("STABLEDAW_MODAL_ENABLE", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def build_status() -> ModalDawStatus:
    operator_armed = _enabled()
    flags = ModalDawFlags(
        starts_gpu=False,
        starts_paid_api=False,
        publishes_stream=False,
        records_audio=False,
        uploads_private_media=False,
        requires_human_approval=not operator_armed,
    )
    return ModalDawStatus(
        status="operator_armed" if operator_armed else "closed_until_human_yes",
        realtime_strategy=[
            "Keep the browser DAW timeline, sequencer, piano roll, waveform editing, analyzer, and audition playback local for sub-50ms feel.",
            "Send only bounded render jobs to Modal: text-to-audio, audio-to-audio, inpainting, continuation, stem/effect batch jobs, and LoRA training.",
            "Return finished audio artifacts to the IndexedDB/library workflow; do not stream raw private microphone audio to Modal by default.",
            "Use local preview loops and clip transforms during performance while Modal renders the next phrase/section asynchronously.",
        ],
        lanes=[
            {
                "lane": "generate",
                "purpose": "Stable Audio 3 text-to-audio clip renders for Deck/Library import.",
                "first_safe_action": "Deploy modal/stabledaw_modal_worker.py and call /generate with a 2-5s smoke prompt.",
                "hardware": "A10G/L4-class GPU for small tests; larger GPU for medium/long renders.",
            },
            {
                "lane": "inpaint_continue",
                "purpose": "Regenerate a selected waveform region or continue from a bounced clip.",
                "first_safe_action": "Upload a short local bounce, run a capped duration job, return WAV plus metadata.",
                "hardware": "GPU; queue this behind local editor selection approval.",
            },
            {
                "lane": "lora_training",
                "purpose": "Train style packs from approved/private datasets.",
                "first_safe_action": "Dataset receipt + dry-run config validation before paid GPU training.",
                "hardware": "Longer GPU job; never automatic from the DAW UI.",
            },
        ],
        flags=flags,
    )


@router.get("/status")
async def modal_daw_status() -> ModalDawStatus:
    return build_status()


@router.get("/preflight")
async def modal_daw_preflight() -> dict:
    status = build_status()
    endpoint = os.getenv("STABLEDAW_MODAL_ENDPOINT_URL", "")
    return {
        "ok": True,
        "mode": status.status,
        "has_endpoint_url": bool(endpoint),
        "endpoint_env": "STABLEDAW_MODAL_ENDPOINT_URL",
        "safe": "No Modal network call or GPU start was made by this preflight.",
        "next_manual_commands": [
            "modal deploy modal/stabledaw_modal_worker.py",
            "export STABLEDAW_MODAL_ENABLE=true",
            "export STABLEDAW_MODAL_ENDPOINT_URL=<deployed endpoint URL>",
        ],
        "flags": status.flags.model_dump(),
    }


@router.post("/plan-render")
async def modal_daw_plan_render() -> dict:
    status = build_status()
    return {
        "ok": True,
        "plan_only": True,
        "status": "modal_render_plan_only_no_gpu_started",
        "recommended_flow": [
            "Bounce selected clip/region locally from StableDAW.",
            "Create a Modal job payload with prompt, duration cap, seed, model, and optional init/inpaint audio.",
            "Poll Modal job status while the browser DAW remains playable.",
            "Import completed WAV/FLAC into the local Library and timeline.",
        ],
        "flags": status.flags.model_dump(),
    }
