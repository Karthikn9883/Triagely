import React from "react";
import axios from "axios";
import { useAuth } from "../../AuthProvider";

export default function ConnectGmailButton() {
  const { getIdToken } = useAuth();

  const handleConnect = async () => {
    const idToken = await getIdToken();
    const { data } = await axios.get("/gmail/connect", {
      baseURL: process.env.REACT_APP_API_BASE_URL,
      headers: { Authorization: `Bearer ${idToken}` },   // <- back-ticks!
    });
    window.location.href = data.auth_url;
  };

  return (
    <button onClick={handleConnect} style={buttonStyle}>
      Connect Gmail
    </button>
  );
}


const buttonStyle = {
  background: "#fff",
  color: "#ea4335",
  border: "1.5px solid #eadcf4",
  borderRadius: 7,
  padding: "11px 18px",
  fontWeight: 600,
  fontSize: "1em",
  cursor: "pointer",
  marginBottom: 8,
  marginRight: 12
};
