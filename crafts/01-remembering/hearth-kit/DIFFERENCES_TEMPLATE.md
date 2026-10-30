# When it works on one agent and not another

Use this when the same memory protocol behaves differently under two agents or two run modes (for example, a cloud task and a local one). Freeze one copy of the code, run the same checks under each, and write down every difference. Then sort each one into a bin.

| What you observed | Agent / mode A | Agent / mode B | Bin | What to do |
|---|---|---|---|---|
| Where the work runs (your machine, a cloud workspace) | | | | |
| Can the hooks see the folder the memory lives in? | | | | |
| Is the root set explicitly, or guessed from a default? | | | | |
| File permissions after a write (asked for vs. got) | | | | |
| Can a temporary file be removed? | | | | |
| Does a just-written file read back the same, right away? | | | | |
| Does a new folder show up right away? | | | | |
| Longest a single command may run | | | | |
| Which copy of the scripts actually loaded | | | | |
| Does `kindle` say "this session will not bank" when it should? | | | | |

**Bins**
- **Setting:** something you can change yourself (a run mode, an environment variable, a root file).
- **Platform:** a limit of the tool or host you can't change, so design around it.
- **Assumption:** something your own code took for granted, so fix the code.

A difference with no bin is still a hunch. The goal is a short list where every row has one.
