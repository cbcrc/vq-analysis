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

## Usage

### Upscale ladder outputs

Upscale encoded ladder outputs to a common reference resolution.

Example:

```bash
vq upscale \
  -I outputs/ladder_encodes \
  -i "**/*.mp4" \
  -o outputs/ladder_encodes_upscaled
```

This will:

- recursively find encoded files (in this case all `.mp4` files in each subfolder)
- upscale them to **1920×1080**
- preserve the original directory structure
- encode the intermediate files using **FFV1** (a lossless video codec)