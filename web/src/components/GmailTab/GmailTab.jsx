// src/components/GmailTab/GmailTab.jsx
import React, { useEffect, useState, useCallback } from "react";
import axios from "axios";
import { useAuth } from "../../AuthProvider";
import styles from "./GmailTab.module.css";

const fmtDate = (iso) =>
  new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });

export default function GmailTab({ selected, setSelected }) {
  const { getIdToken } = useAuth();

  const [msgs, setMsgs]   = useState([]);
  const [loading, setLoad] = useState(true);
  const [error, setErr]    = useState("");

  const fetchMessages = useCallback(async () => {
    try {
      setLoad(true);
      setErr("");
      const tk = await getIdToken();
      const res = await axios.get(`${process.env.REACT_APP_API_BASE_URL}/gmail/messages`, {
        headers: { Authorization: `Bearer ${tk}` },
      });
      setMsgs(res.data);
      if (!selected && res.data.length) {
        setSelected(res.data[0]);
      }
    } catch (e) {
      console.error("Failed to fetch Gmail messages:", e);
      setErr(e.response?.data?.detail || e.message || "Fetch failed");
    } finally {
      setLoad(false);
    }
  }, [getIdToken, selected, setSelected]);

  // Initial load
  useEffect(() => {
    fetchMessages();
  }, [fetchMessages]);

  if (loading) return <div className={styles.placeholder}>Loading Gmail…</div>;
  if (error)   return <div className={styles.error}>⚠ {error}</div>;

  return (
    <div>
      <div className={styles.toolbar}>
        <button onClick={fetchMessages} className={styles.refreshBtn}>
          Refresh
        </button>
      </div>
      <ul className={styles.list}>
        {msgs.map((m) => (
          <li
            key={m.MessageID}
            className={selected?.MessageID === m.MessageID ? styles.rowSel : styles.row}
            onClick={() => setSelected(m)}
          >
            <div className={styles.cellLeft}>
              <div className={styles.sender}>{m.sender.replace(/<.*/, "")}</div>
              <div className={styles.preview}>
                {m.urgent && <span className={styles.urgentChip}>🚩 Urgent</span>}
                {m.subject || "(No subject)"}
              </div>
              <div className={styles.snip}>{m.snippet}</div>
            </div>
            <div className={styles.date}>{fmtDate(m.dateISO)}</div>
          </li>
        ))}
      </ul>
    </div>
  );
}