"""Capture hardware/runtime metadata for benchmark reports."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Any


def capture_hardware() -> dict[str, Any]:
    meminfo = _read_meminfo()
    return {
        "hostname": platform.node(),
        "os": platform.platform(),
        "python": platform.python_version(),
        "cpu": _cpu_model(),
        "cpu_count": os.cpu_count(),
        "ram_kb_total": meminfo.get("MemTotal"),
        "ram_kb_available": meminfo.get("MemAvailable"),
        "gpu": _nvidia_smi(),
        "threads": os.environ.get("OMP_NUM_THREADS") or os.environ.get("OLLAMA_NUM_THREAD"),
    }


def _cpu_model() -> str | None:
    path = Path("/proc/cpuinfo")
    if not path.exists():
        return platform.processor() or None
    for line in path.read_text(errors="replace").splitlines():
        if line.lower().startswith("model name"):
            return line.split(":", 1)[1].strip()
    return None


def _read_meminfo() -> dict[str, int]:
    path = Path("/proc/meminfo")
    result: dict[str, int] = {}
    if not path.exists():
        return result
    for line in path.read_text().splitlines():
        parts = line.replace(":", " ").split()
        if len(parts) >= 2 and parts[1].isdigit():
            result[parts[0]] = int(parts[1])
    return result


def _nvidia_smi() -> dict[str, Any] | None:
    binary = shutil.which("nvidia-smi")
    if not binary:
        return None
    try:
        proc = subprocess.run(
            [binary, "--query-gpu=name,memory.total,memory.used,driver_version", "--format=csv,noheader"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    gpus = []
    for line in proc.stdout.strip().splitlines():
        fields = [x.strip() for x in line.split(",")]
        gpus.append(
            {
                "name": fields[0] if fields else None,
                "vram": fields[1] if len(fields) > 1 else None,
                "vram_used": fields[2] if len(fields) > 2 else None,
                "driver": fields[3] if len(fields) > 3 else None,
            }
        )
    return {"gpus": gpus}
