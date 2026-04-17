let token = localStorage.getItem("token") || "";
let currentUser = localStorage.getItem("username") || "";
let currentPlan = localStorage.getItem("plan") || "free";
let currentRole = localStorage.getItem("role") || "user";
let editCustomerId = null;
let tagChart = null;

const pageMeta = {
  dashboardPage: {
    title: "Dashboard",
    subtitle: "ภาพรวมลูกค้า แผนสมาชิก และยอดใช้งาน"
  },
  customersPage: {
    title: "Customers",
    subtitle: "จัดการลูกค้า ค้นหา แก้ไข และลบข้อมูล"
  },
  billingPage: {
    title: "Billing",
    subtitle: "PromptPay และการปลดล็อก PRO"
  },
  settingsPage: {
    title: "Settings",
    subtitle: "โปรไฟล์ บัญชี และสิทธิ์การใช้งาน"
  }
};

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

function isImpersonating() {
  return Boolean(localStorage.getItem("crm_admin_backup_token"));
}

function showAuth() {
  $("auth").classList.remove("hidden");
  $("app").classList.add("hidden");
  closeSidebar();
  closeProfileMenu();
}

function showApp() {
  $("auth").classList.add("hidden");
  $("app").classList.remove("hidden");
}

function openSidebar() {
  document.body.classList.add("sidebar-open");
}

function closeSidebar() {
  document.body.classList.remove("sidebar-open");
}

function toggleProfileMenu(event) {
  if (event) event.stopPropagation();
  $("profileMenu").classList.toggle("open");
}

function closeProfileMenu() {
  $("profileMenu").classList.remove("open");
}

function updateSidebarPlan(plan) {
  const sidebarPlanText = $("sidebarPlanText");
  if (sidebarPlanText) {
    sidebarPlanText.textContent = (plan || "free").toUpperCase();
  }
}

function updateImpersonationBanner() {
  const banner = $("impersonationBanner");
  const name = $("impersonationName");

  if (!banner || !name) return;

  const active = isImpersonating();
  banner.classList.toggle("d-none", !active);
  if (active) {
    name.textContent = currentUser || "-";
  }
}

function updateAdminPanelVisibility() {
  const adminPanel = $("adminPanel");
  if (!adminPanel) return;

  const visible = currentRole === "admin" && !isImpersonating();
  adminPanel.classList.toggle("d-none", !visible);

  if (visible) {
    loadAdminUsers();
  }
}

function showPage(pageId) {
  document.querySelectorAll(".page").forEach((page) => {
    page.classList.remove("active");
    page.style.display = "none";
  });

  const target = $(pageId);
  if (target) {
    target.style.display = "block";
    target.classList.add("active");
  }

  document.querySelectorAll("[data-nav]").forEach((btn) => btn.classList.remove("active"));
  const activeNav = document.querySelector(`[data-nav="${pageId}"]`);
  if (activeNav) {
    activeNav.classList.add("active");
  }

  const meta = pageMeta[pageId] || pageMeta.dashboardPage;
  $("pageTitle").textContent = meta.title;
  $("pageSubtitle").textContent = meta.subtitle;

  closeProfileMenu();

  if (window.innerWidth < 992) {
    closeSidebar();
  }
}

function setPlanUI(plan, remaining, role) {
  const normalizedPlan = plan || "free";
  const normalizedRole = role || "user";

  const planBadge = $("planBadge");
  planBadge.textContent = normalizedPlan.toUpperCase();
  planBadge.classList.remove("plan-pro");
  if (normalizedPlan === "pro") {
    planBadge.classList.add("plan-pro");
  }

  $("roleBadge").textContent = normalizedRole.toUpperCase();
  $("remainingCount").textContent = normalizedPlan === "pro" ? "∞" : String(remaining ?? 0);
  $("paymentNote").textContent = normalizedPlan === "pro"
    ? "คุณใช้งาน PRO แล้ว"
    : "สแกน QR แล้วกดยืนยัน";

  $("heroPlanText").textContent = normalizedPlan.toUpperCase();
  $("heroRoleText").textContent = normalizedRole.toUpperCase();
  $("heroRemainingText").textContent = normalizedPlan === "pro" ? "∞" : String(remaining ?? 0);

  $("billingPlanText").textContent = normalizedPlan.toUpperCase();
  $("billingRemainingText").textContent = normalizedPlan === "pro" ? "∞" : String(remaining ?? 0);
  $("billingStatusText").textContent = normalizedPlan === "pro" ? "Unlocked" : "Ready";

  $("settingsUser").textContent = currentUser || "-";
  $("settingsRole").textContent = normalizedRole.toUpperCase();
  $("settingsPlan").textContent = normalizedPlan.toUpperCase();

  document.querySelectorAll("[data-upgrade-btn]").forEach((btn) => {
    btn.disabled = normalizedPlan === "pro";
  });

  updateSidebarPlan(normalizedPlan);
  updateImpersonationBanner();
  updateAdminPanelVisibility();
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
    currentRole = data.role || "user";

    localStorage.setItem("token", token);
    localStorage.setItem("username", currentUser);
    localStorage.setItem("plan", currentPlan);
    localStorage.setItem("role", currentRole);

    showApp();
    showPage("dashboardPage");
    $("userLine").textContent = `${currentUser} • ${currentPlan.toUpperCase()}`;
    await refreshAll();
  } catch (error) {
    alert("เชื่อมต่อเซิร์ฟเวอร์ไม่ได้");
  }
}

function logout() {
  localStorage.removeItem("token");
  localStorage.removeItem("username");
  localStorage.removeItem("plan");
  localStorage.removeItem("role");
  localStorage.removeItem("crm_admin_backup_token");
  localStorage.removeItem("crm_admin_backup_username");
  localStorage.removeItem("crm_admin_backup_plan");
  localStorage.removeItem("crm_admin_backup_role");
  token = "";
  currentUser = "";
  currentPlan = "free";
  currentRole = "user";
  closeSidebar();
  closeProfileMenu();
  location.reload();
}

function saveAdminBackupOnce() {
  if (isImpersonating()) return;

  localStorage.setItem("crm_admin_backup_token", token);
  localStorage.setItem("crm_admin_backup_username", currentUser);
  localStorage.setItem("crm_admin_backup_plan", currentPlan);
  localStorage.setItem("crm_admin_backup_role", currentRole);
}

async function returnToAdmin() {
  const backupToken = localStorage.getItem("crm_admin_backup_token");
  const backupUsername = localStorage.getItem("crm_admin_backup_username");
  const backupPlan = localStorage.getItem("crm_admin_backup_plan");
  const backupRole = localStorage.getItem("crm_admin_backup_role");

  if (!backupToken || !backupUsername) {
    alert("ไม่มี session แอดมินสำรอง");
    return;
  }

  token = backupToken;
  currentUser = backupUsername;
  currentPlan = backupPlan || "pro";
  currentRole = backupRole || "admin";

  localStorage.setItem("token", token);
  localStorage.setItem("username", currentUser);
  localStorage.setItem("plan", currentPlan);
  localStorage.setItem("role", currentRole);

  localStorage.removeItem("crm_admin_backup_token");
  localStorage.removeItem("crm_admin_backup_username");
  localStorage.removeItem("crm_admin_backup_plan");
  localStorage.removeItem("crm_admin_backup_role");

  showApp();
  showPage("dashboardPage");
  await refreshAll();
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

  setPlanUI(data.plan || "free", data.remaining, data.role || currentRole);
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

  const tbody = $("customerRows");
  tbody.innerHTML = "";

  if (!data.length) {
    tbody.innerHTML = `
      <tr>
        <td colspan="4" class="text-center text-soft py-4">ยังไม่มีลูกค้า</td>
      </tr>
    `;
    renderChart({ total: 0, vip: 0, counts: { New: 0, VIP: 0, Regular: 0 } });
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
  showPage("billingPage");
  alert("อัปเกรดสำเร็จ");
}

function confirmPayment() {
  upgrade();
}

async function impersonateUser(id) {
  saveAdminBackupOnce();

  const res = await fetch(`/admin/impersonate/${id}`, {
    method: "POST",
    headers: { "Authorization": `Bearer ${token}` }
  });

  const data = await res.json();
  if (!res.ok) {
    alert(data.error || "impersonate ไม่สำเร็จ");
    return;
  }

  token = data.token;
  currentUser = data.username || "";
  currentPlan = data.plan || "free";
  currentRole = data.role || "user";

  localStorage.setItem("token", token);
  localStorage.setItem("username", currentUser);
  localStorage.setItem("plan", currentPlan);
  localStorage.setItem("role", currentRole);

  showApp();
  showPage("dashboardPage");
  await refreshAll();
}

async function adminSetPlan(id, plan) {
  const res = await fetch(`/admin/users/${id}/plan`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token}`
    },
    body: JSON.stringify({ plan })
  });

  const data = await res.json();
  if (!res.ok) {
    alert(data.error || "อัปเดต plan ไม่สำเร็จ");
    return;
  }

  await loadAdminUsers();
  await refreshAll();
}

async function adminSetRole(id, role) {
  const res = await fetch(`/admin/users/${id}/role`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token}`
    },
    body: JSON.stringify({ role })
  });

  const data = await res.json();
  if (!res.ok) {
    alert(data.error || "อัปเดต role ไม่สำเร็จ");
    return;
  }

  await loadAdminUsers();
  await refreshAll();
}

async function loadAdminUsers() {
  const tbody = $("adminUsersRows");
  const adminPanel = $("adminPanel");
  if (!tbody || !adminPanel) return;

  if (currentRole !== "admin" || isImpersonating()) {
    adminPanel.classList.add("d-none");
    return;
  }

  adminPanel.classList.remove("d-none");

  const res = await fetch("/admin/users", {
    headers: { "Authorization": `Bearer ${token}` }
  });

  const data = await res.json();
  if (!res.ok) {
    tbody.innerHTML = `
      <tr>
        <td colspan="5" class="text-center text-soft py-4">โหลด admin panel ไม่ได้</td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = data.map((row) => {
    const planBadge = row.plan === "pro" ? "plan-pro" : "plan-free";
    const canChangeSelf = row.username === currentUser;

    return `
      <tr>
        <td>${escapeHtml(row.username)}</td>
        <td><span class="badge-pill ${planBadge}">${escapeHtml(row.plan.toUpperCase())}</span></td>
        <td>${escapeHtml(row.role.toUpperCase())}</td>
        <td>${escapeHtml(row.customers)}</td>
        <td class="d-flex flex-wrap gap-2">
          <button class="btn btn-sm btn-outline-light" ${canChangeSelf ? "disabled" : ""} onclick="adminSetPlan(${row.id}, 'pro')">PRO</button>
          <button class="btn btn-sm btn-outline-light" ${canChangeSelf ? "disabled" : ""} onclick="adminSetPlan(${row.id}, 'free')">FREE</button>
          <button class="btn btn-sm btn-outline-light" ${canChangeSelf ? "disabled" : ""} onclick="adminSetRole(${row.id}, 'admin')">ADMIN</button>
          <button class="btn btn-sm btn-outline-light" ${canChangeSelf ? "disabled" : ""} onclick="adminSetRole(${row.id}, 'user')">USER</button>
          <button class="btn btn-sm btn-warning" onclick="impersonateUser(${row.id})">Open as</button>
        </td>
      </tr>
    `;
  }).join("");
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
        backgroundColor: [
          "rgba(96, 165, 250, 0.95)",
          "rgba(245, 158, 11, 0.95)",
          "rgba(16, 185, 129, 0.95)"
        ],
        borderColor: "#0b1220",
        borderWidth: 3,
        hoverOffset: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "72%",
      animation: {
        duration: 800,
        easing: "easeOutQuart"
      },
      plugins: {
        legend: {
          position: "bottom",
          labels: {
            color: "#e5eefb",
            usePointStyle: true,
            pointStyle: "circle",
            padding: 18
          }
        },
        tooltip: {
          backgroundColor: "#0b1320",
          titleColor: "#ffffff",
          bodyColor: "#e5eefb",
          borderColor: "rgba(148, 163, 184, 0.2)",
          borderWidth: 1
        }
      }
    }
  });
}

function applySearchFilter() {
  const searchInput = $("search");
  if (!searchInput) return;

  const query = searchInput.value.toLowerCase();
  document.querySelectorAll('[data-row="customer"]').forEach((row) => {
    row.style.display = row.innerText.toLowerCase().includes(query) ? "" : "none";
  });
}

function bindGlobalEvents() {
  document.addEventListener("click", () => {
    closeProfileMenu();
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeSidebar();
      closeProfileMenu();
    }
  });

  const searchInput = $("search");
  if (searchInput) {
    searchInput.addEventListener("input", applySearchFilter);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  bindGlobalEvents();

  if (token) {
    currentUser = localStorage.getItem("username") || "";
    currentPlan = localStorage.getItem("plan") || "free";
    currentRole = localStorage.getItem("role") || "user";
    showApp();
    showPage("dashboardPage");
    updateSidebarPlan(currentPlan);
    updateImpersonationBanner();
    refreshAll();
  } else {
    showAuth();
  }
});