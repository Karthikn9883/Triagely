import React from "react";
import styles from "./MessageList.module.css";

export default function MessageCard({ message, selected, onClick }) {
  const {
    subject = "",
    snippet = "",
    sender = "",
    senderName,
    dateISO,
    urgent = false,
    source = "",
  } = message;

  // 1) name prefers senderName (if backend split it out), else parse the header
  const displayName =
    senderName ||
    (sender.includes("<") ? sender.split("<")[0].trim() : sender) ||
    "Unknown";

  // 2) choose snippet or subject
  const preview = snippet || subject || "(No subject)";

  // 3) format the ISO date
  const formattedTime = dateISO
    ? new Date(dateISO).toLocaleString(undefined, {
        month: "numeric",
        day: "numeric",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })
    : "";

  return (
    <div
      className={`${styles.card} ${selected ? styles.selected : ""}`}
      onClick={onClick}
      style={{
        borderLeft: urgent ? "4px solid #ee5253" : "4px solid transparent",
      }}
    >
      <div className={styles.header}>
        <b className={styles.senderCol}>{displayName}</b>
        <span className={styles.time}>{formattedTime}</span>
        <span className={styles.sourceTag}>
          {source === "gmail"
            ? "Gmail"
            : source
                .charAt(0)
                .toUpperCase()
                .concat(source.slice(1))}
        </span>
      </div>
      <div className={styles.previewRow}>
        {urgent && <span className={styles.urgentTag}>Urgent</span>}
        <span className={styles.previewText}>{preview}</span>
      </div>
    </div>
  );
}
