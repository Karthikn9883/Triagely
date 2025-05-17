// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
import { getAuth } from "firebase/auth";
// TODO: Add SDKs for Firebase products that you want to use
// https://firebase.google.com/docs/web/setup#available-libraries

// Your web app's Firebase configuration
// For Firebase JS SDK v7.20.0 and later, measurementId is optional
const firebaseConfig = {
  apiKey: "AIzaSyAtX-2ZmuRC6eDapi2WkYtR7kF-vSf_BAw",
  authDomain: "triagely-c4f38.firebaseapp.com",
  projectId: "triagely-c4f38",
  storageBucket: "triagely-c4f38.firebasestorage.app",
  messagingSenderId: "462011870278",
  appId: "1:462011870278:web:029a5396c60877c79e2e47",
  measurementId: "G-L9DZWQD0KM"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const analytics = getAnalytics(app);
export const auth = getAuth(app);