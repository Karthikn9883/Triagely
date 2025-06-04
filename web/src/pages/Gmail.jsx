// src/pages/Gmail.jsx   (only the Refresh handler changed)
import React, { useEffect, useState } from "react";
import axios from "axios";
import { useAuth } from "../AuthProvider";

export default function Gmail() {
  const { getIdToken } = useAuth();
  const [threads, setThreads] = useState([]);
  const [loading, setLoading] = useState(true);

  /* ------------- load cached list -------------- */
  const loadMessages = async () => {
    const tk   = await getIdToken();
    const resp = await axios.get(
      `${process.env.REACT_APP_API_BASE_URL}/gmail/messages`,
      { headers: { Authorization: `Bearer ${tk}` } }
    );
    setThreads(resp.data);
  };

  useEffect(() => {
    loadMessages().finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /* ------------- NEW Refresh handler ----------- */
  const handleRefresh = async () => {
    setLoading(true);
    const tk = await getIdToken();

    /* 1️⃣  trigger the backend pull */
    await axios.post(
      `${process.env.REACT_APP_API_BASE_URL}/gmail/fetch`,
      {},                                           // empty body
      { headers: { Authorization: `Bearer ${tk}` } }
    );

    /* 2️⃣  immediately re-download the merged cache */
    await loadMessages();
    setLoading(false);
  };

  /* ---------- very small UI sample ------------- */
  return (
    <section style={{ flex: 1, padding: 20 }}>
      <header style={{ display: "flex", justifyContent: "space-between" }}>
        <h2>Gmail</h2>
        <button onClick={handleRefresh} disabled={loading}>
          {loading ? "Loading…" : "Refresh"}
        </button>
      </header>

      <ul style={{ marginTop: 20 }}>
        {threads.map(t => (
          <li key={t.MessageID}>
            <strong>{t.subject}</strong>
            <br />
            <small>{t.sender} — {new Date(t.dateISO).toLocaleString()}</small>
          </li>
        ))}
      </ul>
    </section>
  );
}