import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth";
import { FyProvider } from "./FyContext";
import FySelect from "./FySelect";

export { useFy } from "./FyContext";

const NAV = [
  { to: "/", label: "Home", end: true },
  { to: "/trades", label: "TradeBook", end: false },
  { to: "/pnl", label: "P&L", end: false },
  { to: "/targets", label: "Target", end: false },
];

export default function Layout() {
  const { user, logout } = useAuth();
  return (
    <FyProvider>
      <div className="app">
        <nav className="sidebar" aria-label="Main">
          <div className="brand">F&amp;O Tracker</div>
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.end} className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}>
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="main">
          <header className="topbar">
            <FySelect />
            <span className="muted">{user?.email}</span>
            <button type="button" onClick={logout}>
              Log out
            </button>
          </header>
          <main className="page">
            <Outlet />
          </main>
        </div>
      </div>
    </FyProvider>
  );
}
