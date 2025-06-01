import React from "react";
import styles from "./Sidebar.module.css";
import { FaInbox, FaSlack, FaGoogle, FaTasks, FaBell } from "react-icons/fa";
import ConnectGmailButton from "../AccountConnect/ConnectGmailButton";
import ConnectSlackButton from "../AccountConnect/ConnectSlackButton";

export default function Sidebar({ activeTab, setActiveTab, connectedAccounts }) {
  const navItems = [
    { label: "Priority", icon: <FaInbox />, count: 5 },
    { label: "Gmail", icon: <FaGoogle />, count: 12 },
    { label: "Slack", icon: <FaSlack />, count: 8 },
    { label: "Tasks", icon: <FaTasks />, count: 3 },
    { label: "Snoozed", icon: <FaBell />, count: 0 }
  ];

  return (
    <nav className={styles.sidebar}>
      <div className={styles.logo}>
        <div className={styles.logoIcon}>T</div>
        <span className={styles.logoText}>Triagely</span>
      </div>
      <input className={styles.search} type="text" placeholder="Search messages…" />

      {/* --- Connect buttons here --- */}
      <div style={{ margin: "18px 0 10px 20px" }}>
        <ConnectGmailButton />
        <ConnectSlackButton />
      </div>

      <ul className={styles.navList}>
        {navItems.map(item => (
          <li
            key={item.label}
            className={activeTab === item.label ? styles.active : ""}
            onClick={() => setActiveTab(item.label)}
          >
            {item.icon}
            <span>{item.label}</span>
            {item.count > 0 && <span className={styles.count}>{item.count}</span>}
          </li>
        ))}
      </ul>
      <div className={styles.accountsLabel}>CONNECTED ACCOUNTS</div>
      <ul className={styles.accountsList}>
        {connectedAccounts.map(acc => (
          <li key={acc.email}>
            {acc.type === "gmail" ? <FaGoogle color="#ea4335" /> : <FaSlack color="#4A154B" />}
            <span style={{ marginLeft: 8 }}>{acc.email}</span>
          </li>
        ))}
      </ul>
    </nav>
  );
}
