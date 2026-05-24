#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "README.md",
    "LICENSE",
    "backend/server.py",
    "backend/modules/modal_daw/module.json",
    "backend/modules/modal_daw/router.py",
    "docs/integrations/MODAL_REALTIME_DAW.md",
    "docs/integrations/LIVE_LOOP_ELEMENTARY_ACE_STEP.md",
    "modal/stabledaw_modal_worker.py",
    "backend/modules/live_loop/module.json",
    "backend/modules/live_loop/router.py",
    "catalog/backend-cards/elementary-audio-live-loop.md",
    "catalog/backend-cards/ace-step-next-phrase.md",
    "scripts/build_live_loop_smoke.py",
    "frontend/package.json",
]

REQUIRED_NEEDLES = {
    "backend/modules/modal_daw/router.py": [
        "closed_until_human_yes",
        "starts_gpu: bool = False",
        "uploads_private_media: bool = False",
        "No Modal network call or GPU start was made",
        "modal_render_plan_only_no_gpu_started",
    ],
    "docs/integrations/MODAL_REALTIME_DAW.md": [
        "StableDAW is already a strong browser DAW",
        "Keep the playable DAW local",
        "Modal power layer",
        "STABLEDAW_MODAL_ENABLE=false",
        "starts_gpu: false",
    ],
    "modal/stabledaw_modal_worker.py": [
        "stabledaw-modal-worker",
        "scaledown_window=60",
        "duration), 30.0",
        "modal deploy modal/stabledaw_modal_worker.py",
    ],
    "backend/modules/live_loop/router.py": [
        "Elementary Audio",
        "ACE-Step v1.5",
        "live_loop_bus_plan_no_mic_no_gpu_no_stream",
        "opens_microphone: bool = False",
        "No browser microphone, Modal endpoint, GPU, recording, upload, or stream is started",
    ],
    "docs/integrations/LIVE_LOOP_ELEMENTARY_ACE_STEP.md": [
        "Elementary Audio",
        "ACE-Step",
        "loop-bank response",
        "offline smoke verified",
        "No real WebRTC room yet",
    ],
}


def main() -> None:
    missing = [path for path in REQUIRED_FILES if not (ROOT / path).exists()]
    if missing:
        raise SystemExit(f"Missing required files: {missing}")

    module = json.loads((ROOT / "backend/modules/modal_daw/module.json").read_text())
    assert module["enabled"] is True
    assert module["api_prefix"] == "/api/modal-daw"
    live_module = json.loads((ROOT / "backend/modules/live_loop/module.json").read_text())
    assert live_module["enabled"] is True
    assert live_module["api_prefix"] == "/api/live-loop"

    for rel, needles in REQUIRED_NEEDLES.items():
        text = (ROOT / rel).read_text(errors="replace")
        absent = [needle for needle in needles if needle not in text]
        if absent:
            raise SystemExit(f"Missing needles in {rel}: {absent}")

    gitignore = (ROOT / ".gitignore").read_text(errors="replace")
    if ".env" not in gitignore:
        raise SystemExit(".env is not ignored")

    receipt_path = ROOT / "docs/assets/audio/live-loop-elementary-ace-test/LIVE_LOOP_ELEMENTARY_ACE_TEST_RECEIPT.json"
    if not receipt_path.exists():
        raise SystemExit("missing live-loop smoke receipt; run scripts/build_live_loop_smoke.py")
    receipt = json.loads(receipt_path.read_text())
    if receipt.get("status") != "offline_live_loop_smoke_verified":
        raise SystemExit("live-loop smoke receipt status is not verified")
    if receipt.get("framework_added") != "Elementary Audio" or "ACE-Step" not in receipt.get("model_lane_added", ""):
        raise SystemExit("live-loop receipt does not name Elementary Audio + ACE-Step")
    for artifact in receipt.get("artifacts", []):
        if artifact.get("rms", 0) <= 0 or artifact.get("peak", 0) <= 0:
            raise SystemExit(f"silent live-loop artifact: {artifact.get('file')}")
        mp3 = ROOT / artifact.get("mp3_file", "")
        if not mp3.exists() or mp3.stat().st_size < 100_000:
            raise SystemExit(f"missing/small mp3 live-loop artifact: {mp3}")
    if not all(value is False for value in receipt.get("fail_closed_flags", {}).values()):
        raise SystemExit("live-loop receipt fail-closed flags must all be false")

    print("verify ok")


if __name__ == "__main__":
    main()
