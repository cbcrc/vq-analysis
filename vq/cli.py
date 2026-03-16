import argparse
import logging
import os
import sys
from glob import glob
from pathlib import Path

from vq.metrics import (
    MetricsOptions,
    infer_reference_path,
    make_metrics_output_path,
    run_metrics,
)
from vq.upscale import UpscaleOptions, upscale_batch

logger = logging.getLogger(__name__)

DEFAULT_REFERENCE_EXTENSIONS = (
    ".mkv",
    ".y4m",
    ".mp4",
    ".mov",
)


def _configure_logging(debug: bool = False, quiet: bool = False) -> None:
    if debug and quiet:
        raise ValueError("Cannot enable both debug and quiet logging.")

    if debug:
        level = logging.DEBUG
    elif quiet:
        level = logging.WARNING
    else:
        level = logging.INFO

    logging.basicConfig(
        level=level,
        format="%(levelname)s %(name)s: %(message)s",
    )


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

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging.",
    )

    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only show warnings and errors.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    metrics_parser = subparsers.add_parser(
        "metrics",
        help="Compute quality metrics using FFmpeg/libvmaf.",
    )
    metrics_parser.add_argument(
        "-I",
        "--input-root",
        required=True,
        help="Root directory for distorted / encoded input files.",
    )
    metrics_parser.add_argument(
        "-R",
        "--reference-root",
        required=True,
        help="Root directory for reference files.",
    )
    metrics_parser.add_argument(
        "--ref-ext",
        action="append",
        help="Reference file extension(s) to try when resolving reference files "
        "(e.g. --ref-ext .mxf --ref-ext .mkv).",
    )
    metrics_parser.add_argument(
        "-i",
        "--input",
        action="append",
        required=True,
        help=(
            "Input glob pattern relative to --input-root, "
            'e.g. "**/*.mkv". Can be passed multiple times.'
        ),
    )
    metrics_parser.add_argument(
        "-o",
        "--output",
        required=True,
        help="Output directory for libvmaf JSON logs.",
    )
    metrics_parser.add_argument("--ffmpeg", default="ffmpeg")
    metrics_parser.add_argument(
        "--threads", type=int, default=max(1, os.cpu_count() // 2)
    )
    metrics_parser.add_argument("--overwrite", action="store_true")
    metrics_parser.add_argument("--dry-run", action="store_true")
    metrics_parser.add_argument(
        "--no-psnr",
        action="store_true",
        help="Disable PSNR feature extraction.",
    )
    metrics_parser.add_argument(
        "--no-float-ms-ssim",
        action="store_true",
        help="Disable float_ms_ssim feature extraction.",
    )
    metrics_parser.add_argument(
        "--ciede",
        action="store_true",
        help="Enable CIEDE feature extraction.",
    )

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


def _run_metrics(args: argparse.Namespace) -> int:
    input_root = Path(args.input_root).resolve()
    reference_root = Path(args.reference_root).resolve()
    output_root = Path(args.output).resolve()
    ref_exts = args.ref_ext or DEFAULT_REFERENCE_EXTENSIONS

    logger.debug("Metrics input root: %s", input_root)
    logger.debug("Metrics reference root: %s", reference_root)
    logger.debug("Metrics output root: %s", output_root)

    dist_files = _expand_inputs(args.input, input_root)

    if not dist_files:
        logger.error("No input files matched the provided pattern(s).")
        return 1

    logger.info("Matched %d distorted input file(s).", len(dist_files))

    options = MetricsOptions(
        ffmpeg_bin=args.ffmpeg,
        n_threads=args.threads,
        overwrite=args.overwrite,
        feature_psnr=not args.no_psnr,
        feature_float_ms_ssim=not args.no_float_ms_ssim,
        feature_ciede=args.ciede,
    )

    logger.debug("Metrics options: %s", options)

    results = []

    for dist_path in dist_files:
        rel_path = dist_path.relative_to(input_root)
        ref_path = infer_reference_path(
            dist_path=dist_path,
            input_root=input_root,
            reference_root=reference_root,
            reference_extensions=ref_exts,
        )

        log_path = make_metrics_output_path(
            dist_path=dist_path,
            output_root=output_root,
            dist_root=input_root,
        )

        logger.debug("Metrics input: %s", dist_path)
        logger.debug("Reference path: %s", ref_path)
        logger.debug("Log output path: %s", log_path)

        if not ref_path.exists():
            results.append(
                {
                    "dist": str(dist_path),
                    "ref": str(ref_path),
                    "log_path": str(log_path),
                    "status": "missing-reference",
                    "elapsed_s": None,
                    "stderr": "",
                    "cmd": None,
                    "dry_run": False,
                }
            )
            logger.warning("Missing reference for %s", rel_path)
            continue

        result = run_metrics(
            dist_path=dist_path,
            ref_path=ref_path,
            log_path=log_path,
            options=options,
            dry_run=args.dry_run,
        )
        results.append(result)

        if result["dry_run"]:
            logger.info("DRY RUN: %s", rel_path)
        elif result["status"] == "done":
            logger.info("Computed metrics: %s", rel_path)
        elif result["status"] == "skipped":
            logger.warning("Skipping existing metrics log for %s", rel_path)
        else:
            logger.error("Metrics computation failed for %s", rel_path)
            if result["stderr"]:
                logger.debug("FFmpeg stderr for %s:\n%s", rel_path, result["stderr"])

    num_done = sum(r["status"] == "done" for r in results)
    num_skipped = sum(r["status"] == "skipped" for r in results)
    num_missing_ref = sum(r["status"] == "missing-reference" for r in results)
    num_errors = sum(r["status"] == "error" for r in results)
    num_dry = sum(r["dry_run"] for r in results)

    logger.info(
        "Summary: done=%d, skipped=%d, missing-reference=%d, dry-run=%d, errors=%d",
        num_done,
        num_skipped,
        num_missing_ref,
        num_dry,
        num_errors,
    )

    return 1 if num_errors else 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    _configure_logging(debug=args.debug, quiet=args.quiet)

    if args.command == "metrics":
        return _run_metrics(args)
    if args.command == "upscale":
        return _run_upscale(args)

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
