"""Measure model line coverage using only Python's standard library.

Run in a fresh process: python3 tools/measure_coverage.py
Produces TEST_COVERAGE.md and annotated .coverage/model.*.cover files.
"""

import contextlib
import io
import os
from pathlib import Path
import re
import sys
import trace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def run_tests():
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    return unittest.TextTestRunner(verbosity=2).run(suite)


def main() -> int:
    os.chdir(ROOT)
    # Do not use ignoredirs: trace caches basename decisions, so ignoring a
    # stdlib __init__.py can accidentally hide model/__init__.py as well.
    tracer = trace.Trace(count=True, trace=False)
    outcome = tracer.runfunc(run_tests)
    counts = {(filename, line): count for (filename, line), count in tracer.results().counts.items()
              if Path(filename).resolve().parent == ROOT / "model"}
    # Include entirely unexecuted modules rather than silently omitting them.
    for source in (ROOT / "model").glob("*.py"):
        counts.setdefault((str(source), 0), 0)
    results = trace.CoverageResults(counts=counts)
    details = ROOT / ".coverage"
    details.mkdir(exist_ok=True)
    for old_report in details.glob("*.cover"):
        old_report.unlink()
    summary = io.StringIO()
    with contextlib.redirect_stdout(summary):
        results.write_results(show_missing=True, summary=True, coverdir=str(details))
    # The .cover format is provided by trace: '>>>>>>' marks an unexecuted
    # executable line; an integer prefix marks a line actually executed.
    rows = []
    for path in sorted(details.glob("*.cover")):
        hit = missed = 0
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith(">>>>>>"):
                missed += 1
            elif re.match(r"^\s*\d+:", line):
                hit += 1
        total = hit + missed
        module = path.name.removesuffix(".cover")
        name = "model/__init__.py" if module == "model" else module.replace(".", "/") + ".py"
        rows.append((name, hit, total))
    if not rows:
        raise RuntimeError("No model coverage was measured.")
    hit_total = sum(row[1] for row in rows)
    line_total = sum(row[2] for row in rows)
    report = ["# Model unit test line coverage", "",
              f"Measured using Python {sys.version.split()[0]} and the standard-library trace module.", "",
              "Reproduce from the project root with `python3 tools/measure_coverage.py`.", "",
              f"Test result: {outcome.testsRun} tests executed; "
              f"{len(outcome.failures)} failures; {len(outcome.errors)} errors.", "",
              "| Model source | Executed lines | Executable lines | Line coverage |",
              "| --- | ---: | ---: | ---: |"]
    for name, hit, total in rows:
        percentage = 100 * hit / total if total else 100
        report.append(f"| {name} | {hit} | {total} | {percentage:.2f}% |")
    report.extend([f"| **Total** | **{hit_total}** | **{line_total}** | **{100 * hit_total / line_total:.2f}%** |", "",
                   "Scope: every Python module in model; controller and CLI tests also run, but their lines are excluded.", "",
                   "Method: trace measures executed source lines, including import-time class/function definitions. "
                   "It is line coverage, not branch or path coverage. Percentages use executed / executable lines "
                   "reported by trace, without excluding error paths or model code.", "",
                   "Annotated per-line details are regenerated in .coverage/; >>>>>> means not executed.", ""])
    (ROOT / "TEST_COVERAGE.md").write_text("\n".join(report), encoding="utf-8")
    print("\n".join(report))
    return 0 if outcome.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
