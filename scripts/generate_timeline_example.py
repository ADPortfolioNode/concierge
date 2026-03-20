#!/usr/bin/env python3
"""Generate a sample sacred timeline PNG using the renderer in the codebase.

This script avoids initializing heavy components by calling the
`SacredTimeline.get_plan_graph_png` method with a minimal dummy `self`
that implements `get_last_plan()`.
"""
from __future__ import annotations

from pathlib import Path
import sys

# Ensure repository root is on sys.path so local packages can be imported
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestration.sacred_timeline import SacredTimeline


SAMPLE_PLAN = {
    "tasks": [
        {"task_id": "t1", "title": "Collect data", "instructions": "Fetch data from source A.", "depends_on": []},
        {"task_id": "t2", "title": "Clean data", "instructions": "Normalize fields and remove duplicates.", "depends_on": ["t1"]},
        {"task_id": "t3", "title": "Analyze", "instructions": "Compute summary statistics.", "depends_on": ["t1"]},
        {"task_id": "t4", "title": "Report", "instructions": "Create report and charts.", "depends_on": ["t2", "t3"]},
    ]
}


class _DummySelf:
    def get_last_plan(self):
        return SAMPLE_PLAN


def main() -> None:
    out = Path.cwd() / "timeline_example.png"
    png = SacredTimeline.get_plan_graph_png(_DummySelf())
    out.write_bytes(png)
    print(f"Wrote sample timeline to: {out}")


if __name__ == "__main__":
    main()
