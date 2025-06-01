import React, { useEffect, useState, useRef } from "react";
import axios from "axios";
import { useAuth } from "../../AuthProvider";
import styles from "./GmailTab.module.css";

const fmtDate = iso =>
  new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });

export default function GmailTab({ selected, setSelected }) {
  const { getIdToken } = useAuth();
  const [msgs, setMsgs] = useState([]);
  const [load, setLoad] = useState(true);
  const [error, setErr] = useState("");
  const timerRef = useRef(null);

  // Fetch emails
  const fetchMessages = async () => {
    try {
      setLoad(true); setErr("");
      const tk = await getIdToken();
      const res = await axios.get(
        `${process.env.REACT_APP_API_BASE_URL}/gmail/messages`,
        { headers: { Authorization: `Bearer ${tk}` } }
      );
      setMsgs(res.data);
      if (!selected && res.data.length) setSelected(res.data[0]);
    } catch (e) { setErr(e.message); }
    finally { setLoad(false); }
  };

  useEffect(() => {
    fetchMessages(); // Initial fetch

    // Poll every 30s
    timerRef.current = setInterval(fetchMessages, 30000);

    return () => clearInterval(timerRef.current);
    // eslint-disable-next-line
  }, []);

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", marginBottom: 10, paddingLeft: 8 }}>
        <h2 style={{ margin: 0, fontSize: "1.18em", flex: 1 }}>Gmail</h2>
        <button
          style={{
            marginLeft: "auto",
            background: "#eeeafd",
            color: "#6843be",
            border: "none",
            borderRadius: 7,
            padding: "7px 18px",
            cursor: "pointer",
            fontWeight: 600,
            fontSize: "1em"
          }}
          onClick={fetchMessages}
          disabled={load}
        >
          {load ? "Refreshing..." : "Refresh"}
        </button>
      </div>
      {load && <div className={styles.placeholder}>Loading…</div>}
      {error && <div className={styles.error}>⚠ {error}</div>}
      <ul className={styles.list} style={{ opacity: load ? 0.5 : 1 }}>
        {msgs.map(m => (
          <li
            key={m.MessageID}
            className={selected?.MessageID === m.MessageID ? styles.rowSel : styles.row}
            onClick={() => setSelected(m)}
          >
            <div className={styles.cellLeft}>
              <div className={styles.sender}>{m.sender.replace(/<.*/, "")}</div>
              <div className={styles.preview}>
                {m.urgent && <span className={styles.urgentChip}>🚩 Urgent</span>}
                {m.subject}
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
