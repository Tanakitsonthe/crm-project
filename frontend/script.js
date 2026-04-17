let token = "";

function addCustomer() {
  fetch("/customers",{
    method:"POST",
    headers:{
      "Content-Type":"application/json",
      "Authorization":"Bearer "+token
    },
    body:JSON.stringify({
      name:name.value,
      phone:phone.value,
      tag:tag.value
    })
  })
  .then(res=>{
    if(!res.ok){
      alert("เพิ่มไม่สำเร็จ");
    }
    return res.json();
  })
  .then(data=>{
    console.log(data);
    loadCustomers();
  });
} // ✅ ปิดตรงนี้

// ================= FIX =================

function loadCustomers() {
  fetch("/customers", {
    headers: {
      "Authorization": "Bearer " + token
    }
  })
  .then(res => res.json())
  .then(data => {
    let list = document.getElementById("customers");
    if(!list) return;

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