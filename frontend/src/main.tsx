import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";

// Apply saved theme before React mounts to avoid flash
const savedTheme = localStorage.getItem("vajans-theme") || "dark";
if (savedTheme === "light") {
  document.documentElement.classList.add("light");
} else {
  document.documentElement.classList.add("dark");
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
