let currentUser = null;

function register() {
  let username = prompt("username:");
  let password = prompt("password:");

  fetch("http://127.0.0.1:5000/register", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({username, password})
  })
  .then(res => res.json())
  .then(() => alert("Registered"));
}

function login() {
  let username = prompt("username:");
  let password = prompt("password:");

  fetch("http://127.0.0.1:5000/login", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({username, password})
  })
  .then(res => res.json())
  .then(data => {
    if (data.token) {
      localStorage.setItem("token", data.token);
      currentUser = username;
      updateUI();
      loadCustomers();
      loadDashboard();
      loadAI();
    }
  });
}

function logout() {
  localStorage.removeItem("token");
  currentUser = null;
  updateUI();
}

function addCustomer() {
  let name = document.getElementById("name").value;
  let phone = document.getElementById("phone").value;
  let tag = document.getElementById("tag").value;

  fetch("http://127.0.0.1:5000/add_customer", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": localStorage.getItem("token")
    },
    body: JSON.stringify({name, phone, tag})
  })
  .then(() => loadCustomers());
}

function loadCustomers() {
  fetch("http://127.0.0.1:5000/customers", {
    headers: {
      "Authorization": localStorage.getItem("token")
    }
  })
  .then(res => res.json())
  .then(data => {
    let list = document.getElementById("list");
    list.innerHTML = "";

    data.forEach(c => {
      let li = document.createElement("li");
      li.innerText = `${c[1]} - ${c[2]} (${c[3]})`;
      list.appendChild(li);
    });
  });
}

function loadDashboard() {
  fetch("http://127.0.0.1:5000/dashboard", {
    headers: {
      "Authorization": localStorage.getItem("token")
    }
  })
  .then(res => res.json())
  .then(res => {
    let labels = res.data.map(d => d[0]);
    let values = res.data.map(d => d[1]);

    new Chart(document.getElementById("chart"), {
      type: 'doughnut',
      data: {
        labels: labels,
        datasets: [{
          data: values
        }]
      }
    });
  });
}

function loadAI() {
  fetch("http://127.0.0.1:5000/ai", {
    headers: {
      "Authorization": localStorage.getItem("token")
    }
  })
  .then(res => res.json())
  .then(data => {
    document.getElementById("ai").innerText = data.insight;
  });
}

function updateUI() {
  document.getElementById("user").innerText =
    currentUser ? "Logged in: " + currentUser : "Not logged in";
}