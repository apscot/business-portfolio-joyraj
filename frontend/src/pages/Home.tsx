import { useCallback, useEffect, useRef, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, ApiError } from "../api";
import Card from "../components/Card";
import Empty from "../components/Empty";
import { useFy } from "../components/FyContext";
import Table from "../components/Table";
import type { Column } from "../components/Table";

interface Holding {
  id: number;
  name: string;
  kind: string;
  amount: string | number;
  as_of_date: string;
}
interface Entry {
  id: number;
  date: string;
  amount: string | number;
  note: string;
}
interface GrowthPoint {
  date: string;
  invested: string | number;
  total: string | number;
}
interface Summary {
  fy: string;
  invested: string | number;
  interest: string | number;
  total: string | number;
  holdings: string | number;
  series: GrowthPoint[];
}
interface Data {
  summary: Summary;
  holdings: Holding[];
  interest: Entry[];
  investments: Entry[];
}
type Kind = "gsec" | "mutual_fund" | "other";
type Resource = "holdings" | "interest" | "investments";

const KIND_LABELS: Record<Kind, string> = { gsec: "G-Sec", mutual_fund: "Mutual fund", other: "Other" };
const AMOUNT_RE = /^\d{1,16}(\.\d{1,2})?$/;
const money = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 });

function fmt(value: string | number): string {
  return money.format(Number(value));
}

function pad(n: number): string {
  return String(n).padStart(2, "0");
}

/** First and last calendar day (YYYY-MM-DD) of a financial-year label such as "2026-27". */
function fyBounds(fy: string): { min: string; max: string } {
  const start = Number.parseInt(fy.slice(0, 4), 10);
  return { min: `${start}-04-01`, max: `${start + 1}-03-31` };
}

/** Today (local) clamped into the financial year, as YYYY-MM-DD. */
function defaultDate(fy: string): string {
  const now = new Date();
  const today = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
  const { min, max } = fyBounds(fy);
  return today < min ? min : today > max ? max : today;
}

function validateCommon(amount: string, date: string, fy: string): { amount?: string; date?: string } {
  const errors: { amount?: string; date?: string } = {};
  if (!AMOUNT_RE.test(amount.trim()) || Number(amount) <= 0) errors.amount = "Enter an amount above 0 with up to 2 decimals.";
  const { min, max } = fyBounds(fy);
  if (!date) errors.date = "Choose a date.";
  else if (date < min || date > max) errors.date = `Date must be within FY ${fy}.`;
  return errors;
}

function Field({ id, label, error, children }: { id: string; label: string; error?: string; children: ReactNode }) {
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      {children}
      {error && (
        <div className="field-error" id={`${id}-error`}>
          {error}
        </div>
      )}
    </div>
  );
}

function HoldingForm({ fy, onSubmit }: { fy: string; onSubmit: (body: Record<string, string>) => Promise<boolean> }) {
  const [name, setName] = useState("");
  const [kind, setKind] = useState<Kind>("gsec");
  const [amount, setAmount] = useState("");
  const [date, setDate] = useState(() => defaultDate(fy));
  const [errors, setErrors] = useState<{ name?: string; amount?: string; date?: string }>({});
  const [busy, setBusy] = useState(false);
  const { min, max } = fyBounds(fy);

  async function submit(e: FormEvent) {
    e.preventDefault();
    const next: { name?: string; amount?: string; date?: string } = validateCommon(amount, date, fy);
    const trimmed = name.trim();
    if (!trimmed) next.name = "Enter a name.";
    else if (trimmed.length > 200) next.name = "Name must be at most 200 characters.";
    setErrors(next);
    if (next.name || next.amount || next.date) return;
    setBusy(true);
    const ok = await onSubmit({ name: trimmed, kind, amount: amount.trim(), as_of_date: date });
    setBusy(false);
    if (ok) {
      setName("");
      setAmount("");
    }
  }

  return (
    <form onSubmit={submit} noValidate aria-label="Add holding">
      <Field id="holding-name" label="Holding name" error={errors.name}>
        <input id="holding-name" value={name} maxLength={200} onChange={(e) => setName(e.target.value)} aria-invalid={errors.name ? true : undefined} />
      </Field>
      <Field id="holding-kind" label="Type">
        <select id="holding-kind" value={kind} onChange={(e) => setKind(e.target.value as Kind)}>
          {(Object.keys(KIND_LABELS) as Kind[]).map((k) => (
            <option key={k} value={k}>
              {KIND_LABELS[k]}
            </option>
          ))}
        </select>
      </Field>
      <Field id="holding-amount" label="Holding amount (₹)" error={errors.amount}>
        <input id="holding-amount" inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value)} aria-invalid={errors.amount ? true : undefined} />
      </Field>
      <Field id="holding-date" label="Holding as-of date" error={errors.date}>
        <input id="holding-date" type="date" min={min} max={max} value={date} onChange={(e) => setDate(e.target.value)} aria-invalid={errors.date ? true : undefined} />
      </Field>
      <button type="submit" className="btn-primary" disabled={busy}>
        {busy ? "Adding…" : "Add holding"}
      </button>
    </form>
  );
}

function EntryForm({
  fy,
  idPrefix,
  label,
  onSubmit,
}: {
  fy: string;
  idPrefix: string;
  label: string;
  onSubmit: (body: Record<string, string>) => Promise<boolean>;
}) {
  const [amount, setAmount] = useState("");
  const [date, setDate] = useState(() => defaultDate(fy));
  const [note, setNote] = useState("");
  const [errors, setErrors] = useState<{ amount?: string; date?: string; note?: string }>({});
  const [busy, setBusy] = useState(false);
  const { min, max } = fyBounds(fy);

  async function submit(e: FormEvent) {
    e.preventDefault();
    const next: { amount?: string; date?: string; note?: string } = validateCommon(amount, date, fy);
    if (note.trim().length > 500) next.note = "Note must be at most 500 characters.";
    setErrors(next);
    if (next.amount || next.date || next.note) return;
    setBusy(true);
    const ok = await onSubmit({ amount: amount.trim(), date, note: note.trim() });
    setBusy(false);
    if (ok) {
      setAmount("");
      setNote("");
    }
  }

  return (
    <form onSubmit={submit} noValidate aria-label={`Add ${label.toLowerCase()}`}>
      <Field id={`${idPrefix}-amount`} label={`${label} amount (₹)`} error={errors.amount}>
        <input id={`${idPrefix}-amount`} inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value)} aria-invalid={errors.amount ? true : undefined} />
      </Field>
      <Field id={`${idPrefix}-date`} label={`${label} date`} error={errors.date}>
        <input id={`${idPrefix}-date`} type="date" min={min} max={max} value={date} onChange={(e) => setDate(e.target.value)} aria-invalid={errors.date ? true : undefined} />
      </Field>
      <Field id={`${idPrefix}-note`} label={`${label} note (optional)`} error={errors.note}>
        <input id={`${idPrefix}-note`} value={note} maxLength={500} onChange={(e) => setNote(e.target.value)} />
      </Field>
      <button type="submit" className="btn-primary" disabled={busy}>
        {busy ? "Adding…" : `Add ${label.toLowerCase()}`}
      </button>
    </form>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
    </Card>
  );
}

function GrowthChart({ series }: { series: GrowthPoint[] }) {
  if (series.length === 0) return <Empty message="No invested or interest entries in this financial year yet." />;
  const data = series.map((p) => ({ date: p.date, invested: Number(p.invested), total: Number(p.total) }));
  return (
    <div style={{ width: "100%", height: 280 }} role="img" aria-label="Portfolio growth chart">
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis dataKey="date" tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} width={72} tickFormatter={(v: number) => money.format(v)} />
          <Tooltip formatter={(v: number) => money.format(v)} />
          <Legend />
          <Line type="monotone" dataKey="total" name="Invested + interest" stroke="var(--primary)" strokeWidth={2} dot={false} />
          <Line type="monotone" dataKey="invested" name="Invested" stroke="var(--success)" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export default function Home() {
  const { fy } = useFy();
  const [data, setData] = useState<Data | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<{ text: string; error: boolean } | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);
  const requestId = useRef(0);
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const showToast = useCallback((text: string, isError = false) => {
    if (toastTimer.current) clearTimeout(toastTimer.current);
    setToast({ text, error: isError });
    toastTimer.current = setTimeout(() => setToast(null), 4000);
  }, []);

  useEffect(
    () => () => {
      if (toastTimer.current) clearTimeout(toastTimer.current);
    },
    [],
  );

  const load = useCallback(async (): Promise<void> => {
    const id = ++requestId.current;
    setLoading(true);
    setError(null);
    try {
      const [summary, holdings, interest, investments] = await Promise.all([
        api.get<Summary>("/summary", { fy }),
        api.get<Holding[]>("/holdings", { fy }),
        api.get<Entry[]>("/interest", { fy }),
        api.get<Entry[]>("/investments", { fy }),
      ]);
      if (id !== requestId.current) return;
      setData({ summary, holdings, interest, investments });
    } catch (err) {
      if (id !== requestId.current) return;
      setError(err instanceof ApiError ? err.message : "Could not load your portfolio.");
    } finally {
      if (id === requestId.current) setLoading(false);
    }
  }, [fy]);

  useEffect(() => {
    void load();
    return () => {
      requestId.current++;
    };
  }, [load]);

  async function add(resource: Resource, body: Record<string, string>, success: string): Promise<boolean> {
    try {
      await api.post(`/${resource}`, body);
    } catch (err) {
      showToast(err instanceof ApiError ? err.message : "Could not save. Please try again.", true);
      return false;
    }
    showToast(success);
    await load();
    return true;
  }

  async function remove(resource: Resource, id: number, success: string) {
    const key = `${resource}-${id}`;
    setDeleting(key);
    try {
      await api.del(`/${resource}/${id}`);
      showToast(success);
      await load();
    } catch (err) {
      showToast(err instanceof ApiError ? err.message : "Could not delete. Please try again.", true);
    } finally {
      setDeleting(null);
    }
  }

  function deleteColumn<T extends { id: number }>(resource: Resource, what: string, success: string): Column<T> {
    return {
      key: "delete",
      header: "",
      render: (row) => (
        <button type="button" className="btn-danger" disabled={deleting === `${resource}-${row.id}`} aria-label={`Delete ${what} ${row.id}`} onClick={() => void remove(resource, row.id, success)}>
          Delete
        </button>
      ),
    };
  }

  const holdingColumns: Column<Holding>[] = [
    { key: "name", header: "Name", render: (r) => r.name },
    { key: "kind", header: "Type", render: (r) => KIND_LABELS[r.kind as Kind] ?? r.kind },
    { key: "amount", header: "Amount", numeric: true, render: (r) => fmt(r.amount) },
    { key: "date", header: "As of", render: (r) => r.as_of_date },
    deleteColumn<Holding>("holdings", "holding", "Holding deleted."),
  ];
  const entryColumns = (resource: Resource, what: string, success: string): Column<Entry>[] => [
    { key: "date", header: "Date", render: (r) => r.date },
    { key: "amount", header: "Amount", numeric: true, render: (r) => fmt(r.amount) },
    { key: "note", header: "Note", render: (r) => r.note || "—" },
    deleteColumn<Entry>(resource, what, success),
  ];

  return (
    <>
      <h1>Home</h1>
      <p className="muted">Portfolio for financial year {fy}.</p>

      {error && (
        <div className="banner banner-error" role="alert">
          {error}{" "}
          <button type="button" onClick={() => void load()}>
            Retry
          </button>
        </div>
      )}

      {loading && !data && <div className="loading">Loading…</div>}

      {data && (
        <div aria-busy={loading} style={{ opacity: loading ? 0.6 : 1 }}>
          <div className="grid" style={{ marginBottom: 16 }}>
            <Stat label="Invested value" value={fmt(data.summary.invested)} />
            <Stat label="Interest accrued" value={fmt(data.summary.interest)} />
            <Stat label="Invested + interest" value={fmt(data.summary.total)} />
            <Stat label="Holdings" value={fmt(data.summary.holdings)} />
          </div>

          <Card title="Growth">
            <GrowthChart series={data.summary.series} />
          </Card>
        </div>
      )}

      <div className="grid" style={{ margin: "16px 0" }}>
        <Card title="Add holding">
          <HoldingForm key={`h-${fy}`} fy={fy} onSubmit={(b) => add("holdings", b, "Holding added.")} />
        </Card>
        <Card title="Add interest">
          <EntryForm key={`i-${fy}`} fy={fy} idPrefix="interest" label="Interest" onSubmit={(b) => add("interest", b, "Interest added.")} />
        </Card>
        <Card title="Add invested value">
          <EntryForm key={`v-${fy}`} fy={fy} idPrefix="invested" label="Invested value" onSubmit={(b) => add("investments", b, "Invested value added.")} />
        </Card>
      </div>

      {data && (
        <div style={{ display: "grid", gap: 16 }}>
          <Card title="Holdings">
            <Table columns={holdingColumns} rows={data.holdings} rowKey={(r) => r.id} emptyMessage="No holdings in this financial year. Add one above." />
          </Card>
          <Card title="Interest">
            <Table columns={entryColumns("interest", "interest entry", "Interest deleted.")} rows={data.interest} rowKey={(r) => r.id} emptyMessage="No interest entries in this financial year. Add one above." />
          </Card>
          <Card title="Invested value">
            <Table columns={entryColumns("investments", "invested value entry", "Invested value deleted.")} rows={data.investments} rowKey={(r) => r.id} emptyMessage="No invested value entries in this financial year. Add one above." />
          </Card>
        </div>
      )}

      {toast && (
        <div className="toast" role="status" style={toast.error ? { background: "var(--danger)" } : undefined}>
          {toast.text}
        </div>
      )}
    </>
  );
}
