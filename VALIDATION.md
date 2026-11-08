# Analysis-output validation

Prepared 11/2026. All 22 assertions below passed in a fresh box run. These checks document the original audited analysis. The implemented cleaner now also has a 12-test acceptance/regression suite; see TEST_RESULTS.md.

- PASS: 490 unique 11-digit tract keys
- PASS: County allowlist and counts
- PASS: Wide/curated/mapping/DQ key agreement
- PASS: Clean primary rates stay in 0–100
- PASS: LILA flags are binary
- PASS: Expected LILA sensitivity counts
- PASS: Expected poverty screening selection
- PASS: Top-ten order and eligibility
- PASS: Core rates match original ACS rows
- PASS: Exact raw-to-clean match: poverty
- PASS: Exact raw-to-clean match: snap
- PASS: Exact raw-to-clean match: population
- PASS: 12 censored cells have explicit bounds
- PASS: No flagged cell with numeric sentinel remains exact in wide output
- PASS: Neighborhood threshold honored
- PASS: Low-confidence geographic labels require review
- PASS: 1,695 retailer points remain separate
- PASS: No CFL reliable-transportation rate fabricated
- PASS: All joined source fields in column dictionary
- PASS: Cell-level flags auditable
- PASS: Unrelated business indicators excluded from curated screening fields
- PASS: CSV and parquet numerics agree

The reusable pipeline is implemented and verified; see README.md and TEST_RESULTS.md. Statistical rankings and geographic labels still require local review.
