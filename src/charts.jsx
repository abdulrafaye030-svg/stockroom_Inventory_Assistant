import React, { useRef, useState } from "react";
import Icon from "./Icon.jsx";
import { formatNumber, formatRs, niceScale, stockProportion } from "./inventory.js";

// Shared hover/focus tooltip, positioned inside the chart's own box.
function useTooltip() {
  const boxRef = useRef(null);
  const [tip, setTip] = useState(null);
  function show(event, content) {
    const box = boxRef.current?.getBoundingClientRect();
    const mark = event.currentTarget.getBoundingClientRect();
    if (!box) return;
    setTip({ x: mark.left + mark.width / 2 - box.left, y: mark.top - box.top, content });
  }
  return { boxRef, tip, show, hide: () => setTip(null) };
}

function Tooltip({ tip }) {
  if (!tip) return null;
  return (
    <div className="chart-tooltip" style={{ left: tip.x, top: tip.y }} role="tooltip">
      {tip.content}
    </div>
  );
}

function TipRows({ title, rows }) {
  return (
    <>
      <strong>{title}</strong>
      {rows.map(([label, value]) => (
        <span key={label} className="tip-row"><span>{label}</span><b>{value}</b></span>
      ))}
    </>
  );
}

/* Horizontal bars: stock on hand per product, with each product's reorder point marked. */
export function StockBars({ products, limit = 8 }) {
  const { boxRef, tip, show, hide } = useTooltip();
  const rows = [...products]
    .sort((a, b) => stockProportion(a) - stockProportion(b) || a.stock - b.stock)
    .slice(0, limit);
  const { max, ticks } = niceScale(Math.max(1, ...rows.map((p) => Math.max(p.stock, p.reorder_level))));
  const pct = (value) => `${(Math.max(0, value) / max) * 100}%`;

  return (
    <div className="hbar-chart" ref={boxRef} onMouseLeave={hide}>
      <div className="hbar-grid" aria-hidden="true">
        {ticks.map((t) => (
          <span key={t} className="hbar-gridline" style={{ left: pct(t) }}><span>{formatNumber(t)}</span></span>
        ))}
      </div>
      {rows.map((p) => (
        <div
          key={p.name}
          className="hbar-row"
          tabIndex={0}
          aria-label={`${p.name}: ${p.stock} ${p.unit} on hand, reorder at ${p.reorder_level}`}
          onMouseEnter={(e) => show(e, <TipRows title={p.name} rows={[["On hand", `${p.stock} ${p.unit}`], ["Reorder at", p.reorder_level]]} />)}
          onFocus={(e) => show(e, <TipRows title={p.name} rows={[["On hand", `${p.stock} ${p.unit}`], ["Reorder at", p.reorder_level]]} />)}
          onBlur={hide}
        >
          <span className="hbar-label">{p.name}</span>
          <span className="hbar-track">
            {p.stock > 0 && <span className="hbar-fill" style={{ width: pct(p.stock) }} />}
            <span className="hbar-reorder" style={{ left: pct(p.reorder_level) }} />
          </span>
          <span className="hbar-value">{p.stock}</span>
        </div>
      ))}
      <Tooltip tip={tip} />
    </div>
  );
}

/* Vertical bars: amount owed per customer; the largest is emphasised, the rest stay grey. */
export function BalanceBars({ customers, limit = 7 }) {
  const { boxRef, tip, show, hide } = useTooltip();
  const rows = customers.filter((c) => c.due > 0).slice(0, limit);
  if (rows.length === 0) return <p className="chart-empty">All customer balances are clear.</p>;
  const { max } = niceScale(Math.max(...rows.map((c) => c.due)));
  const top = rows[0].name;

  return (
    <div className="vbar-chart" ref={boxRef} onMouseLeave={hide}>
      {rows.map((c) => {
        const content = <TipRows title={c.name} rows={[["Billed", formatRs(c.billed)], ["Paid", formatRs(c.paid)], ["Owes", formatRs(c.due)]]} />;
        return (
          <div
            key={c.name}
            className={`vbar-col ${c.name === top ? "is-top" : ""}`}
            tabIndex={0}
            aria-label={`${c.name} owes ${formatRs(c.due)}`}
            onMouseEnter={(e) => show(e, content)}
            onFocus={(e) => show(e, content)}
            onBlur={hide}
          >
            <span className="vbar-slot">
              {c.name === top && <span className="vbar-value">{formatRs(c.due)}</span>}
              <span className="vbar-fill" style={{ height: `${(c.due / max) * 100}%` }} />
            </span>
            <span className="vbar-label">{c.name}</span>
          </div>
        );
      })}
      <Tooltip tip={tip} />
    </div>
  );
}

/* Half-circle tick gauge for a single percentage. */
export function TickGauge({ percent, label }) {
  const count = 34;
  const filled = Math.round((Math.max(0, Math.min(100, percent)) / 100) * count);
  const ticks = Array.from({ length: count }, (_, i) => {
    const angle = Math.PI - (i / (count - 1)) * Math.PI;
    const cos = Math.cos(angle);
    const sin = Math.sin(angle);
    return { x1: 100 + cos * 66, y1: 100 - sin * 66, x2: 100 + cos * 90, y2: 100 - sin * 90, on: i < filled };
  });
  return (
    <div className="gauge">
      <svg viewBox="0 0 200 106" role="img" aria-label={`${Math.round(percent)}% ${label}`}>
        {ticks.map((t, i) => (
          <line key={i} x1={t.x1} y1={t.y1} x2={t.x2} y2={t.y2} className={t.on ? "gauge-on" : "gauge-off"} />
        ))}
      </svg>
      <div className="gauge-center">
        <strong>{Math.round(percent)}%</strong>
        <span>{label}</span>
      </div>
    </div>
  );
}

/* Healthy / Low / Out counts, each with a bar showing its share of all products. */
export function StatusSplit({ overview, onSelect }) {
  const total = Math.max(1, overview.total_products);
  const healthy = overview.total_products - overview.low_stock - overview.out_of_stock;
  const cells = [
    { id: "healthy", filter: "in_stock", label: "Healthy", value: healthy, icon: "check" },
    { id: "low", filter: "low_stock", label: "Low stock", value: overview.low_stock, icon: "alert" },
    { id: "out", filter: "out_of_stock", label: "Out of stock", value: overview.out_of_stock, icon: "xcircle" },
  ];
  return (
    <div className="status-split">
      {cells.map((cell) => (
        <button key={cell.id} className={`split-cell split-${cell.id}`} onClick={() => onSelect(cell.filter)}>
          <span className="split-top">
            <span className="split-icon"><Icon name={cell.icon} size={14} /></span>
            <strong>{cell.value}</strong>
          </span>
          <span className="split-label">{cell.label}</span>
          <span className="split-track"><span style={{ width: `${(cell.value / total) * 100}%` }} /></span>
        </button>
      ))}
    </div>
  );
}
