import { useState } from "react";
import { auth } from "./firebaseConfig";
import { signInWithEmailAndPassword, createUserWithEmailAndPassword } from "firebase/auth";
import axios from "axios";

function App() {
  const [email,setEmail] = useState("");
  const [pw,setPw]     = useState("");
  const [msg,setMsg]   = useState("");

  const handleSignup = async () => {
    try {
      await createUserWithEmailAndPassword(auth, email, pw);
      setMsg("Signed up! Now please log in.");
    } catch (e) {
      setMsg(e.message);
    }
  };

  const handleLogin = async () => {
    try {
      const { user } = await signInWithEmailAndPassword(auth, email, pw);
      const token = await user.getIdToken();
      const res = await axios.get("http://localhost:8000/protected", {
        headers: { Authorization: `Bearer ${token}` },
      });
      setMsg(res.data.message);
    } catch (e) {
      setMsg(e.response?.data?.detail || e.message);
    }
  };

  return (
    <div style={{ maxWidth: 400, margin: "2rem auto" }}>
      <h2>Triagely MVP Auth Test</h2>
      <input
        type="email" placeholder="Email"
        value={email} onChange={e=>setEmail(e.target.value)}
        style={{width:"100%",padding:8,marginBottom:8}}
      />
      <input
        type="password" placeholder="Password"
        value={pw} onChange={e=>setPw(e.target.value)}
        style={{width:"100%",padding:8,marginBottom:8}}
      />
      <button onClick={handleSignup} style={{marginRight:8}}>Sign Up</button>
      <button onClick={handleLogin}>Log In & Call API</button>
      <p>{msg}</p>
    </div>
  );
}

export default App;