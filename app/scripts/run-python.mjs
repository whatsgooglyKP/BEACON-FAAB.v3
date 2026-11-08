// Cross-platform Python launcher: tries python3, python, then the Windows "py -3" launcher.
import { spawnSync } from "node:child_process";

const args = process.argv.slice(2);
const candidates = [["python3"], ["python"], ["py", "-3"]];

for (const [cmd, ...pre] of candidates) {
  const probe = spawnSync(cmd, [...pre, "--version"], { encoding: "utf8", shell: false });
  const out = `${probe.stdout || ""}${probe.stderr || ""}`;
  if (probe.status === 0 && /Python 3\./.test(out)) {
    const run = spawnSync(cmd, [...pre, ...args], { stdio: "inherit", shell: false });
    process.exit(run.status ?? 1);
  }
}
console.error("Python 3 was not found. Install it from https://www.python.org/downloads (Windows: tick 'Add python.exe to PATH'), then open a new terminal.");
process.exit(1);
