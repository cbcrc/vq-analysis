#!/bin/bash

# -----------------------------------------------------------------------------
# Description: 
#   This script processes visual quality metrics by comparing distorted 
#   video files against reference video files.
#
# Usage:
#   ./compute_metrics.sh <reference_pattern> <distorted_pattern> [destination_folder]
#
# Arguments:
#   <reference_pattern>   - File pattern for reference files (e.g., 'videos/ref/*.mov')
#   <distorted_pattern>   - File pattern for distorted files (e.g., 'videos/dist/*.mp4')
#   [destination_folder]  - (Optional) Folder where output metric files will be stored
#   			    (default: current directory)
#
# Example:
#   ./compute_metrics.sh "ref_videos/*.mov" "dist_videos/*.mp4" "output/metrics"
#   ./compute_metrics.sh "ref_videos/*.mov" "dist_videos/*.mp4"
#
# Requirements:
#   - FFMPEG
#
# -----------------------------------------------------------------------------

# Check if at least two arguments are provided
if [ $# -lt 2 ]; then
  echo "Usage: $0 <reference_pattern> <distorted_pattern> [destination_folder]"
  echo "Example: $0 'videos/ref/*.mov' 'videos/dist/*.mp4' 'output/metrics'"
  exit 1
fi

REF_PATTERN="$1"
DIST_PATTERN="$2"
DEST_FOLDER="${3:-.}"  # Default to current directory if no destination is provided

validate_pattern() {
  local pattern="$1"
  
  # Ensure the pattern contains a valid path, wildcard '*', and extension
  if [[ ! "$pattern" =~ ^.+/[^/]*\*[^/]*\.[a-zA-Z0-9]+$ ]]; then
    echo "Error: Invalid pattern '$pattern'. Expected format: 'folder/subfolder/*.extension'"
    exit 1
  fi
}

validate_pattern "$REF_PATTERN"
validate_pattern "$DIST_PATTERN"

# Extract folder paths from patterns
REF_FOLDER=$(dirname "$REF_PATTERN")
DIST_FOLDER=$(dirname "$DIST_PATTERN")

# Check if the reference and distorted folders exist
if [ ! -d "$REF_FOLDER" ]; then
  echo "Error: The reference folder '$REF_FOLDER' does not exist."
  exit 1
fi

if [ ! -d "$DIST_FOLDER" ]; then
  echo "Error: The distorted folder '$DIST_FOLDER' does not exist."
  exit 1
fi

# Check if the destination folder exists, if not, create it
if [ ! -d "$DEST_FOLDER" ]; then
  echo "Destination folder '$DEST_FOLDER' does not exist. Creating it..."
  mkdir -p "$DEST_FOLDER"
fi

# Expand distorted files (globbing)
DIST_FILES=($DIST_PATTERN)

# Ensure distorted files exist
if [ ${#DIST_FILES[@]} -eq 0 ]; then
  echo "Error: No distorted files found matching pattern '$DIST_PATTERN'."
  exit 1
fi

echo "Processing visual quality metrics for files matching '$DIST_PATTERN' and checking against '$REF_PATTERN'..."

# Extract reference folder and extension
REF_FOLDER=$(dirname "$REF_PATTERN")
REF_EXTENSION="${REF_PATTERN##*.}"

# Loop through each distorted file and find a matching reference file
for dist_file in "${DIST_FILES[@]}"; do
  # Extract filename without extension
  dist_basename=$(basename "$dist_file" | sed 's/\.[^.]*$//')

  # Look for a matching reference file with any extension
  ref_file=$(find "$REF_FOLDER" -type f -name "${dist_basename}.$REF_EXTENSION")

  if [ -f "$ref_file" ]; then
    echo "[INFO] Comparing: $ref_file vs $dist_file"

    ffmpeg -i $dist_file -i $ref_file -lavfi libvmaf=n_threads=8:log_path=$DEST_FOLDER/${dist_basename}.json:log_fmt='json':feature='name=psnr|name=float_ms_ssim|name=ciede' -f null -
  else
    echo "[WARNING] No matching reference file found for '$dist_file' in '$REF_PATTERN'."
  fi
done

