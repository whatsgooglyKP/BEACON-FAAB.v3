// Runs the app's REAL ranking code (app/src/domain.js) and prints the shortlist
// GEOIDs as JSON. The Python lab compares itself against this to prove its
// port of the ranking rule matches the shipped app exactly.
import { readFileSync } from "node:fs";
import { candidates } from "../app/src/domain.js";
const here = new URL(".", import.meta.url);
const { tracts } = JSON.parse(readFileSync(new URL("../app/public/data/tracts.json", here)));
const out = {};
for (const d of ["sd", "dd"]) for (const c of [false, true]) out[`${d}_${c}`] = candidates(tracts, d, c).map((t) => t.geoid);
console.log(JSON.stringify(out));
