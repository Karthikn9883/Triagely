import React, { useEffect, useState } from "react";
import Sidebar from "../components/Sidebar/Sidebar";
import MessageList from "../components/MessageList/MessageList";
import MessageDetail from "../components/MessageDetail/MessageDetail";
import { useAuth } from "../AuthProvider";
import styles from "./Home.module.css";
import axios from "axios";

export default function Home() {
  const { getIdToken, signOut } = useAuth();

  const [messages, setMessages] = useState([]);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sidebarTab, setSidebarTab] = useState("Priority");
  const [error, setError] = useState(null);

  // Fetch messages from backend
  useEffect(() => {
    async function fetchMessages() {
      try {
        setLoading(true);
        setError(null);
        const idToken = await getIdToken();
        const res = await axios.get(
          `${process.env.REACT_APP_API_BASE_URL}/messages`,
          { headers: { Authorization: `Bearer ${idToken}` } }
        );
        setMessages(res.data);
        setSelected(res.data[0] || null);
      } catch (err) {
        setError(err.response?.data?.detail || err.message);
      } finally {
        setLoading(false);
      }
    }
    fetchMessages();
  }, [getIdToken]);

  return (
    <div className={styles.homeRoot}>
      <button
        onClick={signOut}
        style={{
          position: "absolute",
          top: 18,
          right: 22,
          padding: 8,
          borderRadius: 7,
          background: "#eee",
          color: "#6843be",
        }}
      >
        Logout
      </button>
      <Sidebar
        activeTab={sidebarTab}
        setActiveTab={setSidebarTab}
        connectedAccounts={[
          { email: "work@example.com", type: "gmail" },
          { email: "Marketing Team", type: "slack" },
        ]}
      />
      <main className={styles.mainPane}>
        <h2 className={styles.inboxTitle}>
          {sidebarTab === "Priority" ? "Priority Inbox" : sidebarTab}
        </h2>
        {loading && <div style={{ padding: 32 }}>Loading...</div>}
        {error && <div style={{ color: "red", padding: 32 }}>{error}</div>}
        {!loading && !error && (
          <MessageList
            messages={messages}
            selected={selected}
            setSelected={setSelected}
          />
        )}
      </main>
      <aside className={styles.detailPane}>
        {selected ? (
          <MessageDetail message={selected} />
        ) : (
          <div style={{ padding: 32, color: "#999" }}>
            Select a message…
          </div>
        )}
      </aside>
    </div>
  );
}
