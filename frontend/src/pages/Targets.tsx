import { useEffect, useState } from "react";
import { api, ApiError } from "../api";
import Card from "../components/Card";
import Empty from "../components/Empty";
import { useFy } from "../components/FyContext";

interface TargetCard {
  period: string;
  label: string;
  start: string;
  end: string;
  target: string;
  achieved: string;
  status: string;
  progress: string;
}

const inr = new Intl.NumberFormat("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

function money(value: string): string {
  const n = Number(value);
  return Number.isFinite(n) ? inr.format(n) : value;
}

const TITLES: Record<string, string> = {
  yearly: "Yearly",
  quarterly: "Quarterly",
  monthly: "Monthly",
  weekly: "Weekly",
};

function badgeClass(status: string): string {
  if (status === "Met") return "badge badge-success";
  if (status === "In progress") return "badge badge-warning";
  return "badge badge-danger";
}

export default function Targets() {
  const { fy } = useFy();
  const [cards, setCards] = useState<TargetCard[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    api
      .get<TargetCard[]>("/targets", { fy })
      .then((res) => {
        if (!cancelled) setCards(res);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Could not load targets.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [fy, reloadKey]);

  return (
    <>
      <h1>Target</h1>
      {error && (
        <div className="banner banner-error" role="alert">
          {error}{" "}
          <button type="button" onClick={() => setReloadKey((k) => k + 1)}>
            Retry
          </button>
        </div>
      )}
      {loading && <div className="loading">Loading…</div>}
      {!loading && !error && cards && cards.length === 0 && (
        <Card>
          <Empty message="No targets to show for this financial year." />
        </Card>
      )}
      {!loading && !error && cards && cards.length > 0 && (
        <div className="grid">
          {cards.map((c) => {
            const pct = Math.min(100, Math.max(0, Number(c.progress) || 0));
            const achieved = Number(c.achieved);
            return (
              <Card key={c.period} title={TITLES[c.period] ?? c.period}>
                <p className="muted" style={{ marginTop: 0 }}>
                  {c.label}
                </p>
                <div className="stat-label">Target</div>
                <div className="stat-value">₹{money(c.target)}</div>
                <div className="stat-label" style={{ marginTop: 8 }}>
                  Achieved
                </div>
                <div className={`stat-value ${achieved > 0 ? "pos" : achieved < 0 ? "neg" : ""}`}>₹{money(c.achieved)}</div>
                <div
                  className="progress"
                  role="progressbar"
                  aria-label={`${TITLES[c.period] ?? c.period} progress`}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-valuenow={pct}
                  style={{ margin: "12px 0 8px" }}
                >
                  <span style={{ width: `${pct}%` }} />
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span className="muted">{pct.toFixed(0)}%</span>
                  <span className={badgeClass(c.status)}>{c.status}</span>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </>
  );
}
