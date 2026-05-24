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
    "modal/stabledaw_modal_worker.py",
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
}


def main() -> None:
    missing = [path for path in REQUIRED_FILES if not (ROOT / path).exists()]
    if missing:
        raise SystemExit(f"Missing required files: {missing}")

    module = json.loads((ROOT / "backend/modules/modal_daw/module.json").read_text())
    assert module["enabled"] is True
    assert module["api_prefix"] == "/api/modal-daw"

    for rel, needles in REQUIRED_NEEDLES.items():
        text = (ROOT / rel).read_text(errors="replace")
        absent = [needle for needle in needles if needle not in text]
        if absent:
            raise SystemExit(f"Missing needles in {rel}: {absent}")

    gitignore = (ROOT / ".gitignore").read_text(errors="replace")
    if ".env" not in gitignore:
        raise SystemExit(".env is not ignored")

    print("verify ok")


if __name__ == "__main__":
    main()
