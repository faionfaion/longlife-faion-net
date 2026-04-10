"""Run report: tracks pipeline execution and saves to state/runs/."""

from __future__ import annotations

import json
import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from pipeline.config import STATE_DIR

logger = logging.getLogger(__name__)


@dataclass
class StageEntry:
    name: str
    status: str = "running"
    duration_s: float = 0.0
    error: str | None = None


@dataclass
class RunReport:
    dry_run: bool = False
    resume_from_stage: int = 1
    stages: list[StageEntry] = field(default_factory=list)
    slug: str = ""
    author: str = ""
    image_generated: bool = False
    msg_id: int | None = None
    failed_stage: str | None = None
    error: str | None = None
    status: str = "running"
    start_time: float = 0.0
    end_time: float = 0.0

    def begin(self):
        self.start_time = time.time()

    def add_stage(self, name: str) -> StageEntry:
        entry = StageEntry(name=name)
        self.stages.append(entry)
        return entry

    def finish(self, status: str):
        self.status = status
        self.end_time = time.time()

    def save(self) -> Path:
        runs_dir = STATE_DIR / "runs"
        runs_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
        path = runs_dir / f"{ts}.json"
        data = {
            "timestamp": ts,
            "status": self.status,
            "dry_run": self.dry_run,
            "slug": self.slug,
            "author": self.author,
            "duration_s": round(self.end_time - self.start_time, 1),
            "image_generated": self.image_generated,
            "msg_id": self.msg_id,
            "failed_stage": self.failed_stage,
            "error": self.error,
            "stages": [
                {
                    "name": s.name,
                    "status": s.status,
                    "duration_s": round(s.duration_s, 1),
                    "error": s.error,
                }
                for s in self.stages
            ],
        }
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return path


@contextmanager
def time_stage(report: RunReport, name: str):
    entry = report.add_stage(name)
    t0 = time.time()
    try:
        yield entry
        entry.status = "ok"
    except Exception as e:
        entry.status = "failed"
        entry.error = str(e)[:200]
        raise
    finally:
        entry.duration_s = time.time() - t0
