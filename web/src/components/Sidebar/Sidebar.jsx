// Sidebar.jsx
import React, { useEffect, useState } from "react";
import {
  FaInbox,
  FaSlack,
  FaGoogle,
  FaTasks,
  FaBell,
  FaSignOutAlt,
  FaChevronDown,
} from "react-icons/fa";
import axios from "axios";

import { useAuth } from "../../AuthProvider";
import ConnectGmailButton from "../AccountConnect/ConnectGmailButton";
import ConnectSlackButton from "../AccountConnect/ConnectSlackButton";
import styles from "./Sidebar.module.css";

/* ─────────────────────────────────────────────────────────── */

export default function Sidebar({
  activeTab,
  setActiveTab,
  connectedAccounts = [],
  onLogout,
  userName = "User",
}) {
  const { getIdToken } = useAuth();

  // ── local state ────────────────────────────────
  const [gmailOpen, setGmailOpen] = useState(false);
  const [gmailAccounts, setGmailAccounts] = useState([]);

  // ── pull Gmail addresses once on mount ─────────
  useEffect(() => {
    (async () => {
      try {
        const tk = await getIdToken();
        const { data } = await axios.get(
          `${process.env.REACT_APP_API_BASE_URL}/gmail/accounts`,
          { headers: { Authorization: `Bearer ${tk}` } }
        );
        setGmailAccounts(data || []);
      } catch (err) {
        console.error("Could not load Gmail accounts:", err);
      }
    })();
  }, [getIdToken]);

  // nav items **excluding Priority & Gmail**
  const otherNavItems = [
    { label: "Slack", icon: <FaSlack /> },
    { label: "Tasks", icon: <FaTasks /> },
    { label: "Snoozed", icon: <FaBell /> },
  ];

  /* ─────────────────────────────────────────────── */
  return (
    <nav className={styles.sidebar}>
      {/* ── Logo */}
      <div className={styles.logo}>
        <div className={styles.logoIcon}>T</div>
        <span className={styles.logoText}>Triagely</span>
      </div>

      {/* ── Search box */}
      <input
        className={styles.search}
        type="text"
        placeholder="Search messages…"
      />

      {/* ── Connect buttons */}
      <div style={{ margin: "18px 0 10px 20px" }}>
        <ConnectGmailButton />
        <ConnectSlackButton />
      </div>

      {/* ── Navigation list ───────────────────────── */}
      <ul className={styles.navList}>
        {/* Priority — always on top */}
        <li
          className={activeTab === "Priority" ? styles.active : undefined}
          onClick={() => setActiveTab("Priority")}
        >
          <FaInbox />
          <span style={{ marginLeft: 10 }}>Priority</span>
        </li>

        {/* Gmail item + chevron */}
        <li
          className={
            activeTab === "Gmail" || gmailOpen ? styles.active : undefined
          }
          onClick={() => {
            setActiveTab("Gmail");
            setGmailOpen(!gmailOpen);
          }}
        >
          <FaGoogle />
          <span style={{ marginLeft: 10 }}>Gmail</span>
          <FaChevronDown
            className={gmailOpen ? styles.chevronOpen : styles.chevronClosed}
          />
        </li>

        {/* Collapsible Gmail accounts */}
        {gmailOpen &&
          gmailAccounts.map((addr) => (
            <li key={addr} className={styles.subItem}>
              {addr}
            </li>
          ))}

        {/* Remaining nav items */}
        {otherNavItems.map((item) => (
          <li
            key={item.label}
            className={activeTab === item.label ? styles.active : undefined}
            onClick={() => setActiveTab(item.label)}
          >
            {item.icon}
            <span style={{ marginLeft: 10 }}>{item.label}</span>
          </li>
        ))}
      </ul>

      {/* ── Connected accounts (non-Gmail) ────────── */}
      <div className={styles.accountsLabel}>CONNECTED ACCOUNTS</div>
      <ul className={styles.accountsList}>
        {connectedAccounts
          .filter((acc) => acc.type !== "gmail")
          .map((acc) => (
            <li key={acc.email}>
              {acc.type === "gmail" ? (
                <FaGoogle color="#ea4335" />
              ) : (
                <FaSlack color="#4A154B" />
              )}
              <span style={{ marginLeft: 8 }}>{acc.email}</span>
            </li>
          ))}
      </ul>

      {/* ── Spacer pushes logout to bottom ───────── */}
      <div className={styles.flexSpacer} />

      {/* ── Logout row */}
      <button className={styles.logoutRow} onClick={onLogout}>
        <FaSignOutAlt style={{ marginRight: 8 }} />
        <span>{userName}</span>
      </button>
    </nav>
  );
}