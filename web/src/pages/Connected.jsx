// src/pages/Connected.jsx
import { useEffect } from "react";

export default function Connected() {
  useEffect(() => {
    setTimeout(() => {
      window.location.href = "/";
    }, 2000); // Redirect after 2 seconds
  }, []);
  const provider = new URLSearchParams(window.location.search).get("provider");
  return (
    <div style={{ textAlign: "center", marginTop: 60 }}>
      <h2>{provider ? `Connected to ${provider}!` : "Connected!"}</h2>
      <p>Redirecting you to your inbox...</p>
    </div>
  );
}
