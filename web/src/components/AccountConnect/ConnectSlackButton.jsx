import React from "react";
import axios from "axios";
import { useAuth } from "../../AuthProvider";

export default function ConnectSlackButton({ onConnected }) {
  const { getIdToken } = useAuth();

  const handleConnect = async () => {
    const idToken = await getIdToken();
    // Call backend to get Slack OAuth URL
    const { data } = await axios.get("/slack/connect", {
      baseURL: process.env.REACT_APP_API_BASE_URL,
      headers: { Authorization: `Bearer ${idToken}` },
    });
    // Redirect to Slack for consent
    window.location.href = data.auth_url;
  };

  return (
    <button onClick={handleConnect} style={buttonStyle}>
      Connect Slack
    </button>
  );
}

const buttonStyle = {
  background: "#fff",
  color: "#4A154B",
  border: "1.5px solid #eadcf4",
  borderRadius: 7,
  padding: "11px 18px",
  fontWeight: 600,
  fontSize: "1em",
  cursor: "pointer",
  marginBottom: 8
};
