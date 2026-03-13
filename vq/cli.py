import argparse


def main():
    parser = argparse.ArgumentParser(
        prog="vq", description="Video Quality Analysis tools"
    )

    subparsers = parser.add_subparsers(dest="command")

    # upscale command
    upscale_parser = subparsers.add_parser(
        "upscale", help="Upscale videos to a target resolution"
    )

    upscale_parser.add_argument(
        "-i", "--input", required=True, help="Input file pattern (glob)"
    )

    upscale_parser.add_argument(
        "-o", "--output", required=True, help="Output directory"
    )

    upscale_parser.add_argument("--ffmpeg", default="ffmpeg", help="FFmpeg executable")

    args = parser.parse_args()

    if args.command == "upscale":
        print("Upscale command not implemented yet")
    else:
        parser.print_help()
