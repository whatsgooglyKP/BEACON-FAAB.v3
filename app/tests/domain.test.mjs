import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
const exists = fs.existsSync(new URL("../src/domain.js", import.meta.url));
test("approved domain model exists", () =>
  assert.ok(exists, "screening/review/export model is not implemented"));
if (exists) {
  const m = await import("../src/domain.js");
  const { tracts } = JSON.parse(
    fs.readFileSync(new URL("../public/data/tracts.json", import.meta.url)),
  );
  test("real baseline has 490 tracts and 68 default candidates", () => {
    assert.equal(tracts.length, 490);
    assert.equal(m.candidates(tracts, "sd", false).length, 68);
  });
  test("conservative mode uses poverty lower90 and retains 7 SD candidates", () =>
    assert.equal(m.candidates(tracts, "sd", true).length, 7));
  test("distance selection uses actual corresponding LILA fields", () => {
    const expected = tracts.filter(
      (x) => x.lila_dd_half_10 === 1 && x.poverty_pct >= 17.025,
    );
    assert.equal(m.candidates(tracts, "dd", false).length, expected.length);
  });
  test("Apopka evidence is exact and sample size is not invented", () => {
    const t = tracts.find((x) => x.geoid === "12095017703");
    assert.equal(t.poverty_pct, 43.7);
    assert.equal(t.poverty_moe_pp, 11.4);
    assert.equal(t.actual_sample_size, "Not provided");
    assert.equal(t.lila_sd_half_10, 1);
    assert.equal(t.lila_dd_half_10, 1);
  });
  test("two reviewers disagree without last-write-wins resolution", () => {
    const events = [
      {
        id: "a",
        geoid: "g",
        reviewer: "Organizer",
        kind: "decision",
        decision: "approve",
      },
      {
        id: "b",
        geoid: "g",
        reviewer: "Field reviewer",
        kind: "decision",
        decision: "reject",
      },
    ];
    assert.equal(m.reviewSummary(events, "g").conflict, true);
    assert.equal(m.reviewSummary(events, "g").decisions.length, 2);
  });
  test("same reviewer may revise their own decision while audit is retained", () => {
    const events = [
      { geoid: "g", reviewer: "A", kind: "decision", decision: "reject" },
      { geoid: "g", reviewer: "A", kind: "decision", decision: "approve" },
    ];
    const s = m.reviewSummary(events, "g");
    assert.equal(s.conflict, false);
    assert.equal(s.decisions[0].decision, "approve");
    assert.equal(events.length, 2);
  });
  test("sample briefs are explicitly not operational decisions", () => {
    const t = tracts.find((x) => x.geoid === "12095017703");
    assert.ok(
      m
        .briefHTML(t, { events: [], order: [] }, "sd", false, { demo: true })
        .includes("SAMPLE DEMONSTRATION — not an operational decision"),
    );
  });
  test("manual rank is separate from scientific evidence score", () => {
    const rows = m.candidates(tracts, "sd", false);
    const id = rows[3].geoid;
    const sorted = m.orderCandidates(rows, [id]);
    assert.equal(sorted[0].geoid, id);
    assert.equal(sorted[0].poverty_pct, rows[3].poverty_pct);
  });
  test("brief escapes notes, retains sources, and labels observations as unverified", () => {
    const t = tracts.find((x) => x.geoid === "12095017703");
    const events = [
      {
        id: "n",
        geoid: t.geoid,
        kind: "note",
        reviewer: "Organizer",
        text: "<script>alert(1)</script>",
        at: 0,
      },
    ];
    const html = m.briefHTML(t, { events, order: [] }, "sd", false);
    assert.ok(html.includes("43.7%"));
    assert.ok(html.includes("11.4"));
    assert.ok(html.includes("&lt;script&gt;"));
    assert.ok(!html.includes("<script>alert"));
    assert.ok(html.includes("Unverified"));
    assert.ok(html.includes("SNAP-authorized"));
    assert.ok(html.includes("@page"));
  });
}
