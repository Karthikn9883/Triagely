import React from "react";
import styles from "./AISummaryBox.module.css";

export default function AISummaryBox({ summary, checklist }) {
  return (
    <div className={styles.box}>
      <div className={styles.heading}>AI Summary & Action Items</div>
      {typeof summary === "string" ? (
        <div className={styles.summaryText}>{summary}</div>
      ) : (
        <div className={styles.summaryText}>
          {summary?.map((s, i) => (
            <div key={i}>{s}</div>
          ))}
        </div>
      )}
      <div className={styles.checklistLabel}>Action Items:</div>
      <ul className={styles.checklist}>
        {checklist?.map((c, i) => (
          <li key={i} className={c.checked ? styles.checked : ""}>
            <input type="checkbox" checked={c.checked} readOnly />
            <span>{c.text}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
