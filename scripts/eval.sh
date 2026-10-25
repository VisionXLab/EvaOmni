#!/usr/bin/env bash
# Run the MiMo adapter. Provider settings must be exported in the caller's
# environment; see .env.example. Nothing is hardcoded here so the script is
# safe to commit.
set -euo pipefail

: "${BASE_URL:?Set BASE_URL to the OpenAI-compatible base URL, for example https://<your-host>/v1}"
: "${API_KEY:?Set API_KEY to the provider API key}"
: "${MODEL_NAME:?Set MODEL_NAME to the model identifier, for example mimo-v2.6-flash}"

ANNOTATION_FILE="${ANNOTATION_FILE:-data/test_file.json}"
VIDEO_ROOT="${VIDEO_ROOT:-data/resized_video}"
RESULTS_DIR="${RESULTS_DIR:-outputs/mimo}"

python3 scripts/eval_mimo.py \
  --annotation "${ANNOTATION_FILE}" \
  --video-root "${VIDEO_ROOT}" \
  --results-dir "${RESULTS_DIR}" \
  --workers "${WORKERS:-4}" \
  --retries "${RETRIES:-3}" \
  --limit "${LIMIT:-0}"