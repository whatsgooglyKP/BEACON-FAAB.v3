// Shared organizer-only formatting. No resident flyer imports this module.
const number = (value) => (Number.isFinite(value) ? value.toFixed(1) : null);
const escape = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
export const SNAP_CAVEAT =
  "Expected participation among all households, not eligibility, food need or proven under-enrollment. ACS 01/2020–12/2024; associations, not causes. Verify locally.";
// This translates existing labels; it never reclassifies a tract or changes a score.
const plainDriver = (driver) => {
  if (!driver) return "Some information needed for this comparison is missing.";
  const higher = driver.contribution_pp >= 0;
  switch (driver.feature) {
    case "poverty_pct":
      return higher
        ? "High poverty for this area"
        : "Lower poverty in this area";
    case "log_median_household_income":
      return higher
        ? "Lower household incomes in this area"
        : "Higher household incomes in this area";
    case "unemployment_pct":
      return higher
        ? "Higher unemployment in this area"
        : "Lower unemployment in this area";
    case "low_access_population_sd_pct_2020":
      return "How far people live from food stores";
    case "urban":
      return "Whether this area is urban or rural";
    case "lila_sd_half_10":
      return "Local incomes and access to food stores";
    default:
      return "Local income and food-store information";
  }
};
export function snapGapView(gap, tract = {}) {
  const n = gap || {};
  const flagged = n.label === "likely under-enrolled";
  const comparable =
    Number.isFinite(n.actual_pct) && Number.isFinite(n.expected_pct);
  const leading = flagged
    ? (n.drivers || []).find((d) => d.contribution_pp > 0)
    : (n.drivers || [])[0];
  const university = /university/i.test(
    [tract.neighborhood_label, tract.place_name, tract.official_neighborhood]
      .filter(Boolean)
      .join(" "),
  );
  return {
    badge: flagged
      ? "Fewer sign-ups than expected"
      : n.label === "uncertain"
        ? "Not enough data to say"
        : "Unavailable",
    sentence: comparable
      ? `About ${Math.round(n.actual_pct)} in 100 households here get SNAP. Similar neighborhoods usually have about ${Math.round(n.expected_pct)} in 100.`
      : "We don’t have enough information to compare SNAP sign-ups here.",
    why: flagged
      ? "Some eligible families may not be signed up. A SNAP sign-up event here could help."
      : "Check with local partners before planning a SNAP sign-up event.",
    reasonHeading: flagged
      ? "Main reason we expected more"
      : "Main reason for this estimate",
    mainReason: comparable
      ? plainDriver(leading)
      : "Some information needed for this comparison is missing.",
    caution: "This is an estimate to check with local partners, not proof.",
    areaCaution: university
      ? "In university areas, student benefit rules may explain the difference. Check who qualifies before planning outreach."
      : "",
    label: n.label || "unavailable",
    expected:
      number(n.expected_pct) === null
        ? "Not available"
        : `${number(n.expected_pct)}%`,
    actual:
      number(n.actual_pct) === null
        ? "Not available"
        : `${number(n.actual_pct)}% ±${number(n.snap_moe_pp) ?? "?"} pp`,
    gap:
      number(n.gap_pp) === null
        ? "Not available"
        : `${n.gap_pp > 0 ? "+" : ""}${number(n.gap_pp)} pp`,
    reason: n.reason || "No model result available for this tract.",
    drivers: (n.drivers || []).slice(0, 3),
    method:
      "Five-fold held-out ridge estimate. Gap = actual − expected; negative means below expected.",
    allowance:
      number(n.model_tolerance_pp) === null
        ? ""
        : `Shortfall must exceed SNAP MOE plus ${number(n.model_tolerance_pp)} pp model-error allowance; SNAP MOE <10 pp and relative CV ≤0.30. This is a screening rule, not a probability or confidence interval.`,
    caveat: SNAP_CAVEAT,
  };
}
export const SNAP_LIMITATIONS =
  "Missing predictors or unstable SNAP estimates force uncertainty. Predictor MOEs are not propagated; random-fold validation may be optimistic for neighboring tracts. Eligibility and student benefit rules are not measured. Expected means a model estimate for comparable local conditions, not a directly measured average of matched neighborhoods.";
export function snapGapTechnicalHTML(gap) {
  const v = snapGapView(gap),
    e = escape;
  return `<p>Model label: ${e(v.label)}</p><p><strong>Expected ${e(v.expected)} · Actual ${e(v.actual)} · Gap ${e(v.gap)}</strong></p><p>${e(v.method)} ${e(v.reason)}</p>${v.drivers.length ? `<h4>Top model associations</h4><ul>${v.drivers.map((d) => `<li>${e(d.description)}</li>`).join("")}</ul>` : ""}<p>${e(v.allowance)}</p><p>${e(SNAP_LIMITATIONS)}</p><p>${e(v.caveat)}</p>`;
}
export function snapGapBriefHTML(gap, tract = {}) {
  const v = snapGapView(gap, tract),
    e = escape;
  return `<section class="snap-gap-brief" style="font-size:11px;line-height:1.35"><style>.snap-gap-brief details:not([open])>.snap-gap-technical{display:none}.snap-gap-brief .snap-gap-technical{font-size:10px}.snap-gap-brief summary{cursor:pointer;color:#385981}</style><h2 style="margin:10px 0 4px">SNAP sign-ups · ${e(v.badge)}</h2><p>${e(v.sentence)}</p><p><strong>Why it matters:</strong> ${e(v.why)}</p><p><strong>${e(v.reasonHeading)}:</strong> ${e(v.mainReason)}</p>${v.areaCaution ? `<p>${e(v.areaCaution)}</p>` : ""}<p>${e(v.caution)}</p><details><summary>How we got this</summary><div class="snap-gap-technical">${snapGapTechnicalHTML(gap)}</div></details></section>`;
}
