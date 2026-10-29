#!/usr/bin/env python3
"""Package the verified, unmodified upstream vkd3d 3.1 x64 DLL pair."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile

REPO = Path(__file__).resolve().parents[1]
BASE = "4522cc1a8b1347f1ab1b0f7b14a23ed9444d95d1"
ARCHIVE = "b85ea8219b71093a3924913dd7aae6172333dc0c069983ed510816d67f02120b"
VERSION = "3.1-nvk.1"

def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()

def git(*args):
    return subprocess.check_output(["git", *args], cwd=REPO, text=True).strip()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream-archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if git("status", "--porcelain"):
        raise SystemExit("Use a clean source checkout")
    changed = git("diff", "--name-only", BASE).splitlines()
    if any(name != "README.md" and not name.startswith(("docs/", "tools/")) for name in changed):
        raise SystemExit("Runtime sources differ from the qualified upstream DLLs")
    if digest(args.upstream_archive) != ARCHIVE:
        raise SystemExit("Upstream archive checksum mismatch")
    output = args.output.absolute()
    if output.exists() or output.is_symlink():
        raise SystemExit("Choose a new output directory")
    root = output / ("vkd3d-nvk-" + VERSION)
    (root / "x64").mkdir(parents=True)
    with tarfile.open(args.upstream_archive) as source:
        for name in ("d3d12.dll", "d3d12core.dll"):
            member = source.getmember("vkd3d-proton-3.1/x64/" + name)
            if not member.isfile() or member.size > 64 * 1024 * 1024:
                raise SystemExit("Invalid upstream DLL entry")
            with source.extractfile(member) as stream:
                data = stream.read()
            offset = int.from_bytes(data[60:64], "little")
            if data[:2] != b"MZ" or data[offset:offset+6] != b"PE\0\0\x64\x86":
                raise SystemExit("Expected x64 PE DLL")
            (root / "x64" / name).write_bytes(data)
    for name in ("LICENSE", "COPYING", "AUTHORS"):
        shutil.copyfile(REPO / name, root / name)
    shutil.copyfile(REPO / "docs/NATIVE-NVK.md", root / "README.md")
    changes = subprocess.check_output(["git", "diff", "--binary", BASE, "HEAD"], cwd=REPO)
    (root / "source-changes.patch").write_bytes(changes)
    files = {str(p.relative_to(root)): digest(p) for p in sorted(root.rglob("*")) if p.is_file()}
    record = {
        "version": VERSION, "fork": "https://github.com/HighDelay/vkd3d-nvk",
        "packaging_revision": git("rev-parse", "HEAD"), "runtime_source_revision": BASE,
        "runtime_modified": False, "binary_origin": "Unmodified upstream release; extracted, not rebuilt",
        "archive_url": "https://github.com/HansKristian-Work/vkd3d-proton/releases/download/v3.1/vkd3d-proton-3.1.tar.zst",
        "archive_sha256": ARCHIVE, "files": files,
        "driver_provider_required": "/Library/GPUBundles/nvmtl/wine",
        "validation": {"hardware": "RTX 2060 SUPER / macOS Tahoe 26.7.1 / YAAGL Wine 11.0-1",
                       "zzz_d3d12": "user-confirmed", "dlss_sr": "probe and user-confirmed",
                       "dlss_frame_generation": "NOT TESTED", "ray_tracing": "NOT TESTED"},
    }
    (root / "BUILD.json").write_text(json.dumps(record, indent=2) + "\n")
    with (root / "SHA256SUMS").open("w") as manifest:
        for p in sorted(root.rglob("*")):
            if p.is_file() and p.name != "SHA256SUMS":
                manifest.write(digest(p) + "  " + str(p.relative_to(root)) + "\n")
    archive = output / (root.name + "-x64.tar.gz")
    with tarfile.open(archive, "w:gz", format=tarfile.PAX_FORMAT) as dest:
        for path in [root, *sorted(root.rglob("*"))]:
            info = dest.gettarinfo(path, arcname=str(path.relative_to(output)))
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            info.pax_headers = {}
            if path.is_file():
                with path.open("rb") as stream:
                    dest.addfile(info, stream)
            else:
                dest.addfile(info)
    (output / "SHA256SUMS").write_text(digest(archive) + "  " + archive.name + "\n")
    print(json.dumps({"archive": str(archive), "sha256": digest(archive), "files": files}, indent=2))

if __name__ == "__main__":
    main()
