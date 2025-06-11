// src/pages/Home.jsx
import React, { useEffect, useState } from "react";
import Sidebar from "../components/Sidebar/Sidebar";
import GmailTab from "../components/GmailTab/GmailTab";
import MessageDetail from "../components/MessageDetail/MessageDetail";
import { useAuth } from "../AuthProvider";
import styles from "./Home.module.css";

export default function Home() {
  const { signOut, user, getIdToken } = useAuth();
  const [sidebarTab, setSidebarTab] = useState("Priority");
  const [selected, setSelected]     = useState(null);

  // For AI summary/checklist
  const [aiSummary, setAISummary] = useState("");
  const [aiChecklist, setAIChecklist] = useState([]);
  const [loadingSummary, setLoadingSummary] = useState(false);

  // Clear selection when tab changes
  useEffect(() => {
    setSelected(null);
    setAISummary("");
    setAIChecklist([]);
    setLoadingSummary(false);
  }, [sidebarTab]);

  // Fetch AI summary for the selected message
  useEffect(() => {
    if (
      selected &&
      selected.MessageID // Make sure this matches your backend field
    ) {
      setLoadingSummary(true);
      (async () => {
        try {
          const token = await getIdToken();
          // POST to backend to trigger/fetch summary
          const res = await fetch(
            `${process.env.REACT_APP_API_BASE_URL}/nlp/summaries/${encodeURIComponent(selected.MessageID)}`,
            {
              method: "POST",
              headers: {
                Authorization: `Bearer ${token}`,
                "Content-Type": "application/json",
              },
              body: JSON.stringify({}), // Some backends need a body for POST
            }
          );
          const data = await res.json();
          setAISummary(data.summary || "");
          setAIChecklist(data.checklist || []);
        } catch (e) {
          setAISummary("AI summary could not be fetched.");
          setAIChecklist([]);
        } finally {
          setLoadingSummary(false);
        }
      })();
    } else {
      setAISummary("");
      setAIChecklist([]);
      setLoadingSummary(false);
    }
  }, [selected, getIdToken]);

  // Post-OAuth hook (unchanged)
  useEffect(() => {
    const p = new URLSearchParams(window.location.search).get("provider");
    if (p) {
      alert(`Connected ${p}!`);
      window.history.replaceState({}, "", window.location.pathname);
    }
  }, []);

  return (
    <div className={styles.homeRoot}>
      <Sidebar
        activeTab={sidebarTab}
        setActiveTab={setSidebarTab}
        connectedAccounts={[]}
        onLogout={signOut}
        userName={user?.username || "User"}
      />

      <main className={styles.mainPane}>
        <h2 className={styles.inboxTitle}>
          {sidebarTab === "Priority" ? "Priority Inbox" : sidebarTab}
        </h2>

        {sidebarTab === "Gmail" ? (
          <GmailTab selected={selected} setSelected={setSelected} />
        ) : (
          <div className={styles.placeholder}>
            {/* you can render your other tabs here */}
            Select a tab
          </div>
        )}
      </main>

      <aside className={styles.detailPane}>
        {selected ? (
          <MessageDetail
            message={selected}
            aiSummary={aiSummary}
            aiChecklist={aiChecklist}
            loadingAISummary={loadingSummary}
          />
        ) : (
          <div className={styles.placeholder}>Select a message…</div>
        )}
      </aside>
    </div>
  );
}
