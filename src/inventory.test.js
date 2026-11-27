import { afterEach, describe, expect, it, vi } from "vitest";
import { filterProducts, messageId, requestJson, stockProportion, summarizeInventory } from "./inventory.js";

// Matches the SQLite demo data, plus a negative-stock row.
const products = [
  { name: "Cooking Oil", stock: 0, unit: "bottles", reorder_level: 4, status: "out_of_stock" },
  { name: "Rice", stock: 20, unit: "bags", reorder_level: 5, status: "in_stock" },
  { name: "Salt", stock: -2, unit: "packs", reorder_level: 3, status: "out_of_stock" },
  { name: "Sugar", stock: 3, unit: "bags", reorder_level: 5, status: "low_stock" },
  { name: "Tea", stock: 4, unit: "boxes", reorder_level: 4, status: "low_stock" },
];
const names = (list) => list.map((product) => product.name);

describe("filterProducts", () => {
  it("In stock includes low-stock items and matches the In stock card count", () => {
    const visible = filterProducts(products, "in_stock", "");
    expect(names(visible)).toEqual(["Rice", "Sugar", "Tea"]);
    expect(visible).toHaveLength(summarizeInventory(products).in_stock);
  });

  it("filters other statuses by their exact status", () => {
    expect(names(filterProducts(products, "low_stock", ""))).toEqual(["Sugar", "Tea"]);
    expect(names(filterProducts(products, "out_of_stock", ""))).toEqual(["Cooking Oil", "Salt"]);
    expect(filterProducts(products, "all", "")).toHaveLength(products.length);
  });

  it("combines the filter with a case-insensitive search", () => {
    expect(names(filterProducts(products, "all", "  RICE "))).toEqual(["Rice"]);
    expect(names(filterProducts(products, "in_stock", "oil"))).toEqual([]);
  });
});

describe("summarizeInventory", () => {
  it("counts every metric card", () => {
    expect(summarizeInventory(products)).toEqual({
      total_products: 5, in_stock: 3, low_stock: 2, out_of_stock: 2, needs_attention: 4,
    });
  });
});

describe("stockProportion", () => {
  it("shows an empty bar for negative stock", () => {
    expect(stockProportion({ stock: -2, reorder_level: 3 })).toBe(0);
  });

  it("scales against the reorder point and caps at 100", () => {
    expect(stockProportion({ stock: 2, reorder_level: 4 })).toBe(50);
    expect(stockProportion({ stock: 20, reorder_level: 5 })).toBe(100);
  });

  it("handles a reorder point of zero", () => {
    expect(stockProportion({ stock: 5, reorder_level: 0 })).toBe(100);
    expect(stockProportion({ stock: -1, reorder_level: 0 })).toBe(0);
  });
});

describe("messageId", () => {
  it("returns unique IDs without needing crypto.randomUUID", () => {
    vi.stubGlobal("crypto", {});
    const ids = new Set(Array.from({ length: 50 }, () => messageId()));
    expect(ids.size).toBe(50);
  });
});

describe("requestJson", () => {
  afterEach(() => vi.unstubAllGlobals());

  const stubFetch = (implementation) => vi.stubGlobal("fetch", vi.fn(implementation));

  it("returns the payload of a successful response", async () => {
    stubFetch(async () => new Response(JSON.stringify({ ok: true }), { status: 200 }));
    await expect(requestJson("/api/health")).resolves.toEqual({ ok: true });
  });

  it("explains when the service cannot be reached", async () => {
    stubFetch(async () => { throw new TypeError("Failed to fetch"); });
    await expect(requestJson("/api/health")).rejects.toThrow(
      "Cannot reach the inventory service. Make sure `py server.py` is running.",
    );
  });

  it("explains a non-JSON reply instead of a JSON parse error", async () => {
    stubFetch(async () => new Response("", { status: 500 }));
    await expect(requestJson("/api/products")).rejects.toThrow(
      "The inventory service is unavailable (500). Make sure `py server.py` is running.",
    );
  });

  it("uses the server's error message for JSON errors", async () => {
    stubFetch(async () => new Response(JSON.stringify({ error: "Message is too long." }), { status: 413 }));
    await expect(requestJson("/api/chat")).rejects.toThrow("Message is too long.");
  });

  it("falls back to the status code when the error has no message", async () => {
    stubFetch(async () => new Response(JSON.stringify({}), { status: 404 }));
    await expect(requestJson("/api/missing")).rejects.toThrow("Request failed (404).");
  });
});

import { formatRs, niceScale, productsToCsv } from "./inventory.js";

describe("dashboard helpers", () => {
  it("rounds chart axes to tidy steps", () => {
    expect(niceScale(20)).toEqual({ max: 20, ticks: [0, 5, 10, 15, 20] });
    expect(niceScale(1500)).toEqual({ max: 1500, ticks: [0, 500, 1000, 1500] });
    expect(niceScale(0).max).toBeGreaterThan(0);
  });

  it("formats rupees with thousands separators", () => {
    expect(formatRs(2300)).toBe("Rs 2,300");
  });

  it("exports products as CSV and quotes awkward names", () => {
    const csv = productsToCsv([{ name: 'Oil, "Gold"', stock: 2, unit: "bottles", reorder_level: 4, status: "low_stock" }]);
    expect(csv).toBe('Product,Stock,Unit,Reorder level,Status\n"Oil, ""Gold""",2,bottles,4,low_stock');
  });
});
