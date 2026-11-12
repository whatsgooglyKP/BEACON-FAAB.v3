import { test } from "node:test";
import assert from "node:assert/strict";
import { execFileSync, spawnSync } from "node:child_process";
import { mkdtempSync, cpSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const app = join(dirname(fileURLToPath(import.meta.url)), "..");
const output = join(app, "..", "output");
const python = ["python3", "python"].find((cmd) => spawnSync(cmd, ["--version"]).status === 0);

function check(sourceDir, env = {}) {
  const code = `import sys,csv; sys.path.insert(0, r"${app}"); import prepare_data as p; from pathlib import Path
src=Path(r"${sourceDir}"); ids={r["geoid"] for r in csv.DictReader(open(src/"tract_clean.csv", newline=""))}
g=p.load_snap_gap(src, ids); print("STALE" if g["metadata"].get("stale_warning") else "OK", len(g["rows"]))`;
  return spawnSync(python, ["-c", code], { env: { ...process.env, ...env }, encoding: "utf8" });
}

function copyOutput(transform) {
  const dir = mkdtempSync(join(tmpdir(), "beacon-"));
  cpSync(output, dir, { recursive: true });
  const csv = join(dir, "tract_clean.csv");
  writeFileSync(csv, transform(readFileSync(csv, "utf8")));
  return dir;
}

test("SNAP check passes on the repo data", () => {
  const r = check(output);
  assert.equal(r.status, 0, r.stderr);
  assert.match(r.stdout, /^OK 490/);
});

test("SNAP check passes on a Windows (CRLF) checkout", () => {
  const dir = copyOutput((t) => t.replace(/\r?\n/g, "\r\n"));
  const r = check(dir);
  assert.equal(r.status, 0, r.stderr);
  assert.match(r.stdout, /^OK 490/);
});

test("changed data falls back with a warning instead of crashing", () => {
  const dir = copyOutput((t) => t + "\n");
  const r = check(dir);
  assert.equal(r.status, 0, r.stderr);
  assert.match(r.stdout, /^STALE 490/);
  assert.match(r.stderr, /WARNING: SNAP model may be stale/);
});

test("strict mode still blocks changed data", () => {
  const dir = copyOutput((t) => t + "\n");
  const r = check(dir, { BEACON_STRICT_DATA: "1" });
  assert.notEqual(r.status, 0);
  assert.match(r.stderr, /SNAP model may be stale/);
});
