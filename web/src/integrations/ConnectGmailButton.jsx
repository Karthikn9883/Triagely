import axios from "axios";
import { useAuth } from "../AuthProvider";

export default function ConnectGmailButton() {
  const { getIdToken } = useAuth();

  const connect = async () => {
    const idToken = await getIdToken();
    const { data } = await axios.get("/gmail/connect", {
      baseURL: process.env.REACT_APP_API_BASE_URL,
      headers: { Authorization: `Bearer ${idToken}` },
    });
    window.location.href = data.auth_url;
  };

  return <button onClick={connect}>Connect Gmail</button>;
}
