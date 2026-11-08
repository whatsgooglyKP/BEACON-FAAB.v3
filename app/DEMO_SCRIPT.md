# Demo script v4 — one truck route, under two minutes

Prepared 11/2026. Open http://localhost:5173/?tract=12095017703 at a desktop viewport. Use Straight-line, conservative mode off, and a fresh demonstration workspace. Do not erase a real review history. All local notes below are labelled demo inputs, not source facts.

## 0:00–0:12 · The decision

“We have one new truck route to place. Familiar partners and loud requests often win. When a funder asks ‘why there?’, Beacon keeps the public evidence and the human reasoning together.”

Point to the 68 screening candidates across Lake, Orange, Osceola and Seminole—not ‘68 unserved neighborhoods’.

## 0:12–0:32 · Real evidence, honest uncertainty

Apopka tract 177.03 / GEOID 12095017703 is selected by default.

“Poverty is estimated at 43.7%, with a 90% margin of error of ±11.4 percentage points. Both straight-line and driving access definitions flag this tract. These are SNAP-authorized stores, not necessarily supermarkets. It is a screening signal, not proof of unmet pantry demand.”

“Actual tract sample size is not supplied; we show the wide error bar without inventing a small sample.”

## 0:32–0:47 · SNAP sign-ups — plain-language ML beat

Scroll the evidence card to **SNAP sign-ups** (same Apopka tract). Leave **How we got this** closed unless a judge asks for the method.

“About 22 in 100 households here get SNAP. Similar neighborhoods usually have about 36 in 100. A sign-up event could help. It’s an estimate to check with local partners, not proof.”

The card names high poverty as the main reason we expected more. The rounded counts are a simpler way to display the same 21.5% actual and 35.5311% expected values; no model result or flag rule changed. Do not say the difference counts eligible families missing benefits. The technical explanation remains under **How we got this**.

## 0:47–1:10 · A human owns the next step

Approve to verify → paste reason → Record approval:

`Both access definitions support a field visit; verify existing services and capacity first.`

Review & notes → Use demo example → Save observation:

`DEMO INPUT (unverified): church on Main St already runs a Tuesday pantry here.`

“This is an example organizer observation, not a verified dataset fact.”

Enter owner Volunteer 1 (demo label), choose Assigned, Save assignment. No truck is dispatched.

## 1:10–1:30 · Two audiences, two safe exports

Click Community flyer / message. Show the plain-language draft and clearly marked PANTRY NAME, DATE / TIME and LOCATION fields.

“Residents get official resource information, not internal poverty scores or staff notes. An organizer must fill and verify the details. Nothing claims that a new distribution event exists.”

Show Copy community text or Download community flyer. Do not actually send/post it. Close.

## 1:30–1:43 · Answer the funder

Click Create decision brief. Show the real evidence, uncertainty, human rationale and labelled local input.

“This is the separate board/grant brief. It preserves disagreement and withdrawn notes stay out of the current brief while remaining in the audit.”

Use `exports/apopka-17703-snap-gap-v4-brief.pdf` if a print dialog interrupts the demo. It contains the ML section and no invented review approval.

## 1:43–1:58 · Made, learned, next

“We made an accountable planning desk on open Census, USDA and local geography. We learned that definitions, uncertainty and current services can change a decision. Next we validate labels and pantry coverage with organizers, then pilot whether this reduces the time to a defensible shortlist.”

Do not claim an actual food-bank partnership, co-design session or measured impact that has not happened.

## Optional extension · Human disagreement and corrections

- Replace / review inferred need → enter a reason → Confirm screening hypothesis. ‘Confirm’ supports further investigation, not verified hunger or a confirmed service gap.
- Switch reviewer to Field reviewer, add a reason and Challenge inferred need. The need-hypothesis disagreement remains visible independently of approve/reject for a site visit; the decision brief also carries it.
- Replacement: choose a different tract and give a reason. The old/new GEOIDs are retained in the audit. A replacement already listed is moved rather than duplicated; outside-screening choices have an explicit override warning. Source evidence counts never change.
- Review & notes: each alias can Edit observation or Deactivate observation on its own entries, with a reason. Historical text is retained; current views/briefs use active amended text. Aliases are a same-browser demonstration, not an authentication system.
- Conservative uncertainty reduces the default straight-line shortlist to seven; driving yields 97 candidates, or 14 conservative. These are definition/robustness changes, not a measured worsening of conditions.

## Judge Q&A

- Who built with? For organizers, not yet co-designed with one. Next is a concrete validation conversation—not a claimed partnership.
- What built on? Public Census/USDA sources, official local geometry, standard tract GEOIDs, CSV/Parquet/GeoJSON, inspectable cleaning rules and a source package.
- What happens after? Validate service coverage and labels, assign a maintenance owner, add authenticated collaborative storage, and evaluate an organizer-reviewed planning pilot.
- Are there real pantry locations? The appendix links live locators, not a supplied pantry table. The app links the official finder, with a call-ahead caveat. A food-bank warehouse is not represented as a pantry pickup site.
- Is this AI/ML? A small, explainable ridge regression predicts tract SNAP participation from six non-SNAP indicators; five-fold out-of-fold R² 0.503, MAE 5.58 pp versus a naive 8.21 pp. It is supervised learning, not reinforcement learning or generative AI. The Q&A remains deterministic templating. No clustering, Gemini or automatic decisions were added.
- How safe is the label? Only four tracts pass the SNAP MOE and model-error screening rule; 484 are uncertain and two unavailable. Random-fold CV can be optimistic for neighboring tracts. Predictor MOEs are not propagated; “likely” is not a calibrated probability. Current eligibility and outcomes must be validated locally.
- What drives Apopka? Poverty contributes +14.2 pp and income +7.5 pp relative to its fold’s average; unemployment contributes −0.7 pp. These are associations, not causes.
- Can two colleagues use it? Reviewer aliases and same-origin tabs demonstrate disagreement; cross-device authenticated collaboration is not implemented.

## Optional substitution · Existing Ask the Desk (not a new v4 feature)

If time permits, click Ask the Desk → Why was 17703 flagged? It uses the same cleaned facts and source links; it is not an LLM. Keep this outside the core two-minute flow if showing the ML beat.
