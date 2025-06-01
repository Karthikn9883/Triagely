import React from "react";
import DOMPurify from "dompurify";
import styles from "./MessageDetail.module.css";

export default function MessageDetail({ message }) {
  if (!message) return null;

  // Format date/time
  const when = message.dateISO
    ? new Date(message.dateISO).toLocaleString()
    : "";

  // Extract sender name/email
  let name = "";
  let email = "";
  if (message.sender) {
    const match = message.sender.match(/(.*)<(.*)>/);
    if (match) {
      name = match[1].trim();
      email = match[2].trim();
    } else {
      name = message.sender.trim();
    }
  }

  return (
    <article className={styles.root}>
      {/* ── Header */}
      <header className={styles.head}>
        <h1 className={styles.subject}>{message.subject}</h1>
        <span className={styles.pill}>Gmail</span>
        <span className={styles.date}>{when}</span>
      </header>

      {/* ── AI Box */}
      <section className={styles.aiBox}>
        <div className={styles.aiTitle}>AI Summary & Action Items</div>
        {message.aiSummary?.length > 0 ? (
          <ul className={styles.checkList}>
            {message.aiSummary.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        ) : (
          <em>No summary yet</em>
        )}
      </section>

      {/* ── Sender info */}
      <div className={styles.senderLine}>
        <strong>{name}</strong>
        {email && <span className={styles.senderEmail}>{email}</span>}
      </div>

      {/* ── Body */}
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

      {/* ── Quick reply */}
      <div className={styles.replyRow}>
        <input placeholder="Type your response…" />
        <button>Send</button>
      </div>
    </article>
  );
}
