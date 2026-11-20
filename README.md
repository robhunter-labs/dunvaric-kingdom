# The Dunvaric Kingdom: the public shelf

The Dunvaric Kingdom is the system I use to direct sustained work with AI agents across unlike projects. Each project is a house with its own authority; the houses share a set of crafts; and a person decides. I built it to stop being the memory, the router, and the quality check for every project at once. The system itself is private. This repository is its public shelf, organized by the nine shared crafts.

## Start here

Three things on this shelf can be opened today:

| Start with | What it delivers | Evidence |
|---|---|---|
| **[Hearth kit](crafts/01-remembering/hearth-kit/)** | Picks a project up where the last AI session left off. Each decision records why it was made and what was rejected, or the next session argues it all over again. | Checked on the included synthetic fixtures; its own tests pass |
| **[Bellows](crafts/03-sensing/bellows/)** | Matches outside content against questions written in advance and quarantines anything that lands as data, so it can't become an instruction. Only a person can promote it (a self-declared name; agent names are refused). | Checked on the included synthetic fixtures; its own tests pass |
| **[Chain-test guide](crafts/06-testing/chain-test/)** | The written plan for testing an agent that reads, step by step | Documented plan; no results are claimed |

Each piece says plainly what it doesn't solve. The hardest limit is in the Hearth kit: nothing stops an agent from simply not writing things down, and no script fixes that.

For the story and the map, start with [*Welcome to the Kingdom*](https://robhunterworks.com/writing/welcome-to-the-kingdom/).

## The nine crafts

The labels mean the same thing on every shelf: **Observed** (it happened, and the record is here), **Checked on the included synthetic fixtures** (the code runs and passes its own tests, but hasn't been run against a real system), **Documented plan** (written down and in use, with no results claimed), and **Planned** (not done).

| # | Craft | What it is | On the shelf |
|---|---|---|---|
| 01 | [Remembering](crafts/01-remembering/) | waking a project up where it left off | Hearth kit |
| 03 | [Sensing](crafts/03-sensing/) | standing questions matched against outside content | Bellows |
| 06 | [Testing](crafts/06-testing/) | the bar written first, checked by someone else | Chain-test guide |
| 08 | [Defending](crafts/08-defending/) | outside content as data, never instruction | Planned; Bellows covers part |

Planned, with nothing on the shelf yet: [02 Talking](crafts/02-talking/) (messages between houses, with receipts), [04 Designing](crafts/04-designing/) (questioning the premise before building), [05 Building](crafts/05-building/) (builds that may stop, return, or split), [07 Shipping safely](crafts/07-shipping-safely/) (exact releases, and proof of what actually arrived) and [09 Speaking](crafts/09-speaking/) (private work turned into honest public writing).

## What's here, and what isn't

The two tools on this shelf are small, standalone rewrites of working pieces, each with its own tests, using only Python's standard library (Python 3.9 or newer). The chain-test guide is a written plan, not code. None of it is the private system itself, and none of it reaches a network, an account, or a real target.

If you're doing ambitious work with agents and you've felt yourself becoming the memory, the router, and the quality check, I hope some of this is useful. I don't think I've found the answer. I've found an approach that let me keep going, and I'd like to compare notes: open an issue on this repository or write to hello@robhunterworks.com.

Copyright © 2026 Rob Hunter. Original code is released under the MIT license in `LICENSE`.
