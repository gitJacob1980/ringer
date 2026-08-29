#!/bin/bash
# Ringer engine wrapper: run OpenCode under an OS-level sandbox.
#
# OpenCode has no OS-level sandbox of its own — its --dangerously-skip-permissions
# flag (required for headless runs) disables ALL of its interactive approval
# prompts. This wrapper supplies the real containment: full network and reads,
# writes confined to the task dir, a per-run scratch/cache dir, and OpenCode's
# own state dirs.
#
# Two backends, chosen by what the host has:
#   macOS  — Seatbelt (/usr/bin/sandbox-exec) with a deny-write profile.
#   Linux  — bubblewrap (bwrap): the whole filesystem read-only bind-mounted,
#            the allowed paths re-bound read-write on top. Network is left in
#            the host namespace (OpenCode needs the model API).
# Both express the same policy; keep them in step when you change either.
#
# Usage (as a ringer engine bin):
#   opencode-sandboxed.sh <taskdir> [--no-sandbox] <opencode args...>
#
# The first argument is the task directory (pass "{taskdir}" first in
# args_template). "--no-sandbox" as the second argument skips the sandbox
# entirely — wire it as the engine's full_access_args so ringer's
# allow_full_access gate still applies.
#
# OPENCODE_BIN may be set in the environment to override PATH lookup (used by
# the wrapper's own tests to run a stand-in command under the sandbox).
set -euo pipefail

TASKDIR="${1:?usage: opencode-sandboxed.sh <taskdir> [--no-sandbox] <args...>}"; shift
SANDBOX=1
if [ "${1:-}" = "--no-sandbox" ]; then SANDBOX=0; shift; fi

# Resolve opencode without tripping `set -e` (command -v returns nonzero when absent).
if [ -z "${OPENCODE_BIN:-}" ]; then
  if ! OPENCODE_BIN="$(command -v opencode)" || [ -z "$OPENCODE_BIN" ]; then
    echo "opencode-sandboxed.sh: opencode not found on PATH" >&2
    exit 127
  fi
fi

if [ "$SANDBOX" = "0" ]; then
  exec "$OPENCODE_BIN" "$@" < /dev/null
fi

# Pick a backend before doing any setup, so the error is immediate and clear.
BACKEND=""
if [ -x /usr/bin/sandbox-exec ]; then
  BACKEND=seatbelt
elif command -v bwrap >/dev/null 2>&1; then
  BACKEND=bwrap
else
  echo "opencode-sandboxed.sh: no sandbox backend available." >&2
  echo "  macOS: needs /usr/bin/sandbox-exec.  Linux: install bubblewrap (bwrap)." >&2
  echo "  Or use the engine's full-access mode (--no-sandbox) via a full_access task." >&2
  exit 1
fi

TASKDIR_REAL="$(cd "$TASKDIR" && pwd -P)"

# Per-run scratch root — becomes both TMPDIR and XDG_CACHE_HOME for OpenCode, so
# we never have to open all of /tmp (or /private/tmp) or ~/.cache to the
# sandboxed agent. Resolve to the real path: Seatbelt subpath matching and
# bwrap bind sources both need the canonical path.
SCRATCH="$(cd "$(mktemp -d -t ringer-opencode-scratch.XXXXXX)" && pwd -P)"
PROFILE=""
# Always end with a succeeding command: the EXIT trap's status can replace the
# script's exit status in some bash versions, which would mask the child's rc.
cleanup() { rm -rf "$SCRATCH"; if [ -n "$PROFILE" ]; then rm -f "$PROFILE"; fi; return 0; }
trap cleanup EXIT

OC_SHARE="$HOME/.local/share/opencode"
OC_STATE="$HOME/.local/state/opencode"
OC_CONFIG="$HOME/.config/opencode"
# bwrap refuses to bind a source that does not exist; Seatbelt does not care.
# Creating them is harmless — OpenCode creates them on first run anyway.
mkdir -p "$OC_SHARE" "$OC_STATE" "$OC_CONFIG"

export TMPDIR="$SCRATCH"
export XDG_CACHE_HOME="$SCRATCH/cache"
mkdir -p "$XDG_CACHE_HOME"

# Run the sandboxed process as a child (not exec) so the EXIT trap fires and
# cleans up scratch even on the success path; propagate the child's status.
status=0
case "$BACKEND" in
  seatbelt)
    PROFILE="$(mktemp -t ringer-opencode-prof.XXXXXX)"
    # Paths are passed to the profile via sandbox-exec -D parameters, NOT string
    # interpolation — a task dir containing quotes/parens/newlines can't inject rules.
    cat > "$PROFILE" <<'SBEOF'
(version 1)
(allow default)
(deny file-write*)
(allow file-write*
  (subpath (param "TASKDIR"))
  (subpath (param "SCRATCH"))
  (subpath (param "OC_SHARE"))
  (subpath (param "OC_STATE"))
  (subpath (param "OC_CONFIG")))
; /dev is needed for /dev/null, /dev/urandom, etc.; writes there can't create
; persistent files without root, so a few literals are allowed rather than via param.
(allow file-write-data
  (literal "/dev/null")
  (literal "/dev/dtracehelper")
  (literal "/dev/tty"))
SBEOF
    set +e
    /usr/bin/sandbox-exec \
      -D "TASKDIR=$TASKDIR_REAL" \
      -D "SCRATCH=$SCRATCH" \
      -D "OC_SHARE=$OC_SHARE" \
      -D "OC_STATE=$OC_STATE" \
      -D "OC_CONFIG=$OC_CONFIG" \
      -f "$PROFILE" "$OPENCODE_BIN" "$@" < /dev/null
    status=$?
    set -e
    ;;
  bwrap)
    # Same policy as the Seatbelt profile, expressed as mounts:
    #   --ro-bind / /      everything readable, nothing writable (recursive);
    #   --bind X X         the five allowed roots re-mounted read-write on top;
    #   --dev / --proc     fresh /dev (null, urandom, tty…) and /proc, since the
    #                      read-only host copies would break the runtime;
    #   --die-with-parent  no orphaned agent if ringer kills the wrapper.
    # No --unshare-net: the model API must be reachable. No --unshare-user/pid:
    # not needed for write containment and they surprise some runtimes. Paths
    # are passed as separate argv words — no string interpolation, so a task
    # dir with odd characters cannot inject options.
    set +e
    bwrap \
      --ro-bind / / \
      --dev /dev \
      --proc /proc \
      --bind "$TASKDIR_REAL" "$TASKDIR_REAL" \
      --bind "$SCRATCH" "$SCRATCH" \
      --bind "$OC_SHARE" "$OC_SHARE" \
      --bind "$OC_STATE" "$OC_STATE" \
      --bind "$OC_CONFIG" "$OC_CONFIG" \
      --die-with-parent \
      --chdir "$TASKDIR_REAL" \
      -- "$OPENCODE_BIN" "$@" < /dev/null
    status=$?
    set -e
    ;;
esac
trap - EXIT
cleanup
exit "$status"
