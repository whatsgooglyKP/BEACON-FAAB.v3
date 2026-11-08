import React from "react";
import { snapGapView, snapGapTechnicalHTML } from "./snapGap.js";
export default function SnapGapCard({ gap, tract }) {
  const v = snapGapView(gap, tract);
  return (
    <section className="snap-gap-card" aria-label="SNAP sign-ups">
      <h3>SNAP sign-ups</h3>
      <strong
        className={`snap-gap-label ${v.label === "likely under-enrolled" ? "signal" : ""}`}
      >
        {v.badge}
      </strong>
      <p>{v.sentence}</p>
      <p>
        <strong>Why it matters:</strong> {v.why}
      </p>
      <p>
        <strong>{v.reasonHeading}:</strong> {v.mainReason}
      </p>
      {v.areaCaution && (
        <p className="snap-gap-area-caution">{v.areaCaution}</p>
      )}
      <p className="snap-gap-caveat">{v.caution}</p>
      <details>
        <summary>How we got this</summary>
        <div
          className="snap-gap-technical"
          dangerouslySetInnerHTML={{ __html: snapGapTechnicalHTML(gap) }}
        />
      </details>
    </section>
  );
}
