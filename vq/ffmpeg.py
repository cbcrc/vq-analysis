from __future__ import annotations

import logging
import shlex
import subprocess
import time
from dataclasses import dataclass
from shutil import which

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class FFmpegResult:
    cmd: list[str]
    returncode: int
    elapsed_s: float
    stdout: str
    stderr: str
    dry_run: bool = False

    @property
    def ok(self) -> bool:
        return self.returncode == 0


class FFmpegRunner:
    def __init__(self, executable: str = "ffmpeg", dry_run: bool = False) -> None:
        self.executable = executable
        self.dry_run = dry_run

    def validate(self) -> None:
        if which(self.executable) is None:
            msg = (
                f'FFmpeg executable "{self.executable}" was not found. '
                "Install FFmpeg and ensure it is available in PATH, "
                "or provide a custom executable path."
            )
            logger.error(msg)
            raise FileNotFoundError(msg)

    def run(self, args: list[str]) -> FFmpegResult:
        cmd = [self.executable, *args]

        if self.dry_run:
            logger.info("DRY RUN: %s", cmd)
            return FFmpegResult(
                cmd=cmd,
                returncode=0,
                elapsed_s=0.0,
                stdout="",
                stderr="",
                dry_run=True,
            )

        self.validate()

        logger.debug("Running FFmpeg command:\n$ %s", shlex.join(cmd))
        t0 = time.time()
        proc = subprocess.run(cmd, capture_output=True, text=True)
        elapsed = time.time() - t0
        logger.debug(f"Finished in {elapsed:.2f}s")

        if proc.returncode != 0:
            logger.error("FFmpeg command failed with return code %d", proc.returncode)
            if proc.stderr:
                logger.debug("FFmpeg stderr:\n%s", proc.stderr)

        return FFmpegResult(
            cmd=cmd,
            returncode=proc.returncode,
            elapsed_s=elapsed,
            stdout=proc.stdout,
            stderr=proc.stderr,
            dry_run=False,
        )
