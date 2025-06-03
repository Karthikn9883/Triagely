// src/pages/Home.jsx
import React, { useEffect, useState } from "react";
import Sidebar from "../components/Sidebar/Sidebar";
import GmailTab from "../components/GmailTab/GmailTab";
import MessageDetail from "../components/MessageDetail/MessageDetail";
import { useAuth } from "../AuthProvider";
import styles from "./Home.module.css";

export default function Home() {
  const { signOut, user } = useAuth();
  const [sidebarTab, setSidebarTab] = useState("Priority");
  const [selected, setSelected]     = useState(null);

  // clear selection when tab changes
  useEffect(() => { setSelected(null); }, [sidebarTab]);

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
        connectedAccounts={[] /* you'll fill this from state later */}
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
          <MessageDetail message={selected} />
        ) : (
          <div className={styles.placeholder}>Select a message…</div>
        )}
      </aside>
    </div>
  );
}
