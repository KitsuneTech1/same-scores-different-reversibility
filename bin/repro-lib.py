#!/usr/bin/env python3.13
"""Shared reproducibility helpers for Fulcrum papers.

Provides deterministic JSON serialization, SHA‑256 hashing, manifest
generation/verification, and a simple result‑reporting type.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterable


class ResultStatus(Enum):
    """Outcome of a single verification check."""
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"
    ERROR = "error"


@dataclass
class VerificationResult:
    """Standard shape for a verification script to report."""
    # Human‑readable check name
    name: str
    # PASS, FAIL, SKIP, ERROR
    status: ResultStatus
    # Optional numeric/boolean value that supports the status
    value: Any = None
    # Optional free‑text detail
    detail: str | None = None
    # Optional list of sub‑checks (each a VerificationResult)
    children: list[VerificationResult] | None = None

    def to_dict(self) -> dict:
        """Convert to a JSON‑serializable dict."""
        d = {"name": self.name, "status": self.status.value}
        if self.value is not None:
            d["value"] = self.value
        if self.detail is not None:
            d["detail"] = self.detail
        if self.children:
            d["children"] = [c.to_dict() for c in self.children]
        return d

    @classmethod
    def from_dict(cls, d: dict) -> VerificationResult:
        """Reconstruct from a dict."""
        children = None
        if "children" in d:
            children = [cls.from_dict(c) for c in d["children"]]
        return cls(
            name=d["name"],
            status=ResultStatus(d["status"]),
            value=d.get("value"),
            detail=d.get("detail"),
            children=children
        )


def deterministic_json_dump(obj: Any, indent: int = 2) -> str:
    """JSON with sorted keys, no trailing spaces, default separators.

    Guarantees that two objects that compare equal produce identical
    byte‑for‑byte JSON.
    """
    return json.dumps(
        obj,
        sort_keys=True,
        indent=indent,
        separators=(",", ": "),
        ensure_ascii=False
    )


def file_sha256(path: Path | str, chunk_size: int = 8192) -> str:
    """SHA‑256 of a single file."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"not a file: {path}")
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def tree_sha256(root: Path | str, ignore: set[str] | None = None) -> dict[str, str]:
    """SHA‑256 of every regular file under root, keyed by relative path.

    Ignores directories and files whose name is in `ignore`.
    Paths are normalized with forward slashes.
    """
    if ignore is None:
        ignore = set()
    root = Path(root).resolve()
    out = {}
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if p.name in ignore:
            continue
        rel = p.relative_to(root).as_posix()
        out[rel] = file_sha256(p)
    return out


def write_manifest(
    paper_dir: Path,
    artifact_paths: Iterable[Path],
    extra_info: dict | None = None,
    output_path: Path | None = None
) -> Path:
    """Create a manifest.json with SHA‑256 of each artifact.

    Args:
        paper_dir: Base directory for relative paths.
        artifact_paths: Files to include.
        extra_info: Additional keys to store (e.g., "paper": 1).
        output_path: Where to write manifest.json (default paper_dir/MANIFEST.json).

    Returns:
        Path to the written manifest.
    """
    paper_dir = paper_dir.resolve()
    if output_path is None:
        output_path = paper_dir / "MANIFEST.json"
    manifest = {}
    if extra_info:
        manifest.update(extra_info)
    manifest["artifacts"] = {}
    for p in artifact_paths:
        p = Path(p).resolve()
        if not p.is_file():
            raise FileNotFoundError(f"artifact not a file: {p}")
        rel = p.relative_to(paper_dir).as_posix()
        manifest["artifacts"][rel] = file_sha256(p)
    manifest["generated"] = datetime.now(timezone.utc).isoformat()
    output_path.write_text(deterministic_json_dump(manifest), encoding="utf-8")
    return output_path


def verify_manifest(manifest_path: Path, paper_dir: Path | None = None) -> tuple[bool, list[str]]:
    """Check that every file listed in a manifest matches its recorded hash.

    Args:
        manifest_path: Path to manifest.json.
        paper_dir: Root for relative paths (default manifest_path.parent).

    Returns:
        (all_ok, list_of_errors)
    """
    manifest_path = manifest_path.resolve()
    if paper_dir is None:
        paper_dir = manifest_path.parent
    paper_dir = paper_dir.resolve()
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as e:
        return False, [f"cannot read/parse manifest: {e}"]

    errors = []
    for rel, expected in data.get("artifacts", {}).items():
        p = paper_dir / rel
        if not p.is_file():
            errors.append(f"missing: {rel}")
            continue
        try:
            actual = file_sha256(p)
        except Exception as e:
            errors.append(f"hash failed {rel}: {e}")
            continue
        if actual != expected:
            errors.append(f"hash mismatch: {rel}")
    return len(errors) == 0, errors


def print_results_summary(results: list[VerificationResult]) -> bool:
    """Pretty‑print verification results and return overall pass status."""
    all_pass = True
    for r in results:
        status_char = {
            ResultStatus.PASS: "✓",
            ResultStatus.FAIL: "✗",
            ResultStatus.SKIP: "‑",
            ResultStatus.ERROR: "!",
        }[r.status]
        print(f"  {status_char} {r.name}", end="")
        if r.detail:
            print(f" – {r.detail}")
        else:
            print()
        if r.status != ResultStatus.PASS:
            all_pass = False
    return all_pass


def main() -> None:
    """Demo of the library functions."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "a.txt").write_text("hello")
        (root / "b.txt").write_text("world")
        sub = root / "sub"
        sub.mkdir()
        (sub / "c.txt").write_text("deep")

        print("tree hash:")
        for rel, h in sorted(tree_sha256(root, ignore={"c.txt"}).items()):
            print(f"  {rel}: {h}")

        manifest = write_manifest(
            root,
            [root / "a.txt", root / "b.txt"],
            extra_info={"test": True}
        )
        print("\nmanifest:", manifest.read_text())

        ok, errs = verify_manifest(manifest, root)
        print(f"\nverify: {ok}")
        if errs:
            print("errors:", errs)


if __name__ == "__main__":
    main()