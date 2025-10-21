// src/components/PriorityTab/PriorityTab.jsx

import React, { useEffect, useState, useCallback } from "react";
import axios from "axios";
import { useAuth } from "../../AuthProvider";
import Pagination from "../Pagination/Pagination";
import styles from "./PriorityTab.module.css";
import { FaSpinner } from "react-icons/fa";

const API = process.env.REACT_APP_API_BASE_URL;

export default function PriorityTab({ selected, setSelected }) {
  const { getIdToken } = useAuth();

  const [msgs, setMsgs]             = useState([]);
  const [loading, setLoading]       = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError]           = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [pagination, setPagination] = useState({
    current_page: 1,
    total_pages: 1,
    total_count: 0,
    page_size: 50
  });

  const fetchPriorityMessages = useCallback(async (pageNum = 1) => {
    setLoading(true);
    setError("");
    try {
      const token = await getIdToken();
      const res   = await axios.get(`${API}/gmail/priority-messages`, {
        headers: { Authorization: `Bearer ${token}` },
        params: { page: pageNum, limit: 50 }
      });
      setMsgs(res.data.data || []);
      setPagination(res.data.pagination || pagination);
      
      // Debug logging for pagination
      console.log("Priority API Response:", res.data);
      console.log("Priority Pagination data:", res.data.pagination);
      console.log("Priority Messages count:", res.data.data?.length);
      
      // Only auto-select first message if no message is currently selected
      if (!selected && res.data.data && res.data.data.length > 0) {
        setSelected(res.data.data[0]);
      }
    } catch (e) {
      console.error("Failed to load priority messages:", e);
      setError("Failed to load priority messages");
    } finally {
      setLoading(false);
    }
  }, [getIdToken]);

  useEffect(() => {
    fetchPriorityMessages(currentPage);
  }, [fetchPriorityMessages, currentPage]);

  const handlePageChange = (newPage) => {
    setCurrentPage(newPage);
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    setError("");
    try {
      const token = await getIdToken();
      // 1️⃣ push new into DB
      await axios.post(
        `${API}/gmail/fetch`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      // 2️⃣ reload current page
      await fetchPriorityMessages(currentPage);
    } catch (e) {
      console.error("Refresh failed:", e);
      setError("Refresh failed");
    } finally {
      setRefreshing(false);
    }
  };

  if (loading) return <div className={styles.placeholder}>Loading priority messages…</div>;
  if (error)   return <div className={styles.error}>⚠ {error}</div>;

  return (
    <div className={styles.container}>
      <div className={styles.toolbar}>
        <div className={styles.messageCount}>
          Showing {((pagination.current_page - 1) * pagination.page_size) + 1}-{Math.min(pagination.current_page * pagination.page_size, pagination.total_count)} of {pagination.total_count} priority messages
        </div>
        <button
          onClick={handleRefresh}
          className={styles.refreshBtn}
          disabled={refreshing}
        >
          {refreshing ? <FaSpinner className={styles.spinner} /> : "Refresh"}
        </button>
      </div>

      {msgs.length === 0 ? (
        <div className={styles.placeholder}>
          No high priority messages found. 
          <br />
          <small>Messages are automatically classified when fetched from Gmail.</small>
        </div>
      ) : (
        <>
          <ul className={styles.list}>
            {msgs.map((m) => (
              <li
                key={m.MessageID}
                className={
                  selected?.MessageID === m.MessageID
                    ? styles.rowSel
                    : styles.row
                }
                onClick={() => setSelected(m)}
              >
                <div className={styles.cellLeft}>
                  <div className={styles.sender}>
                    {m.sender.replace(/<.*/, "")}
                  </div>

                  <div className={styles.preview}>
                    {/* Priority chip - always high for this tab */}
                    <span className={styles.priorityChip}>High</span>
                    {m.subject || "(No subject)"}
                  </div>

                  <div className={styles.snip}>{m.snippet}</div>
                </div>

                {/* date on the right */}
                <div className={styles.date}>
                  {new Date(m.dateISO).toLocaleDateString(undefined, {
                    month: "short",
                    day:   "numeric",
                  })}
                </div>
              </li>
            ))}
          </ul>

          <Pagination
            currentPage={pagination.current_page}
            totalPages={pagination.total_pages}
            onPageChange={handlePageChange}
          />
        </>
      )}
    </div>
  );
}