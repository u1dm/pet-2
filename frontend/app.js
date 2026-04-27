const state = {
  users: [],
  products: [],
  orders: [],
  notifications: [],
  tab: "users",
};

const views = {
  users: ["id", "email", "name", "status", "created_at"],
  products: ["id", "sku", "name", "price", "stock", "created_at"],
  orders: ["id", "user_id", "product_id", "quantity", "total", "status", "created_at"],
  notifications: ["id", "user_id", "channel", "message", "status", "created_at"],
};

const $ = (selector) => document.querySelector(selector);

function money(cents) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format((cents || 0) / 100);
}

function setActivity(message, tone = "normal") {
  const log = $("#activity-log");
  log.textContent = message;
  log.style.borderLeftColor = tone === "error" ? "#be123c" : "#b45309";
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "content-type": "application/json" },
    ...options,
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || "Request failed");
  }
  return payload;
}

function formData(form) {
  return Object.fromEntries(new FormData(form).entries());
}

function renderStatus(health) {
  const status = $("#service-status");
  status.innerHTML = "";
  Object.entries(health.services || {}).forEach(([name, service]) => {
    const pill = document.createElement("span");
    pill.className = "status-pill";
    pill.innerHTML = `<span class="status-dot ${service.status === "ok" ? "" : "down"}"></span>${name}`;
    status.appendChild(pill);
  });
}

function normalizeRows(name, rows) {
  if (name === "products") {
    return rows.map((row) => ({ ...row, price: money(row.price_cents) }));
  }
  if (name === "orders") {
    return rows.map((row) => ({ ...row, total: money(row.total_cents) }));
  }
  return rows;
}

function renderTable() {
  const columns = views[state.tab];
  const rows = normalizeRows(state.tab, state[state.tab]);
  $("#table-head").innerHTML = `<tr>${columns.map((column) => `<th>${column.replace("_", " ")}</th>`).join("")}</tr>`;
  if (rows.length === 0) {
    $("#table-body").innerHTML = `<tr><td class="empty-row" colspan="${columns.length}">No records</td></tr>`;
    return;
  }
  $("#table-body").innerHTML = rows
    .map((row) => `<tr>${columns.map((column) => `<td>${row[column] ?? ""}</td>`).join("")}</tr>`)
    .join("");
}

function renderMetrics() {
  $("#metric-users").textContent = state.users.length;
  $("#metric-products").textContent = state.products.length;
  $("#metric-orders").textContent = state.orders.length;
  $("#metric-notifications").textContent = state.notifications.filter((item) => item.status === "queued").length;
}

async function loadData() {
  const [health, users, products, orders, notifications] = await Promise.all([
    api("/health"),
    api("/users"),
    api("/products"),
    api("/orders"),
    api("/notifications"),
  ]);
  Object.assign(state, { users, products, orders, notifications });
  renderStatus(health);
  renderMetrics();
  renderTable();
}

async function submitJson(form, path, payloadBuilder) {
  try {
    const payload = payloadBuilder(formData(form));
    const created = await api(path, { method: "POST", body: JSON.stringify(payload) });
    setActivity(`${path.slice(1, -1) || path.slice(1)} #${created.id} created`);
    await loadData();
  } catch (error) {
    setActivity(error.message, "error");
  }
}

$("#user-form").addEventListener("submit", (event) => {
  event.preventDefault();
  submitJson(event.currentTarget, "/users", (data) => data);
});

$("#product-form").addEventListener("submit", (event) => {
  event.preventDefault();
  submitJson(event.currentTarget, "/products", (data) => ({
    sku: data.sku,
    name: data.name,
    price: data.price,
    stock: Number(data.stock),
  }));
});

$("#order-form").addEventListener("submit", (event) => {
  event.preventDefault();
  submitJson(event.currentTarget, "/orders", (data) => ({
    user_id: Number(data.user_id),
    product_id: Number(data.product_id),
    quantity: Number(data.quantity),
  }));
});

$("#sync-button").addEventListener("click", async () => {
  try {
    const result = await api("/notifications/sync", { method: "POST", body: "{}" });
    setActivity(`${result.created} notification(s) queued`);
    await loadData();
  } catch (error) {
    setActivity(error.message, "error");
  }
});

$("#refresh-button").addEventListener("click", async () => {
  await loadData();
  setActivity("Data refreshed");
});

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((item) => item.classList.remove("is-active"));
    tab.classList.add("is-active");
    state.tab = tab.dataset.tab;
    renderTable();
  });
});

loadData()
  .then(() => setActivity("Ready"))
  .catch((error) => setActivity(error.message, "error"));
