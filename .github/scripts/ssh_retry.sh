#!/usr/bin/env bash
# Retries a transient ssh/scp connection to the deploy server.
# The self-hosted build runner shares the same box the deploy job SSHes into
# right after a heavy multi-image docker build, which can cause a connection
# to drop or time out for no server-side auth reason. Retry before failing.
retry() {
  local max_attempts=5
  local delay=5
  local attempt=1
  until "$@"; do
    if [ "$attempt" -ge "$max_attempts" ]; then
      echo "ERROR: command failed after $max_attempts attempts: $*" >&2
      return 1
    fi
    echo "Attempt $attempt/$max_attempts failed, retrying in ${delay}s: $*" >&2
    sleep "$delay"
    attempt=$((attempt + 1))
  done
}
