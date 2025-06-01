import React, { useEffect, useState } from "react";
import { useAuth } from "../AuthProvider";
import MessageList from "../components/MessageList/MessageList";
import MessageDetail from "../components/MessageDetail/MessageDetail";
import styles from "./Gmail.module.css"; // (Optional: add styles as you like)
import axios from "axios";

export default function Gmail() {
  const { getIdToken } = useAuth();
  const [messages, setMessages] = useState([]);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Fetch Gmail messages on mount
  useEffect(() => {
    async function fetchGmail() {
      setLoading(true);
      setError("");
      try {
        const token = await getIdToken();
        const { data } = await axios.get(
          `${process.env.REACT_APP_API_BASE_URL}/gmail/messages`,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        setMessages(data.messages || []);
        setSelected((data.messages && data.messages[0]) || null);
      } catch (err) {
        setError(err.response?.data?.detail || err.message || "Failed to fetch Gmail.");
      } finally {
        setLoading(false);
      }
    }
    fetchGmail();
    // Optionally, add [getIdToken] to dependency array if getIdToken can change
  }, [getIdToken]);

  // Optional: a refresh button
  const handleRefresh = () => {
    setLoading(true);
    setError("");
    setTimeout(() => window.location.reload(), 100); // Simple reload for demo
  };

  return (
    <div className={styles.gmailRoot || ""} style={{ display: "flex", height: "100%" }}>
      <main style={{ flex: 2, padding: 24, borderRight: "1.5px solid #f2f2f9" }}>
        <div style={{ display: "flex", alignItems: "center", marginBottom: 12 }}>
          <h2 style={{ margin: 0, fontSize: "1.6em", color: "#6843be" }}>Gmail Inbox</h2>
          <button
            onClick={handleRefresh}
            style={{
              marginLeft: "auto",
              background: "#eeeafd",
              color: "#6843be",
              border: "none",
              borderRadius: 6,
              padding: "7px 18px",
              cursor: "pointer"
            }}
          >
            Refresh
          </button>
        </div>
        {loading ? (
          <div style={{ padding: 24 }}>Loading Gmail messages…</div>
        ) : error ? (
          <div style={{ color: "#e24a4a", padding: 24 }}>{error}</div>
        ) : !messages.length ? (
          <div style={{ color: "#999", padding: 24 }}>No Gmail messages found.</div>
        ) : (
          <MessageList messages={messages} selected={selected} setSelected={setSelected} />
        )}
      </main>
      <aside style={{ flex: 3, padding: 24 }}>
        {selected ? (
          <MessageDetail message={selected} />
        ) : (
          <div style={{ color: "#bbb", fontStyle: "italic" }}>Select a message…</div>
        )}
      </aside>
    </div>
  );
}
