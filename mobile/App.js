// mobile/App.js
import React, { useState } from "react";
import { TextInput, Button, Text, View, StyleSheet } from "react-native";
import { initializeApp } from "firebase/app";
import {
  initializeAuth,
  getReactNativePersistence,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
} from "firebase/auth";
import AsyncStorage from "@react-native-async-storage/async-storage";
import axios from "axios";
import Constants from "expo-constants";

// initialize Firebase
const firebaseConfig = {
  apiKey: "AIzaSyAtX-2ZmuRC6eDapi2WkYtR7kF-vSf_BAw",
  authDomain: "triagely-c4f38.firebaseapp.com",
  projectId: "triagely-c4f38",
  storageBucket: "triagely-c4f38.firebasestorage.app",
  messagingSenderId: "462011870278",
  appId: "1:462011870278:web:029a5396c60877c79e2e47",
  measurementId: "G-L9DZWQD0KM"
};
const app = initializeApp(firebaseConfig);
const auth = initializeAuth(app, {
  persistence: getReactNativePersistence(AsyncStorage),
});

export default function App() {
  const [email,setEmail] = useState("");
  const [pw,setPw]     = useState("");
  const [msg,setMsg]   = useState("");

  const handleSignup = async () => {
    try {
      await createUserWithEmailAndPassword(auth, email, pw);
      setMsg("Signed up! Now log in.");
    } catch (e) {
      setMsg(e.message);
    }
  };

  const handleLogin = async () => {
    try {
      const { user } = await signInWithEmailAndPassword(auth, email, pw);
      const token = await user.getIdToken();
      const res = await axios.get("http://10.0.0.2:8000/protected", {
        headers: { Authorization: `Bearer ${token}` },
      });
      setMsg(res.data.message);
    } catch (e) {
      setMsg(e.response?.data?.detail || e.message);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Triagely Mobile Auth</Text>
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
  container: { flex:1, justifyContent:"center", padding:20 },
  title: { fontSize:24, textAlign:"center", marginBottom:20 },
  input: { borderWidth:1, padding:8, marginBottom:12, borderRadius:4 },
  buttons: { flexDirection:"row", justifyContent:"space-between", marginBottom:12 },
  msg: { textAlign:"center", marginTop:12 }
});