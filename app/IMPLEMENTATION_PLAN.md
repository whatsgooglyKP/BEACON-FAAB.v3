# Approved Neighborhood Action Desk implementation

Prepared 11/2026. Kevin approved the supplied feature/design brief. Implementation uses a static React/Vite app and Leaflet with local boundary geometry, not a production routing engine.

1. Write failing Node tests for screening counts, conservative mode, distance switch, preservation of disagreements, and safe HTML brief export.
2. Snapshot audited CSV/GeoJSON/review-report inputs into public/data using a reproducible prepare_data.py command. Never invent missing values or sample sizes.
3. Build branded three-pane workspace: ranked shortlist, clickable tract map, evidence/actions card. Use exact Beacon colors and official logo artwork cropped from its supplied PDF; Avenir fallback only, no unlicensed font downloads.
4. Persist decisions, reasons, owner/status, notes and reorder audit events in localStorage. Reviewer switching and same-origin tab synchronization demonstrate disagreements without silently resolving them. Label local-only collaboration honestly.
5. Add About and Data Health panels; exported one-page HTML brief with source/vintage/limitations, user-entered notes marked unverified, and browser print-to-PDF.
6. Run Node unit/contract tests and production build; start local dev server. Browser screenshots require the platform browser subagent, unavailable to this executor; do not bypass its desktop boundary with shell-driven browser automation. Leave exact capture instructions if unavailable.
7. Write README and DEMO_SCRIPT.md for a sub-two-minute workflow; provide a self-contained static build without external deployment.

Acceptance: 490 mapped tracts, 68 default candidates, Apopka 43.7 ±11.4 pp, SD/DD LILA true, real source metadata, reason-required actions, persistent local notes, disagreement surfaced, printable brief, latest review report, no external deployment.
