#!/usr/bin/env python3.13
"""Fulcrum reproducibility harness: one entry point for every paper under papers/.

Usage:
  py bin/fulcrum_repro.py verify <paper>     # run verification, print JSON summary
  py bin/fulcrum_repro.py figures <paper>    # regenerate figures via figurekit
  py bin/fulcrum_repro.py render <paper>     # render markdown to PDF
  py bin/fulcrum_repro.py all <paper>        # verify → figures → render → SHA-256 manifest (unsigned)
  py bin/fulcrum_repro.py manifest <paper>   # print/verify SHA‑256 of every artifact

Papers are discovered under papers/paper‑N/ with convention:
  paper.md       – main manuscript
  verify/*.py    – verification scripts
  figures/       – generated figures (created by figures)
  MANIFEST.json  – SHA-256 manifest, unsigned (created by all)
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# Local shared helpers. repro-lib.py has a hyphen in its name (house convention
# of bin/*.py), so it is loaded by path with importlib rather than imported.
import importlib.util

_LIB_PATH = Path(__file__).resolve().parent / "repro-lib.py"
_spec = importlib.util.spec_from_file_location("repro_lib", _LIB_PATH)
if _spec is None or _spec.loader is None:
    raise ImportError(f"cannot load {_LIB_PATH}")
repro_lib = importlib.util.module_from_spec(_spec)
# Register before exec: dataclasses inspects sys.modules for the defining module.
sys.modules["repro_lib"] = repro_lib
_spec.loader.exec_module(repro_lib)

VerificationResult = repro_lib.VerificationResult
ResultStatus = repro_lib.ResultStatus
deterministic_json_dump = repro_lib.deterministic_json_dump
file_sha256 = repro_lib.file_sha256
tree_sha256 = repro_lib.tree_sha256
write_manifest = repro_lib.write_manifest
verify_manifest = repro_lib.verify_manifest
print_results_summary = repro_lib.print_results_summary


PAPERS_ROOT = Path("papers").resolve()
BIN = Path(__file__).parent


@dataclass
class Paper:
    """A discovered paper directory."""
    number: int
    path: Path

    @property
    def paper_md(self) -> Path:
        return self.path / "paper.md"

    @property
    def verify_dir(self) -> Path:
        return self.path / "verify"

    @property
    def figures_dir(self) -> Path:
        return self.path / "figures"

    @property
    def manifest_path(self) -> Path:
        return self.path / "MANIFEST.json"

    def exists(self) -> bool:
        """True if the paper directory exists."""
        return self.path.is_dir()

    def has_paper_md(self) -> bool:
        return self.paper_md.is_file()

    def has_verify_scripts(self) -> bool:
        return self.verify_dir.is_dir() and any(
            p.suffix == ".py" for p in self.verify_dir.glob("*.py")
        )

    def list_verify_scripts(self) -> list[Path]:
        """All .py files directly under verify/."""
        if not self.verify_dir.is_dir():
            return []
        return sorted(p for p in self.verify_dir.glob("*.py") if p.is_file())

    def validate(self) -> list[str]:
        """Return list of warnings about missing expected structure."""
        warns = []
        if not self.exists():
            warns.append(f"paper directory {self.path} does not exist")
            return warns
        if not self.has_paper_md():
            warns.append("paper.md missing")
        if not self.has_verify_scripts():
            warns.append("verify/*.py missing")
        return warns


def discover_papers() -> list[Paper]:
    """Find all papers/paper‑N directories."""
    papers = []
    if not PAPERS_ROOT.is_dir():
        return papers
    for p in PAPERS_ROOT.iterdir():
        if p.is_dir() and p.name.startswith("paper-"):
            try:
                num = int(p.name[6:])  # after "paper-"
                papers.append(Paper(num, p))
            except ValueError:
                continue
    papers.sort(key=lambda p: p.number)
    return papers


def find_paper(arg: str) -> Paper | None:
    """Find a paper by number or by path."""
    # If arg looks like a number, try paper‑N
    if arg.isdigit():
        num = int(arg)
        cand = PAPERS_ROOT / f"paper-{num}"
        if cand.is_dir():
            return Paper(num, cand)
    # Otherwise treat as a direct path
    path = Path(arg).resolve()
    # Try to infer number from directory name
    if path.is_dir() and path.name.startswith("paper-"):
        try:
            num = int(path.name[6:])
            return Paper(num, path)
        except ValueError:
            pass
    # Fallback: assume paper‑1 if directory exists
    if path.is_dir():
        return Paper(1, path)
    return None


def _coerce_child_result(name: str, proc, failed: bool = False) -> VerificationResult:
    """Normalize a verify script's output into a VerificationResult.

    Accepts either the house shape ({"name","status","value",...}) or a bare
    JSON object whose truthiness is judged from an OVERALL key or all-true
    boolean leaves. Anything unparseable falls back to the exit code.
    """
    status = ResultStatus.FAIL if failed else ResultStatus.PASS
    detail = f"exit {proc.returncode}"
    if failed and proc.stderr:
        detail += f": {proc.stderr.strip().splitlines()[-1][:200]}"
    try:
        data = json.loads(proc.stdout.strip())
    except Exception:
        return VerificationResult(name=name, status=status, detail=detail)

    if not isinstance(data, dict):
        return VerificationResult(name=name, status=status, detail=detail,
                                  value=data)

    if "status" in data and "name" in data:
        try:
            return VerificationResult.from_dict(data)
        except Exception:
            pass

    overall = data.get("OVERALL")
    if isinstance(overall, dict) and "all_claims_verified" in overall:
        ok = bool(overall["all_claims_verified"])
        return VerificationResult(
            name=name,
            status=ResultStatus.PASS if ok and not failed else ResultStatus.FAIL,
            value=overall["all_claims_verified"],
            detail=detail if not ok else None,
        )
    bool_leaves = [v for v in data.values() if isinstance(v, bool)]
    if bool_leaves:
        ok = all(bool_leaves) and not failed
        return VerificationResult(
            name=name,
            status=ResultStatus.PASS if ok else ResultStatus.FAIL,
            value=f"{sum(bool_leaves)}/{len(bool_leaves)} checks true",
            detail=detail if not ok else None,
        )
    return VerificationResult(name=name, status=status, detail=detail)


def cmd_verify(paper: Paper) -> int:
    """Run verification scripts and print JSON summary."""
    warns = paper.validate()
    if warns:
        for w in warns:
            print(f"warning: {w}", file=sys.stderr)
    if not paper.exists():
        print(f"error: paper directory {paper.path} not found", file=sys.stderr)
        return 2
    scripts = paper.list_verify_scripts()
    if not scripts:
        print("error: no verification scripts found", file=sys.stderr)
        return 3

    overall = VerificationResult(
        name=f"Paper {paper.number} verification",
        status=ResultStatus.PASS,
        children=[]
    )
    for s in scripts:
        try:
            proc = subprocess.run(
                [sys.executable, str(s)],
                cwd=paper.path,
                capture_output=True,
                text=True,
                timeout=300
            )
            if proc.returncode == 0:
                # Try to parse the script's JSON output.
                child = _coerce_child_result(s.name, proc)
                if child.status != ResultStatus.PASS:
                    overall.status = ResultStatus.FAIL
            else:
                child = _coerce_child_result(s.name, proc, failed=True)
                overall.status = ResultStatus.FAIL
        except subprocess.TimeoutExpired:
            child = VerificationResult(
                name=s.name,
                status=ResultStatus.ERROR,
                detail="timeout"
            )
            overall.status = ResultStatus.ERROR
        except Exception as e:
            child = VerificationResult(
                name=s.name,
                status=ResultStatus.ERROR,
                detail=str(e)
            )
            overall.status = ResultStatus.ERROR
        overall.children.append(child)

    print(deterministic_json_dump(overall.to_dict()))
    return 0 if overall.status == ResultStatus.PASS else 1


def cmd_figures(paper: Paper) -> int:
    """Regenerate paper's figures via figurekit."""
    if not paper.exists():
        print(f"error: paper directory {paper.path} not found", file=sys.stderr)
        return 2
    # Currently only paper‑1 has dedicated figure‑generation logic.
    # In the future each paper may have its own figurekit entry point.
    if paper.number == 1:
        # v0.4: recompute every radius from the data files, then draw all six figures
        outdir = paper.figures_dir
        outdir.mkdir(parents=True, exist_ok=True)
        try:
            for script in ("paper1-analysis.py", "paper1-figures.py", "paper1-supplement.py"):
                proc = subprocess.run([sys.executable, str(BIN / script)], capture_output=True,
                                      text=True, timeout=300)
                if proc.returncode != 0:
                    print(f"{script} failed: {proc.stderr}", file=sys.stderr)
                    return proc.returncode
            print(f"results recomputed and figures written to {outdir}")
            return 0
        except subprocess.TimeoutExpired:
            print("figurekit timed out", file=sys.stderr)
            return 124
        except Exception as e:
            print(f"figurekit error: {e}", file=sys.stderr)
            return 5
    else:
        print(f"note: figure generation is not yet implemented for paper {paper.number}; "
              f"skipping (add a figurekit entry point to enable it)", file=sys.stderr)
        return 0


def cmd_render(paper: Paper) -> int:
    """Render paper markdown to PDF."""
    warns = paper.validate()
    for w in warns:
        print(f"warning: {w}", file=sys.stderr)
    if not paper.has_paper_md():
        print("error: paper.md not found", file=sys.stderr)
        return 2

    out_base = Path("build") / f"paper-{paper.number}"
    out_base.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable, str(BIN / "render-paper.py"),
        str(paper.paper_md),
        "--out", str(out_base),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if proc.returncode != 0:
            print(f"render‑paper failed: {proc.stderr}", file=sys.stderr)
            return proc.returncode
        print(f"rendered PDF: {out_base}.pdf")
        return 0
    except subprocess.TimeoutExpired:
        print("render‑paper timed out", file=sys.stderr)
        return 124
    except Exception as e:
        print(f"render‑paper error: {e}", file=sys.stderr)
        return 5


def cmd_all(paper: Paper) -> int:
    """verify → figures → render → write an unsigned SHA-256 manifest."""
    # verify
    print("=== verify ===")
    rc = cmd_verify(paper)
    if rc != 0:
        print("verification failed; stopping", file=sys.stderr)
        return rc
    # figures
    print("\n=== figures ===")
    rc = cmd_figures(paper)
    if rc != 0:
        print("figure generation failed; stopping", file=sys.stderr)
        return rc
    # render
    print("\n=== render ===")
    rc = cmd_render(paper)
    if rc != 0:
        print("rendering failed; stopping", file=sys.stderr)
        return rc
    # manifest
    print("\n=== manifest ===")
    # Collect artifacts: paper.md, figures/*.png, verify/*.py, rendered PDF
    artifacts = []
    if paper.paper_md.is_file():
        artifacts.append(paper.paper_md)
    for fig in paper.figures_dir.glob("*.png"):
        if fig.is_file():
            artifacts.append(fig)
    for scr in paper.list_verify_scripts():
        artifacts.append(scr)
    for extra in sorted(paper.verify_dir.glob("*.json")) + sorted((paper.path / "data").glob("*.json")):
        artifacts.append(extra)
    if (paper.path / "supplement.zip").is_file():
        artifacts.append(paper.path / "supplement.zip")
    pdf = Path("build") / f"paper-{paper.number}.pdf"
    pdf_local = paper.path / "build" / f"paper-{paper.number}.pdf"
    if pdf.is_file():
        pdf_local.parent.mkdir(parents=True, exist_ok=True)
        import shutil
        shutil.copy2(pdf, pdf_local)
        artifacts.append(pdf_local)
    if not artifacts:
        print("error: no artifacts found to include in manifest", file=sys.stderr)
        return 6
    try:
        manifest_path = write_manifest(
            paper.path,
            artifacts,
            extra_info={
                "paper": paper.number,
                "harness": "fulcrum_repro",
                "command": "all"
            }
        )
        print(f"manifest written: {manifest_path}")
        # Verify immediately
        ok, errs = verify_manifest(manifest_path, paper.path)
        if not ok:
            print("error: newly written manifest fails verification:", file=sys.stderr)
            for e in errs:
                print(f"  {e}", file=sys.stderr)
            return 7
        print("manifest verified OK")
        return 0
    except Exception as e:
        print(f"manifest creation failed: {e}", file=sys.stderr)
        return 8


def cmd_manifest(paper: Paper) -> int:
    """Print SHA‑256 of every artifact in the paper's bundle."""
    if not paper.exists():
        print(f"error: paper directory {paper.path} not found", file=sys.stderr)
        return 2
    # If a MANIFEST.json exists, verify it; otherwise compute tree hash.
    if paper.manifest_path.is_file():
        print(f"Verifying {paper.manifest_path}")
        ok, errs = verify_manifest(paper.manifest_path, paper.path)
        if ok:
            print("All hashes match.")
            return 0
        else:
            print("Errors:", file=sys.stderr)
            for e in errs:
                print(f"  {e}", file=sys.stderr)
            return 1
    else:
        print(f"No MANIFEST.json found; computing tree hash of {paper.path}")
        hashes = tree_sha256(paper.path, ignore={"__pycache__", ".pyc", ".DS_Store"})
        if not hashes:
            print("No files found.")
            return 0
        for rel, h in sorted(hashes.items()):
            print(f"{h}  {rel}")
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="fulcrum_repro",
        description="Fulcrum reproducibility harness"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # common paper argument
    def add_paper_arg(p):
        p.add_argument(
            "paper",
            help="paper number or path to a paper-N directory"
        )

    # verify
    verify_parser = subparsers.add_parser("verify", help="run verification scripts")
    add_paper_arg(verify_parser)

    # figures
    figures_parser = subparsers.add_parser("figures", help="regenerate figures")
    add_paper_arg(figures_parser)

    # render
    render_parser = subparsers.add_parser("render", help="render markdown to PDF")
    add_paper_arg(render_parser)

    # all
    all_parser = subparsers.add_parser("all", help="verify → figures → render → manifest")
    add_paper_arg(all_parser)

    # manifest
    manifest_parser = subparsers.add_parser("manifest", help="print/verify SHA‑256 artifacts")
    add_paper_arg(manifest_parser)

    args = parser.parse_args()

    paper = find_paper(args.paper)
    if paper is None:
        print(f"error: paper '{args.paper}' not found", file=sys.stderr)
        return 2

    if args.command == "verify":
        return cmd_verify(paper)
    elif args.command == "figures":
        return cmd_figures(paper)
    elif args.command == "render":
        return cmd_render(paper)
    elif args.command == "all":
        return cmd_all(paper)
    elif args.command == "manifest":
        return cmd_manifest(paper)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())