interface Props {
  page: number;
  pageSize: number;
  total: number;
  onChange: (page: number) => void;
}

export default function Pager({ page, pageSize, total, onChange }: Props) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  const from = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, total);
  return (
    <div className="pager">
      <span className="muted">
        {from}–{to} of {total}
      </span>
      <span>
        <button type="button" onClick={() => onChange(page - 1)} disabled={page <= 1}>
          Previous
        </button>{" "}
        <span aria-live="polite">
          Page {page} of {pages}
        </span>{" "}
        <button type="button" onClick={() => onChange(page + 1)} disabled={page >= pages}>
          Next
        </button>
      </span>
    </div>
  );
}
