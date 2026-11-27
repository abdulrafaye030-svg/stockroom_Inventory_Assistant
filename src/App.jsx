import React, { useEffect, useMemo, useRef, useState } from "react";
import Icon from "./Icon.jsx";
import LoginPage from "./LoginPage.jsx";
import { BalanceBars, StatusSplit, StockBars, TickGauge } from "./charts.jsx";
import {
  filterProducts, formatNumber, formatRs, messageId, productsToCsv, requestJson, stockProportion, summarizeInventory,
} from "./inventory.js";

const views = [
  { id: "dashboard", label: "Dashboard", icon: "grid" },
  { id: "products", label: "Products", icon: "box" },
  { id: "customers", label: "Customers", icon: "users" },
  { id: "assistant", label: "Assistant", icon: "chat" },
];

const titles = { dashboard: "Dashboard", products: "Products", customers: "Customers", assistant: "Assistant" };

const promptOptions = [
  { title: "What's in stock?", message: "available products" },
  { title: "What should I reorder?", message: "low stock products" },
  { title: "Who owes money?", message: "customer dues" },
];

const filters = [
  { id: "all", label: "All" },
  { id: "in_stock", label: "Has stock" },
  { id: "low_stock", label: "Low" },
  { id: "out_of_stock", label: "Out" },
];

const statusInfo = {
  in_stock: { label: "In stock", icon: "check" },
  low_stock: { label: "Low stock", icon: "alert" },
  out_of_stock: { label: "Out of stock", icon: "xcircle" },
};

const today = new Date().toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });

function viewFromHash() {
  const id = window.location.hash.replace(/^#\/?/, "");
  return views.some((view) => view.id === id) ? id : "dashboard";
}

/* ---------- Small pieces ---------- */

function StatusBadge({ status }) {
  const info = statusInfo[status];
  return (
    <span className={`badge badge-${status}`}>
      <Icon name={info.icon} size={13} />
      {info.label}
    </span>
  );
}

function Card({ title, action, children, className = "" }) {
  return (
    <section className={`card ${className}`}>
      {(title || action) && (
        <div className="card-head">
          <h2>{title}</h2>
          {action}
        </div>
      )}
      {children}
    </section>
  );
}

function KpiTile({ label, value, icon, sub, badges = [] }) {
  return (
    <div className="kpi">
      <div className="kpi-head">
        <span>{label}</span>
        <span className="kpi-icon"><Icon name={icon} size={17} /></span>
      </div>
      <div className="kpi-value">{value}</div>
      <div className="kpi-foot">
        {badges.map((badge) => (
          <span key={badge.label} className={`badge badge-${badge.tone}`}>
            <Icon name={badge.icon} size={13} />{badge.label}
          </span>
        ))}
        <span className="kpi-sub">{sub}</span>
      </div>
    </div>
  );
}

function Sidebar({ view, onNavigate, counts, onFilter }) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <span className="brand-mark"><Icon name="stockroom" size={18} /></span>
        <span>Stockroom</span>
      </div>

      <nav className="nav" aria-label="Main">
        {views.map((item) => (
          <a
            key={item.id}
            href={`#/${item.id}`}
            className={`nav-item ${view === item.id ? "active" : ""}`}
            aria-current={view === item.id ? "page" : undefined}
            onClick={(event) => { event.preventDefault(); onNavigate(item.id); }}
          >
            <Icon name={item.icon} size={18} />
            <span>{item.label}</span>
            {counts[item.id] != null && <span className="nav-count">{counts[item.id]}</span>}
          </a>
        ))}
      </nav>

      <div className="nav-section">Stock</div>
      <nav className="nav nav-sub" aria-label="Stock shortcuts">
        <button className="nav-item" onClick={() => onFilter("low_stock")}>
          <span className="sub-dot sub-low" />Low stock
        </button>
        <button className="nav-item" onClick={() => onFilter("out_of_stock")}>
          <span className="sub-dot sub-out" />Out of stock
        </button>
      </nav>
    </aside>
  );
}

function MobileNav({ view, onNavigate }) {
  return (
    <nav className="mobile-nav" aria-label="Main">
      {views.map((item) => (
        <a
          key={item.id}
          href={`#/${item.id}`}
          className={view === item.id ? "active" : ""}
          aria-current={view === item.id ? "page" : undefined}
          onClick={(event) => { event.preventDefault(); onNavigate(item.id); }}
        >
          <Icon name={item.icon} size={18} />
          <span>{item.label}</span>
        </a>
      ))}
    </nav>
  );
}

/* ---------- Products table ---------- */

function ProductTable({ products, onAsk }) {
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Product</th>
            <th>Unit</th>
            <th className="num">On hand</th>
            <th className="num">Reorder at</th>
            <th>Status</th>
            <th><span className="sr-only">Ask assistant</span></th>
          </tr>
        </thead>
        <tbody>
          {products.map((product) => (
            <tr key={product.name}>
              <td className="strong">{product.name}</td>
              <td className="muted">{product.unit}</td>
              <td className="num strong">{product.stock}</td>
              <td className="num muted">{product.reorder_level}</td>
              <td><StatusBadge status={product.status} /></td>
              <td className="row-action">
                <button
                  className="icon-button"
                  aria-label={`Ask about ${product.name}`}
                  title={`Ask about ${product.name}`}
                  onClick={() => onAsk(`stock of ${product.name}`)}
                >
                  <Icon name="chat" size={16} />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function FilterBar({ filter, setFilter, search, setSearch, counts }) {
  return (
    <div className="toolbar">
      <div className="segmented" role="tablist" aria-label="Filter products">
        {filters.map((item) => (
          <button
            key={item.id}
            role="tab"
            aria-selected={filter === item.id}
            className={filter === item.id ? "is-active" : ""}
            onClick={() => setFilter(item.id)}
          >
            {item.label}<span className="seg-count">{counts[item.id]}</span>
          </button>
        ))}
      </div>
      <label className="search">
        <Icon name="search" size={16} />
        <input
          aria-label="Search products"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search products"
        />
      </label>
    </div>
  );
}

/* ---------- Assistant ---------- */

function AssistantPanel({ chat, className = "", onExpand }) {
  const { messages, draft, setDraft, waitingFor, sending, sendMessage, messagesEndRef } = chat;
  return (
    <Card
      title="AI Assistant"
      className={`assistant ${className}`}
      action={onExpand && (
        <button className="link-button" onClick={onExpand}>Open <Icon name="arrow" size={14} /></button>
      )}
    >
      <div className="message-list" aria-live="polite">
        {messages.map((message) => (
          <div key={message.id} className={`message message-${message.role}`}>
            {message.role === "assistant" && <span className="bot-mark"><Icon name="stockroom" size={14} /></span>}
            <div className="bubble">{message.text}</div>
          </div>
        ))}
        {sending && <div className="typing"><span /><span /><span /></div>}
        <div ref={messagesEndRef} />
      </div>

      {messages.length === 1 && (
        <div className="suggestions">
          {promptOptions.map((option) => (
            <button key={option.message} onClick={() => sendMessage(option.message, true)}>
              {option.title}
            </button>
          ))}
        </div>
      )}

      {waitingFor && (
        <div className="follow-up-hint">
          {waitingFor === "product" ? "Type the product name to continue." : "Type the customer name to continue."}
        </div>
      )}

      <form className="composer" onSubmit={sendMessage}>
        <input
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          className="assistant-input"
          placeholder={waitingFor === "product" ? "Product name" : waitingFor === "balance" ? "Customer name" : "Ask about stock or balances"}
          aria-label="Message the inventory assistant"
          disabled={sending}
        />
        <button type="submit" disabled={!draft.trim() || sending} aria-label="Send message">
          <Icon name="send" size={17} />
        </button>
      </form>
    </Card>
  );
}

/* ---------- Pages ---------- */

function DashboardPage({ products, customers, overview, owing, totalDue, hasData, onNavigate, onFilter, onAsk, chat }) {
  const units = products.reduce((sum, p) => sum + Math.max(0, p.stock), 0);
  const healthy = overview.total_products - overview.needs_attention;
  const attention = products
    .filter((p) => p.status !== "in_stock")
    .sort((a, b) => stockProportion(a) - stockProportion(b) || a.name.localeCompare(b.name));
  const dash = (value) => (hasData ? value : "—");

  return (
    <>
      <section className="kpi-row" aria-label="Summary">
        <KpiTile label="Products" icon="box" value={dash(overview.total_products)} sub="product lines tracked" />
        <KpiTile label="Units on hand" icon="layers" value={dash(formatNumber(units))} sub="across all products" />
        <KpiTile
          label="Need restock" icon="alert" value={dash(overview.needs_attention)} sub=""
          badges={hasData ? [
            { label: `${overview.low_stock} low`, tone: "low_stock", icon: "alert" },
            { label: `${overview.out_of_stock} out`, tone: "out_of_stock", icon: "xcircle" },
          ] : []}
        />
        <KpiTile label="Outstanding dues" icon="wallet" value={dash(formatRs(totalDue))} sub={`from ${owing.length} customers`} />
      </section>

      <div className="dash-grid">
        <div className="dash-col">
          <Card title="Stock on hand" className="stock-card">
            <div className="stock-body">
              <div className="hero">
                <span className="hero-value">{dash(`${Math.round((healthy / Math.max(1, overview.total_products)) * 100)}%`)}</span>
                <span className="hero-note">of products are above their reorder point</span>
                <div className="legend">
                  <span><i className="legend-bar" />On hand</span>
                  <span><i className="legend-tick" />Reorder point</span>
                </div>
              </div>
              <div className="stock-chart">
                <div className="chart-caption">Lowest stock first</div>
                <StockBars products={products} />
              </div>
            </div>
            <StatusSplit overview={overview} onSelect={onFilter} />
          </Card>

          <Card
            title="Needs restocking"
            action={<button className="link-button" onClick={() => onNavigate("products")}>View all products <Icon name="arrow" size={14} /></button>}
          >
            {attention.length ? (
              <ProductTable products={attention.slice(0, 6)} onAsk={onAsk} />
            ) : (
              <p className="chart-empty">{hasData ? "Every product is above its reorder point." : "Loading…"}</p>
            )}
          </Card>
        </div>

        <div className="dash-col">
          <Card
            title="Customer balances"
            action={<button className="link-button" onClick={() => onNavigate("customers")}>All customers <Icon name="arrow" size={14} /></button>}
          >
            <BalanceBars customers={customers} />
          </Card>

          <Card title="Stock health">
            <TickGauge percent={(healthy / Math.max(1, overview.total_products)) * 100} label="healthy" />
            <p className="gauge-note">{healthy} of {overview.total_products} products above reorder point</p>
            <div className="center">
              <button className="button" onClick={() => onFilter("low_stock")}>Show low stock</button>
            </div>
          </Card>

          <AssistantPanel chat={chat} className="assistant-compact" onExpand={() => onNavigate("assistant")} />
        </div>
      </div>
    </>
  );
}

function ProductsPage({ products, filter, setFilter, search, setSearch, onAsk, loading }) {
  const visible = useMemo(() => filterProducts(products, filter, search), [products, filter, search]);
  const counts = {
    all: products.length,
    in_stock: filterProducts(products, "in_stock", "").length,
    low_stock: filterProducts(products, "low_stock", "").length,
    out_of_stock: filterProducts(products, "out_of_stock", "").length,
  };
  return (
    <Card title={`${visible.length} of ${products.length} products`} className="page-card">
      <FilterBar filter={filter} setFilter={setFilter} search={search} setSearch={setSearch} counts={counts} />
      {visible.length > 0 && <ProductTable products={visible} onAsk={onAsk} />}
      {!loading && visible.length === 0 && (
        <div className="empty">
          <strong>No matching products</strong>
          <span>Try another search or filter.</span>
          <button className="link-button" onClick={() => { setSearch(""); setFilter("all"); }}>Clear filters</button>
        </div>
      )}
      {loading && <p className="chart-empty">Loading products…</p>}
    </Card>
  );
}

function CustomersPage({ customers, owing, totalDue, hasData, onAsk }) {
  const billed = customers.reduce((sum, c) => sum + c.billed, 0);
  const paid = customers.reduce((sum, c) => sum + c.paid, 0);
  const dash = (value) => (hasData ? value : "—");
  return (
    <>
      <section className="kpi-row" aria-label="Customer summary">
        <KpiTile label="Customers" icon="users" value={dash(customers.length)} sub="with invoices" />
        <KpiTile label="Total billed" icon="layers" value={dash(formatRs(billed))} sub="all invoices" />
        <KpiTile label="Collected" icon="check" value={dash(formatRs(paid))} sub={billed ? `${Math.round((paid / billed) * 100)}% of billed` : ""} />
        <KpiTile label="Outstanding" icon="wallet" value={dash(formatRs(totalDue))} sub={`${owing.length} customers owe money`} />
      </section>

      <Card title="Who owes the most">
        <BalanceBars customers={customers} limit={10} />
      </Card>

      <Card title="All customers" className="page-card">
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Customer</th>
                <th className="num">Billed</th>
                <th className="num">Paid</th>
                <th className="num">Owes</th>
                <th>Status</th>
                <th><span className="sr-only">Ask assistant</span></th>
              </tr>
            </thead>
            <tbody>
              {customers.map((c) => (
                <tr key={c.name}>
                  <td className="strong">{c.name}</td>
                  <td className="num">{formatRs(c.billed)}</td>
                  <td className="num muted">{formatRs(c.paid)}</td>
                  <td className="num strong">{formatRs(c.due)}</td>
                  <td>
                    {c.due > 0 ? (
                      <span className="badge badge-low_stock"><Icon name="alert" size={13} />Owes</span>
                    ) : (
                      <span className="badge badge-in_stock"><Icon name="check" size={13} />Paid up</span>
                    )}
                  </td>
                  <td className="row-action">
                    <button
                      className="icon-button"
                      aria-label={`Ask about ${c.name}'s balance`}
                      title={`Ask about ${c.name}'s balance`}
                      onClick={() => onAsk(`balance of ${c.name}`)}
                    >
                      <Icon name="chat" size={16} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </>
  );
}

/* ---------- App ---------- */

function Stockroom({ user, onSignOut, onSessionExpired }) {
  const [view, setView] = useState(viewFromHash);
  const [products, setProducts] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [source, setSource] = useState("");
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [messages, setMessages] = useState([
    {
      id: "welcome",
      role: "assistant",
      text: "Hi! Ask me about stock levels, what to reorder, or a customer's balance — for example “stock of Sugar” or “how much does Ali owe?”",
    },
  ]);
  const [draft, setDraft] = useState("");
  const [waitingFor, setWaitingFor] = useState(null);
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef(null);
  const overview = useMemo(() => summarizeInventory(products), [products]);
  const owing = customers.filter((c) => c.due > 0);
  const totalDue = owing.reduce((sum, c) => sum + c.due, 0);
  const hasData = Boolean(source);

  useEffect(() => {
    const onHashChange = () => setView(viewFromHash());
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  async function refreshData() {
    setRefreshing(true);
    setError("");
    try {
      const [productData, customerData, health] = await Promise.all([
        requestJson("/api/products"),
        requestJson("/api/customers"),
        requestJson("/api/health"),
      ]);
      setProducts(productData.products);
      setCustomers(customerData.customers);
      setSource(health.source);
    } catch (requestError) {
      if (requestError.status === 401) return onSessionExpired();
      setError(requestError.message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    refreshData();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [messages, sending]);

  function navigate(next) {
    if (next !== view) window.location.hash = `/${next}`;
    setView(next);
    window.scrollTo({ top: 0 });
  }

  function showProducts(nextFilter) {
    setFilter(nextFilter);
    setSearch("");
    navigate("products");
  }

  async function sendMessage(eventOrText, resetFollowUp = false) {
    if (eventOrText?.preventDefault) eventOrText.preventDefault();
    const text = typeof eventOrText === "string" ? eventOrText : draft;
    const message = text.trim();
    if (!message || sending) return;

    const followUp = resetFollowUp ? null : waitingFor;
    setDraft("");
    setSending(true);
    setError("");
    setMessages((current) => [...current, { id: messageId(), role: "user", text: message }]);
    try {
      const response = await requestJson("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, waitingFor: followUp }),
      });
      setMessages((current) => [...current, { id: messageId(), role: "assistant", text: response.answer }]);
      setWaitingFor(response.waitingFor);
    } catch (requestError) {
      if (requestError.status === 401) return onSessionExpired();
      setMessages((current) => [
        ...current,
        { id: messageId(), role: "assistant", text: `I couldn’t complete that request. ${requestError.message}` },
      ]);
      setWaitingFor(null);
    } finally {
      setSending(false);
    }
  }

  // Questions from tables and buttons open the Assistant page, except on the dashboard where the chat is visible.
  function askAssistant(question) {
    if (view !== "dashboard") navigate("assistant");
    if (typeof question === "string" && question.trim()) sendMessage(question, true);
    setTimeout(() => document.querySelector(".assistant-input")?.focus({ preventScroll: view !== "dashboard" }), 50);
  }

  function exportCsv() {
    const blob = new Blob([productsToCsv(products)], { type: "text/csv;charset=utf-8" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `stockroom-products-${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    URL.revokeObjectURL(link.href);
  }

  const chat = { messages, draft, setDraft, waitingFor, sending, sendMessage, messagesEndRef };
  const navCounts = { products: hasData ? products.length : null, customers: hasData ? owing.length : null };

  return (
    <div className="app-shell">
      <Sidebar
        view={view}
        onNavigate={navigate}
        counts={navCounts}
        onFilter={showProducts}
      />
      <main className="main">
        <header className="page-header">
          <h1>{titles[view]}</h1>
          <div className="header-actions">
            <span className="date-chip"><Icon name="calendar" size={16} />{today}</span>
            <button className="button" onClick={refreshData} disabled={refreshing} aria-label="Refresh data">
              <Icon name="refresh" size={16} className={refreshing ? "spin" : ""} />
              <span className="hide-sm">Refresh</span>
            </button>
            {(view === "dashboard" || view === "products") && (
              <button className="button button-primary" onClick={exportCsv} disabled={!products.length}>
                <Icon name="download" size={16} />Export
              </button>
            )}
            <button className="button" onClick={onSignOut} aria-label={`Sign out ${user}`} title={`Signed in as ${user}`}>
              <Icon name="logout" size={16} />
              <span className="hide-sm">Sign out</span>
            </button>
          </div>
        </header>

        {error && (
          <div className="error-banner" role="alert">
            <Icon name="alert" size={18} />
            <span>{error}</span>
            <button className="link-button" onClick={refreshData}>Try again</button>
          </div>
        )}

        {view === "dashboard" && (
          <DashboardPage
            products={products}
            customers={customers}
            overview={overview}
            owing={owing}
            totalDue={totalDue}
            hasData={hasData}
            onNavigate={navigate}
            onFilter={showProducts}
            onAsk={askAssistant}
            chat={chat}
          />
        )}
        {view === "products" && (
          <ProductsPage
            products={products}
            filter={filter}
            setFilter={setFilter}
            search={search}
            setSearch={setSearch}
            onAsk={askAssistant}
            loading={loading}
          />
        )}
        {view === "customers" && (
          <CustomersPage customers={customers} owing={owing} totalDue={totalDue} hasData={hasData} onAsk={askAssistant} />
        )}
        {view === "assistant" && <AssistantPanel chat={chat} className="assistant-full" />}
      </main>
      <MobileNav view={view} onNavigate={navigate} />
    </div>
  );
}

/* ---------- Sign-in gate ---------- */

export default function App() {
  // undefined = still checking the session cookie, null = signed out, string = signed-in username.
  const [user, setUser] = useState(undefined);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    requestJson("/api/session")
      .then((session) => setUser(session.authenticated ? session.user : null))
      .catch(() => setUser(null));
  }, []);

  async function signOut() {
    try {
      await requestJson("/api/logout", { method: "POST" });
    } catch {
      // The cookie expires on its own; show the sign-in form either way.
    }
    setNotice("");
    setUser(null);
  }

  function sessionExpired() {
    setNotice("Your session has ended. Please sign in again.");
    setUser(null);
  }

  if (user === undefined) {
    return <div className="login-page"><p className="chart-empty">Loading…</p></div>;
  }
  if (!user) {
    return <LoginPage notice={notice} onSignedIn={(name) => { setNotice(""); setUser(name); }} />;
  }
  return <Stockroom user={user} onSignOut={signOut} onSessionExpired={sessionExpired} />;
}
