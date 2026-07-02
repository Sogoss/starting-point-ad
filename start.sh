#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status
set -e

ENV_FILE=".env"

if [ -f "$ENV_FILE" ]; then
    echo "Loading environment variables from $ENV_FILE..."
    set -a
    source "$ENV_FILE"
    set +a
else
    echo "Warning: $ENV_FILE not found. Running with current environment variables."
fi

# Execute main.py, passing all arguments along
exec python3 main.py "$@"
