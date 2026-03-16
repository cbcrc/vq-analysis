from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from vq.ffmpeg import FFmpegRunner

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class UpscaleOptions:
    ffmpeg_bin: str = "ffmpeg"
    target_width: int = 1920
    target_height: int = 1080
    scaler: str = "lanczos"
    pix_fmt: str = "yuv420p"
    video_codec: str = "ffv1"
    ffv1_level: int = 3
    output_ext: str = ".mkv"
    overwrite: bool = False
    preserve_fps: bool = True
    fps: str | None = None


def build_filter_string(options: UpscaleOptions) -> str:
    filters = [
        f"scale={options.target_width}:{options.target_height}:flags={options.scaler}"
    ]

    if not options.preserve_fps and options.fps:
        filters.append(f"fps={options.fps}")

    filters.append(f"format={options.pix_fmt}")
    return ",".join(filters)


def make_output_path(
    input_path: Path,
    output_root: Path,
    input_root: Path | None,
    options: UpscaleOptions,
) -> Path:
    if input_root is not None:
        rel_parent = input_path.parent.relative_to(input_root)
        out_dir = output_root / rel_parent
    else:
        out_dir = output_root

    out_dir.mkdir(parents=True, exist_ok=True)

    suffix = f"_up{options.target_height}p_{options.video_codec}"
    return out_dir / f"{input_path.stem}{suffix}{options.output_ext}"


def build_ffmpeg_args(
    input_path: Path,
    output_path: Path,
    options: UpscaleOptions,
) -> list[str]:
    args = [
        "-hide_banner",
        "-loglevel",
        "error",
        "-y" if options.overwrite else "-n",
        "-i",
        str(input_path),
        "-vf",
        build_filter_string(options),
        "-c:v",
        options.video_codec,
        "-an",
    ]

    if options.video_codec == "ffv1":
        args += ["-level", str(options.ffv1_level)]

    args.append(str(output_path))
    return args


def upscale_file(
    input_path: Path,
    output_path: Path,
    options: UpscaleOptions,
    dry_run: bool = False,
) -> dict:
    if output_path.exists() and not options.overwrite:
        logger.debug(f"Output exists and overwrite is disabled: {output_path}")
        return {
            "input": str(input_path),
            "output": str(output_path),
            "status": "skipped",
            "elapsed_s": None,
            "stderr": "",
            "cmd": None,
        }

    runner = FFmpegRunner(executable=options.ffmpeg_bin, dry_run=dry_run)

    args = build_ffmpeg_args(input_path, output_path, options)
    result = runner.run(args)

    return {
        "input": str(input_path),
        "output": str(output_path),
        "status": "done" if result.returncode == 0 else "error",
        "elapsed_s": result.elapsed_s,
        "stderr": result.stderr.strip(),
        "cmd": result.cmd,
        "dry_run": result.dry_run,
    }


def upscale_batch(
    input_files: list[Path],
    output_root: Path,
    input_root: Path | None = None,
    options: UpscaleOptions | None = None,
    dry_run: bool = False,
) -> list[dict]:
    options = options or UpscaleOptions()
    output_root.mkdir(parents=True, exist_ok=True)

    results: list[dict] = []

    logger.info(f"Found {len(input_files)} input file(s) to upscale.")
    logger.debug(f"Upscale output root: {output_root}")
    if input_root is not None:
        logger.debug(f"Upscale input root: {input_root}")
    logger.debug("Upscale options: %s", options)

    for input_path in input_files:
        output_path = make_output_path(
            input_path=input_path,
            output_root=output_root,
            input_root=input_root,
            options=options,
        )

        logger.debug(f"Upscaling {input_path.name} -> {output_path.name}")
        result = upscale_file(
            input_path=input_path,
            output_path=output_path,
            options=options,
            dry_run=dry_run,
        )
        results.append(result)

        status = result["status"]
        if status == "done":
            logger.info(
                f"Completed upscale: {input_path.name} -> {output_path.name}",
            )
        elif status == "skipped":
            logger.warning(f"Skipping existing output: {output_path}")
        elif status == "dry-run":
            logger.info(f"DRY RUN: {input_path.name} -> {output_path.name}")
        else:
            logger.error(f"Upscale failed for {input_path}")
            if result["stderr"]:
                logger.error(
                    f"FFmpeg stderr for {input_path.name}:\n{result['stderr']}"
                )

    return results
