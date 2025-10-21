import React, { useEffect, useState } from "react";
import Sidebar from "../components/Sidebar/Sidebar";
import GmailTab from "../components/GmailTab/GmailTab";
import PriorityTab from "../components/PriorityTab/PriorityTab";
import MessageDetail from "../components/MessageDetail/MessageDetail";
import { useAuth } from "../AuthProvider";
import styles from "./Home.module.css";

const API = process.env.REACT_APP_API_BASE_URL;

export default function Home() {
  const { signOut, user, getIdToken } = useAuth();
  const [sidebarTab, setSidebarTab] = useState("Priority");
  const [selected, setSelected] = useState(null);

  // AI summary, checklist, and priority
  const [aiSummary, setAISummary] = useState("");
  const [aiChecklist, setAIChecklist] = useState([]);
  const [priority, setPriority] = useState("");
  const [loadingSummary, setLoadingSummary] = useState(false);

  // Clear state when the tab changes
  useEffect(() => {
    setSelected(null);
    setAISummary("");
    setAIChecklist([]);
    setPriority("");
    setLoadingSummary(false);
  }, [sidebarTab]);

  // Whenever a message is selected, fetch summary+checklist AND priority
  useEffect(() => {
    if (selected?.MessageID) {
      setLoadingSummary(true);
      (async () => {
        try {
          const token = await getIdToken();

          // 1️⃣ Fetch summary + checklist
          const sumRes = await fetch(
            `${API}/nlp/summaries/${encodeURIComponent(selected.MessageID)}`,
            {
              method: "POST",
              headers: {
                Authorization: `Bearer ${token}`,
                "Content-Type": "application/json",
              },
              body: JSON.stringify({}),
            }
          );
          const sumData = await sumRes.json();
          setAISummary(sumData.summary || "");
          setAIChecklist(sumData.checklist || []);

          // 2️⃣ Fetch priority
          const prioRes = await fetch(
            `${API}/nlp/priority/${encodeURIComponent(selected.MessageID)}`,
            {
              method: "POST",
              headers: {
                Authorization: `Bearer ${token}`,
                "Content-Type": "application/json",
              },
            }
          );
          const prioData = await prioRes.json();
          setPriority(prioData.priority || "");
        } catch (error) {
          console.error("Error fetching AI data:", error);
          setAISummary("AI summary could not be fetched.");
          setAIChecklist([]);
          setPriority("");
        } finally {
          setLoadingSummary(false);
        }
      })();
    } else {
      // Reset if nothing is selected
      setAISummary("");
      setAIChecklist([]);
      setPriority("");
      setLoadingSummary(false);
    }
  }, [selected, getIdToken]);

  // Post-OAuth redirect handler (unchanged)
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

        {sidebarTab === "Priority" ? (
          <PriorityTab selected={selected} setSelected={setSelected} />
        ) : sidebarTab === "Gmail" ? (
          <GmailTab selected={selected} setSelected={setSelected} />
        ) : (
          <div className={styles.placeholder}>Select a tab</div>
        )}
      </main>

      <aside className={styles.detailPane}>
        {selected ? (
          <MessageDetail
            message={selected}
            aiSummary={aiSummary}
            aiChecklist={aiChecklist}
            priority={priority}
            loadingAISummary={loadingSummary}
          />
        ) : (
          <div className={styles.placeholder}>Select a message…</div>
        )}
      </aside>
    </div>
  );
}