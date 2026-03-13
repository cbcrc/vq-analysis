import argparse
import sys
from glob import glob
from pathlib import Path

from vq.upscale import UpscaleOptions, upscale_batch


def _expand_inputs(patterns: str | list[str], input_root: Path | None) -> list[Path]:
    if isinstance(patterns, str):
        patterns = [patterns]

    files: list[Path] = []

    for pattern in patterns:
        full_pattern = str((input_root / pattern) if input_root else Path(pattern))
        matches = sorted(Path(p) for p in glob(full_pattern, recursive=True))
        files.extend(p for p in matches if p.is_file())

    unique_files: list[Path] = []
    seen: set[Path] = set()

    for path in files:
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique_files.append(path)

    return unique_files


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vq",
        description="Video Quality Analysis tools",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    upscale_parser = subparsers.add_parser(
        "upscale",
        help="Upscale encoded ladder outputs to a common resolution.",
    )

    upscale_parser.add_argument(
        "-I",
        "--input-root",
        default=None,
        help="Root directory for input files. "
        "Input glob patterns are resolved relative to this path.",
    )
    upscale_parser.add_argument(
        "-i",
        "--input",
        action="append",
        required=True,
        help='Input glob pattern relative to --input-root, e.g. "**/*.mp4". "'
        "Can be passed multiple times.",
    )
    upscale_parser.add_argument(
        "-o",
        "--output",
        required=True,
        help="Output directory for upscaled files.",
    )
    upscale_parser.add_argument(
        "--width",
        type=int,
        default=1920,
        help="Target output width (default: 1920).",
    )
    upscale_parser.add_argument(
        "--height",
        type=int,
        default=1080,
        help="Target output height (default: 1080).",
    )
    upscale_parser.add_argument(
        "--scaler",
        default="lanczos",
        help="FFmpeg scale flags value (default: lanczos).",
    )
    upscale_parser.add_argument(
        "--pix-fmt",
        default="yuv420p",
        help="Output pixel format (default: yuv420p).",
    )
    upscale_parser.add_argument(
        "--video-codec",
        default="ffv1",
        help="Intermediate video codec (default: ffv1).",
    )
    upscale_parser.add_argument(
        "--ffmpeg",
        default="ffmpeg",
        help='FFmpeg executable to use (default: "ffmpeg").',
    )
    upscale_parser.add_argument(
        "--fps",
        default=None,
        help="Optional FPS override (example: 30000/1001). "
        "Default: preserve source FPS.",
    )
    upscale_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing output files.",
    )
    upscale_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned work without running FFmpeg.",
    )

    return parser


def _run_upscale(args: argparse.Namespace) -> int:
    input_root = Path(args.input_root).resolve() if args.input_root else None
    output_root = Path(args.output).resolve()

    input_files = _expand_inputs(args.input, input_root)

    if not input_files:
        print("No input files matched the provided pattern(s).", file=sys.stderr)
        return 1

    print(f"Matched {len(input_files)} input file(s).")

    options = UpscaleOptions(
        ffmpeg_bin=args.ffmpeg,
        target_width=args.width,
        target_height=args.height,
        scaler=args.scaler,
        pix_fmt=args.pix_fmt,
        video_codec=args.video_codec,
        overwrite=args.overwrite,
        preserve_fps=args.fps is None,
        fps=args.fps,
    )

    results = upscale_batch(
        input_files=input_files,
        output_root=output_root,
        input_root=input_root,
        options=options,
        dry_run=args.dry_run,
    )

    num_done = sum(r["status"] == "done" for r in results)
    num_skipped = sum(r["status"] == "skipped" for r in results)
    num_errors = sum(r["status"] == "error" for r in results)
    num_dry = sum(r["status"] == "dry-run" for r in results)

    print(
        f"Summary: done={num_done}, skipped={num_skipped}, "
        f"dry-run={num_dry}, errors={num_errors}"
    )

    return 1 if num_errors else 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "upscale":
        return _run_upscale(args)

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
