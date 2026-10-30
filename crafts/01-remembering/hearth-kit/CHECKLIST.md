# What has to be true for an agent to keep a hearth

These are the eight conditions from [*What It Takes to Remember*](https://robhunterworks.com/writing/what-it-takes-to-remember/). Each one maps to tests in `tests/test_hearth_kit.py`, where the test names carry the condition number. A condition with no test is a wish.

| # | Condition | How the kit holds it | Tests |
|---|---|---|---|
| C1 | **The agent can read the frame before it acts.** | `kindle` prints the capsule's four shared fields in a fixed order, then a freshness verdict, then any unfolded notes. With no capsule to read, it says so out loud: *this session will not bank*. | `test_c1_*` |
| C2 | **A session starts properly, or it doesn't count.** | A write outside a claim is refused. Overlapping claims are refused. A close that finds changed files leaves the claim open until a person releases it with a reason. | `test_c2_*` |
| C3 | **The scripts are reachable from where commands run.** | One stdlib file, run by path with `--root`, from any working directory. A wrong root refuses and writes nothing. | `test_c3_*` |
| C4 | **The filesystem behaves like the one you designed for.** | The fingerprint probes the folder. On a mount that drops group and other permission bits, it compares content, type and the executable bit, and nothing else. Content edits, exec-bit flips and strict mode still refuse. | `test_c4_*` |
| C5 | **Capture is cheap enough to happen in the moment.** | One call writes one note under a kilobyte. A decision must carry its *why* and what was *rejected*. | `test_c5_*` |
| C6 | **Freshness is checked against the work, not the clock.** | `fresh` compares the capsule's `next` and `open_items` against the board's rows and never looks at a date. | `test_c6_*` |
| C7 | **A person decides what becomes canon.** | `bank` needs a named person and refuses the usual agent names. | `test_c7_*` |
| C8 | **The memory stays small.** | `bank` refuses a capsule over 16 KB. | `test_c8_*` |

`bank` also refuses to finish while notes are unfolded, or while the board's `last_updated` is older than the newest folded note. The board gets refreshed at every bank, or the bank doesn't happen.
