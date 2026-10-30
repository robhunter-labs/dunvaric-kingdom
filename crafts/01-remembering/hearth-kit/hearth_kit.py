#!/usr/bin/env python3
"""Hearth kit: a small, runnable pattern for keeping an AI project's memory between sessions.

This is a teaching rewrite, not the Kingdom's own Hearth. It keeps the shape and drops the rest:

  kindle   read the frame first: the capsule's four shared fields, then a freshness verdict
  capture  one typed note the moment a decision happens (cheap, or it won't happen)
  fold     apply pending notes to the capsule, in order, under a lock
  bank     a person closes the milestone: everything folded, board current, capsule true and small

Plus two helpers the essay leans on: session claims (claim before you write, refuse to close
on a mismatch, a person releases a stuck claim) and a file fingerprint that knows which
filesystem it is standing on.

Layout under --root (default "."):  capsule/CAPSULE.json   the capsule (must already exist)
                                     capsule/pending/       captured, not yet folded
                                     capsule/applied/       folded notes, kept, never deleted
                                     capsule/DECISIONS.jsonl, capsule/sessions/, BOARD.md
Standard library only.
"""
import argparse
import hashlib
import json
import os
import pathlib
import stat
import sys
import tempfile
import time
import uuid

KINDS = ("decision", "open", "resolve", "next")
CAPSULE_FIELDS = ("thesis", "the_governing_gate", "open_items", "next")
CAPSULE_CAP_BYTES = 16 * 1024
STALE_LOCK_SECONDS = 600
NOT_A_PERSON = {"agent", "assistant", "bot", "model", "claude", "chatgpt", "codex", "auto"}


class Refused(Exception):
    """A rule said no. The message says which rule and how to fix it."""


def utc_now():
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


class Hearth:
    def __init__(self, root="."):
        self.root = pathlib.Path(root)
        self.dir = self.root / "capsule"
        self.capsule_path = self.dir / "CAPSULE.json"
        if not self.capsule_path.is_file():
            # Refuse-to-create: a wrong root must fail loudly, never mint a phantom capsule.
            raise Refused(f"no capsule at {self.capsule_path}; copy templates/CAPSULE.json there "
                          "or pass the right --root. Nothing was written.")
        self.pending, self.applied = self.dir / "pending", self.dir / "applied"
        self.ledger, self.sessions = self.dir / "DECISIONS.jsonl", self.dir / "sessions"
        self.lock, self.board = self.dir / ".fold.lock", self.root / "BOARD.md"

    def capsule(self):
        return json.loads(self.capsule_path.read_text())

    def write_capsule(self, cap):
        tmp = self.capsule_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(cap, indent=2) + "\n")
        os.replace(tmp, self.capsule_path)

    # ---- kindle -----------------------------------------------------------------------------
    def kindle(self):
        cap = self.capsule()
        lines = [f"{f}: {json.dumps(cap.get(f))}" for f in CAPSULE_FIELDS]
        findings = self.fresh()
        lines.append("freshness: OK (claims match the board)" if not findings
                     else "freshness: STALE: " + "; ".join(findings))
        waiting = sorted(self.pending.glob("*.json")) if self.pending.is_dir() else []
        if waiting:
            lines.append(f"pending: {len(waiting)} captured note(s) not yet folded")
        return lines

    # ---- capture ----------------------------------------------------------------------------
    def capture(self, kind, text, why="", rejected="", target=""):
        if kind not in KINDS:
            raise Refused(f"unknown kind {kind!r}; use one of {KINDS}")
        if not text.strip():
            raise Refused("a note needs text")
        if kind == "decision" and not (why.strip() and rejected.strip()):
            raise Refused("a decision needs --why and --rejected, or the next session re-argues it")
        if kind == "resolve" and not target.strip():
            raise Refused("resolve needs a non-empty --target (an empty one would match everything)")
        atom = {"id": uuid.uuid4().hex[:12], "kind": kind, "ts": utc_now(), "text": text}
        for k, v in (("why", why), ("rejected", rejected), ("target", target)):
            if v:
                atom[k] = v
        self.pending.mkdir(exist_ok=True)
        path = self.pending / f"{atom['ts']}-{atom['id']}.json"
        path.write_text(json.dumps(atom, sort_keys=True) + "\n")
        return path

    # ---- fold -------------------------------------------------------------------------------
    def _take_lock(self):
        try:
            fd = os.open(self.lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            age = time.time() - self.lock.stat().st_mtime
            if age < STALE_LOCK_SECONDS:
                raise Refused(f"another fold holds the lock ({int(age)}s old); try again shortly")
            os.replace(self.lock, self.dir / f".fold.lock.stale-{utc_now()}")  # kept, not erased
            fd = os.open(self.lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)

    def _apply(self, cap, atom):
        """Return True only if the atom actually wrote something. Archive keys on that."""
        kind = atom.get("kind")
        if kind == "decision":
            seen = set()
            if self.ledger.exists():
                seen = {json.loads(l)["id"] for l in self.ledger.read_text().splitlines() if l}
            if atom["id"] not in seen:
                with self.ledger.open("a") as fh:
                    fh.write(json.dumps(atom, sort_keys=True) + "\n")
            return True
        if kind == "open":
            cap.setdefault("open_items", []).append(atom["text"])
            return True
        if kind == "resolve":
            before = list(cap.get("open_items", []))
            cap["open_items"] = [i for i in before if atom["target"] not in i]
            return len(cap["open_items"]) < len(before)   # matched nothing -> retained, loudly
        if kind == "next":
            cap["next"] = atom["text"]
            return True
        return False

    def fold(self):
        self._take_lock()
        try:
            cap, applied, retained = self.capsule(), [], []
            for path in sorted(self.pending.glob("*.json")) if self.pending.is_dir() else []:
                atom = json.loads(path.read_text())
                (applied if self._apply(cap, atom) else retained).append((path, atom))
            if applied:
                cap["last_folded_atom"] = max(a["ts"] for _, a in applied)
                self.write_capsule(cap)
                self.applied.mkdir(exist_ok=True)
                for path, _ in applied:
                    os.replace(path, self.applied / path.name)
            return [p.name for p, _ in applied], [p.name for p, _ in retained]
        finally:
            os.replace(self.lock, self.dir / ".fold.lock.released") if self.lock.exists() else None

    # ---- freshness: claims against the board, never the clock -------------------------------
    def board_items(self):
        """BOARD.md lines like '- [done] item' or '- [open] item', plus 'last_updated: <ts>'."""
        items, updated = {}, ""
        if self.board.exists():
            for line in self.board.read_text().splitlines():
                line = line.strip()
                if line.startswith("last_updated:"):
                    updated = line.split(":", 1)[1].strip()
                elif line.startswith("- [") and "]" in line:
                    state, text = line[3:].split("]", 1)
                    items[text.strip()] = state.strip().lower()
        return items, updated

    def fresh(self):
        cap, (items, _) = self.capsule(), self.board_items()
        claimed = list(cap.get("open_items", [])) + ([cap["next"]] if cap.get("next") else [])
        findings = []
        for claim in claimed:
            state = next((s for t, s in items.items() if t == claim), None)
            if state == "done":
                findings.append(f"capsule still claims {claim!r}, the board says done")
            elif state is None:
                findings.append(f"capsule claims {claim!r}, the board has no such row")
        return findings

    # ---- bank: a person closes the milestone -------------------------------------------------
    def bank(self, by, note=""):
        if not by.strip() or by.strip().lower() in NOT_A_PERSON:
            raise Refused("bank is a person's act. The maker doesn't get to be the judge.")
        if self.pending.is_dir() and any(self.pending.glob("*.json")):
            raise Refused("unfolded notes are waiting; run fold first")
        cap, (_, board_updated) = self.capsule(), self.board_items()
        newest = cap.get("last_folded_atom", "")
        if newest and (not board_updated or board_updated < newest):
            raise Refused(f"the board was last updated {board_updated or 'never'}, before the newest "
                          f"folded note ({newest}); refresh the board in this bank")
        findings = self.fresh()
        if findings:
            raise Refused("the capsule doesn't tell the truth yet: " + "; ".join(findings))
        cap["freshness"] = {"last_banked": utc_now(), "banked_by": by.strip(), "note": note}
        if len(json.dumps(cap, indent=2).encode()) > CAPSULE_CAP_BYTES:
            raise Refused(f"capsule would exceed {CAPSULE_CAP_BYTES} bytes; compact it first")
        self.write_capsule(cap)
        return cap["freshness"]

    # ---- session claims ---------------------------------------------------------------------
    def _open_claims(self):
        if not self.sessions.is_dir():
            return {}
        out = {}
        for p in self.sessions.glob("*.json"):
            c = json.loads(p.read_text())
            if c["state"] == "open":
                out[c["sid"]] = c
        return out

    def _save_claim(self, c):
        self.sessions.mkdir(exist_ok=True)
        (self.sessions / f"{c['sid']}.json").write_text(json.dumps(c, indent=2) + "\n")

    def claim(self, sid, paths):
        for other in self._open_claims().values():
            clash = set(other["paths"]) & set(paths)
            if clash and other["sid"] != sid:
                raise Refused(f"{sorted(clash)} already claimed by session {other['sid']}")
        self._save_claim({"sid": sid, "state": "open", "paths": sorted(paths), "expected": {}})

    def write(self, sid, rel, data: bytes):
        c = self._open_claims().get(sid)
        if not c or rel not in c["paths"]:
            raise Refused(f"{rel} isn't claimed by session {sid}; claim before you write")
        target = self.root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        c["expected"][rel] = fingerprint(target)
        self._save_claim(c)

    def close(self, sid):
        c = self._open_claims().get(sid)
        if not c:
            raise Refused(f"no open session {sid}")
        bad = [r for r, fp in c["expected"].items() if fingerprint(self.root / r) != fp]
        if bad:
            raise Refused(f"{bad} changed after this session wrote them; claim stays open for a person")
        c["state"] = "closed"
        self._save_claim(c)

    def release(self, sid, by, reason):
        if not by.strip() or by.strip().lower() in NOT_A_PERSON or not reason.strip():
            raise Refused("releasing a stuck claim takes a named person and a reason")
        c = self._open_claims().get(sid)
        if not c:
            raise Refused(f"no open session {sid}")
        c.update(state="released", released_by=by, reason=reason, at=utc_now())
        self._save_claim(c)


# ---- fingerprints that know which filesystem they're on ------------------------------------
def owner_bits_only(directory):
    """True if this filesystem drops group/other permission bits (some synced or bridged mounts)."""
    fd, probe = tempfile.mkstemp(dir=directory, prefix=".fp-probe-")
    os.close(fd)
    try:
        os.chmod(probe, 0o644)
        return stat.S_IMODE(os.stat(probe).st_mode) & 0o077 == 0
    finally:
        try:
            os.unlink(probe)
        except OSError:
            pass   # some mounts refuse removal; a leftover probe is harmless and hidden


def fingerprint(path, strict=False, owner_only=None):
    """sha256 of content + file type + mode. On an owner-bits-only mount (and only there, and
    never in strict mode) the mode is reduced to the executable bit, so a byte-identical file
    doesn't look changed just because the mount rewrote group/other bits."""
    path = pathlib.Path(path)
    st = os.lstat(path)
    kind = "link" if stat.S_ISLNK(st.st_mode) else "file" if stat.S_ISREG(st.st_mode) else "other"
    mode = stat.S_IMODE(st.st_mode)
    if not strict:
        if owner_only is None:
            owner_only = owner_bits_only(path.parent)
        if owner_only:
            mode = mode & stat.S_IXUSR
    body = os.readlink(path).encode() if kind == "link" else path.read_bytes()
    h = hashlib.sha256(body)
    h.update(f"|{kind}|{mode:o}".encode())
    return h.hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=".")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("kindle")
    c = sub.add_parser("capture")
    c.add_argument("kind", choices=KINDS)
    c.add_argument("text")
    for flag in ("--why", "--rejected", "--target"):
        c.add_argument(flag, default="")
    sub.add_parser("fold")
    sub.add_parser("fresh")
    b = sub.add_parser("bank")
    b.add_argument("--by", required=True)
    b.add_argument("--note", default="")
    args = ap.parse_args(argv)
    try:
        h = Hearth(args.root)
        if args.cmd == "kindle":
            print("\n".join(h.kindle()))
        elif args.cmd == "capture":
            print(h.capture(args.kind, args.text, args.why, args.rejected, args.target).name)
        elif args.cmd == "fold":
            applied, retained = h.fold()
            print(f"applied {len(applied)}, retained {len(retained)}: {retained}")
        elif args.cmd == "fresh":
            found = h.fresh()
            print("\n".join(found) if found else "OK: the capsule's claims match the board")
            return 1 if found else 0
        elif args.cmd == "bank":
            print(json.dumps(h.bank(args.by, args.note)))
    except Refused as why:
        if args.cmd == "kindle" and "no capsule at" in str(why):
            # Say it out loud: a session that can't reach its memory must not look like one that can.
            print("this session will not bank: no capsule here, so nothing will be captured, folded "
                  "or banked, and no receipt is written. Pass the right --root to remember.")
        print(f"refused: {why}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
