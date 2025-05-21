import React from "react";
import MessageCard from "./MessageCard";
import styles from "./MessageList.module.css";

export default function MessageList({ messages, selected, setSelected }) {
  return (
    <div className={styles.list}>
      {messages.map(msg => (
        <MessageCard
          key={msg.id}
          message={msg}
          selected={selected && msg.id === selected.id}
          onClick={() => setSelected(msg)}
        />
      ))}
    </div>
  );
}
