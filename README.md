# VQ Analysis

Tools for video quality analysis and bitrate ladder evaluation.

This project aims to provide reproducible utilities for:
- upscaling ladder outputs to a common reference resolution
- computing objective quality metrics
- generating RD plots
- comparing bitrate ladder designs and encoder configurations

The project is under active development.

## Installation

Clone the repository and install the package in editable mode.

git clone https://github.com/cbcrc/vq-analysis.git  
cd vq-analysis  
pip install -e .

This installs the `vq` command line tool.

Requirements:
  - Python ≥ 3.10
  - FFmpeg compiled with libvmaf

You can check libvmaf support with:

```bash
ffmpeg -filters | grep vmaf
```

## Workflow Overview

Typical evaluation pipeline:

```
encoded ladder outputs
        │
        ▼
vq upscale
        │
        ▼
upscaled FFV1 intermediates
        │
        ▼
vq metrics
        │
        ▼
VMAF / PSNR / MS-SSIM JSON logs
```

The intermediate files use FFV1, a lossless codec, so that scaling artifacts do not contaminate metric evaluation.

## Step 1 — Upscale ladder outputs

Example input structure:

```
outputs/bitrate_ladder_folder/
├── DOTA2_60f_420_1080p30_ffv1/
│   ├── 216p_256k.mp4
│   ├── 360p_512k.mp4
│   └── ...
```

Run:

```bash
vq upscale \
  -I outputs/bitrate_ladder_folder \
  -i "**/*.mp4" \
  -o outputs/bitrate_ladder_folder_upscaled
```

Example output:

```
outputs/bitrate_ladder_folder_upscaled/
├── DOTA2_60f_420_1080p30_ffv1/
│   ├── 216p_256k_up1080p_ffv1.mkv
│   ├── 360p_512k_up1080p_ffv1.mkv
│   └── ...
```

## Step 2 — Compute quality metrics

Reference videos should exist one per sequence, named after the sequence folder.

Example:

```
reference/
├── DOTA2_60f_420_1080p30_ffv1.mkv
├── BQTerrace_60f_420_1080p30_ffv1.mkv
```

Run:

```bash
vq metrics \
  -I outputs/bitrate_ladder_folder_upscaled \
  -R reference \
  -i "**/*.mkv" \
  -o outputs/metrics_logs
```

Example output:

```
outputs/metrics_logs/
├── DOTA2_60f_420_1080p30_ffv1/
│   ├── 216p_256k_up1080p_ffv1.json
│   ├── 360p_512k_up1080p_ffv1.json
│   └── ...
```

Each JSON file contains frame-level and pooled metrics from libvmaf.

### Selecting a VMAF model (optional)

You can explicitly select the libvmaf model using `--model`.

Examples:

```bash
# Standard HD model (default in most FFmpeg builds)
vq metrics ... --model "version=vmaf_v0.6.3"

# 4K model (recommended for 4K evaluation)
vq metrics ... --model "version=vmaf_4k_v0.6.1"

# Phone model (mobile viewing conditions)
vq metrics ... --model "version=vmaf_v0.6.3:phone_model=1"
```

If `--model` is not specified, the default model from your FFmpeg/libvmaf build is used.