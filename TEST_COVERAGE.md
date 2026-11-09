# Model unit test line coverage

Measured using Python 3.13.0 and the standard-library trace module.

Reproduce from the project root with `python3 tools/measure_coverage.py`.

Test result: 32 tests executed; 0 failures; 0 errors.

| Model source | Executed lines | Executable lines | Line coverage |
| --- | ---: | ---: | ---: |
| model/__init__.py | 6 | 6 | 100.00% |
| model/criteria.py | 121 | 121 | 100.00% |
| model/errors.py | 11 | 11 | 100.00% |
| model/manager.py | 60 | 60 | 100.00% |
| model/records.py | 96 | 96 | 100.00% |
| model/storage.py | 43 | 43 | 100.00% |
| **Total** | **337** | **337** | **100.00%** |

Scope: every Python module in model; controller and CLI tests also run, but their lines are excluded.

Method: trace measures executed source lines, including import-time class/function definitions. It is line coverage, not branch or path coverage. Percentages use executed / executable lines reported by trace, without excluding error paths or model code.

Annotated per-line details are regenerated in .coverage/; >>>>>> means not executed.
