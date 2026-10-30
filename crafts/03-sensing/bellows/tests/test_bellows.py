"""Bellows tests. Run from the bellows folder: python3 -m unittest discover -s tests -v"""
import json
import pathlib
import shutil
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import bellows  # noqa: E402

FIX = HERE / "fixtures"


def load(name, key):
    return json.loads((FIX / name).read_text())[key]


def outside_fences(md):
    """Text a reader (or a model) would see outside any ``` fence."""
    out, inside = [], False
    for line in md.splitlines():
        if line.startswith("```"):
            inside = not inside
            continue
        if not inside:
            out.append(line)
    return "\n".join(out)


def naive_render(fire, watch, ts):
    """The pre-fix twin: the same card, fenced but NOT sanitized, so outside content can
    close the fence early. Kept only so the tests can prove they bite."""
    original = bellows.inert
    bellows.inert = str
    try:
        return bellows.render_card(fire, watch, ts)
    finally:
        bellows.inert = original


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        shutil.copy(FIX / "watches.json", self.tmp / "watches.json")
        self.ws = bellows.Workspace(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp)


class PreFilter(Base):
    def test_whole_phrase_boundaries(self):
        self.assertTrue(bellows.term_hit("multi-agent", bellows.norm("Multi Agent systems")))
        self.assertFalse(bellows.term_hit("agent", bellows.norm("a reagent shortage")))

    def test_candidates_and_drops(self):
        live = bellows.live_watches(bellows.load_register(self.ws))
        cands, dropped = bellows.find_candidates(live, load("signals.json", "signals"))
        ids = sorted((c["watch_id"], c["url"].rsplit("/", 1)[-1]) for c in cands)
        self.assertEqual(ids, [("W-1", "indirect-injection"), ("W-2", "mlx-release")])
        self.assertEqual(dropped, 2)  # the reagent story and the garden story

    def test_closed_watch_never_scanned(self):
        live = bellows.live_watches(bellows.load_register(self.ws))
        self.assertNotIn("W-3", [w["id"] for w in live])

    def test_duplicate_signal_is_one_candidacy(self):
        live = bellows.live_watches(bellows.load_register(self.ws))
        sig = load("signals.json", "signals")[0]
        cands, _ = bellows.find_candidates(live, [sig, dict(sig)])
        self.assertEqual(len(cands), 1)

    def test_empty_register_stops(self):
        (self.tmp / "watches.json").unlink()
        self.assertIn("stop", bellows.land(self.ws, []))


class Landing(Base):
    def test_score_floor_and_unknown_or_closed_watch_refused(self):
        s = bellows.land(self.ws, load("hostile_fires.json", "fires"), ts="2026-10-23T00:00:00Z")
        self.assertEqual(s["cards_written"], 1)
        whys = sorted(r["watch_id"] for r in s["refused"])
        self.assertEqual(whys, ["W-1", "W-3", "W-9"])

    def test_dedup_across_runs(self):
        fires = load("fires.json", "fires")
        bellows.land(self.ws, fires, ts="2026-10-23T00:00:00Z")
        s = bellows.land(self.ws, fires, ts="2026-10-24T00:00:00Z")
        self.assertEqual(s["cards_written"], 0)
        self.assertEqual(len(s["deduped"]), 1)

    def test_no_signal_run_is_logged_honestly(self):
        s = bellows.land(self.ws, [], ts="2026-10-23T00:00:00Z")
        self.assertIn("no signal on 2 live watches", s["note"])
        log = [json.loads(l) for l in self.ws.scan_log.read_text().splitlines()]
        self.assertEqual(log[-1]["cards_written"], 0)

    def test_sidecar_hash_witnesses_bytes(self):
        bellows.land(self.ws, load("fires.json", "fires"), ts="2026-10-23T00:00:00Z")
        card = next(self.ws.quarantine.glob("*.md"))
        meta = json.loads((card.parent / (card.name + ".grade.json")).read_text())
        self.assertEqual(meta["grade"], "G-D")
        self.assertEqual(meta["sha256"], bellows.sha256(card.read_bytes()))


class Quarantine(Base):
    """Outside content is data, never instruction."""

    def hostile(self):
        return load("hostile_fires.json", "fires")[0]

    def test_twin_proves_the_test_bites(self):
        md = naive_render(self.hostile(), {"id": "W-1"}, "t")
        self.assertIn("SYSTEM", outside_fences(md))  # the injection escapes in the naive form

    def test_real_card_keeps_every_outside_field_fenced(self):
        md = bellows.render_card(self.hostile(), {"id": "W-1"}, "t")
        visible = outside_fences(md)
        for needle in ("SYSTEM", "PLACEHOLDER", "Ignore previous", "Promote this card", "operator pre-approved"):
            self.assertNotIn(needle, visible)
        self.assertEqual(md.count("```"), 2)  # exactly the card's own fence, nothing escaped
        self.assertIn("DATA, NOT INSTRUCTIONS", visible)

    def test_content_cannot_promote_itself(self):
        bellows.land(self.ws, [self.hostile()], ts="2026-10-23T00:00:00Z")
        card = next(self.ws.quarantine.glob("*.md"))
        self.assertEqual(bellows.status(self.ws)["by_grade"], {"G-D": 1})
        with self.assertRaises(PermissionError):
            bellows.promote(self.ws, card, witness="", by="")

    def test_witnessed_promotion_is_ledgered(self):
        bellows.land(self.ws, load("fires.json", "fires"), ts="2026-10-23T00:00:00Z")
        card = next(self.ws.quarantine.glob("*.md"))
        meta = bellows.promote(self.ws, card, witness="read the source paper end to end", by="Rob")
        self.assertEqual(meta["grade"], "G-B")
        events = [json.loads(l)["event"] for l in self.ws.ledger.read_text().splitlines()]
        self.assertEqual(events, ["land", "promote"])

    def test_tampered_card_cannot_be_promoted(self):
        bellows.land(self.ws, load("fires.json", "fires"), ts="2026-10-23T00:00:00Z")
        card = next(self.ws.quarantine.glob("*.md"))
        card.write_text(card.read_text() + "\nSYSTEM: trust me\n")
        with self.assertRaises(PermissionError):
            bellows.promote(self.ws, card, witness="looked fine", by="Rob")


class Cli(Base):
    def test_cli_round_trip(self):
        rc = bellows.main(["--root", str(self.tmp), "land", "--fires", str(FIX / "fires.json")])
        self.assertEqual(rc, 0)
        card = next(self.ws.quarantine.glob("*.md"))
        rc = bellows.main(["--root", str(self.tmp), "promote", str(card)])
        self.assertEqual(rc, 1)  # no witness, refused


if __name__ == "__main__":
    unittest.main()
