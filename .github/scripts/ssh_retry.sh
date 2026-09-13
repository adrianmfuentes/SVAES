#!/usr/bin/env bash
# Retries a transient ssh/scp connection to the deploy server.
# The self-hosted build runner shares the same box the deploy job SSHes into
# right after a heavy multi-image docker build, which can cause a connection
# to drop or time out for no server-side auth reason. Retry before failing.

# Without an explicit ConnectTimeout, a stalled TCP connection (dropped
# packets, half-open connection) makes ssh/scp hang instead of failing fast,
# so a transient hiccup never gets the chance to be retried.
export SSH_OPTS="-o ConnectTimeout=30 -o ServerAliveInterval=15 -o ServerAliveCountMax=3"

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
