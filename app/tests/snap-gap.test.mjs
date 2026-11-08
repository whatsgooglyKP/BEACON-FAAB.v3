import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { JSDOM } from "jsdom";
import { briefHTML } from "../src/domain.js";
import { communityFlyer } from "../src/desk.js";
const root = new URL("../", import.meta.url);
const exists = fs.existsSync(new URL("src/snapGap.js", root));
test("SNAP enrollment gap view model is implemented", () =>
  assert.ok(exists, "SNAP section missing"));
if (exists) {
  const { snapGapView, snapGapBriefHTML } = await import("../src/snapGap.js");
  const { tracts } = JSON.parse(
    fs.readFileSync(new URL("public/data/tracts.json", root)),
  );
  const { rows, metadata } = JSON.parse(
    fs.readFileSync(new URL("public/data/snap_gap.json", root)),
  );
  test("separate snapshot joins 490 string GEOIDs; Apopka uses real held-out estimates", () => {
    assert.equal(rows.length, 490);
    assert.equal(new Set(rows.map((r) => r.geoid)).size, 490);
    const g = rows.find((r) => r.geoid === "12095017703");
    const v = snapGapView(g);
    assert.equal(g.actual_pct, 21.5);
    assert.ok(Math.abs(g.gap_pp - (g.actual_pct - g.expected_pct)) < 1e-8);
    assert.equal(v.drivers.length, 3);
    assert.match(v.caveat, /not eligibility/);
    assert.match(v.method, /held-out/);
    assert.ok(metadata.cv_mae_pp < metadata.baseline_mae_pp);
    assert.equal(
      tracts[0].snap_gap,
      undefined,
      "audited tract snapshot not rewritten",
    );
  });
  test("decision brief includes SNAP section, caveat, drivers and escaped values", () => {
    const t = tracts.find((t) => t.geoid === "12095017703");
    const gap = structuredClone(rows.find((r) => r.geoid === t.geoid));
    gap.reason = "<script>unsafe</script>";
    const html = briefHTML({ ...t, snap_gap: gap });
    assert.match(html, /SNAP sign-ups/);
    assert.match(html, /Expected/);
    assert.match(html, /Actual/);
    assert.match(html, /21.5%/);
    assert.match(html, /not eligibility/);
    assert.match(html, /held-out/);
    assert.ok(html.includes("&lt;script&gt;"));
    assert.ok(!html.includes("<script>unsafe"));
  });
  test("Apopka default uses plain counts, purpose, one reason and a caution", () => {
    const g = rows.find((r) => r.geoid === "12095017703");
    const t = tracts.find((t) => t.geoid === g.geoid);
    const v = snapGapView(g, t);
    assert.equal(v.badge, "Fewer sign-ups than expected");
    assert.equal(
      v.sentence,
      "About 22 in 100 households here get SNAP. Similar neighborhoods usually have about 36 in 100.",
    );
    assert.equal(
      v.why,
      "Some eligible families may not be signed up. A SNAP sign-up event here could help.",
    );
    assert.equal(v.mainReason, "High poverty for this area");
    assert.equal(
      v.caution,
      "This is an estimate to check with local partners, not proof.",
    );
    assert.doesNotMatch(
      [v.badge, v.sentence, v.why, v.mainReason, v.caution].join(" "),
      /\b(pp|MOE|CV|ridge|held-out|fold|association)\b/i,
    );
  });
  test("all uncertain rows stay uncertain in plain badges; missing values are never zero", () => {
    for (const g of rows) {
      const v = snapGapView(g);
      if (g.label === "uncertain")
        assert.equal(v.badge, "Not enough data to say");
      if (g.label === "unavailable") {
        assert.equal(v.badge, "Unavailable");
        assert.doesNotMatch(v.sentence, /about 0 in 100/i);
      }
      assert.doesNotMatch(
        [v.badge, v.sentence, v.why, v.mainReason, v.caution].join(" "),
        /\b(pp|MOE|CV|ridge|held-out|fold|association)\b/i,
      );
    }
  });
  test("University-area caution remains plain and does not claim students qualify", () => {
    const g = rows.find((r) => r.geoid === "12095016510");
    const t = tracts.find((t) => t.geoid === g.geoid);
    const v = snapGapView(g, t);
    assert.match(v.areaCaution, /student benefit rules/i);
    assert.match(v.areaCaution, /Check who qualifies/);
    assert.equal(
      snapGapView(
        rows.find((r) => r.geoid === "12095017703"),
        tracts.find((t) => t.geoid === "12095017703"),
      ).areaCaution,
      "",
    );
  });
  test("brief hides all technical detail inside a closed How we got this section", () => {
    const g = rows.find((r) => r.geoid === "12095017703");
    const t = tracts.find((t) => t.geoid === g.geoid);
    const html = snapGapBriefHTML(g, t);
    const document = new JSDOM(html).window.document;
    const details = document.querySelector("details");
    assert.ok(details);
    assert.equal(details.hasAttribute("open"), false);
    assert.equal(
      details.querySelector("summary").textContent,
      "How we got this",
    );
    for (const pattern of [
      /21.5%/,
      /35.5%/,
      /7.5/,
      /-14.0/,
      /ridge/,
      /Five-fold/,
      /MOE/,
      /CV/,
      /association/,
      /01\/2020/,
      /not eligibility/,
      /not propagated/,
    ])
      assert.match(details.textContent, pattern);
    document.querySelector(".snap-gap-technical").remove();
    assert.match(document.body.textContent, /About 22 in 100/);
    assert.doesNotMatch(
      document.body.textContent,
      /\b(pp|MOE|CV|ridge|held-out|fold|association)\b/i,
    );
  });
  test("resident flyer never contains SNAP predictions or internal gap section", () => {
    const t = {
      ...tracts.find((t) => t.geoid === "12095017703"),
      snap_gap: rows[0],
    };
    const { html, text } = communityFlyer(t);
    assert.ok(!html.includes("SNAP enrollment gap"));
    assert.ok(!html.includes("expected participation"));
    assert.ok(!text.includes("likely under-enrolled"));
  });
  test("missing model rows are explicit and never rendered as zero predictions", () => {
    const v = snapGapView(undefined);
    assert.equal(v.label, "unavailable");
    assert.match(snapGapBriefHTML(undefined), /Unavailable/);
    assert.ok(!snapGapBriefHTML(undefined).includes("0.0%"));
    const unavailable = rows.find((r) => r.label === "unavailable");
    assert.equal(snapGapView(unavailable).expected, "Not available");
  });
}
