"""
Structured event emitter for helper stdout protocol.
Output is newline-delimited JSON (NDJSON).
"""
import json
import sys
from typing import Optional


def emit_event(event_type: str, job: Optional[str] = None, **kwargs) -> None:
    payload = {"event": event_type}
    if job:
        payload["job"] = job
    payload.update(kwargs)
    print(json.dumps(payload), flush=True)


def emit_started(job: str, engine: str) -> None:
    emit_event("started", job=job, engine=engine)


def emit_progress(job: str, percent: int, stage: str) -> None:
    emit_event("progress", job=job, percent=max(0, min(100, int(percent))), stage=stage)


def emit_done(job: str, output: str) -> None:
    emit_event("done", job=job, output=output)


def emit_error(job: str, code: str, message: str) -> None:
    emit_event("error", job=job, code=code, message=message)
