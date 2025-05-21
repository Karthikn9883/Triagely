import React from "react";
import AISummaryBox from "../AISummary/AISummaryBox";
import styles from "./MessageDetail.module.css";

export default function MessageDetail({ message }) {
  if (!message) return null;
  return (
    <div className={styles.detailRoot}>
      <div className={styles.subjectRow}>
        <span className={styles.urgentTag}>{message.urgent && "Urgent"}</span>
        <span className={styles.subject}>{message.subject}</span>
        <span className={styles.sourceTag}>
          {message.source === "gmail" ? "Gmail" : "Slack"}
        </span>
        <span className={styles.time}>{formatTime(message.time)}</span>
      </div>
      <AISummaryBox summary={message.aiSummary} checklist={message.aiChecklist} />
      <div className={styles.bodySection}>
        <div className={styles.senderInfo}>
          <b>{message.sender}</b>
          <span style={{ marginLeft: 8, color: "#aaa" }}>
            {message.source === "gmail"
              ? message.senderEmail || ""
              : message.channel || ""}
          </span>
        </div>
        <pre className={styles.messageBody}>{message.content}</pre>
      </div>
      <div className={styles.prevExchanges}>
        {message.prev?.map((p, i) => (
          <div key={i} className={styles.prevRow}>
            <b>{p.date}</b> – {p.summary}
          </div>
        ))}
      </div>
      <div className={styles.quickReply}>
        <input type="text" placeholder="Type your response…" />
        <button>Send</button>
      </div>
    </div>
  );
}

function formatTime(isoString) {
  if (!isoString) return "";
  const d = new Date(isoString);
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}
