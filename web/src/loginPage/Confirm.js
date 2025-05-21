import React, { useState } from "react";
import styles from "./Login.module.css"; // Use the same styles for all

export default function Confirm({ email, onConfirm, switchToLogin }) {
  const [code, setCode] = useState("");
  const [msg, setMsg] = useState("");

  const handleSubmit = async e => {
    e.preventDefault();
    try {
      await onConfirm(email, code);
      setMsg("Confirmed! Now you can log in.");
    } catch (e) {
      setMsg(e.message);
    }
  };

  return (
    <form onSubmit={handleSubmit} className={styles.formRoot}>
      <div className={styles.title}>Confirm your email</div>
      <input
        type="email"
        value={email}
        className={styles.input}
        disabled
      />
      <input
        type="text"
        placeholder="Verification Code"
        value={code}
        required
        onChange={e => setCode(e.target.value)}
        className={styles.input}
      />
      <button type="submit" className={styles.button}>Confirm Code</button>
      <button type="button" onClick={switchToLogin} className={styles.linkButton}>Back to Login</button>
      <div className={styles.msg}>{msg}</div>
    </form>
  );
}
