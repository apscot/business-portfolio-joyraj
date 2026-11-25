import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import type { ReactNode } from "react";
import { useAuth } from "./auth";
import Layout from "./components/Layout";
import Card from "./components/Card";
import Login from "./pages/Login";

/** Temporary page body; replaced by the real pages in later tasks. */
function Placeholder({ title }: { title: string }) {
  return (
    <>
      <h1>{title}</h1>
      <Card>
        <p className="muted">This page is coming soon.</p>
      </Card>
    </>
  );
}

function RequireAuth({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <div className="loading">Loading…</div>;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        element={
          <RequireAuth>
            <Layout />
          </RequireAuth>
        }
      >
        <Route index element={<Placeholder title="Home" />} />
        <Route path="trades" element={<Placeholder title="TradeBook" />} />
        <Route path="pnl" element={<Placeholder title="P&L" />} />
        <Route path="targets" element={<Placeholder title="Target" />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export { App };
