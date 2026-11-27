import React, { useEffect, useMemo, useRef, useState } from "react";
import Icon from "./Icon.jsx";
import { filterProducts, messageId, requestJson, stockProportion, summarizeInventory } from "./inventory.js";

const promptOptions = [
  { title: "Check stock levels", message: "available products" },
  { title: "Review low stock", message: "low stock products" },
  { title: "Customer balances", message: "customer dues" },
];

const filters = [
  { id: "all", label: "All products" },
  { id: "in_stock", label: "In stock" },
  { id: "low_stock", label: "Low stock" },
  { id: "out_of_stock", label: "Out of stock" },
];

function ProductStatus({ status }) {
  const labels = {
    in_stock: "Healthy",
    low_stock: "Low stock",
    out_of_stock: "Out of stock",
  };
  return <span className={`status-pill status-${status}`}>{labels[status]}</span>;
}

function Sidebar({ source, activeSection, onNavigate, onChat }) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <span className="brand-mark"><Icon name="stockroom" size={21} /></span>
        <span className="brand-copy">
          <strong>Stockroom</strong>
          <small>INVENTORY WORKSPACE</small>
        </span>
      </div>

      <button className="new-chat" onClick={onChat}>
        <Icon name="chat" size={17} />
        <span>Ask the assistant</span>
        <span className="shortcut-key">↵</span>
      </button>

      <div className="nav-label">WORKSPACE</div>
      <nav className="navigation" aria-label="Workspace">
        <button
          className={`nav-item ${activeSection === "overview" ? "active" : ""}`}
          onClick={() => onNavigate("overview")}
        >
          <Icon name="grid" />
          <span>Overview</span>
        </button>
        <button
          className={`nav-item ${activeSection === "products" ? "active" : ""}`}
          onClick={() => onNavigate("products")}
        >
          <Icon name="box" />
          <span>Products</span>
        </button>
        <button className="nav-item" onClick={() => onChat("customer dues")}>
          <Icon name="users" />
          <span>Customer balances</span>
        </button>
      </nav>

      <div className="sidebar-bottom">
        <div className="system-card">
          <div className="system-icon"><Icon name="stockroom" size={17} /></div>
          <div className="system-title">Inventory system</div>
          <p>Product tracking, reorder alerts, and customer account insights in one place.</p>
          <div className="source-status">
            <span className="status-dot" />
            <span>{source || "Connecting to inventory..."}</span>
          </div>
        </div>
      </div>
    </aside>
  );
}

function MetricCard({ icon, label, value, note, tone, onClick }) {
  return (
    <button className="metric-card" onClick={onClick}>
      <span className="metric-top">
        <span className={`metric-icon metric-icon-${tone}`}><Icon name={icon} size={18} /></span>
        <Icon name="arrow" size={15} className="metric-arrow" />
      </span>
      <span className="metric-label">{label}</span>
      <span className="metric-value">{value ?? "—"}</span>
      <span className="metric-note">{note}</span>
    </button>
  );
}

function InventoryTable({ products, loading, filter, setFilter, search, setSearch, onAsk, attentionCount }) {
  const visibleProducts = useMemo(
    () => filterProducts(products, filter, search),
    [products, filter, search],
  );

  return (
    <section id="inventory" className="panel inventory-panel" aria-labelledby="inventory-title">
      <div className="panel-heading inventory-heading">
        <div>
          <div className="eyebrow">PRODUCT CATALOG</div>
          <h2 id="inventory-title">Inventory</h2>
          <p>Keep an eye on availability and reorder points.</p>
        </div>
        <span className="record-count">{visibleProducts.length} items</span>
      </div>

      <div className="inventory-toolbar">
        <div className="filter-tabs" role="tablist" aria-label="Filter products">
          {filters.map((item) => (
            <button
              key={item.id}
              role="tab"
              aria-selected={filter === item.id}
              className={`filter-tab ${filter === item.id ? "is-active" : ""}`}
              onClick={() => setFilter(item.id)}
            >
              {item.label}
            </button>
          ))}
        </div>
        <label className="table-search">
          <Icon name="search" size={16} />
          <input
            aria-label="Search products"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search products"
          />
        </label>
      </div>

      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>PRODUCT</th>
              <th>STOCK LEVEL</th>
              <th>REORDER AT</th>
              <th>STATUS</th>
              <th><span className="sr-only">Ask assistant</span></th>
            </tr>
          </thead>
          <tbody>
            {visibleProducts.map((product) => {
              const proportion = stockProportion(product);
              return (
                <tr key={product.name}>
                  <td>
                    <div className="product-cell">
                      <span className={`product-mark product-mark-${product.status}`}>
                        {product.name.trim().charAt(0).toUpperCase()}
                      </span>
                      <span>
                        <strong>{product.name}</strong>
                        <small>{product.unit}</small>
                      </span>
                    </div>
                  </td>
                  <td>
                    <div className="stock-cell">
                      <strong>{product.stock}</strong>
                      <span className="stock-track" aria-label={`${Math.round(proportion)} percent of reorder point`}>
                        <span
                          className={`stock-fill stock-fill-${product.status}`}
                          style={{ width: `${proportion}%` }}
                        />
                      </span>
                    </div>
                  </td>
                  <td className="reorder-cell">{product.reorder_level} {product.unit}</td>
                  <td><ProductStatus status={product.status} /></td>
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
              );
            })}
            {!loading && visibleProducts.length === 0 && (
              <tr>
                <td colSpan="5">
                  <div className="empty-table">
                    <span className="empty-icon"><Icon name="box" size={20} /></span>
                    <strong>No matching products</strong>
                    <span>Try another search or inventory filter.</span>
                    <button onClick={() => { setSearch(""); setFilter("all"); }}>Clear filters</button>
                  </div>
                </td>
              </tr>
            )}
            {loading && (
              <tr><td colSpan="5" className="table-loading">Loading inventory…</td></tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="table-footnote">
        <span className="legend-dot" />
        Stock bars compare quantities with each product’s reorder point.
      </div>
      <div className="inventory-insight">
        <span className="insight-icon"><Icon name="alert" size={16} /></span>
        <span className="insight-copy">
          <strong>{attentionCount ?? "—"} products need a stock check</strong>
          <small>Low or out of stock based on reorder levels.</small>
        </span>
        <button onClick={() => setFilter("low_stock")}>
          Review low stock <Icon name="arrow" size={14} />
        </button>
      </div>
    </section>
  );
}

function AssistantPanel({ messages, draft, setDraft, waitingFor, sending, onSend, onSuggestion, messagesEndRef }) {
  return (
    <section className="panel assistant-panel" aria-labelledby="assistant-title">
      <div className="assistant-heading">
        <span className="assistant-mark"><Icon name="stockroom" size={19} /></span>
        <div>
          <h2 id="assistant-title">Inventory assistant</h2>
          <span className="assistant-online"><span className="status-dot" />Ready to help</span>
        </div>
      </div>

      <div className="message-list" aria-live="polite">
        {messages.map((message) => (
          <div key={message.id} className={`message-row message-${message.role}`}>
            {message.role === "assistant" && (
              <span className="message-avatar"><Icon name="stockroom" size={14} /></span>
            )}
            <div className="message-bubble">{message.text}</div>
          </div>
        ))}
        {sending && <div className="typing-indicator"><span /><span /><span /> Checking your inventory…</div>}
        <div ref={messagesEndRef} />
      </div>

      {messages.length === 1 && (
        <div className="assistant-suggestions">
          <span className="suggestion-label">TRY ASKING</span>
          {promptOptions.map((option) => (
            <button key={option.message} onClick={() => onSuggestion(option.message)}>
              {option.title}<Icon name="chevron" size={14} />
            </button>
          ))}
        </div>
      )}

      {waitingFor && (
        <div className="follow-up-hint">
          {waitingFor === "product" ? "Enter the product name to continue." : "Enter the customer name to continue."}
        </div>
      )}

      <form className="composer" onSubmit={onSend}>
        <input
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          id="assistant-input"
          placeholder={waitingFor === "product" ? "Product name…" : waitingFor === "balance" ? "Customer name…" : "Ask about your inventory…"}
          aria-label="Message the inventory assistant"
          disabled={sending}
        />
        <button type="submit" disabled={!draft.trim() || sending} aria-label="Send message">
          <Icon name="send" size={17} />
        </button>
      </form>
      <div className="assistant-footnote">Inventory answers are based on your connected data.</div>
    </section>
  );
}

export default function App() {
  const [products, setProducts] = useState([]);
  const [source, setSource] = useState("");
  const [filter, setFilter] = useState("all");
  const [activeSection, setActiveSection] = useState("overview");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [messages, setMessages] = useState([
    {
      id: "welcome",
      role: "assistant",
      text: "Hello! I can help you find stock levels, spot items to reorder, and check customer balances.",
    },
  ]);
  const [draft, setDraft] = useState("");
  const [waitingFor, setWaitingFor] = useState(null);
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef(null);
  const assistantRef = useRef(null);
  const overviewRef = useRef(null);
  const overview = useMemo(() => summarizeInventory(products), [products]);
  const hasInventoryData = Boolean(source);

  async function refreshData() {
    setRefreshing(true);
    setError("");
    try {
      const [productData, health] = await Promise.all([
        requestJson("/api/products"),
        requestJson("/api/health"),
      ]);
      setProducts(productData.products);
      setSource(health.source);
    } catch (requestError) {
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

  async function sendMessage(eventOrText, resetFollowUp = false) {
    if (eventOrText?.preventDefault) {
      eventOrText.preventDefault();
    }
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
      setMessages((current) => [
        ...current,
        { id: messageId(), role: "assistant", text: response.answer },
      ]);
      setWaitingFor(response.waitingFor);
    } catch (requestError) {
      setError(requestError.message);
      setMessages((current) => [
        ...current,
        {
          id: messageId(),
          role: "assistant",
          text: `I couldn’t complete that request. ${requestError.message}`,
        },
      ]);
      setWaitingFor(null);
    } finally {
      setSending(false);
    }
  }

  function askAssistant(question) {
    assistantRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
    if (typeof question === "string" && question.trim()) {
      sendMessage(question, true);
    } else {
      document.getElementById("assistant-input")?.focus();
    }
  }

  function navigateTo(section) {
    setActiveSection(section);
    if (section === "products") {
      setFilter("all");
      document.getElementById("inventory")?.scrollIntoView({ behavior: "smooth", block: "start" });
    } else {
      overviewRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  function selectFilter(nextFilter) {
    setFilter(nextFilter);
    setActiveSection("products");
  }

  return (
    <div className="app-shell">
      <Sidebar
        source={source}
        activeSection={activeSection}
        onNavigate={navigateTo}
        onChat={askAssistant}
      />
      <main className="main-area">
        <header className="topbar">
          <div className="breadcrumb">
            <span>Workspace</span>
            <Icon name="chevron" size={14} />
            <strong>{activeSection === "products" ? "Products" : "Overview"}</strong>
          </div>
          <div className="topbar-right">
            <span className="source-chip"><span className="status-dot" />{source || "Connecting"}</span>
            <button className="refresh-button" onClick={refreshData} disabled={refreshing}>
              <Icon name="refresh" size={16} className={refreshing ? "spin" : ""} />
              <span>{refreshing ? "Refreshing" : "Refresh"}</span>
            </button>
          </div>
        </header>

        <div className="page-content">
          <section className="page-intro" ref={overviewRef}>
            <div>
              <div className="eyebrow">YOUR BUSINESS AT A GLANCE</div>
              <h1>Inventory overview</h1>
              <p>Stay ahead of stock changes and keep customer accounts in view.</p>
            </div>
            <button className="primary-action" onClick={() => askAssistant("low stock products")}>
              <Icon name="box" size={16} /> Get stock insights
            </button>
          </section>

          {error && (
            <div className="error-banner" role="alert">
              <Icon name="alert" size={18} />
              <span>{error}</span>
              <button onClick={refreshData}>Try again</button>
            </div>
          )}

          <section className="metrics-grid" aria-label="Inventory summary">
            <MetricCard
              icon="box" label="Total products" value={hasInventoryData ? overview.total_products : null}
              note="Unique products tracked" tone="blue" onClick={() => selectFilter("all")}
            />
            <MetricCard
              icon="check" label="In stock" value={hasInventoryData ? overview.in_stock : null}
              note="Products with stock on hand" tone="green" onClick={() => selectFilter("in_stock")}
            />
            <MetricCard
              icon="alert" label="Low stock" value={hasInventoryData ? overview.low_stock : null}
              note="At or below reorder point" tone="amber" onClick={() => selectFilter("low_stock")}
            />
            <MetricCard
              icon="box" label="Out of stock" value={hasInventoryData ? overview.out_of_stock : null}
              note="Needs replenishment" tone="rose" onClick={() => selectFilter("out_of_stock")}
            />
          </section>

          <div className="dashboard-grid">
            <InventoryTable
              products={products}
              loading={loading}
              filter={filter}
              setFilter={selectFilter}
              search={search}
              setSearch={setSearch}
              onAsk={askAssistant}
              attentionCount={hasInventoryData ? overview.needs_attention : null}
            />
            <div ref={assistantRef}>
              <AssistantPanel
                messages={messages}
                draft={draft}
                setDraft={setDraft}
                waitingFor={waitingFor}
                sending={sending}
                onSend={sendMessage}
                onSuggestion={(question) => sendMessage(question, true)}
                messagesEndRef={messagesEndRef}
              />
            </div>
          </div>
          <footer className="page-footer">
            <span><span className="status-dot" />Data source: {source || "Connecting…"}</span>
            <span>Stockroom · Inventory assistant</span>
          </footer>
        </div>
      </main>
    </div>
  );
}
