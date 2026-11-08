/** Small, inspectable deterministic helpers. No model, inferred pantry, or service claim. */
import {
  candidates,
  displayName,
  format,
  Q75,
  escapeHTML,
  month,
} from "./domain.js";
export const FOOD_FINDER = "https://feedhopenow.org/find-help/food-finder/";
export const DATA_SOURCE =
  "https://drive.google.com/drive/folders/1zuwSZjkK3gcvEzNFPJ8THFRw9ulCgA-p";
const dataSources = [
  { label: "Public Census / USDA source snapshots", url: DATA_SOURCE },
  {
    label: "USDA SRAM definitions",
    url: "https://www.ers.usda.gov/data-products/food-access-research-atlas/documentation/snap-authorized-retailer-access-map-reference-guide",
  },
];
const limitations =
  "Screening is not proof of unmet food need. ACS 01/2020–12/2024; actual tract sample size is not supplied. SRAM released 07/2026 uses SNAP-authorized stores, not supermarket-only access. No current pantry coverage, hours, capacity or Central Florida adult reliable-transportation rate is supplied. Tracts are not neighborhoods.";
export function answerDesk(
  question,
  { tracts, selected, distance = "sd", conservative = false },
) {
  const q = String(question).trim().toLowerCase();
  const lens = `${distance === "sd" ? "straight-line" : "driving"}; conservative uncertainty ${conservative ? "on" : "off"}`;
  const result = (text, rows = [], sources = dataSources) => ({
    text,
    rows,
    sources,
    limitations,
    lens,
  });
  const full = q.match(/\b\d{11}\b/),
    short = q.match(/\b\d{3}\.\d{2}\b|\b\d{5,6}\b/);
  let target = selected;
  if (full || short) {
    const matches = full
      ? tracts.filter((t) => t.geoid === full[0])
      : tracts.filter(
          (t) =>
            Number(t.geoid.slice(-6)) === Number(short[0].replace(".", "")),
        );
    if (matches.length === 0)
      return result(
        "That tract was not found in the four-county dataset. Use an 11-digit GEOID from the map; do not assume missing geography has no need.",
      );
    if (matches.length > 1)
      return result(
        "That short tract number is ambiguous across counties. Choose an 11-digit GEOID.",
        matches,
      );
    target = matches[0];
  }
  if (/resource|pantr|near me|food help|food bank/.test(q))
    return result(
      `For ${displayName(target)}, we have not imported or verified current pantry locations, hours or capacity. Open Second Harvest's official Food Finder, search your ZIP Code and call ahead. This is a referral, not a nearest-open-pantry match. A food-bank warehouse is not a pantry pickup site; use the partner locator. No precise location or GPS is collected.`,
      [],
      [
        {
          label: "Second Harvest Food Finder — official resource locator",
          url: FOOD_FINDER,
        },
        {
          label: "Feeding America national finder",
          url: "https://www.feedingamerica.org/find-your-local-foodbank",
        },
        ...dataSources,
      ],
    );
  if (/missing|do not know|don't know|limitation|unavailable/.test(q))
    return result(
      `For tract ${target.geoid}, missing information includes current pantry locations, hours and capacity; existing service coverage and unmet demand; affordability and food quality; site suitability; the Central Florida adult reliable-transportation rate; and actual ACS sample size. Missing does not mean zero. Poverty and access indicators describe different vintages, not today's service availability.`,
    );
  if (/which|list|show/.test(q) && /flag|candidate|shortlist/.test(q)) {
    const places = [
      ...new Set(
        tracts
          .flatMap((t) => [t.place_name, t.official_neighborhood])
          .filter(Boolean),
      ),
    ].sort((a, b) => b.length - a.length);
    const place = places.find((p) => q.includes(p.toLowerCase()));
    const rows = candidates(tracts, distance, conservative).filter((t) =>
      place
        ? [t.place_name, t.official_neighborhood].includes(place)
        : t.county === selected.county,
    );
    return result(
      `${rows.length} screening candidates in ${place || selected.county + " County"} under ${lens}. These are areas to investigate, not confirmed unserved households. Click a tract to inspect it.`,
      rows,
    );
  }
  if (/why|flag|poverty|evidence|tract|snap|access/.test(q)) {
    const eligible = candidates(tracts, distance, conservative).some(
      (t) => t.geoid === target.geoid,
    );
    return result(
      `${displayName(target)} · tract ${target.tract_number} · GEOID ${target.geoid}: ${eligible ? "included" : "not included"} in the current screening shortlist (${lens}). Poverty ${format(target.poverty_pct)}% ±${format(target.poverty_moe_pp)} percentage points (90% MOE); fixed cutoff ${Q75}%. Straight-line LILA ${target.lila_sd_half_10 === 1 ? "flagged" : "not flagged"}; driving LILA ${target.lila_dd_half_10 === 1 ? "flagged" : "not flagged"}. SNAP participation ${format(target.snap_pct)}% ±${format(target.snap_moe_pp)} pp is context, not a measure of unmet need. Evidence confidence: ${target.evidence_confidence}; mapping confidence: ${target.mapping_confidence}. Source estimates stay unchanged by organizer reviews.`,
    );
  }
  return result(
    "This is a deterministic, limited-topic assistant. The supported questions are: which local tracts are flagged, why a tract was flagged, what information is missing, and where to find official food-resource information. I cannot predict demand or confirm a pantry is open.",
  );
}

export function applyReplacements(rows, tracts, events) {
  let plan = [...rows];
  const lookup = new Map(tracts.map((t) => [t.geoid, t]));
  for (const e of events.filter((e) => e.kind === "replacement")) {
    const index = plan.findIndex((t) => t.geoid === e.geoid),
      target = lookup.get(e.targetGeoid);
    if (index < 0 || !target) continue;
    const before = plan
      .slice(0, index)
      .filter((t) => t.geoid !== e.targetGeoid);
    const after = plan
      .slice(index + 1)
      .filter((t) => t.geoid !== e.targetGeoid);
    plan = [...before, target, ...after];
  }
  return plan;
}
export function replacementEvent(
  source,
  target,
  reason,
  { tracts, events = [], distance = "sd", conservative = false },
) {
  if (typeof reason !== "string" || !reason.trim())
    throw Error("A replacement reason is required.");
  if (source === target) throw Error("Choose a different tract.");
  if (
    !tracts.some((t) => t.geoid === source) ||
    !tracts.some((t) => t.geoid === target)
  )
    throw Error("Tract not found in this dataset.");
  const edges = new Map(
    events
      .filter((e) => e.kind === "replacement")
      .map((e) => [e.geoid, e.targetGeoid]),
  );
  let cursor = target;
  const visited = new Set();
  while (cursor) {
    if (cursor === source || visited.has(cursor))
      throw Error("Replacement would create a cycle.");
    visited.add(cursor);
    cursor = edges.get(cursor);
  }
  if (edges.has(source))
    throw Error(
      "This tract has already been replaced. Select its current replacement instead.",
    );
  const baseline = candidates(tracts, distance, conservative);
  if (
    !applyReplacements(baseline, tracts, events).some((t) => t.geoid === source)
  )
    throw Error("Select a tract in the current planning shortlist first.");
  return {
    kind: "replacement",
    geoid: source,
    targetGeoid: target,
    reason: reason.trim(),
    manualOverride: !baseline.some((t) => t.geoid === target),
    text: `Replaced ${source} with ${target}: ${reason.trim()}`,
  };
}
export function needVote(choice, reason) {
  if (!["confirm", "challenge"].includes(choice))
    throw Error("Choose a valid need-hypothesis choice.");
  if (typeof reason !== "string" || !reason.trim())
    throw Error("A reason is required for the need hypothesis.");
  return {
    kind: "need",
    choice,
    reason: reason.trim(),
    text: `${choice === "confirm" ? "Supports" : "Challenges"} the screening hypothesis (not verified unmet need): ${reason.trim()}`,
  };
}
export function needSummary(events, geoid) {
  const latest = new Map();
  for (const e of events)
    if (e.geoid === geoid && e.kind === "need") latest.set(e.reviewer, e);
  const votes = [...latest.values()];
  return { votes, conflict: new Set(votes.map((e) => e.choice)).size > 1 };
}

/** Deliberately accepts no workspace: internal scores, notes and identities cannot leak. */
export function communityFlyer(tract, fields = {}) {
  const field = (name, fallback) =>
    String(fields[name] || "")
      .trim()
      .slice(0, 200) || fallback;
  const pantry = field("pantry", "[PANTRY NAME — organizer to fill]");
  const time = field("time", "[DATE / TIME — organizer to fill]");
  const address = field("address", "[LOCATION — organizer to fill]");
  const paragraphs = [
    "DRAFT — organizer review required before sharing",
    `Food help for the ${displayName(tract)} area`,
    "Looking for food assistance? You are not alone. Use the official locator to find food-help partners and call ahead to confirm hours, requirements and availability.",
    `Second Harvest Food Finder: ${FOOD_FINDER}`,
    "Search your ZIP Code. Food is not distributed directly to individuals from the food bank’s facilities; use the partner locator. This guide does not announce a new distribution event.",
    "Potential local information — organizer-entered, not verified by this app:",
    `Pantry / program: ${pantry}`,
    `Date / time: ${time}`,
    `Location: ${address}`,
    "Do not travel based on unfilled or unverified details. Call the listed pantry before visiting.",
    "For help outside regular hours, dial 2-1-1 as directed by Second Harvest. For other regions: https://www.feedingamerica.org/find-your-local-foodbank",
    `Resource guide prepared ${month(Date.now())} ET. Source: Second Harvest Food Finder. Hours, availability and eligibility must be confirmed locally. No service coverage or eligibility is inferred.`,
  ];
  const e = escapeHTML;
  const text = paragraphs.join("\n\n");
  const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Beacon · Community food-help draft</title><style>@page{size:A4;margin:16mm}*{box-sizing:border-box}body{font-family:Avenir,'Segoe UI',sans-serif;color:#1e343f;line-height:1.6;max-width:730px;margin:20px auto;padding:20px}h1{font-size:30px;line-height:1.2}.draft{background:#fff1df;border-left:4px solid #f79122;padding:12px;font-weight:700}.details{padding:15px;background:#f1f5f8;border-radius:8px}a{color:#385981;overflow-wrap:anywhere}.footer{font-size:11px;border-top:1px solid #d3dfe6;padding-top:12px}button{padding:10px 16px;background:#1e343f;color:white;border:0;border-radius:6px}@media print{body{margin:0;padding:0;max-width:none}button{display:none}}</style></head><body><button onclick="window.print()">Print / save as PDF</button><p class="draft">${e(paragraphs[0])}</p><p>BEACON · COMMUNITY RESOURCE GUIDE</p><h1>${e(paragraphs[1])}</h1><p>${e(paragraphs[2])}</p><p><strong><a href="${FOOD_FINDER}">Second Harvest Food Finder ↗</a></strong><br>${FOOD_FINDER}</p><p>${e(paragraphs[4])}</p><section class="details"><strong>${e(paragraphs[5])}</strong><p>${e(paragraphs[6])}</p><p>${e(paragraphs[7])}</p><p>${e(paragraphs[8])}</p></section><p>${e(paragraphs[9])}</p><p>${e(paragraphs[10])}</p><p class="footer">${e(paragraphs[11])}</p></body></html>`;
  return { text, html };
}
