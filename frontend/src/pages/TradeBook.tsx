import { useEffect, useRef, useState } from "react";
import type { ChangeEvent, DragEvent } from "react";
import { api, ApiError } from "../api";
import type { TradeUploadResult } from "../api";
import Card from "../components/Card";
import Empty from "../components/Empty";
import { useFy } from "../components/FyContext";
import Pager from "../components/Pager";
import Table from "../components/Table";
import type { Column } from "../components/Table";

const PAGE_SIZE = 15;
const MAX_UPLOAD_BYTES = 5 * 1024 * 1024;

export interface Trade {
  id: number;
  symbol: string;
  isin: string;
  trade_date: string;
  exchange: string;
  segment: string;
  series: string;
  trade_type: string;
  auction: boolean;
  quantity: string | number;
  price: string | number;
  trade_id: string;
  order_id: string;
  order_execution_time: string;
  expiry_date: string | null;
  underlying: string;
}

interface TradePage {
  items: Trade[];
  total: number;
  page: number;
  page_size: number;
}

const columns: Column<Trade>[] = [
  { key: "symbol", header: "Symbol", render: (t) => t.symbol },
  { key: "isin", header: "ISIN", render: (t) => t.isin },
  { key: "trade_date", header: "Trade date", render: (t) => t.trade_date },
  { key: "exchange", header: "Exchange", render: (t) => t.exchange },
  { key: "segment", header: "Segment", render: (t) => t.segment },
  { key: "series", header: "Series", render: (t) => t.series },
  {
    key: "trade_type",
    header: "Type",
    render: (t) => (
      <span className={`badge ${t.trade_type.toLowerCase() === "buy" ? "badge-success" : "badge-danger"}`}>{t.trade_type}</span>
    ),
  },
  { key: "auction", header: "Auction", render: (t) => (t.auction ? "Yes" : "No") },
  { key: "quantity", header: "Quantity", numeric: true, render: (t) => String(t.quantity) },
  { key: "price", header: "Price", numeric: true, render: (t) => String(t.price) },
  { key: "trade_id", header: "Trade ID", render: (t) => t.trade_id },
  { key: "order_id", header: "Order ID", render: (t) => t.order_id },
  { key: "order_execution_time", header: "Order execution time", render: (t) => t.order_execution_time.replace("T", " ") },
  { key: "expiry_date", header: "Expiry date", render: (t) => t.expiry_date ?? "—" },
  { key: "underlying", header: "Underlying", render: (t) => t.underlying },
];

function messageOf(err: unknown): string {
  return err instanceof ApiError ? err.message : "Something went wrong. Please try again.";
}

export default function TradeBook() {
  const { fy } = useFy();
  const [page, setPage] = useState(1);
  const [data, setData] = useState<TradePage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reload, setReload] = useState(0);

  const [uploading, setUploading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [result, setResult] = useState<TradeUploadResult | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setPage(1);
  }, [fy]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    api
      .get<TradePage>("/trades", { fy, page, page_size: PAGE_SIZE })
      .then((res) => {
        if (cancelled) return;
        setData(res);
        setLoading(false);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(messageOf(err));
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [fy, page, reload]);

  async function upload(file: File | undefined) {
    if (!file) return;
    setResult(null);
    setUploadError(null);
    if (!file.name.toLowerCase().endsWith(".csv")) {
      setUploadError("Please choose a .csv file.");
      return;
    }
    if (file.size > MAX_UPLOAD_BYTES) {
      setUploadError("File exceeds 5 MB.");
      return;
    }
    setUploading(true);
    try {
      setResult(await api.upload<TradeUploadResult>("/trades/upload", file));
      setPage(1);
      setReload((n) => n + 1);
    } catch (err) {
      setUploadError(messageOf(err));
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  function onChoose(e: ChangeEvent<HTMLInputElement>) {
    void upload(e.target.files?.[0]);
  }

  function onDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragging(false);
    if (!uploading) void upload(e.dataTransfer.files[0]);
  }

  const total = data?.total ?? 0;

  return (
    <>
      <h1>TradeBook</h1>

      <Card title="Upload trades">
        <div
          data-testid="dropzone"
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          style={{
            border: `2px dashed ${dragging ? "var(--primary)" : "var(--border)"}`,
            background: dragging ? "var(--primary-soft)" : "var(--surface-alt)",
            borderRadius: "var(--radius)",
            padding: "calc(var(--space) * 3) calc(var(--space) * 2)",
            textAlign: "center",
          }}
        >
          <p className="muted">Drag and drop a tradebook CSV here, or</p>
          <input
            ref={inputRef}
            id="trade-file"
            type="file"
            accept=".csv,text/csv"
            onChange={onChoose}
            disabled={uploading}
            hidden
          />
          <button type="button" className="btn-primary" onClick={() => inputRef.current?.click()} disabled={uploading}>
            {uploading ? "Uploading…" : "Choose CSV file"}
          </button>
        </div>

        {uploadError && (
          <div className="banner banner-error" role="alert" style={{ marginTop: "calc(var(--space) * 2)" }}>
            {uploadError}
          </div>
        )}
        {result && (
          <div role="status" style={{ marginTop: "calc(var(--space) * 2)" }}>
            <div className="banner banner-success">
              <strong>Upload complete:</strong> {result.inserted} inserted, {result.duplicates} duplicate
              {result.duplicates === 1 ? "" : "s"} skipped, {result.invalid.length} invalid.
            </div>
            {result.invalid.length > 0 && (
              <ul>
                {result.invalid.slice(0, 20).map((r) => (
                  <li key={`${r.row}-${r.reason}`}>
                    Row {r.row}: {r.reason}
                  </li>
                ))}
                {result.invalid.length > 20 && <li>…and {result.invalid.length - 20} more.</li>}
              </ul>
            )}
          </div>
        )}
      </Card>

      <Card title={`Trades — FY ${fy}`}>
        {error && (
          <div className="banner banner-error" role="alert">
            {error}{" "}
            <button type="button" onClick={() => setReload((n) => n + 1)}>
              Retry
            </button>
          </div>
        )}
        {loading && !data && !error && <div className="loading">Loading…</div>}
        {data && !error && (
          <div aria-busy={loading}>
            {total === 0 ? (
              <Empty message={`No trades for FY ${fy}. Upload a tradebook CSV to get started.`} />
            ) : (
              <>
                <Table columns={columns} rows={data.items} rowKey={(t) => t.id} />
                <Pager page={page} pageSize={PAGE_SIZE} total={total} onChange={setPage} />
              </>
            )}
          </div>
        )}
      </Card>
    </>
  );
}
