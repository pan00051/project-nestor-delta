#!/bin/sh
set -eu

case "${RAILWAY_SERVICE_NAME:-}" in
  api)
    # RunStore is process-local. Do not add workers until storage is shared.
    exec uvicorn nestor_delta_service.app:app \
      --host 0.0.0.0 --port "${PORT:-8000}" --workers 1
    ;;
  web)
    : "${DELTA_API_BASE_URL:?DELTA_API_BASE_URL must point to the FastAPI service}"
    exec streamlit run src/nestor_delta_web/streamlit_app.py \
      --server.address 0.0.0.0 --server.port "${PORT:-8501}" --server.headless true
    ;;
  *)
    echo "Unsupported Railway service: ${RAILWAY_SERVICE_NAME:-unset}" >&2
    exit 64
    ;;
esac
