import React, { useState } from "react";
import styles from "./Login.module.css";

export default function Login({ onLogin, switchToSignup }) {
  const [email, setEmail] = useState("");
  const [pw, setPw] = useState("");
  const [msg, setMsg] = useState("");

  const handleSubmit = async e => {
    e.preventDefault();
    try {
      await onLogin(email, pw);
      setMsg("");
    } catch (e) {
      setMsg(e.message);
    }
  };

  return (
    <form onSubmit={handleSubmit} className={styles.formRoot}>
      <div className={styles.title}>Sign in to Triagely</div>
      <input
        type="email"
        placeholder="Email"
        value={email}
        required
        onChange={e => setEmail(e.target.value)}
        className={styles.input}
        autoFocus
      />
      <input
        type="password"
        placeholder="Password"
        value={pw}
        required
        onChange={e => setPw(e.target.value)}
        className={styles.input}
      />
      <button type="submit" className={styles.button}>Log In</button>
      <button type="button" onClick={switchToSignup} className={styles.linkButton}>Create Account</button>
      <div className={styles.msg}>{msg}</div>
    </form>
  );
}
