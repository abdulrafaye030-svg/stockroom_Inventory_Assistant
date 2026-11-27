// Plain inventory and API helpers used by App.jsx. Kept free of React so they can be unit tested.

let nextMessageId = 0;

// Counter-based IDs work everywhere; crypto.randomUUID() is missing on plain-HTTP LAN addresses.
export function messageId() {
  nextMessageId += 1;
  return `message-${nextMessageId}`;
}

export async function requestJson(url, options) {
  let response;
  try {
    response = await fetch(url, options);
  } catch {
    throw new Error("Cannot reach the inventory service. Make sure `py server.py` is running.");
  }
  let payload;
  try {
    payload = await response.json();
  } catch {
    throw new Error(`The inventory service is unavailable (${response.status}). Make sure \`py server.py\` is running.`);
  }
  if (!response.ok) {
    throw new Error(payload.error || `Request failed (${response.status}).`);
  }
  return payload;
}

export function summarizeInventory(products) {
  return products.reduce((summary, product) => {
    summary.total_products += 1;
    if (product.stock > 0) summary.in_stock += 1;
    if (product.status === "low_stock") summary.low_stock += 1;
    if (product.status === "out_of_stock") summary.out_of_stock += 1;
    summary.needs_attention = summary.low_stock + summary.out_of_stock;
    return summary;
  }, { total_products: 0, in_stock: 0, low_stock: 0, out_of_stock: 0, needs_attention: 0 });
}

export function filterProducts(products, filter, search) {
  const term = search.trim().toLocaleLowerCase();
  return products.filter((product) => {
    // "In stock" includes low-stock items, matching the In stock metric card.
    const matchesFilter = filter === "all"
      || (filter === "in_stock" ? product.stock > 0 : product.status === filter);
    return matchesFilter && (!term || product.name.toLocaleLowerCase().includes(term));
  });
}

// Width of the stock bar, from 0 to 100 percent of the reorder point.
export function stockProportion(product) {
  if (product.reorder_level > 0) {
    return Math.min(100, Math.max(0, (product.stock / product.reorder_level) * 100));
  }
  return product.stock > 0 ? 100 : 0;
}
