# v2 verification — 11/2026

Command: `npm test` (snapshot refresh, Vite production build, Node contracts and compiled-app virtual-DOM workflows).

- **26 passed, zero failures/skips.** Original eleven tests retained and passing.
- Latest measured build: 1.73 seconds; tests: 1.52 seconds.
- Test-first cycles observed failing missing-feature assertions for Q&A, replacement/need feedback, observation amendments, and resident export before implementation; regression failures reproduced/fixed for explicit-GEOID missing-information scope, missing reason validation, and brief disagreement visibility.
- Q&A: exact Apopka values and uncertainty, complete default local candidate listing, official resource referral, missing-data transparency, unknown/unsupported questions, explicit GEOID scoping.
- Human controls: required reasons/IDs, no self replacement or cycles, no duplicate planned tracts, ineligible override flag, immutable source evidence, independent need votes/revisions/disagreement.
- Notes: own-alias edit/deactivation, required reasons, immutable original events, inactive text excluded from current brief.
- Flyer: explicit placeholders, official URLs/call-ahead warning, no internal metrics/notes/identities, escaped organizer fields, unverified-input labelling.
- Both actual compiled-app workflows pass in jsdom: original approval/note/assignment/disagreement/brief; v2 Q&A → hypothesis disagreement → note edit/deactivate → replacement → resident preview/copy fallback.
- `exports/apopka-community-flyer-v2-draft.pdf` is **one A4 page**, rendered and visually inspected. Image: `screenshots/community-flyer-v2.png`.
- These are not real-browser visual/layout tests. Main-map/evidence screenshots and browser print/copy permissions still need a permitted browser delegate.
- Independent reviewer dispatch is unavailable to this executor; a local code review and contract/integration tests were performed instead. No claim of independent review.

Clean source extraction: `npm ci --offline && npm test` passed all 26 tests, including a fresh production build (1.72 seconds). No existing node_modules or parent datasets were used; all six required snapshots came from the source ZIP. Install emitted an esbuild postinstall-policy warning but the bundled platform binary worked and the build/test command exited 0. Packaging and external-upload status are recorded in V2_DELIVERY.md. No real organizer validation or production collaboration was claimed.

## v3 SNAP model verification (11/2026)

`npm test`: **31 passed, 0 failed**, all original 26 retained. New tests cover separate 490-key model snapshot, exact Apopka data, shared card/brief formatting and escaping, missing-model handling, resident-flyer exclusion; production-bundle workflow now checks visible model section and exported caveat.

Root Python contracts: five model tests (determinism including row reorder, schema, strict allowlist/held-out perturbation, uncertainty gates/missingness, coefficient reconstruction, stale/duplicate snapshot rejection). Original 12 cleaner tests remain passing. Optional WeasyPrint render regression confirms a normal Apopka ML brief with real logo, demo note and owner stays one page. CSV/metadata full rerun byte-identical. Audited tract CSV/JSON/geometry hashes unchanged. See V3_DELIVERY.md and V3_PACKAGE_MANIFEST.json.

Real exported one-page sample and two PDF-raster PNGs were inspected. These are document/file renders, not a real-browser screenshot. Browser layout/interactive print behavior remains unverified because no permitted browser delegate was available.

## v4 presentation-only verification (11/2026)

`npm test`: **35 passed, 0 failed**. Existing 26 workflows retained. Exact Apopka plain wording tested; all uncertain rows stay “Not enough data to say”; unavailable never displays an invented zero. University-area caution remains. Card and brief technical text is contained in a closed **How we got this** section; compiled card can expand/collapse it. Default text has no pp/MOE/CV/ridge/held-out/fold/association jargon.

Python one-page regression additionally confirms plain counts appear and model-method/association text is hidden in the default PDF. Model/requirements/CSV/JSON and tract/geometry hashes unchanged. No retraining or rule change. Current genuine PDF-raster captures use v4 names; live-browser visual behavior remains untested.
