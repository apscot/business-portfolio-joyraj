import { useEffect, useState } from "react";
import { api, ApiError } from "../api";
import Card from "../components/Card";
import { useFy } from "../components/FyContext";
import Table from "../components/Table";
import type { Column } from "../components/Table";

interface PnlRow {
  expiry_date: string;
  underlying: string;
  trades: number;
  pnl: string;
  open: boolean;
}

interface PnlResponse {
  fy: string;
  rows: PnlRow[];
  total: string;
}

type Filter = "All" | "NIFTY" | "SENSEX";
const FILTERS: Filter[] = ["All", "NIFTY", "SENSEX"];

const inr = new Intl.NumberFormat("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

function money(value: string): string {
  const n = Number(value);
  return Number.isFinite(n) ? inr.format(n) : value;
}

function tone(value: string): string {
  const n = Number(value);
  if (n > 0) return "pos";
  if (n < 0) return "neg";
  return "";
}

const columns: Column<PnlRow>[] = [
  { key: "expiry", header: "Expiry", render: (r) => r.expiry_date },
  { key: "underlying", header: "Underlying", render: (r) => r.underlying },
  { key: "trades", header: "Trades", numeric: true, render: (r) => r.trades },
  {
    key: "pnl",
    header: "P&L (₹)",
    numeric: true,
    render: (r) => <span className={tone(r.pnl)}>{money(r.pnl)}</span>,
  },
  {
    key: "status",
    header: "Status",
    render: (r) => (r.open ? <span className="badge badge-warning">Open</span> : <span className="muted">Closed</span>),
  },
];

export default function PnL() {
  const { fy } = useFy();
  const [filter, setFilter] = useState<Filter>("All");
  const [data, setData] = useState<PnlResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    api
      .get<PnlResponse>("/pnl", { fy, underlying: filter === "All" ? undefined : filter })
      .then((res) => {
        if (!cancelled) setData(res);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Could not load P&L.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [fy, filter, reloadKey]);

  return (
    <>
      <h1>P&amp;L</h1>
      <Card>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center", marginBottom: 16 }}>
          <span className="muted">Underlying:</span>
          {FILTERS.map((f) => (
            <button
              key={f}
              type="button"
              className={f === filter ? "btn-primary" : undefined}
              aria-pressed={f === filter}
              onClick={() => setFilter(f)}
            >
              {f}
            </button>
          ))}
        </div>

        {error && (
          <div className="banner banner-error" role="alert">
            {error}{" "}
            <button type="button" onClick={() => setReloadKey((k) => k + 1)}>
              Retry
            </button>
          </div>
        )}
        {loading && <div className="loading">Loading…</div>}
        {!loading && !error && data && (
          <>
            <Table
              columns={columns}
              rows={data.rows}
              rowKey={(r) => `${r.expiry_date}|${r.underlying}`}
              emptyMessage="No trades with expiries in this financial year."
            />
            {data.rows.length > 0 && (
              <p style={{ textAlign: "right", fontWeight: 600, marginBottom: 0 }}>
                Total: <span className={tone(data.total)}>₹{money(data.total)}</span>
              </p>
            )}
          </>
        )}
      </Card>
    </>
  );
}
