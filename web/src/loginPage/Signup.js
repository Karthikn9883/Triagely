import React, { useState } from "react";
import styles from "./Login.module.css"; // Use the same styles for consistency

export default function Signup({ onSignup, switchToLogin }) {
  const [email, setEmail] = useState("");
  const [pw, setPw] = useState("");
  const [name, setName] = useState("");
  const [msg, setMsg] = useState("");

  const handleSubmit = async e => {
    e.preventDefault();
    try {
      await onSignup(email, pw, name);
      setMsg("Signup success! Check your email for the code.");
    } catch (e) {
      setMsg(e.message);
    }
  };

  return (
    <form onSubmit={handleSubmit} className={styles.formRoot}>
      <div className={styles.title}>Create your Triagely account</div>
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
      <input
        type="text"
        placeholder="Full name"
        value={name}
        required
        onChange={e => setName(e.target.value)}
        className={styles.input}
      />
      <button type="submit" className={styles.button}>Sign Up</button>
      <button type="button" onClick={switchToLogin} className={styles.linkButton}>Back to Login</button>
      <div className={styles.msg}>{msg}</div>
    </form>
  );
}
