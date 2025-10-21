// src/components/MessageDetail/MessageDetail.jsx

import React from "react";
import DOMPurify from "dompurify";
import styles from "./MessageDetail.module.css";
import AISummaryBox from "../AISummary/AISummaryBox";

export default function MessageDetail({
  message,
  aiSummary,
  aiChecklist,
  loadingAISummary,
  priority,
}) {
  if (!message) return null;

  // Format date + time
  const when = message.dateISO
    ? new Date(message.dateISO).toLocaleString(undefined, {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })
    : "";

  // Sender name vs. email
  const rawFrom = message.sender || "";
  const namePart = rawFrom.includes("<")
    ? rawFrom.split("<")[0].trim()
    : rawFrom;
  const emailPart = rawFrom.includes("<")
    ? rawFrom.match(/<([^>]+)>/)?.[1] ?? ""
    : "";

  return (
    <article className={styles.root}>
      {/* Header: Subject, source pill, priority tag, and date */}
      <header className={styles.head}>
        <h1 className={styles.subject}>
          {message.subject || "(No subject)"}
        </h1>
        <span className={styles.pill}>Gmail</span>
        {priority && (
          <span
            className={
              priority === "High" ? styles.highPrio : styles.normalPrio
            }
          >
            {priority}
          </span>
        )}
        <span className={styles.date}>{when}</span>
      </header>

      {/* AI Summary & Checklist */}
      <section className={styles.aiBox}>
        {loadingAISummary ? (
          <div>Loading summary…</div>
        ) : (
          <AISummaryBox summary={aiSummary} checklist={aiChecklist} />
        )}
      </section>

      {/* Sender info */}
      <div className={styles.senderLine}>
        <strong>{namePart || "Unknown Sender"}</strong>
        {emailPart && <span className={styles.senderEmail}>{emailPart}</span>}
      </div>

      {/* Message body, HTML if available else plain text */}
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

      {/* Quick reply stub */}
      <div className={styles.replyRow}>
        <input placeholder="Type your response…" />
        <button>Send</button>
      </div>
    </article>
  );
}