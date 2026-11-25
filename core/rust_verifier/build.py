"""Build script to compile core/rust_verifier/src/lib.rs into cegis_bellman_verifier.{dll,so,dylib} using rustc directly."""

import os
import platform
import subprocess
import sys


def main() -> int:
    here = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(here, "src", "lib.rs")
    sysname = platform.system()
    if sysname == "Windows":
        out_name = "cegis_bellman_verifier.dll"
    elif sysname == "Darwin":
        out_name = "libcegis_bellman_verifier.dylib"
    else:
        out_name = "libcegis_bellman_verifier.so"
    out_path = os.path.join(here, out_name)
    cmd = [
        "rustc",
        "--edition", "2021",
        "--crate-type", "cdylib",
        "-C", "opt-level=3",
        "-C", "target-cpu=native",
        "-o", out_path,
        src,
    ]
    print("Building:", " ".join(cmd))
    res = subprocess.run(cmd)
    if res.returncode == 0:
        print(f"Built cleanly: {out_path} ({os.path.getsize(out_path):,} bytes)")
    return res.returncode


if __name__ == "__main__":
    sys.exit(main())
