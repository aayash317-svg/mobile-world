// Mobile World Sales & Service - Customer Storefront Logic

let productsState = [];
let cartState = JSON.parse(localStorage.getItem("mw_cart") || "[]");
const FLAT_DELIVERY_FEE = 50.00;

document.addEventListener("DOMContentLoaded", () => {
  initCatalogue();
  initCart();
  initSearchAndFilters();
  initCheckout();
});

// --- Catalogue Loading & Rendering ---
async function initCatalogue() {
  const grid = document.getElementById("productsGrid");
  try {
    grid.innerHTML = `
      <div style="grid-column: 1/-1; text-align: center; padding: 40px; color: #64748b;">
        <p>Loading Mobile World inventory...</p>
      </div>`;
    
    const res = await fetch("/api/products");
    if (!res.ok) throw new Error("Could not load products");
    productsState = await res.json();
    renderProducts(productsState);
  } catch (err) {
    grid.innerHTML = `
      <div style="grid-column: 1/-1; text-align: center; padding: 40px; color: #ef4444;">
        <p>Failed to load products. Please ensure the backend is running.</p>
      </div>`;
  }
}

function renderProducts(items) {
  const grid = document.getElementById("productsGrid");
  if (!items || items.length === 0) {
    grid.innerHTML = `
      <div style="grid-column: 1/-1; text-align: center; padding: 60px 20px; color: #64748b;">
        <h3>No matching products found</h3>
        <p>Try searching for a different keyword or category.</p>
      </div>`;
    return;
  }

  grid.innerHTML = items.map(p => {
    let stockBadge = "";
    if (p.is_out_of_stock) {
      stockBadge = `<span class="stock-pill stock-out">Out of Stock</span>`;
    } else if (p.is_low_stock) {
      stockBadge = `<span class="stock-pill stock-low">Only ${p.stock} Left</span>`;
    } else {
      stockBadge = `<span class="stock-pill stock-in">In Stock (${p.stock})</span>`;
    }

    const disabledAttr = p.is_out_of_stock ? "disabled" : "";

    return `
      <div class="product-card" data-id="${p.id}">
        <div class="card-img-wrap">
          <img src="${p.image_url || '/static/images/products/charger.svg'}" alt="${p.name}" class="card-img" loading="lazy" />
          ${stockBadge}
        </div>
        <div class="card-content">
          <div class="card-meta">
            <span class="card-brand">${p.brand}</span>
            <span class="card-category">${p.category}</span>
          </div>
          <h3 class="card-title">${p.name}</h3>
          <p class="card-desc">${p.description || 'Authentic product verified by Mobile World.'}</p>
          <div class="card-footer">
            <div class="price-box">
              <span class="price-label">Price</span>
              <span class="price-val">₹${p.price.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
            </div>
            <button class="add-btn" onclick="addToCart(${p.id})" ${disabledAttr}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 5v14M5 12h14"/></svg>
              ${p.is_out_of_stock ? 'Sold Out' : 'Add'}
            </button>
          </div>
        </div>
      </div>
    `;
  }).join("");
}

// --- Filtering & Search ---
function initSearchAndFilters() {
  const tabs = document.querySelectorAll(".tab-btn");
  const searchInput = document.getElementById("searchInput");

  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      tabs.forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      applyFilters();
    });
  });

  if (searchInput) {
    searchInput.addEventListener("input", () => {
      applyFilters();
    });
  }
}

function applyFilters() {
  const activeTab = document.querySelector(".tab-btn.active");
  const category = activeTab ? activeTab.getAttribute("data-category") : "all";
  const search = document.getElementById("searchInput").value.trim().toLowerCase();

  let filtered = productsState.filter(p => {
    const matchesCat = (category === "all") || (p.category.toLowerCase() === category.toLowerCase());
    const matchesSearch = !search || 
      p.name.toLowerCase().includes(search) || 
      p.brand.toLowerCase().includes(search) ||
      (p.description && p.description.toLowerCase().includes(search));
    return matchesCat && matchesSearch;
  });

  renderProducts(filtered);
}

// --- Cart System ---
function initCart() {
  updateCartBadge();
  renderCartDrawer();

  const cartToggle = document.getElementById("cartToggle");
  const closeCart = document.getElementById("closeCart");
  const cartBackdrop = document.getElementById("cartBackdrop");

  if (cartToggle) cartToggle.addEventListener("click", openCart);
  if (closeCart) closeCart.addEventListener("click", closeCartDrawer);
  if (cartBackdrop) {
    cartBackdrop.addEventListener("click", (e) => {
      if (e.target === cartBackdrop) closeCartDrawer();
    });
  }
}

function openCart() {
  document.getElementById("cartBackdrop").classList.add("active");
  renderCartDrawer();
}

function closeCartDrawer() {
  document.getElementById("cartBackdrop").classList.remove("active");
}

function addToCart(productId) {
  const prod = productsState.find(p => p.id === productId);
  if (!prod) return;

  const existing = cartState.find(item => item.id === productId);
  if (existing) {
    if (existing.quantity >= prod.stock) {
      alert(`Cannot add more. Only ${prod.stock} units available in stock.`);
      return;
    }
    existing.quantity += 1;
  } else {
    cartState.push({
      id: prod.id,
      name: prod.name,
      price: prod.price,
      image_url: prod.image_url,
      quantity: 1,
      stock: prod.stock
    });
  }

  saveCart();
  updateCartBadge();
  openCart();
}

function updateQuantity(productId, delta) {
  const item = cartState.find(i => i.id === productId);
  if (!item) return;

  const prod = productsState.find(p => p.id === productId);
  const maxStock = prod ? prod.stock : item.stock;

  const newQty = item.quantity + delta;
  if (newQty <= 0) {
    removeFromCart(productId);
    return;
  }

  if (newQty > maxStock) {
    alert(`Only ${maxStock} units currently available.`);
    return;
  }

  item.quantity = newQty;
  saveCart();
  renderCartDrawer();
  updateCartBadge();
}

function removeFromCart(productId) {
  cartState = cartState.filter(i => i.id !== productId);
  saveCart();
  renderCartDrawer();
  updateCartBadge();
}

function saveCart() {
  localStorage.setItem("mw_cart", JSON.stringify(cartState));
}

function updateCartBadge() {
  const badge = document.getElementById("cartBadge");
  const count = cartState.reduce((sum, item) => sum + item.quantity, 0);
  if (badge) badge.textContent = count;
}

function renderCartDrawer() {
  const body = document.getElementById("cartBody");
  const subtotalElem = document.getElementById("cartSubtotal");
  const feeElem = document.getElementById("cartFee");
  const totalElem = document.getElementById("cartTotal");
  const checkoutBtn = document.getElementById("proceedCheckoutBtn");

  if (!cartState || cartState.length === 0) {
    body.innerHTML = `
      <div class="cart-empty">
        <div class="cart-empty-icon">🛒</div>
        <h3>Your shopping cart is empty</h3>
        <p>Explore our genuine mobile devices and accessories to add items.</p>
      </div>`;
    subtotalElem.textContent = "₹0.00";
    feeElem.textContent = "₹0.00";
    totalElem.textContent = "₹0.00";
    if (checkoutBtn) checkoutBtn.disabled = true;
    return;
  }

  body.innerHTML = cartState.map(item => `
    <div class="cart-item">
      <img src="${item.image_url || '/static/images/products/charger.svg'}" alt="${item.name}" class="cart-item-img" />
      <div class="cart-item-info">
        <div class="cart-item-title">${item.name}</div>
        <div class="cart-item-price">₹${item.price.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</div>
      </div>
      <div class="qty-control">
        <button class="qty-btn" onclick="updateQuantity(${item.id}, -1)">−</button>
        <span class="qty-num">${item.quantity}</span>
        <button class="qty-btn" onclick="updateQuantity(${item.id}, 1)">+</button>
      </div>
      <button class="item-del-btn" onclick="removeFromCart(${item.id})" title="Remove item">✕</button>
    </div>
  `).join("");

  const subtotal = cartState.reduce((sum, i) => sum + (i.price * i.quantity), 0);
  const total = subtotal + FLAT_DELIVERY_FEE;

  subtotalElem.textContent = `₹${subtotal.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
  feeElem.textContent = `₹${FLAT_DELIVERY_FEE.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
  totalElem.textContent = `₹${total.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
  if (checkoutBtn) checkoutBtn.disabled = false;
}

// --- Checkout Modal & COD Flow ---
function initCheckout() {
  const proceedBtn = document.getElementById("proceedCheckoutBtn");
  const modal = document.getElementById("checkoutModal");
  const closeModal = document.getElementById("closeCheckoutModal");
  const checkoutForm = document.getElementById("checkoutForm");

  if (proceedBtn) {
    proceedBtn.addEventListener("click", () => {
      closeCartDrawer();
      openCheckoutModal();
    });
  }

  if (closeModal) {
    closeModal.addEventListener("click", () => {
      modal.classList.remove("active");
    });
  }

  if (checkoutForm) {
    checkoutForm.addEventListener("submit", handleOrderSubmit);
  }
}

function openCheckoutModal() {
  const modal = document.getElementById("checkoutModal");
  const subtotal = cartState.reduce((sum, i) => sum + (i.price * i.quantity), 0);
  const total = subtotal + FLAT_DELIVERY_FEE;

  document.getElementById("modalSubtotal").textContent = `₹${subtotal.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
  document.getElementById("modalTotal").textContent = `₹${total.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;

  modal.classList.add("active");
}

async function handleOrderSubmit(e) {
  e.preventDefault();

  const submitBtn = document.getElementById("submitOrderBtn");
  submitBtn.disabled = true;
  submitBtn.textContent = "Securing COD Order...";

  const name = document.getElementById("custName").value.trim();
  const phone = document.getElementById("custPhone").value.trim();
  const email = document.getElementById("custEmail").value.trim();
  const address = document.getElementById("custAddress").value.trim();
  const notes = document.getElementById("custNotes").value.trim();

  // Generate unique idempotency key
  const idempotencyKey = "MW_IDEMP_" + Date.now() + "_" + Math.random().toString(36).substring(2, 9);

  const payload = {
    customer_name: name,
    customer_phone: phone,
    customer_email: email,
    delivery_address: address,
    order_notes: notes,
    idempotency_key: idempotencyKey,
    items: cartState.map(i => ({
      product_id: i.id,
      quantity: i.quantity
    }))
  };

  try {
    const res = await fetch("/api/orders", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.error || "Failed to place order.");
    }

    // Success: clear cart and show confirmation
    cartState = [];
    saveCart();
    updateCartBadge();
    showOrderConfirmation(data.order);

  } catch (err) {
    alert("Order Error: " + err.message);
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Confirm Cash on Delivery Order";
  }
}

function showOrderConfirmation(order) {
  const modalBody = document.querySelector("#checkoutModal .modal-box");
  modalBody.innerHTML = `
    <div class="success-card">
      <div class="success-icon">✓</div>
      <h2>Order Placed Successfully!</h2>
      <p style="color: #64748b; margin-top: 6px;">Your Cash on Delivery order has been registered with Mobile World.</p>
      
      <div class="ref-pill">${order.order_reference}</div>

      <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 18px; text-align: left; margin-bottom: 24px; font-size: 0.9rem;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
          <span style="color: #64748b;">Customer:</span>
          <strong>${order.customer_name}</strong>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
          <span style="color: #64748b;">Phone:</span>
          <strong>${order.customer_phone}</strong>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
          <span style="color: #64748b;">Total to Pay:</span>
          <strong style="color: #0066ff; font-size: 1.1rem;">${order.total_amount_formatted}</strong>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
          <span style="color: #64748b;">Payment Method:</span>
          <span style="color: #059669; font-weight: 700;">Cash on Delivery (Pending)</span>
        </div>
        <div style="margin-top: 10px; padding-top: 8px; border-top: 1px dashed #cbd5e1; font-size: 0.82rem; color: #64748b;">
          <strong>Delivery to:</strong> ${order.delivery_address}
        </div>
      </div>

      <div style="background: #ecfdf5; border: 1px solid #a7f3d0; border-radius: 8px; padding: 12px; font-size: 0.85rem; color: #065f46; margin-bottom: 24px;">
        💵 <strong>Payment Notice:</strong> Please keep cash ready at delivery. Our representative will collect ₹${order.total_amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })} upon handover.
      </div>

      <button class="btn-primary" style="width: 100%; justify-content: center;" onclick="window.location.reload()">
        Continue Shopping
      </button>
    </div>
  `;
}
