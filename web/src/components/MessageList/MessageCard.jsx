import React from "react";
import styles from "./MessageList.module.css";

export default function MessageCard({ message, selected, onClick }) {
  return (
    <div
      className={`${styles.card} ${selected ? styles.selected : ""}`}
      onClick={onClick}
      style={{
        borderLeft: message.urgent ? "4px solid #ee5253" : "4px solid transparent"
      }}
    >
      <div className={styles.header}>
        <b>{message.sender}</b>
        <span className={styles.sourceTag}>{message.source === "gmail" ? "Gmail" : "Slack"}</span>
        <span className={styles.time}>{formatTime(message.time)}</span>
      </div>
      <div className={styles.subjectRow}>
        {message.urgent && <span className={styles.urgentTag}>Urgent</span>}
        <span className={styles.subject}>{message.subject}</span>
      </div>
      <div className={styles.summary}>
        <b>AI Summary:</b>
        <ul>
          {message.aiSummary.map((sum, i) => (
            <li key={i}>{sum}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function formatTime(isoString) {
  if (!isoString) return "";
  const d = new Date(isoString);
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}
