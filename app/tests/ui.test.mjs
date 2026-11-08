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

test("real built app supports approval, notes, assignment, disagreement and brief preview in a virtual DOM", async () => {
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
  assert.ok(w.document.body.textContent.includes("43.7"));
  assert.equal(w.document.querySelectorAll(".tract-row").length, 68);
  const gapCard = w.document.querySelector(".snap-gap-card");
  assert.ok(gapCard, "SNAP gap section is visible on the evidence card");
  assert.match(gapCard.textContent, /SNAP sign-ups/);
  assert.match(gapCard.textContent, /21.5%/);
  assert.match(gapCard.textContent, /held-out/);
  assert.match(gapCard.textContent, /not eligibility/);
  assert.equal(gapCard.querySelectorAll("li").length, 3);
  assert.equal(gapCard.querySelector("details").open, false);
  assert.equal(gapCard.querySelector("summary").textContent, "How we got this");
  gapCard.querySelector("summary").click();
  assert.equal(gapCard.querySelector("details").open, true);
  gapCard.querySelector("summary").click();
  assert.equal(gapCard.querySelector("details").open, false);
  const simpleCard = gapCard.cloneNode(true);
  simpleCard.querySelector(".snap-gap-technical").remove();
  assert.match(
    simpleCard.textContent,
    /About 22 in 100 households here get SNAP/,
  );
  assert.match(simpleCard.textContent, /Fewer sign-ups than expected/);
  assert.doesNotMatch(
    simpleCard.textContent,
    /\b(pp|MOE|CV|ridge|held-out|fold|association)\b/i,
  );
  assert.ok(
    w.document.body.textContent.includes(
      "Actual tract sample size is not supplied",
    ),
  );
  click("Approve to verify");
  await until(() => w.document.querySelector("[role=dialog]"));
  input(
    w.document.querySelector("[role=dialog] textarea"),
    "Both access definitions support a field visit; verify existing services first.",
  );
  await pause(50);
  click("Record approval");
  await until(() => !w.document.querySelector("[role=dialog]"));
  click("Review & notes");
  await until(() => w.document.querySelector(".note-form"));
  click("Use demo example");
  await pause(30);
  click("Save observation");
  await pause(50);
  assert.ok(w.document.body.textContent.includes("DEMO INPUT"));
  input(
    w.document.querySelector('input[placeholder="e.g., Volunteer 1"]'),
    "Volunteer 1",
  );
  await pause(30);
  click("Save assignment");
  await pause(40);
  const select = w.document.querySelector(
    'select[aria-label="Active reviewer"]',
  );
  select.value = "Field reviewer";
  select.dispatchEvent(new w.Event("change", { bubbles: true }));
  await pause(40);
  click("Reject");
  await until(() => w.document.querySelector("[role=dialog] textarea"));
  input(
    w.document.querySelector("[role=dialog] textarea"),
    "Validate the existing Tuesday service before adding another stop.",
  );
  await pause(40);
  click("Record rejection");
  await until(() => !w.document.querySelector("[role=dialog]"));
  assert.ok(w.document.body.textContent.includes("Two reviewers disagree"));
  const stored = JSON.parse(w.localStorage.getItem("beacon-action-desk-v1"));
  assert.equal(stored.events.filter((e) => e.kind === "decision").length, 2);
  assert.equal(
    stored.events.find((e) => e.kind === "assignment").owner,
    "Volunteer 1",
  );
  assert.equal(stored.events.filter((e) => e.kind === "note").length, 1);
  click("Create decision brief");
  await until(() => w.document.querySelector("iframe"));
  const html = w.document.querySelector("iframe").srcdoc;
  assert.ok(html.includes("43.7%"));
  assert.ok(html.includes("DISAGREEMENT"));
  assert.ok(html.includes("DEMO INPUT"));
  assert.ok(html.includes("Volunteer 1"));
  assert.ok(html.includes("SNAP sign-ups"));
  assert.ok(html.includes("not eligibility"));
  dom.window.close();
  assert.deepEqual(errors, []);
});
