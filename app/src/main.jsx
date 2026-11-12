import SnapGapCard from "./SnapGapCard.jsx";
import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import {
  MapPinned,
  Layers,
  ArrowUpRight,
  ArrowUp,
  ArrowDown,
  Check,
  CheckCheck,
  X,
  ChevronRight,
  ChevronDown,
  Search,
  SlidersHorizontal,
  ShieldCheck,
  Info,
  Download,
  FileText,
  MessageSquare,
  Users,
  Flag,
  Clock,
  LocateFixed,
  Compass,
  AlertTriangle,
  ArrowRight,
  ClipboardCheck,
  Route,
  Activity,
  ExternalLink,
  Plus,
  Printer,
  RotateCcw,
} from "lucide-react";
import {
  Q75,
  STORAGE_KEY,
  PROBLEM,
  format,
  month,
  displayName,
  candidates,
  orderCandidates,
  reviewSummary,
  moveInOrder,
  briefHTML,
  escapeHTML,
} from "./domain.js";
import "./styles.css";
import {
  AskDesk,
  ReviewControls,
  Observations,
  CommunityFlyer,
} from "./DeskPanels.jsx";
import { applyReplacements, needSummary } from "./desk.js";

function loadWorkspace() {
  try {
    return (
      JSON.parse(localStorage.getItem(STORAGE_KEY)) || { events: [], order: [] }
    );
  } catch {
    return {
      events: [],
      order: [],
      warning:
        "Stored workspace could not be read. Export a backup before clearing browser storage.",
    };
  }
}
function download(name, text, type = "text/html") {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}
const statusLabels = {
  approve: "Approved for verification",
  reject: "Rejected by reviewer",
  unreviewed: "Not yet reviewed",
  disagreement: "Reviewer disagreement",
};
function Badge({ children, tone = "", icon: Icon }) {
  return (
    <span className={`badge ${tone}`}>
      {Icon && <Icon size={12} />} {children}
    </span>
  );
}
function Modal({ title, subtitle, children, onClose, wide = false }) {
  useEffect(() => {
    const f = (e) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", f);
    return () => window.removeEventListener("keydown", f);
  }, [onClose]);
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <section
        className={`modal ${wide ? "wide" : ""}`}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={(e) => e.stopPropagation()}
      >
        <header className="modal-header">
          <div>
            <h2>{title}</h2>
            {subtitle && <p>{subtitle}</p>}
          </div>
          <button
            className="icon-button"
            aria-label="Close dialog"
            onClick={onClose}
          >
            <X size={20} />
          </button>
        </header>
        {children}
      </section>
    </div>
  );
}
function TractMap({
  geo,
  tracts,
  distance,
  conservative,
  selected,
  onSelect,
  focusToken,
}) {
  const host = useRef(),
    map = useRef(),
    layers = useRef(new Map()),
    marker = useRef();
  const byId = useMemo(
    () => new Map(tracts.map((t) => [t.geoid, t])),
    [tracts],
  );
  useEffect(() => {
    const m = L.map(host.current, {
      zoomControl: false,
      preferCanvas: true,
      attributionControl: false,
      minZoom: 7,
      maxZoom: 15,
    });
    map.current = m;
    L.control.zoom({ position: "bottomright" }).addTo(m);
    const group = L.geoJSON(geo, {
      style: {
        color: "#c5d1d8",
        weight: 0.65,
        fillColor: "#dfe7eb",
        fillOpacity: 0.8,
      },
      onEachFeature: (f, layer) => {
        const id = f.properties.geoid;
        layers.current.set(id, layer);
        layer.on("click", () => onSelect(id));
        layer.bindTooltip(
          () => {
            const t = byId.get(id);
            return `${escapeHTML(displayName(t))} · tract ${escapeHTML(t.tract_number)}<br>Poverty: ${format(t.poverty_pct)}%`;
          },
          { sticky: true, direction: "top" },
        );
      },
    }).addTo(m);
    m.fitBounds(group.getBounds(), { padding: [28, 28] });
    const resize = new ResizeObserver(() => m.invalidateSize());
    resize.observe(host.current);
    return () => {
      resize.disconnect();
      m.remove();
      map.current = null;
      layers.current.clear();
    };
  }, [geo]);
  useEffect(() => {
    for (const [id, layer] of layers.current) {
      const t = byId.get(id),
        eligible = t && t[`lila_${distance}_half_10`] === 1,
        robust = !conservative || t?.poverty_lower90_pct >= Q75;
      let color = "#e2e9ed";
      if (eligible && robust && t.poverty_pct != null) {
        color =
          t.poverty_pct >= 35
            ? "#a14d0b"
            : t.poverty_pct >= 25
              ? "#d67516"
              : t.poverty_pct >= Q75
                ? "#F79122"
                : "#FDCB9C";
      }
      layer.setStyle({
        fillColor: color,
        fillOpacity:
          id === selected?.geoid?.toString()
            ? 1
            : eligible && robust
              ? 0.85
              : 0.55,
        color: id === selected?.geoid ? "#1E343F" : "#afc0ca",
        weight: id === selected?.geoid ? 2.7 : 0.65,
      });
    }
    const layer = layers.current.get(selected?.geoid);
    if (layer && map.current) {
      layer.bringToFront();
      if (marker.current) marker.current.remove();
      marker.current = L.circleMarker(layer.getBounds().getCenter(), {
        radius: 8,
        color: "#fff",
        weight: 3,
        fillColor: "#1E343F",
        fillOpacity: 1,
      }).addTo(map.current);
    }
  }, [distance, conservative, selected, byId]);
  useEffect(() => {
    const layer = layers.current.get(selected?.geoid);
    if (focusToken && layer && map.current)
      map.current.flyToBounds(layer.getBounds(), {
        padding: [65, 65],
        maxZoom: 13,
        duration: 0.6,
      });
  }, [focusToken]);
  return (
    <div className="map-shell">
      <div
        ref={host}
        className="tract-map"
        aria-label="Interactive map of 490 Central Florida census tracts"
      />
      <div className="map-title">
        <div className="map-dot" />
        <div>
          <strong>Central Florida</strong>
          <small>490 tracts · 4 counties</small>
        </div>
      </div>
      <div className="north">
        <Compass size={23} />
        <span>N</span>
      </div>
      <div className="map-caption">
        Census tract boundaries · No site location implied
      </div>
      <div className="map-legend">
        <div>
          SCREENING PRIORITY <Info size={11} />
        </div>
        <section>
          <i style={{ background: "#e2e9ed" }} />
          <i style={{ background: "#FDCB9C" }} />
          <i style={{ background: "#F79122" }} />
          <i style={{ background: "#d67516" }} />
          <i style={{ background: "#a14d0b" }} />
        </section>
        <footer>
          <span>Not LILA / filtered</span>
          <span>Higher poverty</span>
        </footer>
      </div>
    </div>
  );
}

function App() {
  const [data, setData] = useState(),
    [error, setError] = useState(),
    [workspace, setWorkspace] = useState(loadWorkspace),
    [selectedId, setSelectedId] = useState(
      new URLSearchParams(location.search).get("tract") || "12095017703",
    ),
    [distance, setDistance] = useState("sd"),
    [conservative, setConservative] = useState(false),
    [query, setQuery] = useState(""),
    [county, setCounty] = useState("All counties"),
    [reviewer, setReviewer] = useState("Organizer"),
    [modal, setModal] = useState(null),
    [reason, setReason] = useState(""),
    [note, setNote] = useState(""),
    [owner, setOwner] = useState(""),
    [status, setStatus] = useState("Needs verification"),
    [focusToken, setFocusToken] = useState(0),
    [tab, setTab] = useState("evidence"),
    [toast, setToast] = useState(""),
    [changeDirection, setChangeDirection] = useState(0),
    [reorderId, setReorderId] = useState(null),
    [flagged, setFlagged] = useState(false);
  useEffect(() => {
    Promise.all(
      [
        "tracts.json",
        "tracts.geojson",
        "review_report.json",
        "metadata.json",
        "run_info.json",
        "snap_gap.json",
      ].map((name) =>
        fetch(`./data/${name}`).then((r) => {
          if (!r.ok) throw Error(`${name}: ${r.status}`);
          return r.json();
        }),
      ),
    )
      .then(([table, geo, health, meta, run, gaps]) => {
        const byId = new Map(gaps.rows.map((row) => [row.geoid, row]));
        setData({
          tracts: table.tracts.map((t) => ({
            ...t,
            snap_gap: byId.get(t.geoid),
          })),
          geo,
          health,
          meta,
          run,
        });
      })
      .catch((e) => setError(e.message));
  }, []);
  useEffect(() => {
    const onStorage = (e) => {
      if (e.key === STORAGE_KEY) {
        setWorkspace(loadWorkspace());
        setToast("Local workspace updated from another tab");
      }
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);
  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(""), 3400);
      return () => clearTimeout(timer);
    }
  }, [toast]);
  const selected =
      data?.tracts.find((t) => t.geoid === selectedId) || data?.tracts[0],
    summary = reviewSummary(workspace.events || [], selected?.geoid);
  useEffect(() => {
    setOwner(summary.assignment?.owner || "");
    setStatus(summary.assignment?.status || "Needs verification");
    setNote("");
    setFlagged(false);
  }, [selectedId, workspace.events.length]);
  const allCandidates = useMemo(
    () => (data ? candidates(data.tracts, distance, conservative) : []),
    [data, distance, conservative],
  );
  const ranked = useMemo(
    () =>
      data
        ? applyReplacements(
            orderCandidates(allCandidates, workspace.order),
            data.tracts,
            workspace.events,
          )
        : [],
    [allCandidates, workspace.order, workspace.events, data],
  );
  const visible = ranked.filter(
    (t) =>
      (county === "All counties" || t.county === county) &&
      `${t.neighborhood_label} ${t.geoid} ${t.tract_number}`
        .toLowerCase()
        .includes(query.toLowerCase()),
  );
  const robustCount = data ? candidates(data.tracts, distance, true).length : 0;
  function persist(edit) {
    const current = loadWorkspace();
    const next = edit(current);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    setWorkspace(next);
  }
  function event(payload) {
    const entry = {
      ...payload,
      id: crypto.randomUUID(),
      geoid: selected.geoid,
      reviewer,
      at: Date.now(),
    };
    persist((current) => ({ ...current, events: [...current.events, entry] }));
    return entry;
  }
  function select(id) {
    setSelectedId(id);
    setFocusToken((x) => x + 1);
    const url = new URL(location.href);
    url.searchParams.set("tract", id);
    history.replaceState(null, "", url);
  }
  function askDecision(decision) {
    setReason("");
    setModal(decision);
  }
  function saveDecision(e) {
    e.preventDefault();
    if (!reason.trim()) return;
    event({ kind: "decision", decision: modal, reason: reason.trim() });
    setModal(null);
    setToast("Decision recorded. Nothing has been dispatched.");
  }
  function reorder(t, direction) {
    setReason("");
    setReorderId(t.geoid);
    setChangeDirection(direction);
    setModal("reorder");
  }
  function saveReorder(e) {
    e.preventDefault();
    if (!reason.trim()) return;
    const order = moveInOrder(ranked, reorderId, changeDirection);
    persist((current) => ({
      ...current,
      order,
      events: [
        ...current.events,
        {
          id: crypto.randomUUID(),
          geoid: reorderId,
          reviewer,
          at: Date.now(),
          kind: "reorder",
          reason: reason.trim(),
          text: `Moved ${changeDirection < 0 ? "up" : "down"} in planning shortlist`,
        },
      ],
    }));
    setModal(null);
    setToast("Manual planning order updated; evidence values unchanged.");
  }
  function addNote(e) {
    e.preventDefault();
    if (!note.trim()) return;
    event({
      kind: flagged ? "flag" : "note",
      text: note.trim(),
      demo: note.startsWith("DEMO INPUT"),
    });
    setNote("");
    setFlagged(false);
    setToast("Local observation saved as unverified input.");
  }
  function saveAssignment(e) {
    e.preventDefault();
    if (!owner.trim()) return;
    event({
      kind: "assignment",
      owner: owner.trim(),
      status,
      text: `Assigned to ${owner.trim()} · ${status}`,
    });
    setToast("Owner and verification status saved locally.");
  }
  function exportBrief() {
    setModal("brief");
  }
  if (error)
    return (
      <div className="loading">
        <AlertTriangle size={30} />
        <h1>Data could not be loaded</h1>
        <p>{error}</p>
        <p>
          Run npm start from the app folder to refresh the audited data
          snapshot.
        </p>
      </div>
    );
  if (!data || !selected)
    return (
      <div className="loading">
        <div className="loader" />
        <p>Preparing an evidence-led shortlist…</p>
      </div>
    );
  const selectedEligible = allCandidates.some(
      (t) => t.geoid === selected.geoid,
    ),
    approved = workspace.events
      .filter((e) => e.kind === "decision" && e.decision === "approve")
      .map((e) => e.geoid),
    hasBlocking = data.health.blocking,
    needReview = needSummary(workspace.events, selected.geoid);
  const brief = briefHTML(
    selected,
    workspace,
    distance,
    conservative,
    data.meta,
  );
  return (
    <div className="app-shell">
      <aside className="rail">
        <img src="./brand/beacon-white.png" className="brand" alt="Beacon" />
        <div className="rail-divider" />
        <button className="rail-item active" aria-label="Neighborhood planning">
          <MapPinned size={23} />
          <span>Plan</span>
        </button>
        <button
          className="rail-item"
          onClick={() => setModal("health")}
          aria-label="Data health"
        >
          <Activity size={23} />
          <span>Data</span>
        </button>
        <button
          className="rail-item"
          onClick={() => setModal("about")}
          aria-label="About the prototype"
        >
          <Info size={23} />
          <span>About</span>
        </button>
        <div className="rail-bottom">
          <span className="connected-dot" />
          <span>
            LOCAL
            <br />
            PROTOTYPE
          </span>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div className="breadcrumbs">
            BEACON <ChevronRight size={12} /> COMMUNITY OPERATIONS{" "}
            <ChevronRight size={12} /> <b>ACTION DESK</b>
          </div>
          <div className="topbar-right">
            <span className="local-label">
              <span className="connected-dot" /> Same-browser workspace
            </span>
            <label className="reviewer-select">
              <span className="avatar">
                {reviewer === "Organizer" ? "OR" : "FR"}
              </span>
              <select
                aria-label="Active reviewer"
                value={reviewer}
                onChange={(e) => setReviewer(e.target.value)}
              >
                <option>Organizer</option>
                <option>Field reviewer</option>
              </select>
            </label>
          </div>
        </header>
        <main>
          <section className="page-heading">
            <div>
              <div className="eyebrow">
                CENTRAL FLORIDA · FOOD ACCESS PLANNING
              </div>
              <h1>One route. A defensible next stop.</h1>
              <p>
                Turn public-data signals into a locally verified decision. Keep
                the reasoning with it.
              </p>
            </div>
            <div className="heading-actions">
              <button
                className="small-button ask-launch"
                onClick={() => setModal("ask")}
              >
                Ask the Desk
              </button>
              <button
                className={`health-button ${hasBlocking ? "bad" : ""}`}
                onClick={() => setModal("health")}
              >
                <ShieldCheck size={17} />
                <div>
                  <strong>Data health</strong>
                  <span>
                    {hasBlocking
                      ? "Blocking issues need review"
                      : "No blocking issues"}{" "}
                    · {data.health.items.length} review note
                  </span>
                </div>
                <ChevronRight size={16} />
              </button>
            </div>
          </section>
          {workspace.events.some((e) => e.kind === "replacement") && (
            <div className="desk-disclosure">
              Manual replacement plan: {ranked.length} tracts in the current
              planning list. The evidence screen still has{" "}
              {allCandidates.length} candidates; source scores are unchanged.
            </div>
          )}
          {workspace.warning && (
            <div className="warning-box">{workspace.warning}</div>
          )}
          <section className="metrics">
            <div className="metric-card">
              <div className="metric-icon orange">
                <MapPinned size={20} />
              </div>
              <div>
                <strong>
                  {allCandidates.length}
                  <small>areas to investigate</small>
                </strong>
                <span>
                  {distance === "sd" ? "Straight-line" : "Driving"} LILA + high
                  poverty
                </span>
              </div>
            </div>
            <div className="metric-card">
              <div className="metric-icon blue">
                <ShieldCheck size={20} />
              </div>
              <div>
                <strong>
                  {robustCount}
                  <small>robust to uncertainty</small>
                </strong>
                <span>Poverty lower bound stays above Q75</span>
              </div>
            </div>
            <div className="metric-card">
              <div className="metric-icon slate">
                <Layers size={20} />
              </div>
              <div>
                <strong>
                  490<small>tracts · 4 counties</small>
                </strong>
                <span>Lake, Orange, Osceola, Seminole</span>
              </div>
            </div>
            <div className="metric-card scenario">
              <div className="metric-icon orange">
                <Route size={20} />
              </div>
              <div>
                <strong>
                  1<small>new route to place</small>
                </strong>
                <span>Demo scenario · not a data estimate</span>
              </div>
            </div>
          </section>
          <section className="control-bar">
            <div className="lens-label">
              <SlidersHorizontal size={16} />
              <b>Evidence lens</b>
              <span>Compare definitions, not just a score.</span>
            </div>
            <div className="lens-options">
              <div
                className="segmented"
                role="group"
                aria-label="Access distance definition"
              >
                <button
                  className={distance === "sd" ? "selected" : ""}
                  onClick={() => setDistance("sd")}
                >
                  Straight-line
                </button>
                <button
                  className={distance === "dd" ? "selected" : ""}
                  onClick={() => setDistance("dd")}
                >
                  Driving distance
                </button>
              </div>
              <label className="toggle">
                <input
                  type="checkbox"
                  checked={conservative}
                  onChange={(e) => setConservative(e.target.checked)}
                />
                <span className="toggle-track" />
                <span>Conservative uncertainty</span>
                <Info size={13} />
              </label>
            </div>
          </section>
          <div className="desk-grid">
            <section className="shortlist panel">
              <header className="panel-heading">
                <div>
                  <span className="eyebrow">YOUR PLANNING QUEUE</span>
                  <h2>
                    Neighborhood shortlist{" "}
                    <span className="count">{visible.length}</span>
                  </h2>
                </div>
                <ClipboardCheck size={21} />
              </header>
              <div className="search-box">
                <Search size={15} />
                <input
                  aria-label="Search shortlist"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search an area or tract…"
                />
              </div>
              <div className="list-filters">
                <select
                  aria-label="Filter county"
                  value={county}
                  onChange={(e) => setCounty(e.target.value)}
                >
                  <option>All counties</option>
                  {["Lake", "Orange", "Osceola", "Seminole"].map((v) => (
                    <option key={v}>{v}</option>
                  ))}
                </select>
                <span>
                  {workspace.order.length
                    ? "Manual planning order"
                    : "Highest poverty first"}
                </span>
              </div>
              <div className="shortlist-rows">
                {visible.map((t, i) => {
                  const s = reviewSummary(workspace.events, t.geoid);
                  return (
                    <article
                      key={t.geoid}
                      className={`tract-row ${selected.geoid === t.geoid ? "active" : ""}`}
                    >
                      <button
                        className="tract-select"
                        onClick={() => select(t.geoid)}
                      >
                        <span className="rank">
                          {ranked.findIndex((v) => v.geoid === t.geoid) + 1}
                        </span>
                        <span className="tract-label">
                          <strong>{displayName(t)}</strong>
                          <small>
                            {t.county} Co. · tract {t.tract_number}
                          </small>
                          <span className="row-status">
                            {s.conflict ? (
                              <>
                                <AlertTriangle size={10} /> Disagreement
                              </>
                            ) : s.decision === "approve" ? (
                              <>
                                <CheckCheck size={10} /> Verify locally
                              </>
                            ) : s.decision === "reject" ? (
                              <>
                                <X size={10} /> Rejected for now
                              </>
                            ) : t.high_poverty_moe ? (
                              "Wide margin of error"
                            ) : (
                              "Stronger evidence"
                            )}
                          </span>
                        </span>
                        <span className="row-value">
                          {format(t.poverty_pct)}
                          <small>% poverty</small>
                        </span>
                      </button>
                      <div className="row-reorder">
                        <button
                          aria-label={`Move tract ${t.tract_number} up`}
                          disabled={
                            ranked.findIndex((v) => v.geoid === t.geoid) === 0
                          }
                          onClick={() => reorder(t, -1)}
                        >
                          <ArrowUp size={12} />
                        </button>
                        <button
                          aria-label={`Move tract ${t.tract_number} down`}
                          disabled={
                            ranked.findIndex((v) => v.geoid === t.geoid) ===
                            ranked.length - 1
                          }
                          onClick={() => reorder(t, 1)}
                        >
                          <ArrowDown size={12} />
                        </button>
                      </div>
                    </article>
                  );
                })}
                {!visible.length && (
                  <div className="empty">
                    No areas match this lens or search. Try a different
                    definition.
                  </div>
                )}
              </div>
              <footer className="queue-footer">
                <Info size={14} />
                <span>
                  {conservative
                    ? "Poverty lower 90% bound ≥17.0%. Descriptive check, not a significance test."
                    : "Flags identify areas to investigate—not confirmed unmet food need."}
                </span>
              </footer>
            </section>
            <section className="map-panel panel">
              <header className="map-panel-header">
                <div>
                  <span className="eyebrow">WHERE THE SIGNALS CONVERGE</span>
                  <h2>Explore the evidence</h2>
                </div>
                <button
                  className="small-button"
                  onClick={() => setFocusToken((x) => x + 1)}
                >
                  <LocateFixed size={14} /> Focus tract
                </button>
              </header>
              <TractMap
                geo={data.geo}
                tracts={data.tracts}
                distance={distance}
                conservative={conservative}
                selected={selected}
                onSelect={select}
                focusToken={focusToken}
              />
              <div className="map-foot">
                <span>
                  <span className="legend-pip" /> Color = poverty among LILA
                  tracts
                </span>
                <button onClick={() => setModal("method")}>
                  How this is calculated <ArrowUpRight size={13} />
                </button>
              </div>
            </section>
            <aside className="evidence-panel panel">
              <header className="evidence-header">
                <div>
                  <div className="eyebrow">SELECTED AREA</div>
                  <h2>{displayName(selected)}</h2>
                  <p>
                    {selected.county} County · tract{" "}
                    <b>{selected.tract_number}</b>
                  </p>
                </div>
                <div className="selected-icon">
                  <MapPinned size={21} />
                </div>
              </header>
              <div className="tract-id">
                <span>GEOID</span>
                <code>{selected.geoid}</code>
                <Badge
                  tone={
                    summary.conflict
                      ? "danger"
                      : summary.decision === "approve"
                        ? "success"
                        : ""
                  }
                >
                  {summary.conflict
                    ? "Disagreement"
                    : summary.decision === "approve"
                      ? "Verify next"
                      : summary.decision === "reject"
                        ? "Rejected"
                        : "Needs review"}
                </Badge>
              </div>
              <div className="detail-tabs">
                <button
                  className={tab === "evidence" ? "active" : ""}
                  onClick={() => setTab("evidence")}
                >
                  <Layers size={14} /> Evidence
                </button>
                <button
                  className={tab === "actions" ? "active" : ""}
                  onClick={() => setTab("actions")}
                >
                  <Users size={14} /> Review & notes{" "}
                  {summary.notes.length > 0 && (
                    <span>{summary.notes.length}</span>
                  )}
                </button>
              </div>
              <div className="detail-content">
                {!selectedEligible && (
                  <div className="notice compact">
                    <Info size={15} />
                    <span>
                      Not in the shortlist under the active lens. Its underlying
                      evidence is still shown.
                    </span>
                  </div>
                )}
                {summary.conflict && (
                  <div className="conflict-box">
                    <AlertTriangle size={17} />
                    <div>
                      <strong>Two reviewers disagree</strong>
                      <p>
                        Both positions are retained. Resolve with local
                        verification, not last-write-wins.
                      </p>
                      {summary.decisions.map((d) => (
                        <small key={d.id}>
                          {d.reviewer}: {d.decision} — {d.reason}
                        </small>
                      ))}
                    </div>
                  </div>
                )}
                {needReview.votes.length > 0 && (
                  <div
                    className={
                      needReview.conflict ? "conflict-box" : "desk-disclosure"
                    }
                  >
                    <div>
                      <strong>
                        {needReview.conflict
                          ? "Need hypothesis disagreement — local review required"
                          : "Human feedback on inferred need"}
                      </strong>
                      {needReview.votes.map((v) => (
                        <p key={v.reviewer}>
                          {v.reviewer}:{" "}
                          {v.choice === "confirm" ? "Supports" : "Challenges"} —{" "}
                          {v.reason}
                        </p>
                      ))}
                      <small>User judgment, not verified unmet demand.</small>
                    </div>
                  </div>
                )}
                {tab === "evidence" ? (
                  <>
                    <div className="evidence-confidence">
                      <span>
                        <span
                          className={`status-dot ${selected.evidence_confidence.toLowerCase()}`}
                        />
                        {selected.evidence_confidence} evidence confidence
                      </span>
                      <span className="tiny">
                        Human review{" "}
                        {selected.review_tier === "Review required"
                          ? "required"
                          : "recommended"}
                      </span>
                    </div>
                    <section className="poverty-card">
                      <div className="card-label">
                        PEOPLE BELOW THE POVERTY LINE <Info size={12} />
                      </div>
                      <div className="poverty-number">
                        {format(selected.poverty_pct)}
                        <span>%</span>
                        <small>±{format(selected.poverty_moe_pp)} pp</small>
                      </div>
                      <div className="range-labels">
                        <span>{format(selected.poverty_lower90_pct)}%</span>
                        <span>{format(selected.poverty_upper90_pct)}%</span>
                      </div>
                      <div className="range-bar">
                        <div
                          style={{
                            left: `${selected.poverty_lower90_pct ?? 0}%`,
                            width: `${(selected.poverty_upper90_pct ?? 0) - (selected.poverty_lower90_pct ?? 0)}%`,
                          }}
                        />
                        <i style={{ left: `${selected.poverty_pct ?? 0}%` }} />
                      </div>
                      <div className="range-caption">
                        90% uncertainty interval · estimate, not a headcount
                      </div>
                    </section>
                    <div className="why-heading">
                      <Check size={15} />
                      <strong>Why this was flagged</strong>
                    </div>
                    <ul className="reason-list">
                      <li>
                        <span className="reason-check">
                          <Check size={12} />
                        </span>
                        <span>
                          {selected.poverty_pct >= Q75 ? (
                            <>
                              Poverty estimate exceeds the{" "}
                              <b>{Q75.toFixed(1)}%</b> regional screening
                              cutoff.
                            </>
                          ) : (
                            <>
                              Poverty estimate does not cross the{" "}
                              <b>{Q75.toFixed(1)}%</b> regional screening
                              cutoff.
                            </>
                          )}
                        </span>
                      </li>
                      <li>
                        <span className="reason-check">
                          <Check size={12} />
                        </span>
                        <span>
                          {selected[`lila_${distance}_half_10`] === 1 ? (
                            <>
                              Low income + low access to{" "}
                              <b>SNAP-authorized stores</b>.
                            </>
                          ) : (
                            <>
                              Not flagged under the selected low-income /
                              low-access definition.
                            </>
                          )}
                        </span>
                      </li>
                    </ul>
                    <div className="distance-flags">
                      <div>
                        <span>Straight-line</span>
                        <Badge
                          tone={selected.lila_sd_half_10 === 1 ? "success" : ""}
                          icon={selected.lila_sd_half_10 === 1 ? Check : Info}
                        >
                          {selected.lila_sd_half_10 === 1
                            ? "LILA flagged"
                            : "Not flagged"}
                        </Badge>
                      </div>
                      <div>
                        <span>Driving distance</span>
                        <Badge
                          tone={selected.lila_dd_half_10 === 1 ? "success" : ""}
                          icon={selected.lila_dd_half_10 === 1 ? Check : Info}
                        >
                          {selected.lila_dd_half_10 === 1
                            ? "LILA flagged"
                            : "Not flagged"}
                        </Badge>
                      </div>
                    </div>
                    <div className="warning-box">
                      <AlertTriangle size={16} />
                      <div>
                        <strong>
                          {selected.high_poverty_moe
                            ? "Wide margin of error"
                            : "Read the uncertainty"}
                        </strong>
                        <p>
                          ACS is sample-based. Actual tract sample size is not
                          supplied; a wide error bar does not prove a small
                          sample.
                        </p>
                      </div>
                    </div>
                    <div className="context-line">
                      <span>Households receiving SNAP</span>
                      <b>
                        {format(selected.snap_pct)}%{" "}
                        <small>±{format(selected.snap_moe_pp)} pp</small>
                      </b>
                    </div>
                    <SnapGapCard gap={selected.snap_gap} tract={selected} />
                    <div className="mapping-line">
                      <MapPinned size={14} />
                      <div>
                        <strong>
                          {selected.mapping_confidence} mapping confidence
                        </strong>
                        <p>
                          {selected.official_neighborhood
                            ? "Official Orlando neighborhood overlap"
                            : "Census place / CDP context"}{" "}
                          · {format(selected.largest_place_area_share * 100)}%
                          area overlap. A tract is not a neighborhood.
                        </p>
                      </div>
                    </div>
                    <details className="limitations">
                      <summary>
                        Sources, vintage & what we do not know{" "}
                        <ChevronDown size={14} />
                      </summary>
                      <p>
                        ACS 01/2020–12/2024. SRAM released 07/2026; store
                        snapshot 06/2025 and population base 04/2020. SRAM
                        includes SNAP-authorized stores, not supermarket-only
                        access. Central Florida’s adult reliable-transportation
                        rate is unavailable. No current pantry capacity, hours,
                        site suitability or unmet demand is measured.
                      </p>
                      <a
                        href={data.meta.usdaDocumentation}
                        target="_blank"
                        rel="noreferrer"
                      >
                        USDA definitions <ExternalLink size={11} />
                      </a>
                    </details>
                  </>
                ) : (
                  <>
                    <div className="local-collaboration">
                      <Users size={16} />
                      <div>
                        <strong>Local review room</strong>
                        <span>
                          Switch reviewer above or open a second tab.
                          Same-browser storage only—not cloud collaboration.
                        </span>
                      </div>
                    </div>
                    {summary.decisions.length > 0 && (
                      <div className="decision-list">
                        {summary.decisions.map((d) => (
                          <div key={d.id}>
                            <Badge
                              tone={
                                d.decision === "approve" ? "success" : "danger"
                              }
                            >
                              {d.decision === "approve" ? "Approve" : "Reject"}
                            </Badge>
                            <strong>{d.reviewer}</strong>
                            <p>{d.reason}</p>
                          </div>
                        ))}
                      </div>
                    )}
                    <form className="assignment-form" onSubmit={saveAssignment}>
                      <h3>Give the next step an owner</h3>
                      <label>
                        Volunteer / owner
                        <input
                          value={owner}
                          required
                          maxLength={60}
                          onChange={(e) => setOwner(e.target.value)}
                          placeholder="e.g., Volunteer 1"
                        />
                      </label>
                      <label>
                        Verification status
                        <select
                          value={status}
                          onChange={(e) => setStatus(e.target.value)}
                        >
                          <option>Needs verification</option>
                          <option>Assigned</option>
                          <option>In progress</option>
                          <option>Verified locally</option>
                          <option>Blocked / conflicting evidence</option>
                        </select>
                      </label>
                      <button className="small-button" type="submit">
                        <Check size={13} /> Save assignment
                      </button>
                    </form>
                    <form className="note-form" onSubmit={addNote}>
                      <div className="form-title">
                        <h3>Add local knowledge</h3>
                        <Badge>Unverified input</Badge>
                      </div>
                      <textarea
                        value={note}
                        maxLength={600}
                        rows={3}
                        onChange={(e) => setNote(e.target.value)}
                        placeholder="What should the next reviewer know? Existing services, partner questions, site constraints…"
                      />
                      <div className="note-options">
                        <label>
                          <input
                            type="checkbox"
                            checked={flagged}
                            onChange={(e) => setFlagged(e.target.checked)}
                          />{" "}
                          Flag for local review
                        </label>
                        <button
                          type="button"
                          className="text-button"
                          onClick={() =>
                            setNote(
                              "DEMO INPUT (unverified): church on Main St already runs a Tuesday pantry here.",
                            )
                          }
                        >
                          Use demo example
                        </button>
                      </div>
                      <button
                        type="submit"
                        className="small-button"
                        disabled={!note.trim()}
                      >
                        <Plus size={13} /> Save observation
                      </button>
                    </form>
                    <Observations
                      key={selected.geoid + reviewer}
                      events={workspace.events}
                      selected={selected}
                      reviewer={reviewer}
                      onRecord={event}
                    />
                    <div className="audit-heading">
                      <h3>Review trail</h3>
                      <span>
                        {summary.history.length} entries · append-only
                      </span>
                    </div>
                    <div className="audit-list">
                      {[...summary.history].reverse().map((e) => (
                        <div className="audit-item" key={e.id}>
                          <div className="audit-dot" />
                          <div>
                            <strong>
                              {e.reviewer}{" "}
                              <span>
                                · {e.kind}
                                {e.demo ? " · DEMO INPUT" : ""}
                              </span>
                            </strong>
                            <p>
                              {e.kind === "reorder"
                                ? `${e.text}: ${e.reason}`
                                : [
                                      "observation_edit",
                                      "observation_deactivate",
                                    ].includes(e.kind)
                                  ? `${e.text} · Change reason: ${e.reason}`
                                  : e.text ||
                                    `${e.decision === "approve" ? "Approved" : "Rejected"}: ${e.reason}`}{" "}
                            </p>
                            <small>
                              {month(e.at)} ET · user-entered, not source data
                            </small>
                          </div>
                        </div>
                      ))}
                      {!summary.history.length && (
                        <p className="muted">
                          No human review yet. Machine flags do not allocate a
                          route.
                        </p>
                      )}
                    </div>
                  </>
                )}
              </div>
              <footer className="action-footer">
                <div className="review-actions">
                  <button
                    className="approve"
                    onClick={() => askDecision("approve")}
                  >
                    <Check size={16} /> Approve to verify
                  </button>
                  <button
                    className="reject"
                    onClick={() => askDecision("reject")}
                  >
                    <X size={15} /> Reject
                  </button>
                </div>
                <button
                  className="small-button"
                  onClick={() => setModal("controls")}
                >
                  Replace / review inferred need
                </button>
                <button
                  className="small-button"
                  onClick={() => setModal("flyer")}
                >
                  Community flyer / message
                </button>
                <button
                  className={
                    summary.decisions.length > 0
                      ? "export-button export-button-ready"
                      : "export-button"
                  }
                  onClick={exportBrief}
                >
                  <FileText size={15} /> Create decision brief{" "}
                  <ArrowUpRight size={14} />
                </button>
              </footer>
            </aside>
          </div>
          <footer className="page-footer">
            <span>
              <ShieldCheck size={13} /> Evidence informs. Local organizers
              decide.
            </span>
            <span>
              Source snapshot 11/2026 · No external deployment ·{" "}
              <button onClick={() => setModal("about")}>
                About this prototype
              </button>
            </span>
          </footer>
        </main>
      </div>
      {(modal === "approve" || modal === "reject") && (
        <Modal
          title={
            modal === "approve"
              ? "Approve for local verification"
              : "Reject this recommendation"
          }
          subtitle={`${displayName(selected)} · tract ${selected.tract_number} · ${reviewer}`}
          onClose={() => setModal(null)}
        >
          <form onSubmit={saveDecision}>
            <div className="notice">
              Approval is a decision to investigate—not permission to dispatch a
              truck or claim an unmet service gap.
            </div>
            <label className="block-label">
              Why this decision?
              <textarea
                autoFocus
                required
                maxLength={300}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                rows={4}
                placeholder="Record the reasoning another teammate or funder should see."
              />
            </label>
            <button className="primary" type="submit" disabled={!reason.trim()}>
              {modal === "approve" ? "Record approval" : "Record rejection"}{" "}
              <ArrowRight size={15} />
            </button>
          </form>
        </Modal>
      )}
      {modal === "reorder" && (
        <Modal
          title="Change the planning order"
          subtitle="Evidence values do not change. Your reason remains in the audit trail."
          onClose={() => setModal(null)}
        >
          <form onSubmit={saveReorder}>
            <label className="block-label">
              Reason for moving this area {changeDirection < 0 ? "up" : "down"}
              <textarea
                required
                autoFocus
                maxLength={300}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                rows={3}
              />
            </label>
            <button className="primary" type="submit" disabled={!reason.trim()}>
              Save planning order
            </button>
          </form>
        </Modal>
      )}
      {modal === "about" && (
        <Modal
          title="Evidence that stands up to ‘why there?’"
          subtitle="Beacon · Neighborhood Action Desk · hackathon prototype"
          onClose={() => setModal(null)}
          wide
        >
          <div className="about-problem">{PROBLEM}</div>
          <div className="about-grid">
            <div>
              <h3>Built on open evidence</h3>
              <p>
                Census ACS, USDA SRAM and official geographic boundaries. Fixed
                core scope: Lake, Orange, Osceola and Seminole counties. Inputs
                are traceable to the source and cleaning review report.
              </p>
            </div>
            <div>
              <h3>Built for a local decision</h3>
              <p>
                Approve to investigate, challenge a signal, surface conflicting
                observations and record a rationale. Current pantry services,
                capacity and site suitability must be checked locally.
              </p>
            </div>
            <div>
              <h3>Honest about this prototype</h3>
              <p>
                Local browser storage, not a real shared backend. No accounts or
                authorization. Notes and approvals are user input. No actual
                food-bank partnership or co-design is claimed.
              </p>
            </div>
            <div>
              <h3>What happens next</h3>
              <p>
                Validate labels and workflows with organizers, connect current
                service/capacity records, then pilot a human-reviewed shortlist.
                Add authenticated collaborative storage before operational use.
              </p>
            </div>
          </div>
          <a
            className="external-link"
            href={data.meta.sourceFolder}
            target="_blank"
            rel="noreferrer"
          >
            Open original source folder <ExternalLink size={14} />
          </a>
          <button
            className="small-button"
            onClick={() =>
              download(
                "beacon-local-workspace.json",
                JSON.stringify(workspace, null, 2),
                "application/json",
              )
            }
          >
            <Download size={14} /> Download local audit backup
          </button>
        </Modal>
      )}
      {modal === "health" && (
        <Modal
          title="Data health & provenance"
          subtitle="Latest clean.py review report captured when this app starts/builds"
          onClose={() => setModal(null)}
          wide
        >
          <div className={`health-summary ${hasBlocking ? "bad" : ""}`}>
            <ShieldCheck size={25} />
            <div>
              <h3>
                {hasBlocking
                  ? "Blocking input changes require review"
                  : "No blocking pipeline issues"}
              </h3>
              <p>
                490 unique tract keys · all source snapshots retained ·{" "}
                {data.run.runtime_seconds}s last pipeline run
              </p>
            </div>
          </div>
          {data.health.items.map((item, i) => (
            <div className="health-item" key={i}>
              <Badge tone={item.blocking ? "danger" : ""}>
                {item.blocking ? "Blocking" : "Review note"}
              </Badge>
              <strong>{item.source}</strong>
              <p>{item.detail}</p>
              <code>{item.category}</code>
            </div>
          ))}
          <div className="about-grid">
            <div>
              <h3>What the cleaner fixes</h3>
              <p>
                Encoding, headers, GEOIDs, known sentinel values, declared units
                and exact duplicates. Nulls are not zeros; unknown schemas and
                conflicting duplicate values require review.
              </p>
            </div>
            <div>
              <h3>What it never invents</h3>
              <p>
                Suppressed values, a transportation rate, actual sample sizes,
                current pantry capacity or a proven service gap. Retailer
                addresses are not automatic tract-level density.
              </p>
            </div>
          </div>
          <div className="hash-line">
            APP INPUT SHA256 <code>{data.meta.dataHash}</code>
          </div>
          <a
            className="external-link"
            href="./data/review_report.json"
            target="_blank"
            rel="noreferrer"
          >
            Inspect original review JSON <ExternalLink size={13} />
          </a>
        </Modal>
      )}
      {modal === "method" && (
        <Modal
          title="A visible rule, not a black-box need score"
          subtitle="Default ranking is poverty percentage among LILA + high-poverty tracts."
          onClose={() => setModal(null)}
        >
          <p>
            Shortlist = selected USDA LILA definition at ½ mile urban / 10 miles
            rural AND poverty ≥{Q75.toFixed(1)}% (Q75 across available core
            tracts). Incomplete or special group-quarters/small-denominator rows
            are excluded.
          </p>
          <p>
            Conservative mode substitutes the poverty lower 90% bound for the
            estimate. It is a descriptive sensitivity check, not a formal
            significance test.
          </p>
          <p>
            The map colors the poverty estimate only where the selected LILA
            flag and uncertainty lens apply. Manual reordering changes the
            planning queue, never the underlying evidence.
          </p>
          <div className="notice">
            Changing straight-line to driving changes the distance definition.
            It does not mean conditions changed over time. Neither lens measures
            current unmet pantry demand.
          </div>
        </Modal>
      )}
      {modal === "flyer" && (
        <Modal
          title="Community food-help flyer"
          subtitle="A resident-facing draft, separate from the decision brief"
          onClose={() => setModal(null)}
          wide
        >
          <CommunityFlyer
            key={selected.geoid}
            selected={selected}
            onDownload={download}
          />
        </Modal>
      )}
      {modal === "controls" && (
        <Modal
          title="Human recommendation controls"
          subtitle={`Tract ${selected.geoid} · judgments do not change source data`}
          onClose={() => setModal(null)}
          wide
        >
          <ReviewControls
            key={selected.geoid}
            tracts={data.tracts}
            selected={selected}
            events={workspace.events}
            distance={distance}
            conservative={conservative}
            onRecord={event}
            onSelect={select}
          />
        </Modal>
      )}
      {modal === "ask" && (
        <Modal
          title="Ask the Desk"
          subtitle="Plain-language answers, with sources and limits"
          onClose={() => setModal(null)}
          wide
        >
          <AskDesk
            tracts={data.tracts}
            selected={selected}
            distance={distance}
            conservative={conservative}
            onSelect={select}
          />
        </Modal>
      )}
      {modal === "brief" && (
        <Modal
          title="A decision you can take with you"
          subtitle="One-page brief · real indicators + clearly labelled user observations"
          onClose={() => setModal(null)}
          wide
        >
          <div className="brief-toolbar">
            <button
              className="primary"
              onClick={() =>
                download(`beacon-${selected.geoid}-brief.html`, brief)
              }
            >
              <Download size={15} /> Download printable HTML
            </button>
            <button
              className="small-button"
              onClick={() => {
                const blob = new Blob([brief], { type: "text/html" });
                const url = URL.createObjectURL(blob);
                window.open(url, "_blank", "noopener");
                setTimeout(() => URL.revokeObjectURL(url), 60000);
              }}
            >
              <Printer size={15} /> Open / print to PDF
            </button>
          </div>
          <iframe
            className="brief-preview"
            title="One-page decision brief"
            srcDoc={brief}
          />
        </Modal>
      )}
      {toast && (
        <div className="toast" role="status">
          <CheckCheck size={16} />
          {toast}
        </div>
      )}
    </div>
  );
}
createRoot(document.getElementById("root")).render(<App />);
