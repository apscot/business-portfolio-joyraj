import { useFy } from "./FyContext";

export default function FySelect() {
  const { fy, setFy, options } = useFy();
  return (
    <label style={{ display: "flex", alignItems: "center", gap: 8, margin: 0 }}>
      <span className="muted">Financial year</span>
      <select value={fy} onChange={(e) => setFy(e.target.value)} aria-label="Financial year">
        {options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    </label>
  );
}
