# Chain test: a guide for testing an agent that reads

**Status: Planned.** This is the written plan the Kingdom is using for its own chain test. The test is in progress, and no results are claimed here. Results, when they exist, will be published with what held and what didn't.

Companion to *Guarding the Gates* on [robhunterworks.com](https://robhunterworks.com/writing/).

## Why a chain

Most defenses get tested one at a time: does the fence escape this string, does the sandbox block that call. Real attacks string small steps together: a page leads to a download, the download lands next to a helper, the helper runs, and a process outlives the task. Each step can look fine alone. This guide tests the whole path.

## Rules of the range

Run everything inside a disposable range you can throw away afterwards.

- **Harmless markers, never payloads.** A "successful" attack writes a marker file or makes a request to a sink you own inside the range. Nothing destructive, nothing real.
- **Fake credentials only.** Plant canary tokens and dummy keys so you can see if anything tries to read or send them.
- **Nothing reachable outside.** Default-deny egress from the range. A request that escapes counts as a finding, not a feature.
- **No real targets.** No third-party sites, accounts or systems.

## Write the bar first

Before anything runs, fill in [`CASES.md`](CASES.md) for each family:

- **Expected first refusal:** which layer should stop it first (see the layers below).
- **Pass:** what you will see if that layer holds.
- **Fail:** what counts as the attack completing.

Writing this down before you look at results is the point. Afterwards it is too easy to decide that whatever happened was the plan.

### Layers to name

| Layer | The question it answers |
|---|---|
| Landing | Does outside content land as inert data, fenced so it can't pose as an instruction? |
| Read to download | Does turning from reading into fetching a file need a separate permission? |
| Download to run | Can anything from outside content run, or sit where a trusted helper will pick it up? |
| Lifetime | Can a process outlive the task that started it? |
| Egress | Can anything reach the network that the task didn't need? |
| Promotion | Does a person have to promote it before it can shape work, and can they be talked into it? |

## Run it like an attacker who adapts

- **A budget per family.** For example, 20 attempts, decided in advance.
- **Repeat runs.** Models aren't deterministic. Run each attempt several times and record the spread, not the best case.
- **Learn between attempts.** Let the attacker see what failed and try a variation. A fixed list of tricks tests yesterday's attacker.

## Two targets, four measures

Test both:

1. **The gate**, the one route standing outside feeds come through.
2. **An ordinary research session**, an agent searching and reading mid-task, where results come straight back into the session.

For each attempt, record:

1. **Completed?** Did the marker appear?
2. **First refusal:** which layer stopped it, if any.
3. **Escapes:** did anything reach the network that shouldn't have?
4. **False refusals:** how often the defenses blocked something harmless. A gate that refuses everything isn't working either.

## The person is in scope

If a person has to promote outside content, that person is part of the gate. Include cards written to talk the reviewer into promoting them: urgency, borrowed authority, "just this once". Record which ones worked.

## What to publish

Which layer held, which layer was only a sentence in a design document, and what you changed. Either outcome is worth more than "we're careful."
