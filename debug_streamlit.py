#!/usr/bin/env python3
"""Debug streamlit startup issues."""
import subprocess
import sys
import time

print("Starting streamlit with full output capture...")
print("=" * 60)

proc = subprocess.Popen(
    [sys.executable, "-m", "streamlit", "run", "streamlit_app.py"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1,
)

try:
    for i, line in enumerate(proc.stdout):
        print(line.rstrip())
        if i > 100:  # Show first 100 lines
            print("\n[... truncated ...]")
            break
except KeyboardInterrupt:
    print("\n[Interrupted by user]")
finally:
    proc.terminate()
    proc.wait()
    print("\n" + "=" * 60)
    print(f"Process exited with code: {proc.returncode}")
