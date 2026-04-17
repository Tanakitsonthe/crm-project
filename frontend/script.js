let token = localStorage.getItem("token") || "";
let currentUser = localStorage.getItem("username") || "";
let currentPlan = localStorage.getItem("plan") || "free";
let editCustomerId = null;
let tagChart = null;

function $(id) {
  return document.getElementById(id);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function showAuth() {
  $("auth").classList.remove("hidden");
  $("app").classList.add("hidden");
}

function showApp() {
  $("auth").classList.add("hidden");
  $("app").classList.remove("hidden");
}

function setPlanUI(plan, remaining) {
  const badge = $("planBadge");
  badge.textContent = plan ? plan.toUpperCase() : "FREE";
  badge.classList.remove("plan-free", "plan-pro");
  badge.classList.add(plan === "pro" ? "plan-pro" : "plan-free");

  $("remainingCount").textContent = plan === "pro" ? "∞" : String(remaining ?? 0);
  $("paymentNote").textContent = plan === "pro"
    ? "คุณใช้งาน PRO แล้ว"
    : "สแกน QR แล้วกดยืนยัน";
  $("upgradeBtn").disabled = plan === "pro";
}

async function register() {
  try {
    const res = await fetch("/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: $("username").value.trim(),
        password: $("password").value
      })
    });

    const data = await res.json();
    if (!res.ok) {
      alert(data.error || "สมัครไม่สำเร็จ");
      return;
    }

    alert("สมัครสำเร็จ");
  } catch (error) {
    alert("เชื่อมต่อเซิร์ฟเวอร์ไม่ได้");
  }
}

async function login() {
  try {
    const res = await fetch("/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: $("username").value.trim(),
        password: $("password").value
      })
    });

    const data = await res.json();
    if (!res.ok) {
      alert(data.error || "Login fail");
      return;
    }

    token = data.token;
    currentUser = data.username || "";
    currentPlan = data.plan || "free";

    localStorage.setItem("token", token);
    localStorage.setItem("username", currentUser);
    localStorage.setItem("plan", currentPlan);

    $("userLine").textContent = `${currentUser} • ${currentPlan.toUpperCase()}`;
    showApp();
    await refreshAll();
  } catch (error) {
    alert("เชื่อมต่อเซิร์ฟเวอร์ไม่ได้");
  }
}

function logout() {
  localStorage.removeItem("token");
  localStorage.removeItem("username");
  localStorage.removeItem("plan");
  token = "";
  currentUser = "";
  currentPlan = "free";
  location.reload();
}

async function refreshAll() {
  await Promise.all([loadDashboard(), loadCustomers()]);
}

async function loadDashboard() {
  const res = await fetch("/dashboard", {
    headers: { "Authorization": `Bearer ${token}` }
  });

  if (res.status === 401) {
    logout();
    return;
  }

  const data = await res.json();
  if (!res.ok) {
    alert(data.error || "โหลด dashboard ไม่ได้");
    return;
  }

  $("totalCount").textContent = data.total ?? 0;
  $("vipCount").textContent = data.vip ?? 0;
  $("userLine").textContent = `${currentUser} • ${String(data.plan || "free").toUpperCase()}`;
  setPlanUI(data.plan || "free", data.remaining);

  renderChart(data);
}

async function loadCustomers() {
  const res = await fetch("/customers", {
    headers: { "Authorization": `Bearer ${token}` }
  });

  if (res.status === 401) {
    logout();
    return;
  }

  const data = await res.json();
  if (!res.ok) {
    alert(data.error || "โหลดลูกค้าไม่ได้");
    return;
  }

  const tbody = $("customers");
  tbody.innerHTML = "";

  if (!data.length) {
    tbody.innerHTML = `
      <tr>
        <td colspan="4" class="text-center text-soft py-4">ยังไม่มีลูกค้า</td>
      </tr>
    `;
    renderChart({ total: 0, vip: 0, plan: currentPlan, remaining: 5 });
    return;
  }

  tbody.innerHTML = data.map((customer) => {
    const tagClass = customer.tag === "VIP"
      ? "tag-vip"
      : customer.tag === "Regular"
        ? "tag-regular"
        : "tag-new";

    return `
      <tr data-row="customer">
        <td>${escapeHtml(customer.name)}</td>
        <td>${escapeHtml(customer.phone)}</td>
        <td><span class="badge-tag ${tagClass}">${escapeHtml(customer.tag || "New")}</span></td>
        <td class="d-flex gap-2">
          <button class="btn btn-sm btn-outline-light" onclick='openEdit(${customer.id}, ${JSON.stringify(customer.name)}, ${JSON.stringify(customer.phone)}, ${JSON.stringify(customer.tag || "New")})'>Edit</button>
          <button class="btn btn-sm btn-danger" onclick="deleteCustomer(${customer.id})">Delete</button>
        </td>
      </tr>
    `;
  }).join("");

  applySearchFilter();
  renderChartFromCustomers(data);
}

async function addCustomer() {
  const payload = {
    name: $("name").value.trim(),
    phone: $("phone").value.trim(),
    tag: $("tag").value
  };

  const res = await fetch("/customers", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token}`
    },
    body: JSON.stringify(payload)
  });

  const data = await res.json();

  if (res.status === 403) {
    alert("Free plan เพิ่มได้ 5 ลูกค้าเท่านั้น ต้องอัปเกรด PRO");
    return;
  }

  if (!res.ok) {
    alert(data.error || "เพิ่มไม่สำเร็จ");
    return;
  }

  $("name").value = "";
  $("phone").value = "";
  $("tag").value = "New";

  await refreshAll();
}

async function deleteCustomer(id) {
  if (!confirm("ลบลูกค้าคนนี้ใช่ไหม")) return;

  const res = await fetch(`/customers/${id}`, {
    method: "DELETE",
    headers: { "Authorization": `Bearer ${token}` }
  });

  const data = await res.json();
  if (!res.ok) {
    alert(data.error || "ลบไม่สำเร็จ");
    return;
  }

  await refreshAll();
}

function openEdit(id, name, phone, tag) {
  editCustomerId = id;
  $("editName").value = name || "";
  $("editPhone").value = phone || "";
  $("editTag").value = tag || "New";

  const modal = bootstrap.Modal.getOrCreateInstance($("editModal"));
  modal.show();
}

async function saveEdit() {
  const payload = {
    name: $("editName").value.trim(),
    phone: $("editPhone").value.trim(),
    tag: $("editTag").value
  };

  const res = await fetch(`/customers/${editCustomerId}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token}`
    },
    body: JSON.stringify(payload)
  });

  const data = await res.json();
  if (!res.ok) {
    alert(data.error || "แก้ไขไม่สำเร็จ");
    return;
  }

  const modal = bootstrap.Modal.getInstance($("editModal"));
  if (modal) modal.hide();

  await refreshAll();
}

async function upgrade() {
  const res = await fetch("/upgrade", {
    method: "POST",
    headers: { "Authorization": `Bearer ${token}` }
  });

  const data = await res.json();
  if (!res.ok) {
    alert(data.error || "อัปเกรดไม่สำเร็จ");
    return;
  }

  currentPlan = "pro";
  localStorage.setItem("plan", "pro");
  await refreshAll();
  alert("อัปเกรดสำเร็จ");
}

function confirmPayment() {
  upgrade();
}

function renderChartFromCustomers(customers) {
  const counts = {
    New: 0,
    VIP: 0,
    Regular: 0
  };

  customers.forEach((customer) => {
    const key = customer.tag || "New";
    if (counts[key] === undefined) counts[key] = 0;
    counts[key] += 1;
  });

  renderChart({
    total: customers.length,
    vip: counts.VIP || 0,
    counts
  });
}

function renderChart(data) {
  const canvas = $("tagChart");
  if (!canvas) return;

  const counts = data.counts || {
    New: Math.max(0, (data.total || 0) - (data.vip || 0)),
    VIP: data.vip || 0,
    Regular: 0
  };

  if (tagChart) {
    tagChart.destroy();
  }

  tagChart = new Chart(canvas, {
    type: "doughnut",
    data: {
      labels: ["New", "VIP", "Regular"],
      datasets: [{
        data: [counts.New || 0, counts.VIP || 0, counts.Regular || 0],
        borderWidth: 0
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: {
          position: "bottom",
          labels: {
            color: "#e5eefb"
          }
        }
      }
    }
  });
}

function applySearchFilter() {
  const query = $("search").value.toLowerCase();
  document.querySelectorAll('[data-row="customer"]').forEach((row) => {
    row.style.display = row.innerText.toLowerCase().includes(query) ? "" : "none";
  });
}

document.addEventListener("DOMContentLoaded", () => {
  $("search").addEventListener("input", applySearchFilter);

  if (token) {
    currentUser = localStorage.getItem("username") || "";
    currentPlan = localStorage.getItem("plan") || "free";
    $("userLine").textContent = currentUser ? `${currentUser} • ${currentPlan.toUpperCase()}` : "พร้อมใช้งาน";
    showApp();
    refreshAll();
  } else {
    showAuth();
  }
});