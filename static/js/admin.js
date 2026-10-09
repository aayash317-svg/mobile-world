// Mobile World Sales & Service - Admin Dashboard Logic

let currentRange = "7d";
let salesChartInstance = null;
let statusChartInstance = null;
let topProductsChartInstance = null;
let paymentChartInstance = null;

let ordersCache = [];
let productsCache = [];

document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  initLogout();
  loadAnalytics(currentRange);
  loadAdminOrders();
  loadAdminProducts();
  loadActivityLogs();
});

// --- Tab Switching ---
function initTabs() {
  const tabBtns = document.querySelectorAll(".tab-nav-btn");
  tabBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      const tabId = btn.getAttribute("data-tab");
      switchTab(tabId);
    });
  });
}

function switchTab(tabId) {
  document.querySelectorAll(".tab-nav-btn").forEach(b => {
    b.classList.toggle("active", b.getAttribute("data-tab") === tabId);
  });
  document.querySelectorAll(".tab-panel").forEach(p => {
    p.classList.toggle("active", p.id === tabId);
  });

  if (tabId === "tab-orders") loadAdminOrders();
  if (tabId === "tab-products") loadAdminProducts();
  if (tabId === "tab-logs") loadActivityLogs();
}

// --- Logout ---
function initLogout() {
  const btn = document.getElementById("logoutBtn");
  if (btn) {
    btn.addEventListener("click", async () => {
      await fetch("/admin/logout", { method: "POST" });
      window.location.href = "/admin/login";
    });
  }
}

// --- Analytics & Charts ---
async function changeChartRange(range, btn) {
  currentRange = range;
  document.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));
  btn.classList.add("active");
  await loadAnalytics(range);
}

async function loadAnalytics(range = "7d") {
  try {
    const res = await fetch(`/api/admin/analytics/summary?range=${range}`);
    if (!res.ok) throw new Error("Failed to fetch analytics");
    const data = await res.json();

    // Populate KPIs
    document.getElementById("kpiTotalOrders").textContent = data.totalOrders;
    document.getElementById("kpiCollectedSales").textContent = data.collectedSalesFormatted;
    document.getElementById("kpiAwaitingCod").textContent = data.codAwaitingCollectionFormatted;
    document.getElementById("kpiAov").textContent = data.averageOrderValueFormatted;
    document.getElementById("kpiLowStock").textContent = data.lowStockCount;
    document.getElementById("kpiPending").textContent = data.pendingOrders;

    // Low Stock Alert Banner
    const banner = document.getElementById("lowStockBanner");
    const bannerText = document.getElementById("lowStockBannerText");
    if (data.lowStockCount > 0) {
      banner.style.display = "flex";
      bannerText.textContent = `${data.lowStockCount} item(s) are at or below minimum threshold: ${data.lowStockProducts.map(p => p.name).join(", ")}`;
    } else {
      banner.style.display = "none";
    }

    renderCharts(data);
  } catch (err) {
    console.error("Analytics load error:", err);
  }
}

function renderCharts(data) {
  // 1. Sales Trend Line Chart (Collected vs Order Value)
  const ctxSales = document.getElementById("salesTrendChart").getContext("2d");
  if (salesChartInstance) salesChartInstance.destroy();

  const labels = data.dailyTrends.map(d => d.date);
  const collectedVals = data.dailyTrends.map(d => d.collected);
  const orderVals = data.dailyTrends.map(d => d.order_value);

  salesChartInstance = new Chart(ctxSales, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Collected Sales (₹ Cash)",
          data: collectedVals,
          borderColor: "#10b981",
          backgroundColor: "rgba(16, 185, 129, 0.1)",
          borderWidth: 3,
          tension: 0.35,
          fill: true
        },
        {
          label: "Order Value Placed (₹)",
          data: orderVals,
          borderColor: "#0066ff",
          backgroundColor: "rgba(0, 102, 255, 0.05)",
          borderWidth: 2,
          borderDash: [5, 5],
          tension: 0.35,
          fill: false
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "top" }
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            callback: value => "₹" + value.toLocaleString("en-IN")
          }
        }
      }
    }
  });

  // 2. Orders By Status Doughnut Chart
  const ctxStatus = document.getElementById("orderStatusChart").getContext("2d");
  if (statusChartInstance) statusChartInstance.destroy();

  const statusLabels = Object.keys(data.ordersByStatus);
  const statusCounts = Object.values(data.ordersByStatus);

  statusChartInstance = new Chart(ctxStatus, {
    type: "doughnut",
    data: {
      labels: statusLabels,
      datasets: [{
        data: statusCounts,
        backgroundColor: [
          "#f59e0b", // Pending
          "#0284c7", // Confirmed
          "#8b5cf6", // Packed
          "#3b82f6", // Shipped
          "#10b981", // Delivered
          "#ef4444", // Cancelled
          "#64748b"  // Returned
        ]
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "bottom" }
      }
    }
  });

  // 3. Top Products Bar Chart
  const ctxTop = document.getElementById("topProductsChart").getContext("2d");
  if (topProductsChartInstance) topProductsChartInstance.destroy();

  const topNames = data.topProducts.length ? data.topProducts.map(p => p.name) : ["No Sales Yet"];
  const topUnits = data.topProducts.length ? data.topProducts.map(p => p.units_sold) : [0];

  topProductsChartInstance = new Chart(ctxTop, {
    type: "bar",
    data: {
      labels: topNames,
      datasets: [{
        label: "Units Ordered",
        data: topUnits,
        backgroundColor: "#0066ff",
        borderRadius: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: { beginAtZero: true, ticks: { stepSize: 1 } }
      }
    }
  });

  // 4. Payment Collection Summary
  const ctxPayment = document.getElementById("paymentSummaryChart").getContext("2d");
  if (paymentChartInstance) paymentChartInstance.destroy();

  paymentChartInstance = new Chart(ctxPayment, {
    type: "pie",
    data: {
      labels: ["Collected Revenue", "Awaiting COD Collection"],
      datasets: [{
        data: [data.collectedSales, data.codAwaitingCollection],
        backgroundColor: ["#10b981", "#f59e0b"]
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "bottom" }
      }
    }
  });
}

// --- Orders Management ---
async function loadAdminOrders() {
  const tbody = document.getElementById("ordersTableBody");
  const statusFilter = document.getElementById("orderStatusFilter").value;
  const payFilter = document.getElementById("paymentStatusFilter").value;
  const search = document.getElementById("orderSearch").value.trim();

  let url = `/api/admin/orders?status=${statusFilter}&payment_status=${payFilter}`;
  if (search) url += `&search=${encodeURIComponent(search)}`;

  try {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding: 20px;">Loading orders...</td></tr>`;
    const res = await fetch(url);
    if (!res.ok) throw new Error("Could not load orders");
    ordersCache = await res.json();

    if (!ordersCache.length) {
      tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding: 40px; color: #64748b;">No orders found matching filters.</td></tr>`;
      return;
    }

    tbody.innerHTML = ordersCache.map(o => {
      const statusClass = `badge-${o.order_status.toLowerCase()}`;
      const payClass = o.payment_status === "Collected" ? "badge-paid" : "badge-unpaid";

      let collectAction = "";
      if (o.payment_status === "Pending COD" && o.order_status !== "Cancelled" && o.order_status !== "Returned") {
        collectAction = `
          <button class="action-btn collect" onclick="recordCashPayment(${o.id}, '${o.order_reference}', ${o.total_amount})" title="Record physical cash received">
            💵 Collect Cash
          </button>
        `;
      }

      return `
        <tr>
          <td><strong style="color: #0066ff;">${o.order_reference}</strong></td>
          <td>${o.created_at || 'Just now'}</td>
          <td>
            <strong>${o.customer_name}</strong><br>
            <span style="font-size: 0.8rem; color: #64748b;">📞 ${o.customer_phone}</span>
          </td>
          <td>${o.item_count} items</td>
          <td><strong>${o.total_amount_formatted}</strong></td>
          <td><span class="badge ${payClass}">${o.payment_status}</span></td>
          <td><span class="badge ${statusClass}">${o.order_status}</span></td>
          <td style="white-space: nowrap;">
            <button class="action-btn" onclick="openOrderModal(${o.id})">Details</button>
            ${collectAction}
          </td>
        </tr>
      `;
    }).join("");

  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding: 20px; color: #ef4444;">${err.message}</td></tr>`;
  }
}

// Order Search & Filter listeners
document.getElementById("orderSearch").addEventListener("input", debounce(loadAdminOrders, 300));
document.getElementById("orderStatusFilter").addEventListener("change", loadAdminOrders);
document.getElementById("paymentStatusFilter").addEventListener("change", loadAdminOrders);

function openOrderModal(orderId) {
  const order = ordersCache.find(o => o.id === orderId);
  if (!order) return;

  const modal = document.getElementById("orderModal");
  document.getElementById("modalOrderRef").textContent = `Order ${order.order_reference}`;

  const itemsHtml = order.items.map(it => `
    <div style="display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #f1f5f9; font-size: 0.9rem;">
      <div>
        <strong>${it.product_name}</strong> × ${it.quantity}
      </div>
      <div>${it.line_total_formatted}</div>
    </div>
  `).join("");

  const historyHtml = order.history && order.history.length ? order.history.map(h => `
    <div style="font-size: 0.8rem; color: #64748b; margin-bottom: 4px;">
      • <strong>${h.new_status}</strong> by ${h.changed_by} (${h.created_at}): <em>${h.notes || ''}</em>
    </div>
  `).join("") : `<div style="font-size: 0.8rem; color: #94a3b8;">No status history recorded yet.</div>`;

  document.getElementById("modalOrderContent").innerHTML = `
    <div style="margin-bottom: 16px;">
      <h4 style="font-size: 0.95rem; margin-bottom: 6px;">Customer & Delivery Details:</h4>
      <p style="font-size: 0.88rem; color: #334155;">
        <strong>${order.customer_name}</strong> (Phone: ${order.customer_phone})<br>
        Address: ${order.delivery_address}<br>
        ${order.order_notes ? `Notes: <em>${order.order_notes}</em>` : ''}
      </p>
    </div>

    <div style="margin-bottom: 16px;">
      <h4 style="font-size: 0.95rem; margin-bottom: 6px;">Ordered Items:</h4>
      ${itemsHtml}
      <div style="display: flex; justify-content: space-between; margin-top: 8px; font-weight: 800; font-size: 1rem;">
        <span>Total Payable:</span>
        <span style="color: #0066ff;">${order.total_amount_formatted}</span>
      </div>
    </div>

    <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; margin-bottom: 18px;">
      <label class="form-label">Transition Order Status:</label>
      <div style="display: flex; gap: 8px; margin-top: 6px;">
        <select id="modalStatusSelect" class="form-control" style="flex: 1;">
          <option value="Pending" ${order.order_status === 'Pending' ? 'selected' : ''}>Pending</option>
          <option value="Confirmed" ${order.order_status === 'Confirmed' ? 'selected' : ''}>Confirmed</option>
          <option value="Packed" ${order.order_status === 'Packed' ? 'selected' : ''}>Packed</option>
          <option value="Shipped" ${order.order_status === 'Shipped' ? 'selected' : ''}>Shipped</option>
          <option value="Delivered" ${order.order_status === 'Delivered' ? 'selected' : ''}>Delivered</option>
          <option value="Cancelled" ${order.order_status === 'Cancelled' ? 'selected' : ''}>Cancelled (Restores Stock)</option>
          <option value="Returned" ${order.order_status === 'Returned' ? 'selected' : ''}>Returned (Restores Stock)</option>
        </select>
        <button class="action-btn collect" onclick="applyStatusChange(${order.id})">Update Status</button>
      </div>
    </div>

    <div>
      <h4 style="font-size: 0.88rem; margin-bottom: 6px;">Audit Status History:</h4>
      ${historyHtml}
    </div>
  `;

  modal.style.display = "flex";
}

function closeOrderModal() {
  document.getElementById("orderModal").style.display = "none";
}

async function applyStatusChange(orderId) {
  const newStatus = document.getElementById("modalStatusSelect").value;
  try {
    const res = await fetch(`/api/admin/orders/${orderId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ order_status: newStatus })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Failed to update status");

    alert(`Order status updated to ${newStatus}`);
    closeOrderModal();
    loadAdminOrders();
    loadAnalytics(currentRange);
    loadAdminProducts(); // In case stock restored on cancellation
  } catch (err) {
    alert("Error: " + err.message);
  }
}

async function recordCashPayment(orderId, orderRef, amount) {
  const confirmCollect = confirm(`Confirm cash collection of ₹${amount.toLocaleString('en-IN')} for order ${orderRef}?\n\nThis will record the payment in real revenue and update order status to Delivered.`);
  if (!confirmCollect) return;

  try {
    const res = await fetch(`/api/admin/orders/${orderId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ record_payment: true, payment_notes: "Collected cash at physical handover" })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Failed to record payment");

    alert(`Payment recorded successfully! Order ${orderRef} marked as Delivered with Collected revenue.`);
    loadAdminOrders();
    loadAnalytics(currentRange);
  } catch (err) {
    alert("Error: " + err.message);
  }
}

// --- Products & Inventory Management ---
async function loadAdminProducts() {
  const tbody = document.getElementById("productsTableBody");
  const catFilter = document.getElementById("productCatFilter").value;
  const search = document.getElementById("productSearch").value.trim().toLowerCase();

  try {
    tbody.innerHTML = `<tr><td colspan="9" style="text-align:center; padding: 20px;">Loading inventory...</td></tr>`;
    const res = await fetch("/api/products");
    if (!res.ok) throw new Error("Could not load products");
    productsCache = await res.json();

    let filtered = productsCache.filter(p => {
      const matchCat = (catFilter === "all") || (p.category === catFilter);
      const matchSearch = !search || p.name.toLowerCase().includes(search) || p.sku.toLowerCase().includes(search) || p.brand.toLowerCase().includes(search);
      return matchCat && matchSearch;
    });

    if (!filtered.length) {
      tbody.innerHTML = `<tr><td colspan="9" style="text-align:center; padding: 40px; color: #64748b;">No products found matching filters.</td></tr>`;
      return;
    }

    tbody.innerHTML = filtered.map(p => {
      let invBadge = `<span class="badge badge-delivered">In Stock</span>`;
      if (p.is_out_of_stock) {
        invBadge = `<span class="badge badge-cancelled">Out of Stock</span>`;
      } else if (p.is_low_stock) {
        invBadge = `<span class="badge badge-pending">Low Stock Alert</span>`;
      }

      return `
        <tr>
          <td>
            <div style="display: flex; align-items: center; gap: 10px;">
              <img src="${p.image_url || '/static/images/products/charger.svg'}" alt="${p.name}" style="width: 36px; height: 36px; border-radius: 6px; object-fit: cover;" />
              <div>
                <strong>${p.name}</strong><br>
                <span style="font-size: 0.78rem; color: #64748b;">${p.brand}</span>
              </div>
            </div>
          </td>
          <td><code>${p.sku}</code></td>
          <td>${p.category}</td>
          <td><strong>${p.price_formatted}</strong></td>
          <td><strong style="font-size: 1.05rem; ${p.is_low_stock ? 'color: #d97706;' : ''}">${p.stock}</strong></td>
          <td>${p.low_stock_threshold}</td>
          <td>${invBadge}</td>
          <td>${p.is_active ? '✓ Yes' : '✕ No'}</td>
          <td>
            <div style="display: flex; gap: 6px;">
              <button class="action-btn" onclick="openStockModal(${p.id})">Adjust Stock</button>
              <button class="action-btn" onclick="promptEditPrice(${p.id}, ${p.price})" style="background: #e0f2fe; color: #0369a1; border-color: #bae6fd;">Edit Price</button>
            </div>
          </td>
        </tr>
      `;
    }).join("");

  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="9" style="text-align:center; padding: 20px; color: #ef4444;">${err.message}</td></tr>`;
  }
}

document.getElementById("productSearch").addEventListener("input", debounce(loadAdminProducts, 300));
document.getElementById("productCatFilter").addEventListener("change", loadAdminProducts);

function openStockModal(productId) {
  const prod = productsCache.find(p => p.id === productId);
  if (!prod) return;

  document.getElementById("stockProdId").value = prod.id;
  document.getElementById("stockProdName").textContent = `Product: ${prod.name} (${prod.sku})`;
  document.getElementById("stockQtyInput").value = prod.stock;
  document.getElementById("stockThInput").value = prod.low_stock_threshold;

  document.getElementById("stockModal").style.display = "flex";
}

function closeStockModal() {
  document.getElementById("stockModal").style.display = "none";
}

async function promptEditPrice(productId, currentPrice) {
  const newPriceStr = prompt(`Enter new showroom price for product (Current: ₹${currentPrice}):`, currentPrice);
  if (newPriceStr === null) return;
  const newPrice = parseFloat(newPriceStr);
  if (isNaN(newPrice) || newPrice <= 0) {
    alert("Please enter a valid positive price.");
    return;
  }
  try {
    const res = await fetch(`/api/admin/products/${productId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ price: newPrice })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Failed to update price");
    alert(`Price updated to ₹${newPrice.toFixed(2)}! Any matching customer price drop alerts have been triggered.`);
    loadAdminProducts();
    loadAnalytics(currentRange);
  } catch (err) {
    alert("Error: " + err.message);
  }
}

document.getElementById("stockForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const prodId = document.getElementById("stockProdId").value;
  const newStock = parseInt(document.getElementById("stockQtyInput").value);
  const newThreshold = parseInt(document.getElementById("stockThInput").value);

  try {
    const res = await fetch(`/api/admin/inventory/${prodId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ stock: newStock, low_stock_threshold: newThreshold })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Failed to update inventory");

    closeStockModal();
    loadAdminProducts();
    loadAnalytics(currentRange);
    alert("Stock adjusted successfully!");
  } catch (err) {
    alert("Error: " + err.message);
  }
});

function openAddProductModal() {
  document.getElementById("addProductModal").style.display = "flex";
}

function closeAddProductModal() {
  document.getElementById("addProductModal").style.display = "none";
}

document.getElementById("addProductForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const name = document.getElementById("newProdName").value.trim();
  const brand = document.getElementById("newProdBrand").value.trim();
  const category = document.getElementById("newProdCat").value;
  const price = parseFloat(document.getElementById("newProdPrice").value);
  const sku = document.getElementById("newProdSku").value.trim();
  const stock = parseInt(document.getElementById("newProdStock").value);
  const threshold = parseInt(document.getElementById("newProdThreshold").value);
  const description = document.getElementById("newProdDesc").value.trim();

  try {
    const res = await fetch("/api/admin/products", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name, brand, category, price, sku, stock,
        low_stock_threshold: threshold,
        description,
        image_url: "/static/images/products/charger.svg"
      })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Failed to create product");

    closeAddProductModal();
    document.getElementById("addProductForm").reset();
    loadAdminProducts();
    loadAnalytics(currentRange);
    alert("Product added successfully!");
  } catch (err) {
    alert("Error: " + err.message);
  }
});

// --- Activity Logs ---
async function loadActivityLogs() {
  const tbody = document.getElementById("logsTableBody");
  try {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding: 20px;">Loading audit logs...</td></tr>`;
    const res = await fetch("/api/admin/activity-logs?limit=50");
    if (!res.ok) throw new Error("Could not load activity logs");
    const logs = await res.json();

    if (!logs.length) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding: 40px; color: #64748b;">No activity logs recorded yet.</td></tr>`;
      return;
    }

    tbody.innerHTML = logs.map(l => `
      <tr>
        <td style="white-space: nowrap; font-size: 0.82rem; color: #64748b;">${l.created_at}</td>
        <td><strong>${l.username}</strong></td>
        <td><code>${l.action}</code></td>
        <td>${l.entity_type || '-'} ${l.entity_id ? `(#${l.entity_id})` : ''}</td>
        <td style="font-size: 0.85rem;">${l.details || '-'}</td>
        <td style="font-size: 0.8rem; color: #94a3b8;">${l.ip_address || 'localhost'}</td>
      </tr>
    `).join("");

  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding: 20px; color: #ef4444;">${err.message}</td></tr>`;
  }
}

// Helper Debounce
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}
