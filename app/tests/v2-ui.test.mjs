import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { randomUUID } from "node:crypto";
import { JSDOM, VirtualConsole } from "jsdom";
const root = path.resolve(new URL("..", import.meta.url).pathname);
const pause = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
async function until(fn) {
  for (let i = 0; i < 120; i++) {
    if (fn()) return;
    await pause(20);
  }
  throw Error("Virtual-DOM condition timed out");
}

test("v2 compiled workflow covers cited Q&A, hypothesis disagreement, note amendments, replacement and resident export", async () => {
  const errors = [];
  const virtualConsole = new VirtualConsole();
  virtualConsole.on("jsdomError", (error) => {
    if (!String(error).includes("navigation")) errors.push(String(error));
  });
  const dom = new JSDOM(
    '<!doctype html><html><body><div id="root"></div></body></html>',
    {
      url: "http://localhost:5173/",
      runScripts: "outside-only",
      pretendToBeVisual: true,
      virtualConsole,
    },
  );
  const w = dom.window;
  w.HTMLCanvasElement.prototype.getContext = undefined;
  w.SVGSVGElement.prototype.createSVGRect = () => ({});
  Object.defineProperty(w.HTMLElement.prototype, "clientWidth", {
    get() {
      return this.classList.contains("tract-map") ? 620 : 900;
    },
  });
  Object.defineProperty(w.HTMLElement.prototype, "clientHeight", {
    get() {
      return this.classList.contains("tract-map") ? 600 : 800;
    },
  });
  w.ResizeObserver = class {
    observe() {}
    disconnect() {}
  };
  w.crypto.randomUUID = randomUUID;
  w.fetch = async (url) => ({
    ok: true,
    json: async () =>
      JSON.parse(
        fs.readFileSync(
          path.join(root, "public", String(url).replace(/^\.\//, "")),
          "utf8",
        ),
      ),
  });
  const asset = fs
    .readdirSync(path.join(root, "dist/assets"))
    .find((name) => /^index-.*\.js$/.test(name));
  const code = fs
    .readFileSync(path.join(root, "dist/assets", asset), "utf8")
    .replaceAll(
      "import.meta.url",
      JSON.stringify("http://localhost:5173/assets/" + asset),
    );
  w.eval(code);
  const button = (text) =>
    [...w.document.querySelectorAll("button")].find((node) =>
      node.textContent.includes(text),
    );
  const click = (text) => {
    const found = button(text);
    assert.ok(found, "button " + text + " exists");
    found.click();
  };
  const input = (node, value) => {
    assert.ok(node);
    const prototype =
      node.tagName === "TEXTAREA"
        ? w.HTMLTextAreaElement.prototype
        : w.HTMLInputElement.prototype;
    Object.getOwnPropertyDescriptor(prototype, "value").set.call(node, value);
    node.dispatchEvent(new w.Event("input", { bubbles: true }));
  };
  await until(() => button("Approve to verify"));
  const close = async () => {
    w.document.querySelector('button[aria-label="Close dialog"]').click();
    await until(() => !w.document.querySelector('[role="dialog"]'));
  };
  const changeSelect = (node, value) => {
    node.value = value;
    node.dispatchEvent(new w.Event("change", { bubbles: true }));
  };
  click("Ask the Desk");
  await until(() => button("Why was 17703 flagged?"));
  click("Why was 17703 flagged?");
  await until(() => w.document.querySelector(".desk-answer"));
  assert.ok(
    w.document.querySelector(".desk-answer").textContent.includes("43.7%"),
  );
  assert.ok(
    w.document.querySelector(".desk-answer").textContent.includes("11.4"),
  );
  click("What resources exist near me?");
  await until(() => w.document.querySelectorAll(".desk-answer").length === 2);
  assert.ok(
    w.document
      .querySelectorAll(".desk-answer")[1]
      .textContent.includes("call ahead"),
  );
  assert.ok(
    w.document.querySelector(
      'a[href="https://feedhopenow.org/find-help/food-finder/"]',
    ),
  );
  await close();
  click("Replace / review inferred need");
  await until(() =>
    w.document.querySelector('[aria-label="Need hypothesis reason"]'),
  );
  input(
    w.document.querySelector('[aria-label="Need hypothesis reason"]'),
    "Supports an investigation, not proof of a gap",
  );
  await pause(30);
  click("Confirm screening hypothesis");
  await pause(30);
  changeSelect(
    w.document.querySelector('[aria-label="Active reviewer"]'),
    "Field reviewer",
  );
  await pause(30);
  input(
    w.document.querySelector('[aria-label="Need hypothesis reason"]'),
    "Verify current pantry capacity first",
  );
  await pause(30);
  click("Challenge inferred need");
  await until(() =>
    w.document.body.textContent.includes("Need hypothesis disagreement"),
  );
  await close();
  click("Review & notes");
  await until(() => button("Use demo example"));
  click("Use demo example");
  await pause(30);
  click("Save observation");
  await until(() => button("Edit observation"));
  click("Edit observation");
  await until(() =>
    w.document.querySelector('[aria-label="Updated observation"]'),
  );
  input(
    w.document.querySelector('[aria-label="Updated observation"]'),
    "PRIVATE INTERNAL INPUT — corrected, unverified",
  );
  input(
    w.document.querySelector('[aria-label="Observation change reason"]'),
    "Corrected demonstration wording",
  );
  await pause(30);
  click("Save observation change");
  await until(() =>
    w.document
      .querySelector(".desk-observation")
      .textContent.includes("PRIVATE INTERNAL INPUT"),
  );
  click("Deactivate observation");
  await until(() =>
    w.document.querySelector('[aria-label="Observation change reason"]'),
  );
  input(
    w.document.querySelector('[aria-label="Observation change reason"]'),
    "Withdraw test observation",
  );
  await pause(30);
  click("Save observation change");
  await until(() => !w.document.querySelector(".desk-observation"));
  click("Replace / review inferred need");
  await until(() =>
    w.document.querySelector('[aria-label="Replacement tract"]'),
  );
  changeSelect(
    w.document.querySelector('[aria-label="Replacement tract"]'),
    "12095017600",
  );
  input(
    w.document.querySelector('[aria-label="Replacement reason"]'),
    "Investigate the adjacent Apopka tract instead",
  );
  await pause(30);
  click("Record replacement");
  await until(
    () => new URL(w.location.href).searchParams.get("tract") === "12095017600",
  );
  await close();
  const stored = JSON.parse(w.localStorage.getItem("beacon-action-desk-v1"));
  assert.equal(stored.events.filter((e) => e.kind === "need").length, 2);
  assert.equal(stored.events.filter((e) => e.kind === "replacement").length, 1);
  assert.equal(
    stored.events.filter((e) => e.kind === "observation_edit").length,
    1,
  );
  assert.equal(
    stored.events.filter((e) => e.kind === "observation_deactivate").length,
    1,
  );
  assert.equal(w.document.querySelectorAll(".tract-row").length, 67);
  click("Community flyer / message");
  await until(() => w.document.querySelector("iframe"));
  const html = w.document.querySelector("iframe").srcdoc;
  assert.ok(html.includes("PANTRY NAME"));
  assert.ok(html.includes("DATE / TIME"));
  assert.ok(html.includes("DRAFT"));
  assert.ok(!html.includes("PRIVATE INTERNAL INPUT"));
  assert.ok(!html.includes("35.6%"));
  input(
    w.document.querySelector('[aria-label="Flyer pantry"]'),
    "DEMO ONLY — not a verified pantry",
  );
  await pause(30);
  assert.ok(w.document.querySelector("iframe").srcdoc.includes("DEMO ONLY"));
  click("Copy community text");
  await pause(30);
  assert.ok(w.document.body.textContent.includes("Clipboard unavailable"));
  dom.window.close();
  assert.deepEqual(errors, []);
});
