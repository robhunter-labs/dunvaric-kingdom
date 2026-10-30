# Hearth kit

Every AI session starts cold. This kit is the smallest version I could write of how the Kingdom keeps a project's memory between sessions. It isn't the Kingdom's own Hearth. It's the same shape with the rest stripped out, so you can read all of it in one sitting and build your own.

Four verbs carry it. **Kindle** reads the frame before anything else: the capsule's four shared fields (`thesis`, `the_governing_gate`, `open_items`, `next`), then a freshness verdict. **Capture** writes one typed note at the moment a decision happens. A decision has to say *why*, and what was *rejected*, or the next session argues it all over again. **Fold** applies the waiting notes to the capsule in capture order, under a lock, and archives only the notes that actually wrote something. **Bank** closes a milestone, and it asks for a named person. That check is a speed bump, not identity: it refuses an empty name and obvious agent names ("agent", "Claude Code", "codex-cli"), and it trusts any other name you type.

Two helpers come from the failures the essay describes. **Session claims**: a session claims the files it means to change, writes, then closes. If a file changed underneath it, the close refuses and the claim stays open until a person looks and releases it. **The fingerprint** knows which filesystem it's on. Some synced or bridged folders rewrite permission bits. On those, and only those, it stops counting group and other bits, so a byte-identical file doesn't look tampered with. It still catches a content edit or an executable-bit flip.

## Run it

Python 3.9 or newer, standard library only. The commands below use a POSIX shell (macOS, Linux, WSL).

```bash
cd crafts/01-remembering/hearth-kit
mkdir -p /tmp/hearth-demo/capsule
cp templates/CAPSULE.json /tmp/hearth-demo/capsule/ && cp templates/BOARD.md /tmp/hearth-demo/
python3 hearth_kit.py --root /tmp/hearth-demo kindle
python3 hearth_kit.py --root /tmp/hearth-demo capture decision "chose a short title" \
  --why "it fits the cover" --rejected "the long subtitle"
python3 hearth_kit.py --root /tmp/hearth-demo fold
python3 hearth_kit.py --root /tmp/hearth-demo bank --by "Your Name"
python3 -m unittest discover -s tests -v
```

The first `bank` will refuse. Read why, refresh the board, and try again. That's the point. To refresh it, edit `BOARD.md`: make its rows match the capsule and set `last_updated:` to the current UTC time, as `YYYYMMDDTHHMMSSZ` (for example `20261031T140000Z`) or ISO 8601. If you try to bank under an obvious agent name, it refuses that too.

If a note can never apply (say, a `resolve` whose `--target` matches no open item exactly), bank names it and waits. A person can take it back with `withdraw NOTE --by NAME --reason WHY`; the note moves to `capsule/withdrawn/` and is kept.

## Files

- `hearth_kit.py`: kindle, capture, fold, freshness, bank, withdraw, session claims and the fingerprint.
- `templates/`: a starter capsule and board.
- `CHECKLIST.md`: the eight conditions from the essay, each mapped to its tests.
- `DIFFERENCES_TEMPLATE.md`: when the protocol works under one agent and not another, sort every difference into setting, platform or assumption.
- `tests/test_hearth_kit.py`: 35 tests, named by condition, including the refusals: a wrong root, an empty resolve, a live lock, a stale-but-dated capsule, an agent trying to bank, an oversized capsule, a stuck claim, and the fingerprint's negative cases.

## What's proven, and what isn't

The tests prove the rules in this file hold, on the filesystem the tests run on. That's all they prove.

Untested here: many agents at once on one capsule (the lock is advisory and local), network filesystems with slow or stale reads, and any adversary. Fold is not crash-atomic: it writes the decision ledger, then the capsule, then archives the notes, so a crash between those steps can apply an `open` note twice on the next fold. Nothing stops an agent from simply not calling `capture`. That's the hard part, and no script fixes it. The kit also never deletes anything: superseded locks and folded notes are renamed and kept. On a long-lived project the archive grows, and compacting it is your job, not the kit's.

The Kingdom's Hearth adds a lot that this leaves out: a ledger replay before every commit, duties with witnesses, a compiled boot brief, a typed handoff, and packaging for more than one kind of agent. Those are stories for other pieces.

None of these ideas are new. Write-ahead notes, advisory locks, compare-against-the-record freshness and "the maker doesn't grade their own work" are old patterns. This is one practitioner's small, working version of them.

Copyright © 2026 Rob Hunter. MIT license, as in the repository `LICENSE`.
