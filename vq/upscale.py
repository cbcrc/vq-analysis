from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path


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


def build_ffmpeg_command(
    input_path: Path,
    output_path: Path,
    options: UpscaleOptions,
) -> list[str]:
    cmd = [
        options.ffmpeg_bin,
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
        cmd += ["-level", str(options.ffv1_level)]

    cmd.append(str(output_path))
    return cmd


def upscale_file(
    input_path: Path,
    output_path: Path,
    options: UpscaleOptions,
    dry_run: bool = False,
) -> dict:
    if output_path.exists() and not options.overwrite:
        return {
            "input": str(input_path),
            "output": str(output_path),
            "status": "skipped",
            "elapsed_s": None,
            "stderr": "",
        }

    cmd = build_ffmpeg_command(input_path, output_path, options)

    if dry_run:
        return {
            "input": str(input_path),
            "output": str(output_path),
            "status": "dry-run",
            "elapsed_s": None,
            "stderr": "",
            "cmd": cmd,
        }

    t0 = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - t0

    return {
        "input": str(input_path),
        "output": str(output_path),
        "status": "done" if result.returncode == 0 else "error",
        "elapsed_s": elapsed,
        "stderr": result.stderr.strip(),
        "cmd": cmd,
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

    print(f"Found {len(input_files)} input file(s).")

    for input_path in input_files:
        output_path = make_output_path(
            input_path=input_path,
            output_root=output_root,
            input_root=input_root,
            options=options,
        )

        result = upscale_file(
            input_path=input_path,
            output_path=output_path,
            options=options,
            dry_run=dry_run,
        )
        results.append(result)

        status = result["status"]
        if status == "done":
            print(
                f"[OK] {input_path.name} -> {output_path.name} "
                f"({result['elapsed_s']:.1f}s)"
            )
        elif status == "skipped":
            print(f"[SKIP] {output_path.name}")
        elif status == "dry-run":
            print(f"[DRY-RUN] {output_path.name}")
        else:
            print(f"[ERROR] {input_path.name}")
            if result["stderr"]:
                print(result["stderr"])

    return results
