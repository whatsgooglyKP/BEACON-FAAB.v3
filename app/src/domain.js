import { snapGapBriefHTML } from "./snapGap.js";
/** The ranking is transparent screening, never a prediction of unmet demand. */
export const Q75 = 17.025;
export const STORAGE_KEY = "beacon-action-desk-v1";
export const PROBLEM =
  "Food bank organizers must decide where to place the next mobile pantry or distribution site and defend it. Today they default to the loudest partners or familiar sites; when a funder or board asks ‘why there?’, the answer is gut feel or a spreadsheet no one else can follow.";
export const money = (n) =>
  n == null
    ? "Not available"
    : new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        maximumFractionDigits: 0,
      }).format(n);
export const format = (n) =>
  n == null
    ? "Not available"
    : Number(n).toLocaleString("en-US", { maximumFractionDigits: 1 });
export const month = (time) =>
  new Intl.DateTimeFormat("en-US", {
    month: "2-digit",
    year: "numeric",
    timeZone: "America/New_York",
  }).format(new Date(time));
export const displayName = (tract) =>
  tract.official_neighborhood ||
  tract.place_name ||
  `Unincorporated ${tract.county}`;
export function candidates(tracts, distance = "sd", conservative = false) {
  return tracts
    .filter(
      (t) =>
        t[`lila_${distance}_half_10`] === 1 &&
        t.poverty_pct != null &&
        (conservative ? t.poverty_lower90_pct : t.poverty_pct) >= Q75 &&
        t.core_completeness === 1 &&
        !t.small_denominator_proxy &&
        t.group_quarters_flag !== 1,
    )
    .sort(
      (a, b) =>
        b.poverty_pct - a.poverty_pct ||
        b.low_income_low_access_sd - a.low_income_low_access_sd ||
        a.geoid.localeCompare(b.geoid),
    );
}
export function orderCandidates(rows, order = []) {
  const rank = new Map(order.map((id, i) => [id, i]));
  return [...rows].sort(
    (a, b) =>
      (rank.get(a.geoid) ?? 1e9) - (rank.get(b.geoid) ?? 1e9) ||
      b.poverty_pct - a.poverty_pct ||
      b.low_income_low_access_sd - a.low_income_low_access_sd,
  );
}
export function reviewSummary(events, geoid) {
  const history = events.filter((e) => e.geoid === geoid),
    decisions = new Map();
  for (const e of history)
    if (e.kind === "decision") decisions.set(e.reviewer, e);
  const needByReviewer = new Map();
  for (const e of history)
    if (e.kind === "need") needByReviewer.set(e.reviewer, e);
  const needVotes = [...needByReviewer.values()];
  const latest = [...decisions.values()],
    conflict = new Set(latest.map((e) => e.decision)).size > 1;
  const assignment = [...history]
    .reverse()
    .find((e) => e.kind === "assignment");
  return {
    history,
    decisions: latest,
    conflict,
    needVotes,
    needConflict: new Set(needVotes.map((e) => e.choice)).size > 1,
    assignment,
    notes: activeObservations(history),
    decision: conflict
      ? "disagreement"
      : latest.at(-1)?.decision || "unreviewed",
  };
}
export function moveInOrder(rows, geoid, direction) {
  const ids = rows.map((t) => t.geoid),
    at = ids.indexOf(geoid),
    target = Math.min(ids.length - 1, Math.max(0, at + direction));
  [ids[at], ids[target]] = [ids[target], ids[at]];
  return ids;
}
export const escapeHTML = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (char) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        char
      ],
  );
const trim = (value, max = 260) =>
  String(value ?? "").length > max
    ? String(value).slice(0, max) + "…"
    : String(value ?? "");
export function briefHTML(
  tract,
  workspace = { events: [], order: [] },
  distance = "sd",
  conservative = false,
  metadata = {},
) {
  const e = escapeHTML,
    s = reviewSummary(workspace.events, tract.geoid),
    notes = s.notes.slice(-2),
    assignment = s.assignment;
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Beacon • ${e(displayName(tract))} decision brief</title><style>
 @page{size:A4;margin:12mm}*{box-sizing:border-box}body{margin:0;background:#edf1f4;color:#1E343F;font-family:Avenir,'Avenir Next','Segoe UI',sans-serif;font-size:12px;line-height:1.45}.page{width:186mm;min-height:270mm;margin:20px auto;background:white;padding:0 0 12px;box-shadow:0 6px 30px #1e343f14}.header{background:#1E343F;color:white;padding:20px 24px;border-top:5px solid #F79122;display:flex;justify-content:space-between;align-items:center}.logo{width:137px;height:auto}.kicker{font-size:10px;letter-spacing:1.7px;text-transform:uppercase;color:#6B8FA8;font-weight:700}.header .kicker{color:#FDCB9C}.content{padding:22px 25px}h1{font-size:28px;line-height:1.15;margin:5px 0 7px;font-weight:600}h2{font-size:13px;margin:17px 0 7px}p{margin:5px 0}.muted{color:#61747f}.row{display:flex;gap:12px}.metric{flex:1;padding:13px;background:#f2f5f7;border-radius:8px}.number{font-size:27px;font-weight:700}.orange{color:#b65b09}.pill{padding:4px 8px;border-radius:4px;background:#fff0df;font-size:10px;display:inline-block}.notice{padding:10px 12px;border-left:3px solid #F79122;background:#fff6eb;margin:12px 0}.note{padding:9px 12px;background:#f5f7f9;margin:7px 0;font-size:11px}.table{width:100%;border-collapse:collapse;font-size:11px}.table td{padding:6px 0;border-bottom:1px solid #e5eaed}.table td:first-child{width:32%;color:#61747f}.foot{font-size:9px;color:#61747f;border-top:1px solid #dce4e9;padding-top:10px;margin-top:16px}.print{display:block;margin:20px auto;padding:10px 20px;border:0;background:#1E343F;color:white;cursor:pointer;border-radius:5px}@media print{body{background:white}.page{margin:0;box-shadow:none;min-height:0;width:auto}.print{display:none}.content{padding:18px 22px}a{color:inherit}}
 </style></head><body><button class="print" onclick="window.print()">Print / save as PDF</button><article class="page"><header class="header">${metadata.brandLogoData ? `<img class="logo" alt="Beacon" src="${e(metadata.brandLogoData)}">` : '<strong style="font-size:25px">Beacon</strong>'}<div><div class="kicker">Neighborhood Action Desk</div><div>Decision brief · ${month(Date.now())} ET</div></div></header><div class="content">${metadata.demo ? '<div class="notice" style="margin:0 0 12px">SAMPLE DEMONSTRATION — not an operational decision</div>' : ""}<div class="kicker">One route. An accountable next step.</div><h1>${e(displayName(tract))}</h1><p class="muted">${e(tract.county)} County · Census tract ${e(tract.tract_number)} · GEOID ${e(tract.geoid)}</p><p><span class="pill">${s.conflict || s.needConflict ? "DISAGREEMENT — review required" : s.decision === "approve" ? "APPROVED FOR FIELD VERIFICATION" : s.decision === "reject" ? "REJECTED BY REVIEWER" : "NOT YET REVIEWED"}</span> <span class="pill">${e(tract.evidence_confidence)} evidence confidence</span></p>
 <h2>Why this area was flagged</h2><div class="row"><div class="metric"><div class="kicker">Poverty estimate</div><div class="number orange">${format(tract.poverty_pct)}%</div><div>±${format(tract.poverty_moe_pp)} percentage points</div><div class="muted">90% interval ${format(tract.poverty_lower90_pct)}–${format(tract.poverty_upper90_pct)}%</div></div><div class="metric"><div class="kicker">Low income + low access</div><div style="font-size:17px;font-weight:700;margin:7px 0">Straight-line: ${tract.lila_sd_half_10 === 1 ? "Flagged" : "Not flagged"}<br>Driving: ${tract.lila_dd_half_10 === 1 ? "Flagged" : "Not flagged"}</div><div>½ mile urban / 10 miles rural</div></div></div>
 <p>Poverty screening cutoff: ${Q75.toFixed(1)}% (four-county Q75). Active lens: ${distance === "sd" ? "straight-line" : "driving"}; conservative lower-bound mode ${conservative ? "on" : "off"}. SNAP participation: ${format(tract.snap_pct)}% ±${format(tract.snap_moe_pp)} pp, context only.</p>
 ${snapGapBriefHTML(tract.snap_gap, tract)}
 <div class="notice"><strong>Evidence, not a dispatch order.</strong> ACS is sample-based; actual tract sample size is not supplied. A wide MOE does not prove a small sample. Store-access flags do not establish current pantry demand, food affordability, stock or service capacity.</div>
 <h2>Human review and next step</h2><table class="table"><tr><td>Owner / status</td><td>${e(assignment?.owner || "Unassigned")} / ${e(assignment?.status || "Needs verification")}</td></tr><tr><td>Area-label confidence</td><td>${e(tract.mapping_confidence)} · ${format(tract.largest_place_area_share * 100)}% largest place-area overlap; tract ≠ neighborhood</td></tr>${s.decisions
   .slice(-2)
   .map(
     (d) =>
       `<tr><td>${e(d.reviewer)}: ${e(d.decision)}</td><td>${e(trim(d.reason, 220))}</td></tr>`,
   )
   .join("")}</table>
 ${s.needVotes.length ? `<h2>Screening hypothesis — human feedback, not verified demand</h2><p>${s.needVotes.map((v) => `${e(v.reviewer)}: ${v.choice === "confirm" ? "supports" : "challenges"} — ${e(trim(v.reason, 100))}`).join("<br>")}</p>` : ""}
 <h2>Local observations — Unverified user-entered input</h2>${notes.length ? notes.map((n) => `<div class="note"><strong>${e(n.reviewer)}${n.demo ? " · DEMO INPUT" : ""}</strong>: ${e(trim(n.text, 300))}</div>`).join("") : '<p class="muted">No local observations entered. Validate existing services before selecting a site.</p>'}${s.notes.length > 2 ? `<p class="muted">${s.notes.length - 2} earlier note(s) omitted from this one-page view; retained in the workspace audit.</p>` : ""}
 <div class="foot"><strong>Sources & limitations.</strong> Census ACS 01/2020–12/2024; USDA SRAM released 07/2026, SNAP-store snapshot 06/2025, population base 04/2020. SRAM measures access to SNAP-authorized stores, not supermarket-only access. The Central Florida adult reliable-transportation rate is unavailable. Geometry/labels use Census place/CDP and official Orlando polygons, not equivalent neighborhood boundaries. No partnership, site suitability or unmet demand is inferred. Local review is required.<br><a href="${e(metadata.sourceFolder || "https://drive.google.com/drive/folders/1zuwSZjkK3gcvEzNFPJ8THFRw9ulCgA-p")}">Public hackathon source folder</a> · Retain GEOID ${e(tract.geoid)} with every decision. Local browser workspace; not a multi-user production system.</div></div></article></body></html>`;
}

/** Resolve current local observations without deleting the immutable source events. */
export function activeObservations(events) {
  const notes = new Map();
  for (const e of events) {
    if (e.kind === "note" || e.kind === "flag")
      notes.set(e.id, { ...e, active: true });
    else if (["observation_edit", "observation_deactivate"].includes(e.kind)) {
      const original = notes.get(e.noteId);
      if (
        !original ||
        !original.active ||
        original.geoid !== e.geoid ||
        original.reviewer !== e.reviewer
      )
        continue;
      notes.set(
        e.noteId,
        e.kind === "observation_edit"
          ? { ...original, text: e.text, edited: true }
          : { ...original, active: false },
      );
    }
  }
  return [...notes.values()].filter((n) => n.active);
}
export function observationChange(
  action,
  noteId,
  { text = "", reason, events, geoid, reviewer },
) {
  if (!["edit", "deactivate"].includes(action))
    throw Error("Choose edit or deactivate.");
  if (!String(reason || "").trim())
    throw Error("A reason is required to amend an observation.");
  const original = events.find(
    (e) =>
      e.id === noteId && e.geoid === geoid && ["note", "flag"].includes(e.kind),
  );
  if (!original) throw Error("Observation not found.");
  if (original.reviewer !== reviewer)
    throw Error("You may only amend your own observations in this local demo.");
  if (
    !activeObservations(events.filter((e) => e.geoid === geoid)).some(
      (n) => n.id === noteId,
    )
  )
    throw Error("This observation is inactive.");
  if (action === "edit" && !text.trim())
    throw Error("Observation text is required.");
  return {
    kind: action === "edit" ? "observation_edit" : "observation_deactivate",
    noteId,
    reason: reason.trim(),
    text:
      action === "edit"
        ? text.trim()
        : `Observation deactivated: ${reason.trim()}`,
    demo: original.demo || false,
  };
}
