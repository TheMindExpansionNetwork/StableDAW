from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(tags=["live-loop"])


class LiveLoopFlags(BaseModel):
    starts_gpu: bool = False
    starts_paid_api: bool = False
    publishes_stream: bool = False
    records_audio: bool = False
    uploads_private_media: bool = False
    opens_microphone: bool = False
    requires_human_approval: bool = True


class Bus(BaseModel):
    name: str
    role: str
    default_state: Literal["local_only", "dry_run", "disabled"]


class LiveLoopStatus(BaseModel):
    status: Literal["offline_smoke_verified", "live_room_not_started"] = "offline_smoke_verified"
    framework: str = "Elementary Audio (@elemaudio/core + @elemaudio/web-renderer)"
    model_lane: str = "ACE-Step v1.5 / ACE-Step worker lane for async next-phrase generation"
    realtime_contract: str = "browser_local_audioworklet_loopbank_first_modal_generation_second"
    buses: list[Bus] = Field(default_factory=list)
    response_order: list[str] = Field(default_factory=list)
    flags: LiveLoopFlags = Field(default_factory=LiveLoopFlags)


def build_status() -> LiveLoopStatus:
    return LiveLoopStatus(
        buses=[
            Bus(
                name="room_input_bus",
                role="human mic/instrument/DAW output captured only after explicit browser Start",
                default_state="disabled",
            ),
            Bus(
                name="elementary_dsp_loop_bus",
                role="browser-local Elementary Audio graph for loop-bank playback, delay, filter, gain, ducking, and kill switch",
                default_state="dry_run",
            ),
            Bus(
                name="ai_return_bus",
                role="selected loop-bank or async generated phrase returned to the DAW timeline/monitor mix",
                default_state="dry_run",
            ),
            Bus(
                name="stream_monitor_bus",
                role="local monitor mix with limiter and operator kill switch; no public stream by default",
                default_state="local_only",
            ),
        ],
        response_order=[
            "1. Loop-bank response selected from short-window RMS/centroid/onset cues for playable latency.",
            "2. Elementary Audio DSP transforms the selected loop locally: gain, filter, delay, pitch-ish resampling, ducking.",
            "3. Modal/ACE-Step renders the next 8-30s phrase asynchronously for the next section, not instant notes.",
            "4. Generated audio returns to StableDAW Library/timeline and can refill the loop bank after approval.",
        ],
        flags=LiveLoopFlags(),
    )


@router.get("/status")
async def live_loop_status() -> LiveLoopStatus:
    return build_status()


@router.get("/bus-plan")
async def live_loop_bus_plan() -> dict:
    status = build_status()
    return {
        "ok": True,
        "plan_only": True,
        "status": "live_loop_bus_plan_no_mic_no_gpu_no_stream",
        "framework": status.framework,
        "model_lane": status.model_lane,
        "buses": [bus.model_dump() for bus in status.buses],
        "window_features": [
            "rms_energy",
            "spectral_centroid_brightness",
            "zero_crossing_density",
            "onset_or_transient_density",
            "space_or_silence_gate",
        ],
        "control_targets": [
            "loop_choice",
            "return_gain",
            "ducking_db",
            "delay_feedback",
            "filter_cutoff",
            "modal_next_phrase_prompt",
        ],
        "safe": "No browser microphone, Modal endpoint, GPU, recording, upload, or stream is started by this endpoint.",
        "flags": status.flags.model_dump(),
    }
