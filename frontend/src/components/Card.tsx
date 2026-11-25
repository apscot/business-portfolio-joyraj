import type { ReactNode } from "react";

export default function Card({ title, children, className }: { title?: string; children: ReactNode; className?: string }) {
  return (
    <section className={className ? `card ${className}` : "card"}>
      {title && <h3>{title}</h3>}
      {children}
    </section>
  );
}
