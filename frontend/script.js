let token = "";

function register() {
  fetch("/register", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      username: username.value,
      password: password.value
    })
  }).then(() => alert("สมัครสำเร็จ"));
}

function login() {
  fetch("/login", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      username: username.value,
      password: password.value
    })
  })
  .then(res => res.json())
  .then(data => {
    token = data.token;
    document.getElementById("auth").style.display = "none";
    document.getElementById("app").style.display = "block";
    loadCustomers();
    loadDashboard();
  });
}

function addCustomer() {
  fetch("/customers", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": "Bearer " + token
    },
    body: JSON.stringify({
      name: name.value,
      phone: phone.value,
      tag: tag.value
    })
  }).then(() => loadCustomers());
}

function loadCustomers() {
  fetch("/customers", {
    headers: {
      "Authorization": "Bearer " + token
    }
  })
  .then(res => res.json())
  .then(data => {
    let list = document.getElementById("customers");
    list.innerHTML = "";

    data.forEach(c => {
      let li = document.createElement("li");
      li.innerHTML = `
        ${c.name} (${c.phone}) [${c.tag}]
        <button onclick="deleteCustomer(${c.id})">ลบ</button>
      `;
      list.appendChild(li);
    });
  });
}

function deleteCustomer(id) {
  fetch("/customers/" + id, {
    method: "DELETE",
    headers: {
      "Authorization": "Bearer " + token
    }
  }).then(() => loadCustomers());
}

function loadDashboard() {
  fetch("/dashboard", {
    headers: {
      "Authorization": "Bearer " + token
    }
  })
  .then(res => res.json())
  .then(data => {
    document.getElementById("dashboard").innerText =
      "ลูกค้าทั้งหมด: " + data.total + " | VIP: " + data.vip;
  });
}

// 🔍 search
document.addEventListener("input", function(e) {
  if (e.target.id === "search") {
    let val = e.target.value.toLowerCase();
    document.querySelectorAll("#customers li").forEach(li => {
      li.style.display = li.innerText.toLowerCase().includes(val) ? "" : "none";
    });
  }
});