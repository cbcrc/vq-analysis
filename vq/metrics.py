from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from vq.ffmpeg import FFmpegRunner

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class MetricsOptions:
    ffmpeg_bin: str = "ffmpeg"
    n_threads: int = max(1, os.cpu_count() // 2)
    log_fmt: str = "json"
    overwrite: bool = False
    feature_psnr: bool = True
    feature_float_ms_ssim: bool = True
    feature_ciede: bool = False
    model: str | None = None


def infer_reference_path(
    dist_path: Path,
    input_root: Path,
    reference_root: Path,
    reference_extensions: Iterable[str],
) -> Path:
    rel_path = dist_path.relative_to(input_root)
    clip_name = rel_path.parts[0]

    for ext in reference_extensions:
        candidate = reference_root / f"{clip_name}{ext}"
        if candidate.exists():
            return candidate

    return reference_root / f"{clip_name}{reference_extensions[0]}"


def build_libvmaf_feature_string(options: MetricsOptions) -> str:
    features: list[str] = []

    if options.feature_psnr:
        features.append("name=psnr")
    if options.feature_float_ms_ssim:
        features.append("name=float_ms_ssim")
    if options.feature_ciede:
        features.append("name=ciede")

    return "|".join(features)


def make_metrics_output_path(
    dist_path: Path,
    output_root: Path,
    dist_root: Path | None = None,
) -> Path:
    if dist_root is not None:
        rel_parent = dist_path.parent.relative_to(dist_root)
        out_dir = output_root / rel_parent
    else:
        out_dir = output_root

    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / f"{dist_path.stem}.json"


def build_libvmaf_args(
    dist_path: Path,
    ref_path: Path,
    log_path: Path,
    options: MetricsOptions,
) -> list[str]:
    libvmaf_parts = [
        f"n_threads={options.n_threads}",
        f"log_path={log_path}",
        f"log_fmt={options.log_fmt}",
    ]

    if options.model:
        libvmaf_parts.append(f"model=version={options.model}")

    feature_string = build_libvmaf_feature_string(options)
    if feature_string:
        libvmaf_parts.append(f"feature={feature_string}")

    libvmaf_filter = "libvmaf=" + ":".join(libvmaf_parts)

    args = [
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(dist_path),
        "-i",
        str(ref_path),
        "-lavfi",
        libvmaf_filter,
        "-f",
        "null",
        "-",
    ]

    return args


def run_metrics(
    dist_path: Path,
    ref_path: Path,
    log_path: Path,
    options: MetricsOptions | None = None,
    dry_run: bool = False,
) -> dict:
    opts = options or MetricsOptions()

    if log_path.exists() and not opts.overwrite:
        logger.warning("Skipping existing metrics log: %s", log_path.name)
        return {
            "dist": str(dist_path),
            "ref": str(ref_path),
            "log_path": str(log_path),
            "status": "skipped",
            "elapsed_s": None,
            "stderr": "",
            "cmd": None,
            "dry_run": False,
        }

    logger.debug(
        "Computing metrics for %s (reference: %s)",
        dist_path.name,
        ref_path.name,
    )

    args = build_libvmaf_args(
        dist_path=dist_path,
        ref_path=ref_path,
        log_path=log_path,
        options=opts,
    )

    runner = FFmpegRunner(
        executable=opts.ffmpeg_bin,
        dry_run=dry_run,
    )
    result = runner.run(args)

    return {
        "dist": str(dist_path),
        "ref": str(ref_path),
        "log_path": str(log_path),
        "status": "done" if result.ok else "error",
        "elapsed_s": result.elapsed_s,
        "stderr": result.stderr.strip(),
        "cmd": result.cmd,
        "dry_run": result.dry_run,
    }


def load_metrics_json(log_path: Path) -> dict:
    with log_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def extract_pooled_metrics(log_data: dict) -> dict:
    pooled = log_data.get("pooled_metrics", {})

    summary: dict = {}

    if "vmaf" in pooled:
        summary["vmaf"] = pooled["vmaf"].get("mean")

    if "psnr" in pooled:
        summary["psnr_y"] = pooled["psnr"].get("mean")

    if "float_ms_ssim" in pooled:
        summary["float_ms_ssim"] = pooled["float_ms_ssim"].get("mean")

    if "ciede" in pooled:
        summary["ciede"] = pooled["ciede"].get("mean")

    return summary
