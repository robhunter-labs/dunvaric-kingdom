"""Hearth kit tests. Run from the hearth-kit folder: python3 -m unittest discover -s tests -v

Each test names the CHECKLIST condition it holds up (C1-C8)."""
import contextlib
import io
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

HERE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import hearth_kit as hk  # noqa: E402


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        (self.tmp / "capsule").mkdir()
        shutil.copy(HERE / "templates" / "CAPSULE.json", self.tmp / "capsule" / "CAPSULE.json")
        shutil.copy(HERE / "templates" / "BOARD.md", self.tmp / "BOARD.md")
        self.h = hk.Hearth(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def set_board(self, rows, updated):
        body = [f"last_updated: {updated}", ""] + [f"- [{s}] {t}" for t, s in rows]
        (self.tmp / "BOARD.md").write_text("\n".join(body) + "\n")


class Frame(Base):
    def test_c1_kindle_reads_the_four_fields_in_order_then_freshness(self):
        lines = self.h.kindle()
        self.assertEqual([l.split(":")[0] for l in lines[:4]], list(hk.CAPSULE_FIELDS))
        self.assertTrue(lines[4].startswith("freshness: OK"))

    def test_c3_wrong_root_refuses_and_creates_nothing(self):
        empty = pathlib.Path(tempfile.mkdtemp())
        with self.assertRaises(hk.Refused):
            hk.Hearth(empty)
        self.assertEqual(list(empty.iterdir()), [])
        shutil.rmtree(empty)

    def test_c1_kindle_without_a_capsule_says_it_will_not_bank(self):
        empty = pathlib.Path(tempfile.mkdtemp())
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = hk.main(["--root", str(empty), "kindle"])
        self.assertEqual(code, 2)
        self.assertIn("this session will not bank", out.getvalue())
        self.assertEqual(list(empty.iterdir()), [])
        shutil.rmtree(empty)

    def test_c3_runs_from_any_working_directory(self):
        out = subprocess.run([sys.executable, str(HERE / "hearth_kit.py"), "--root", str(self.tmp),
                              "kindle"], cwd=tempfile.gettempdir(), capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("thesis:", out.stdout)


class Capture(Base):
    def test_c5_one_small_note(self):
        p = self.h.capture("decision", "chose X", why="because Y", rejected="Z")
        self.assertLess(p.stat().st_size, 1024)
        self.assertEqual(json.loads(p.read_text())["rejected"], "Z")

    def test_c5_decision_without_why_or_rejected_refused(self):
        with self.assertRaises(hk.Refused):
            self.h.capture("decision", "chose X", why="because Y")

    def test_empty_resolve_target_refused(self):
        with self.assertRaises(hk.Refused):
            self.h.capture("resolve", "done", target="  ")


class Fold(Base):
    def test_fold_applies_in_order_and_archives_only_what_wrote(self):
        self.h.capture("open", "Fix the index")
        self.h.capture("resolve", "closed", target="no such item")   # matches nothing
        self.h.capture("next", "Draft the first chapter")
        applied, retained = self.h.fold()
        self.assertEqual(len(applied), 2)
        self.assertEqual(len(retained), 1)                            # retained loudly, not lost
        self.assertIn("Fix the index", self.h.capsule()["open_items"])
        self.assertEqual(len(list(self.h.pending.glob("*.json"))), 1)

    def test_decision_ledger_is_idempotent(self):
        p = self.h.capture("decision", "chose X", why="Y", rejected="Z")
        atom = p.read_text()
        self.h.fold()
        (self.h.pending / "again.json").write_text(atom)              # a replayed note
        self.h.fold()
        self.assertEqual(len(self.h.ledger.read_text().splitlines()), 1)

    def test_live_lock_refuses_and_stale_lock_is_broken_but_kept(self):
        self.h.lock.write_text("123")
        with self.assertRaises(hk.Refused):
            self.h.fold()
        old = time.time() - hk.STALE_LOCK_SECONDS - 5
        os.utime(self.h.lock, (old, old))
        self.h.fold()
        self.assertTrue(list(self.h.dir.glob(".fold.lock.stale-*")))


class Freshness(Base):
    def test_c6_fresh_date_but_false_claims_is_stale(self):
        self.set_board([("Draft the first chapter", "done"), ("Outline the second chapter", "open")],
                       hk.utc_now())
        os.utime(self.h.capsule_path, None)                           # touched just now
        found = self.h.fresh()
        self.assertEqual(len(found), 1)
        self.assertIn("board says done", found[0])

    def test_c6_claim_missing_from_board_is_named(self):
        self.set_board([("Outline the second chapter", "open")], hk.utc_now())
        self.assertTrue(any("no such row" in f for f in self.h.fresh()))


class Bank(Base):
    def ready(self):
        self.h.capture("next", "Outline the second chapter")
        self.h.fold()
        self.set_board([("Draft the first chapter", "open"), ("Outline the second chapter", "open")],
                       hk.utc_now())

    def test_c7_a_named_person_banks(self):
        self.ready()
        self.assertEqual(self.h.bank("Rob")["banked_by"], "Rob")

    def test_c7_the_maker_cannot_bank(self):
        self.ready()
        for who in ("", "agent", "Claude", "codex"):
            with self.assertRaises(hk.Refused):
                self.h.bank(who)

    def test_bank_refuses_unfolded_notes(self):
        self.ready()
        self.h.capture("open", "Something new")
        with self.assertRaises(hk.Refused):
            self.h.bank("Rob")

    def test_bank_refuses_a_board_older_than_the_newest_note(self):
        self.h.capture("next", "Outline the second chapter")
        self.h.fold()
        self.set_board([("Draft the first chapter", "open"), ("Outline the second chapter", "open")],
                       "20000101T000000Z")
        with self.assertRaisesRegex(hk.Refused, "refresh the board"):
            self.h.bank("Rob")

    def test_c8_bank_refuses_an_oversized_capsule(self):
        self.ready()
        cap = self.h.capsule()
        cap["thesis"] = "x" * (hk.CAPSULE_CAP_BYTES + 1)
        self.h.write_capsule(cap)
        with self.assertRaisesRegex(hk.Refused, "compact"):
            self.h.bank("Rob")


class Sessions(Base):
    def test_c2_unclaimed_write_refused(self):
        with self.assertRaises(hk.Refused):
            self.h.write("s1", "notes.md", b"hello")

    def test_c2_claim_write_close(self):
        self.h.claim("s1", ["notes.md"])
        self.h.write("s1", "notes.md", b"hello")
        self.h.close("s1")
        with self.assertRaises(hk.Refused):                         # a closed claim can't write
            self.h.write("s1", "notes.md", b"again")

    def test_c2_overlapping_claim_refused(self):
        self.h.claim("s1", ["notes.md"])
        with self.assertRaises(hk.Refused):
            self.h.claim("s2", ["notes.md"])

    def test_c2_mismatch_keeps_claim_open_until_a_person_releases_it(self):
        self.h.claim("s1", ["notes.md"])
        self.h.write("s1", "notes.md", b"hello")
        (self.tmp / "notes.md").write_bytes(b"someone else")
        with self.assertRaises(hk.Refused):
            self.h.close("s1")
        with self.assertRaises(hk.Refused):
            self.h.release("s1", "agent", "it's fine")
        self.h.release("s1", "Rob", "checked on disk; peer edit is correct")
        self.h.claim("s2", ["notes.md"])                              # path is free again


class Fingerprint(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.f = self.tmp / "a.txt"
        self.f.write_text("same bytes")
        os.chmod(self.f, 0o644)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def fp(self, **kw):
        return hk.fingerprint(self.f, **kw)

    def test_c4_owner_only_mount_ignores_group_other_bits(self):
        before = self.fp(owner_only=True)
        os.chmod(self.f, 0o600)
        self.assertEqual(before, self.fp(owner_only=True))

    def test_c4_normal_disk_still_sees_group_other_bits(self):
        before = self.fp(owner_only=False)
        os.chmod(self.f, 0o600)
        self.assertNotEqual(before, self.fp(owner_only=False))

    def test_c4_content_edit_always_refused(self):
        before = self.fp(owner_only=True)
        self.f.write_text("other bytes")
        self.assertNotEqual(before, self.fp(owner_only=True))

    def test_c4_exec_bit_flip_always_refused(self):
        before = self.fp(owner_only=True)
        os.chmod(self.f, 0o744)
        self.assertNotEqual(before, self.fp(owner_only=True))

    def test_c4_strict_mode_never_normalizes(self):
        before = self.fp(strict=True, owner_only=True)
        os.chmod(self.f, 0o600)
        self.assertNotEqual(before, self.fp(strict=True, owner_only=True))

    def test_mount_probe_runs_and_answers(self):
        self.assertIn(hk.owner_bits_only(self.tmp), (True, False))


if __name__ == "__main__":
    unittest.main()
