import React, { useState } from "react";
import { TextInput, Button, Text, View, StyleSheet } from "react-native";
import { Amplify, Auth } from "aws-amplify";
import config from "./src/aws-exports";
import axios from "axios";
import Constants from "expo-constants";

// Config loaded via amplifyConfig.js

export default function App() {
  const [email, setEmail] = useState("");
  const [pw, setPw] = useState("");
  const [msg, setMsg] = useState("");

  const handleSignup = async () => {
    try {
      await Auth.signUp({
        username: email,
        password: pw,
        attributes: { email },
      });
      setMsg("Signed up! Check your email to verify, then log in.");
    } catch (e) {
      setMsg(e.message || JSON.stringify(e));
    }
  };

  const handleLogin = async () => {
    try {
      await Auth.signIn(email, pw);
      const session = await Auth.currentSession();
      const token = session.getIdToken().getJwtToken();
      // Get API base URL from app.json > extra
      const apiBaseUrl = Constants.expoConfig?.extra?.apiBaseUrl || "http://10.0.0.2:8000";
      const res = await axios.get(`${apiBaseUrl}/protected`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setMsg(res.data.message);
    } catch (e) {
      setMsg(e.message || JSON.stringify(e));
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Triagely Mobile Auth (Cognito)</Text>
      <TextInput
        style={styles.input}
        placeholder="Email" value={email}
        onChangeText={setEmail}
      />
      <TextInput
        style={styles.input}
        secureTextEntry
        placeholder="Password" value={pw}
        onChangeText={setPw}
      />
      <View style={styles.buttons}>
        <Button title="Sign Up" onPress={handleSignup} />
        <Button title="Log In & Call API" onPress={handleLogin} />
      </View>
      <Text style={styles.msg}>{msg}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: "center", padding: 20 },
  title: { fontSize: 24, textAlign: "center", marginBottom: 20 },
  input: { borderWidth: 1, padding: 8, marginBottom: 12, borderRadius: 4 },
  buttons: { flexDirection: "row", justifyContent: "space-between", marginBottom: 12 },
  msg: { textAlign: "center", marginTop: 12 }
});
