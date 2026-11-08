import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
const file = new URL("../src/desk.js", import.meta.url);
test("v2 deterministic desk module exists", () =>
  assert.ok(fs.existsSync(file), "Ask the Desk is not implemented"));
if (fs.existsSync(file)) {
  const m = await import("../src/desk.js");
  const { tracts } = JSON.parse(
    fs.readFileSync(new URL("../public/data/tracts.json", import.meta.url)),
  );
  const selected = tracts.find((t) => t.geoid === "12095017703");
  test("Ask explains exact short tract ID and uncertainty with sources", () => {
    const a = m.answerDesk("Why was 17703 flagged?", {
      tracts,
      selected,
      distance: "sd",
    });
    assert.ok(a.text.includes("43.7%"));
    assert.ok(a.text.includes("11.4"));
    assert.ok(a.text.includes("12095017703"));
    assert.ok(a.sources.length);
    assert.ok(a.limitations.includes("sample size"));
  });
  test("Ask lists every eligible Apopka tract and current lens", () => {
    const a = m.answerDesk("Which Apopka tracts are flagged?", {
      tracts,
      selected,
      distance: "sd",
    });
    assert.ok(a.rows.length >= 2);
    assert.ok(a.rows.some((t) => t.geoid === selected.geoid));
    assert.ok(
      a.rows.every(
        (t) =>
          t.place_name === "Apopka" &&
          t.lila_sd_half_10 === 1 &&
          t.poverty_pct >= 17.025,
      ),
    );
    assert.ok(a.text.includes("straight-line"));
    assert.ok(a.sources.length);
  });
  test("Ask missing information never invents transportation or pantry capacity", () => {
    const a = m.answerDesk("What information are you missing for this tract?", {
      tracts,
      selected,
    });
    for (const word of ["transportation", "capacity", "sample size"])
      assert.ok(a.text.includes(word));
  });
  test("Ask resource lookup links official finder and never supplies warehouse or fictional pantry", () => {
    const a = m.answerDesk("What resources exist near me?", {
      tracts,
      selected,
    });
    assert.ok(
      a.sources.some(
        (s) => s.url === "https://feedhopenow.org/find-help/food-finder/",
      ),
    );
    assert.ok(a.text.includes("call ahead"));
    assert.ok(a.text.includes("not a pantry"));
    assert.ok(!a.text.includes("411 Mercy"));
    assert.ok(!a.text.includes("church on Main"));
  });
  test("Ask returns explicit unsupported/unknown geography responses", () => {
    assert.ok(
      m
        .answerDesk("What will stock prices do?", { tracts, selected })
        .text.includes("supported"),
    );
    assert.ok(
      m
        .answerDesk("Why was 99999 flagged?", { tracts, selected })
        .text.includes("not found"),
    );
  });
}

{
  const m = await import("../src/desk.js");
  const { tracts } = JSON.parse(
    fs.readFileSync(new URL("../public/data/tracts.json", import.meta.url)),
  );
  const d = await import("../src/domain.js");
  const source = "12095017703",
    target = "12095017600";
  test("replacement requires valid different IDs and a reason, preserves baseline and records overrides", () => {
    assert.equal(
      typeof m.replacementEvent,
      "function",
      "Traceable replacement is missing",
    );
    const context = { tracts, events: [] };
    assert.throws(
      () => m.replacementEvent(source, target, " ", context),
      /reason/i,
    );
    assert.throws(
      () => m.replacementEvent(source, source, "test", context),
      /different/i,
    );
    assert.throws(
      () => m.replacementEvent(source, "99999999999", "test", context),
      /not found/i,
    );
    const before = JSON.stringify(tracts),
      e = m.replacementEvent(source, target, "Validate adjacent area", context);
    assert.equal(e.kind, "replacement");
    assert.equal(e.geoid, source);
    assert.equal(e.targetGeoid, target);
    const rows = m.applyReplacements(d.candidates(tracts), tracts, [e]);
    assert.equal(rows[0].geoid, target);
    assert.ok(!rows.some((t) => t.geoid === source));
    assert.equal(new Set(rows.map((t) => t.geoid)).size, rows.length);
    assert.equal(JSON.stringify(tracts), before);
    assert.throws(
      () =>
        m.replacementEvent(target, source, "reverse", { tracts, events: [e] }),
      /cycle/i,
    );
    const outside = tracts.find(
      (t) => t.poverty_pct != null && t.poverty_pct < 17.025,
    );
    assert.equal(
      m.replacementEvent(
        source,
        outside.geoid,
        "Local context overrides screen",
        context,
      ).manualOverride,
      true,
    );
  });
  test("need hypothesis votes require reasons, remain separate from visit decisions and surface disagreement", () => {
    assert.equal(
      typeof m.needVote,
      "function",
      "Independent need feedback is missing",
    );
    assert.throws(() => m.needVote("confirm", ""), /reason/i);
    assert.throws(() => m.needVote("unknown", "test"), /choice/i);
    const events = [
      {
        ...m.needVote("confirm", "Screening evidence supports investigation"),
        geoid: source,
        reviewer: "Organizer",
      },
      {
        ...m.needVote("challenge", "Check current services first"),
        geoid: source,
        reviewer: "Field reviewer",
      },
    ];
    assert.equal(m.needSummary(events, source).conflict, true);
    assert.equal(d.reviewSummary(events, source).decision, "unreviewed");
    events.push({
      ...m.needVote("challenge", "Revised after review"),
      geoid: source,
      reviewer: "Organizer",
    });
    assert.equal(m.needSummary(events, source).conflict, false);
    assert.equal(events.length, 3);
  });
}

{
  const d = await import("../src/domain.js");
  const geoid = "12095017703";
  test("observation edits and deactivation retain immutable history and remove withdrawn text from current brief", () => {
    assert.equal(
      typeof d.observationChange,
      "function",
      "Observation amendment is missing",
    );
    const events = [
      {
        id: "n1",
        kind: "note",
        geoid,
        reviewer: "Organizer",
        text: "Original private input",
        at: 0,
      },
    ];
    const context = {
      events,
      geoid,
      reviewer: "Organizer",
      reason: "Corrected after discussion",
      text: "Corrected unverified observation",
    };
    assert.throws(
      () => d.observationChange("edit", "n1", { ...context, reason: "" }),
      /reason/i,
    );
    assert.throws(
      () =>
        d.observationChange("edit", "n1", {
          ...context,
          reviewer: "Field reviewer",
        }),
      /own/i,
    );
    const edit = {
      ...d.observationChange("edit", "n1", context),
      id: "e1",
      geoid,
      reviewer: "Organizer",
      at: 1,
    };
    events.push(edit);
    assert.equal(
      d.reviewSummary(events, geoid).notes[0].text,
      "Corrected unverified observation",
    );
    assert.equal(events[0].text, "Original private input");
    const off = {
      ...d.observationChange("deactivate", "n1", { ...context, events }),
      id: "e2",
      geoid,
      reviewer: "Organizer",
      at: 2,
    };
    events.push(off);
    assert.equal(d.reviewSummary(events, geoid).notes.length, 0);
    assert.equal(events.length, 3);
    assert.throws(
      () => d.observationChange("edit", "n1", { ...context, events }),
      /inactive/i,
    );
    const { tracts } = JSON.parse(
      fs.readFileSync(new URL("../public/data/tracts.json", import.meta.url)),
    );
    const html = d.briefHTML(
      tracts.find((t) => t.geoid === geoid),
      { events, order: [] },
    );
    assert.ok(!html.includes("Original private input"));
    assert.ok(!html.includes("Corrected unverified observation"));
  });
}

{
  const m = await import("../src/desk.js");
  const { tracts } = JSON.parse(
    fs.readFileSync(new URL("../public/data/tracts.json", import.meta.url)),
  );
  const t = tracts.find((t) => t.geoid === "12095017703");
  test("community flyer has explicit placeholders, real referrals and no internal metrics or notes", () => {
    assert.equal(
      typeof m.communityFlyer,
      "function",
      "Resident-facing export is missing",
    );
    const f = m.communityFlyer(
      t,
      {},
      {
        events: [{ text: "PRIVATE INTERNAL NOTE", owner: "Volunteer Secret" }],
      },
    );
    for (const word of [
      "DRAFT",
      "PANTRY NAME",
      "DATE / TIME",
      "LOCATION",
      "call ahead",
    ])
      assert.ok(f.text.includes(word));
    assert.ok(
      f.text.includes("https://feedhopenow.org/find-help/food-finder/"),
    );
    for (const hidden of [
      "43.7",
      "11.4",
      "17.025",
      "poverty",
      "PRIVATE INTERNAL NOTE",
      "Volunteer Secret",
    ])
      assert.ok(!f.text.includes(hidden));
    assert.ok(f.html.includes("@page"));
    assert.ok(f.html.includes("organizer"));
  });
  test("community HTML safely escapes organizer fields and clearly labels them unverified", () => {
    const f = m.communityFlyer(t, {
      pantry: "<script>alert(1)</script>",
      time: "Tuesday morning",
      address: "Organizer example only",
    });
    assert.ok(f.html.includes("&lt;script&gt;"));
    assert.ok(!f.html.includes("<script>alert"));
    assert.ok(f.text.includes("not verified by this app"));
    assert.ok(f.text.includes("Tuesday morning"));
  });
}

test("an explicit GEOID in a missing-data question overrides the selected tract", async () => {
  const m = await import("../src/desk.js");
  const { tracts } = JSON.parse(
    fs.readFileSync(new URL("../public/data/tracts.json", import.meta.url)),
  );
  const selected = tracts.find((t) => t.geoid === "12095017703");
  assert.ok(
    m
      .answerDesk("What information is missing for tract 12117020901?", {
        tracts,
        selected,
      })
      .text.includes("12117020901"),
  );
});

test("missing reasons fail closed with a meaningful validation message", async () => {
  const m = await import("../src/desk.js");
  const { tracts } = JSON.parse(
    fs.readFileSync(new URL("../public/data/tracts.json", import.meta.url)),
  );
  assert.throws(() => m.needVote("confirm", undefined), /reason/i);
  assert.throws(
    () =>
      m.replacementEvent("12095017703", "12095017600", undefined, { tracts }),
    /reason/i,
  );
});

test("decision brief surfaces need-hypothesis disagreement rather than hiding it behind visit approval", async () => {
  const d = await import("../src/domain.js");
  const { tracts } = JSON.parse(
    fs.readFileSync(new URL("../public/data/tracts.json", import.meta.url)),
  );
  const t = tracts.find((t) => t.geoid === "12095017703");
  const events = [
    {
      id: "a",
      geoid: t.geoid,
      kind: "decision",
      reviewer: "Organizer",
      decision: "approve",
      reason: "Verify first",
    },
    {
      id: "b",
      geoid: t.geoid,
      kind: "need",
      reviewer: "Organizer",
      choice: "confirm",
      reason: "Evidence supports investigation",
    },
    {
      id: "c",
      geoid: t.geoid,
      kind: "need",
      reviewer: "Field reviewer",
      choice: "challenge",
      reason: "Current service coverage unknown",
    },
  ];
  const html = d.briefHTML(t, { events, order: [] });
  assert.ok(html.includes("DISAGREEMENT"));
  assert.ok(html.includes("Current service coverage unknown"));
});
