from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from shutil import which


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
            raise FileNotFoundError(msg)

    def run(self, args: list[str]) -> FFmpegResult:
        cmd = [self.executable, *args]

        if self.dry_run:
            return FFmpegResult(
                cmd=cmd,
                returncode=0,
                elapsed_s=0.0,
                stdout="",
                stderr="",
                dry_run=True,
            )

        self.validate()

        t0 = time.time()
        proc = subprocess.run(cmd, capture_output=True, text=True)
        elapsed = time.time() - t0

        return FFmpegResult(
            cmd=cmd,
            returncode=proc.returncode,
            elapsed_s=elapsed,
            stdout=proc.stdout,
            stderr=proc.stderr,
            dry_run=False,
        )
