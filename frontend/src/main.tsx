import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth";
import "./styles.css";

// Placeholder shell; the layout, routes and pages are added by the next frontend tasks.
function App() {
  const { user, loading } = useAuth();
  return (
    <main className="page">
      <h1>F&amp;O Portfolio Tracker</h1>
      <p className="muted">{loading ? "Loading…" : user ? `Signed in as ${user.email}` : "Not signed in"}</p>
    </main>
  );
}

const container = document.getElementById("root");
if (!container) throw new Error("Root element #root not found");

createRoot(container).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <App />
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
);
