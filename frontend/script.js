const fetchCustomers = async () => {
    const token = localStorage.getItem('token');
    const res = await fetch('/customers', {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    const data = await res.json();
    // นำ data ไปแสดงผลในตารางที่จัดดีไซน์ด้วย Tailwind
}
function loadChart(data){
  let ctx = document.getElementById("chart");

  new Chart(ctx, {
    type: "bar",
    data: {
      labels: data.map((_,i)=>"ลูกค้า "+(i+1)),
      datasets: [{
        label: "จำนวนลูกค้า",
        data: data.map((_,i)=>i+1)
      }]
    }
  });
}


<div class="card p-3 mb-3">
  <h5>📊 Customer Growth</h5>
  <canvas id="chart"></canvas>
</div>