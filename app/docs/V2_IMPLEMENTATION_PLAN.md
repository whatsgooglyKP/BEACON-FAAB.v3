# Action Desk v2 implementation plan

Prepared 11/2026. Execute the supplied PROPOSED_QUICK_FIXES.md design inline for this local, non-repository prototype. No external publication without the actual owner authorization.

Architecture: retain React/Leaflet, immutable audited data and localStorage event history. New pure logic in src/desk.js; new focused components in src/DeskPanels.jsx; small main.jsx integration. Keep original eleven tests.

1. Ask the Desk: write failing tests for natural-language tract/Apopka listing, exact evidence, missing information, real resource referrals and unsupported questions. Implement deterministic answers with sources/limitations, add modal chat UI, verify tests/build before next task.
2. Human review: write failing replacement/need-vote tests; implement reason-required replacement edges, planning-only overrides/cycle rejection and independent need hypothesis votes, add UI and audit rendering, verify tests/build.
3. Observations: write failing edit/deactivate tests; resolve append-only observation amendments without deleting history, integrate current notes into briefs and UI; verify tests/build.
4. Community flyer: write failing public-export privacy/placeholder/escaping tests; implement text and printable HTML plus preview/copy controls; verify tests/build.
5. Extend compiled-app UI workflow across all four additions; run complete suite, format, rebuild, verify baseline data unchanged, update README and under-two-minute demo; package v2 static and separate source ZIP including snapshot data needed for one-command run. Verify archives independently. Drive changes are gated on actual owner authorization, not a parent assertion.
