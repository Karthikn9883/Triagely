// src/components/MessageDetail/MessageDetail.jsx
import React from "react";
import DOMPurify from "dompurify";
import styles from "./MessageDetail.module.css";
import AISummaryBox from "../AISummary/AISummaryBox"; // Adjust path as needed

export default function MessageDetail({
  message,
  aiSummary,
  aiChecklist,
  loadingAISummary,
}) {
  if (!message) return null;

  // Format date + time:
  const when = message.dateISO
    ? new Date(message.dateISO).toLocaleString(undefined, {
        month: "short",
        day:   "numeric",
        year:  "numeric",
        hour:  "2-digit",
        minute:"2-digit",
      })
    : "";

  // Extract “From” name vs email
  const rawFrom = message.sender || "";
  const namePart = rawFrom.includes("<")
    ? rawFrom.split("<")[0].trim()
    : rawFrom;
  const emailPart = rawFrom.includes("<")
    ? rawFrom.match(/<([^>]+)>/)?.[1] ?? ""
    : "";

  return (
    <article className={styles.root}>
      {/* ── Header (Subject + Gmail pill + date) ─────────────────────────── */}
      <header className={styles.head}>
        <h1 className={styles.subject}>{message.subject || "(No subject)"}</h1>
        <span className={styles.pill}>Gmail</span>
        <span className={styles.date}>{when}</span>
      </header>

      {/* ── AI Box ────────────────────────────────────────────────────────── */}
      <section className={styles.aiBox}>
        {loadingAISummary ? (
          <div>Loading summary…</div>
        ) : (
          <AISummaryBox summary={aiSummary} checklist={aiChecklist} />
        )}
      </section>

      {/* ── From line ────────────────────────────────────────────────────── */}
      <div className={styles.senderLine}>
        <strong>{namePart || "Unknown Sender"}</strong>
        {emailPart && <span className={styles.senderEmail}>{emailPart}</span>}
      </div>

      {/* ── Body: HTML or plain text ─────────────────────────────────────── */}
      {message.html ? (
        <div
          className={styles.bodyHtml}
          dangerouslySetInnerHTML={{
            __html: DOMPurify.sanitize(message.html),
          }}
        />
      ) : (
        <pre className={styles.bodyPlain}>{message.plain}</pre>
      )}

      {/* ── Quick reply (optional) ────────────────────────── */}
      <div className={styles.replyRow}>
        <input placeholder="Type your response…" />
        <button>Send</button>
      </div>
    </article>
  );
}
