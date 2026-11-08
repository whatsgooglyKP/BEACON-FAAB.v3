import React, { useState } from "react";
import {
  answerDesk,
  replacementEvent,
  needVote,
  needSummary,
  communityFlyer,
} from "./desk.js";
import { candidates, reviewSummary, observationChange } from "./domain.js";
export function AskDesk({
  tracts,
  selected,
  distance,
  conservative,
  onSelect,
}) {
  const [question, setQuestion] = useState(""),
    [messages, setMessages] = useState([]);
  function ask(text) {
    if (!text.trim()) return;
    setMessages((m) => [
      ...m,
      {
        question: text,
        answer: answerDesk(text, { tracts, selected, distance, conservative }),
      },
    ]);
    setQuestion("");
  }
  return (
    <section className="desk-panel">
      <p className="desk-disclosure">
        Templated data assistant — not live AI. Uses audited public data, not
        your private notes. Answers retain the lens and tract context at the
        time asked.
      </p>
      <div className="desk-prompts">
        {[
          "Which Apopka tracts are flagged?",
          "Why was 17703 flagged?",
          "What information are you missing for this tract?",
          "What resources exist near me?",
        ].map((q) => (
          <button key={q} className="small-button" onClick={() => ask(q)}>
            {q}
          </button>
        ))}
      </div>
      <div className="desk-conversation" aria-live="polite">
        {messages.map((m, i) => (
          <article key={i} className="desk-answer">
            <strong>You: {m.question}</strong>
            <p>{m.answer.text}</p>
            {m.answer.rows.length > 0 && (
              <ul>
                {m.answer.rows.map((t) => (
                  <li key={t.geoid}>
                    <button
                      className="text-button"
                      onClick={() => onSelect(t.geoid)}
                    >
                      {t.neighborhood_label} · {t.geoid} · poverty{" "}
                      {t.poverty_pct}% ±{t.poverty_moe_pp} pp
                    </button>
                  </li>
                ))}
              </ul>
            )}
            <small>Lens: {m.answer.lens}</small>
            <details open>
              <summary>Sources & limitations</summary>
              <p>{m.answer.limitations}</p>
              {m.answer.sources.map((s) => (
                <p key={s.url}>
                  <a href={s.url} target="_blank" rel="noreferrer">
                    {s.label} ↗
                  </a>
                </p>
              ))}
            </details>
          </article>
        ))}
      </div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          ask(question);
        }}
      >
        <label>
          Ask a question
          <input
            aria-label="Ask the Desk question"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            maxLength={400}
            placeholder="Why was 17703 flagged?"
          />
        </label>
        <button className="small-button" disabled={!question.trim()}>
          Ask the Desk
        </button>
      </form>
    </section>
  );
}

export function ReviewControls({
  tracts,
  selected,
  events,
  distance,
  conservative,
  onRecord,
  onSelect,
}) {
  const [reason, setReason] = useState(""),
    [target, setTarget] = useState(""),
    [error, setError] = useState("");
  const [needReason, setNeedReason] = useState("");
  const eligible = new Set(
    candidates(tracts, distance, conservative).map((t) => t.geoid),
  );
  const need = needSummary(events, selected.geoid);
  const options = [...tracts].sort(
    (a, b) =>
      Number(eligible.has(b.geoid)) - Number(eligible.has(a.geoid)) ||
      a.geoid.localeCompare(b.geoid),
  );
  function recordVote(choice) {
    try {
      onRecord(needVote(choice, needReason));
      setNeedReason("");
      setError("");
    } catch (e) {
      setError(e.message);
    }
  }
  return (
    <section className="desk-panel">
      <p className="desk-disclosure">
        Human judgments are separate from source evidence. These controls never
        establish that a tract is currently unserved or dispatch a route.
      </p>
      {error && (
        <p role="alert" className="desk-error">
          {error}
        </p>
      )}
      <div className="desk-controls">
        <h3>Confirm or challenge inferred need</h3>
        <p>
          Confirm means you support the screening hypothesis for
          investigation—not a verified service gap. Opinions from both reviewers
          remain visible.
        </p>
        {need.conflict && (
          <strong className="desk-error">
            Need hypothesis disagreement — verify locally
          </strong>
        )}
        {need.votes.map((v) => (
          <p key={v.reviewer}>
            {v.reviewer}: {v.choice === "confirm" ? "Supports" : "Challenges"} —{" "}
            {v.reason}
          </p>
        ))}
        <label>
          Reason for need hypothesis
          <textarea
            aria-label="Need hypothesis reason"
            value={needReason}
            onChange={(e) => setNeedReason(e.target.value)}
            maxLength={600}
          />
        </label>
        <button
          className="small-button"
          disabled={!needReason.trim()}
          onClick={() => recordVote("confirm")}
        >
          Confirm screening hypothesis
        </button>
        <button
          className="small-button"
          disabled={!needReason.trim()}
          onClick={() => recordVote("challenge")}
        >
          Challenge inferred need
        </button>
      </div>
      <form
        className="desk-controls"
        onSubmit={(e) => {
          e.preventDefault();
          try {
            const entry = replacementEvent(selected.geoid, target, reason, {
              tracts,
              events,
              distance,
              conservative,
            });
            onRecord(entry);
            setError("");
            setReason("");
            setTarget("");
            onSelect(target);
          } catch (err) {
            setError(err.message);
          }
        }}
      >
        <h3>Replace this recommendation</h3>
        <p>
          Swap a tract in the active planning list. Evidence counts and scores
          remain unchanged; a replacement already listed is moved, not
          duplicated.
        </p>
        <label>
          Replacement tract
          <select
            aria-label="Replacement tract"
            value={target}
            onChange={(e) => setTarget(e.target.value)}
            required
          >
            <option value="">Choose another tract…</option>
            {options
              .filter((t) => t.geoid !== selected.geoid)
              .map((t) => (
                <option key={t.geoid} value={t.geoid}>
                  {t.neighborhood_label} · {t.geoid}
                  {eligible.has(t.geoid) ? "" : " — OUTSIDE SCREENING"}
                </option>
              ))}
          </select>
        </label>
        {target && !eligible.has(target) && (
          <p className="desk-warning">
            Manual override: target is outside the active evidence-screening
            shortlist. This does not change its evidence or prove need.
          </p>
        )}
        <label>
          Reason for replacement
          <textarea
            aria-label="Replacement reason"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            maxLength={600}
            required
          />
        </label>
        <button className="small-button" disabled={!target || !reason.trim()}>
          Record replacement
        </button>
      </form>
    </section>
  );
}

export function Observations({ events, selected, reviewer, onRecord }) {
  const [edit, setEdit] = useState(null),
    [text, setText] = useState(""),
    [reason, setReason] = useState(""),
    [error, setError] = useState("");
  const notes = reviewSummary(events, selected.geoid).notes;
  function begin(note, action) {
    setEdit({ noteId: note.id, action });
    setText(note.text);
    setReason("");
    setError("");
  }
  return (
    <section className="desk-panel">
      <h3>Current local observations</h3>
      <p className="tiny">
        Unverified user input. Amend only your own observations; originals and
        withdrawal reasons remain in the review trail. Reviewer aliases are not
        authentication.
      </p>
      {notes.map((n) => (
        <article className="desk-observation" key={n.id}>
          <strong>
            {n.reviewer} · {n.kind}
            {n.demo ? " · DEMO INPUT" : ""}
            {n.edited ? " · edited" : ""}
          </strong>
          <p>{n.text}</p>
          {n.reviewer === reviewer && n.id && (
            <div>
              <button className="text-button" onClick={() => begin(n, "edit")}>
                Edit observation
              </button>
              {" · "}
              <button
                className="text-button"
                onClick={() => begin(n, "deactivate")}
              >
                Deactivate observation
              </button>
            </div>
          )}
        </article>
      ))}
      {!notes.length && (
        <p className="muted">
          No active observations. Withdrawn entries remain in the audit.
        </p>
      )}
      {edit && (
        <form
          className="desk-controls"
          onSubmit={(e) => {
            e.preventDefault();
            try {
              onRecord(
                observationChange(edit.action, edit.noteId, {
                  text,
                  reason,
                  events,
                  geoid: selected.geoid,
                  reviewer,
                }),
              );
              setEdit(null);
              setError("");
            } catch (err) {
              setError(err.message);
            }
          }}
        >
          <h3>
            {edit.action === "edit"
              ? "Amend observation"
              : "Deactivate observation"}
          </h3>
          {edit.action === "edit" && (
            <label>
              Updated unverified text
              <textarea
                aria-label="Updated observation"
                value={text}
                onChange={(e) => setText(e.target.value)}
                maxLength={600}
                required
              />
            </label>
          )}
          <label>
            Reason for change
            <textarea
              aria-label="Observation change reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              maxLength={300}
              required
            />
          </label>
          {error && (
            <p role="alert" className="desk-error">
              {error}
            </p>
          )}
          <div>
            <button
              className="small-button"
              disabled={
                !reason.trim() || (edit.action === "edit" && !text.trim())
              }
            >
              Save observation change
            </button>
            <button
              className="text-button"
              type="button"
              onClick={() => setEdit(null)}
            >
              Cancel
            </button>
          </div>
        </form>
      )}
    </section>
  );
}

export function CommunityFlyer({ selected, onDownload }) {
  const [fields, setFields] = useState({ pantry: "", time: "", address: "" }),
    [copyStatus, setCopyStatus] = useState("");
  const flyer = communityFlyer(selected, fields);
  async function copy() {
    try {
      if (!navigator.clipboard?.writeText) throw Error("Clipboard unavailable");
      await navigator.clipboard.writeText(flyer.text);
      setCopyStatus("Copied draft text. Review before sharing.");
    } catch {
      setCopyStatus(
        "Clipboard unavailable: select and copy the plain text below.",
      );
    }
  }
  function open() {
    const url = URL.createObjectURL(
      new Blob([flyer.html], { type: "text/html" }),
    );
    window.open(url, "_blank", "noopener");
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  }
  return (
    <section className="desk-panel">
      <p className="desk-disclosure">
        Resident-facing draft: no internal scores, staff names or review notes.
        Unfilled fields remain visibly marked placeholders. Verify details
        before sharing; this app never sends or posts.
      </p>
      <div className="flyer-fields">
        {[
          ["pantry", "Pantry / program name"],
          ["time", "Date / time (use MM/YYYY for dates)"],
          ["address", "Location / address"],
        ].map(([key, label]) => (
          <label key={key}>
            {label}
            <input
              aria-label={`Flyer ${key}`}
              maxLength={200}
              value={fields[key]}
              placeholder="Organizer to fill — not verified by this app"
              onChange={(e) => setFields({ ...fields, [key]: e.target.value })}
            />
          </label>
        ))}
      </div>
      <div className="desk-actions">
        <button
          className="small-button"
          onClick={() =>
            onDownload(
              `beacon-${selected.geoid}-community-draft.html`,
              flyer.html,
            )
          }
        >
          Download community flyer
        </button>
        <button className="small-button" onClick={open}>
          Open / print community flyer
        </button>
        <button className="small-button" onClick={copy}>
          Copy community text
        </button>
      </div>
      {copyStatus && <p role="status">{copyStatus}</p>}
      <details>
        <summary>Plain text for copying</summary>
        <textarea
          aria-label="Community flyer plain text"
          value={flyer.text}
          readOnly
          rows={12}
        />
      </details>
      <iframe
        className="desk-preview"
        title="Resident-facing community flyer"
        srcDoc={flyer.html}
      />
    </section>
  );
}
