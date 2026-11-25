import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { api } from "../api";

/** Label of the Indian financial year (Apr–Mar) containing today, e.g. "2026-27". */
export function currentFy(today: Date = new Date()): string {
  const start = today.getMonth() >= 3 ? today.getFullYear() : today.getFullYear() - 1;
  return `${start}-${String((start + 1) % 100).padStart(2, "0")}`;
}

interface FyState {
  /** Selected financial year label; pages pass it as the `fy` query parameter. */
  fy: string;
  setFy: (fy: string) => void;
  /** Available labels, newest first (always includes the current FY). */
  options: string[];
}

const FyContext = createContext<FyState | null>(null);

export function FyProvider({ children }: { children: ReactNode }) {
  const [fy, setFy] = useState<string>(() => currentFy());
  const [fetched, setFetched] = useState<string[]>([]);

  useEffect(() => {
    let cancelled = false;
    api
      .get<string[]>("/fy")
      .then((list) => {
        if (!cancelled) setFetched(list);
      })
      .catch(() => {
        // The selector still works with just the current FY.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const options = useMemo(() => {
    const set = new Set<string>([currentFy(), ...fetched]);
    return [...set].sort().reverse();
  }, [fetched]);

  const value = useMemo<FyState>(() => ({ fy, setFy, options }), [fy, options]);
  return <FyContext.Provider value={value}>{children}</FyContext.Provider>;
}

export function useFy(): FyState {
  const ctx = useContext(FyContext);
  if (!ctx) throw new Error("useFy must be used inside <FyProvider>");
  return ctx;
}
