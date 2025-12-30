document.addEventListener("DOMContentLoaded", function () {
    const API_BASE_URL = "/api/v1/analytics/";

    // Helper to format numbers with commas
    const formatNumber = (num) => {
        if (num === null || num === undefined) return "N/A";
        return new Intl.NumberFormat('en-US').format(num);
    };

    // Helper to format currency
    const formatCurrency = (num) => {
        if (num === null || num === undefined) return "N/A";
        return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(num);
    };

    // Fetch KPI data
    fetch(`${API_BASE_URL}kpis/`)
        .then(response => response.json())
        .then(data => {
            if (data && data.data) {
                document.getElementById("total-revenue").textContent = formatCurrency(data.data.total_revenue);
                document.getElementById("total-orders").textContent = formatNumber(data.data.total_orders);
                document.getElementById("total-customers").textContent = formatNumber(data.data.total_customers);
                document.getElementById("new-customers").textContent = formatNumber(data.data.new_customers);
            }
        })
        .catch(error => console.error("Error fetching KPIs:", error));

    // Fetch and render Sales Over Time chart
    fetch(`${API_BASE_URL}sales-over-time/`)
        .then(response => response.json())
        .then(data => {
            if (data && data.data) {
                const ctx = document.getElementById("salesOverTimeChart").getContext("2d");
                new Chart(ctx, {
                    type: "line",
                    data: {
                        labels: data.data.map(item => item.date),
                        datasets: [{
                            label: "Revenue",
                            data: data.data.map(item => item.daily_revenue),
                            borderColor: "rgba(75, 192, 192, 1)",
                            backgroundColor: "rgba(75, 192, 192, 0.2)",
                            fill: true,
                            tension: 0.1
                        }]
                    },
                    options: {
                        responsive: true,
                        scales: {
                            x: {
                                title: { display: true, text: "Date" }
                            },
                            y: {
                                title: { display: true, text: "Revenue" }
                            }
                        }
                    }
                });
            }
        })
        .catch(error => console.error("Error fetching sales data:", error));

    // Fetch and render Order Status Breakdown chart
    fetch(`${API_BASE_URL}order-status-breakdown/`)
        .then(response => response.json())
        .then(data => {
            if (data && data.data) {
                const ctx = document.getElementById("orderStatusChart").getContext("2d");
                new Chart(ctx, {
                    type: "doughnut",
                    data: {
                        labels: data.data.map(item => item.status.charAt(0).toUpperCase() + item.status.slice(1)),
                        datasets: [{
                            data: data.data.map(item => item.count),
                            backgroundColor: [
                                'rgba(255, 99, 132, 0.7)',
                                'rgba(54, 162, 235, 0.7)',
                                'rgba(255, 206, 86, 0.7)',
                                'rgba(75, 192, 192, 0.7)',
                                'rgba(153, 102, 255, 0.7)',
                                'rgba(255, 159, 64, 0.7)'
                            ],
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                    }
                });
            }
        })
        .catch(error => console.error("Error fetching order status data:", error));

    // Fetch and populate Top Products table
    fetch(`${API_BASE_URL}products/`)
        .then(response => response.json())
        .then(data => {
            if (data && data.data) {
                const tableBody = document.getElementById("top-products-table");
                tableBody.innerHTML = ""; // Clear loading state
                data.data.slice(0, 5).forEach(product => { // Show top 5
                    const row = `
                        <tr>
                            <td class="px-6 py-4 whitespace-nowrap">${product.product_name}</td>
                            <td class="px-6 py-4 whitespace-nowrap">${formatNumber(product.total_units_sold)}</td>
                            <td class="px-6 py-4 whitespace-nowrap">${formatCurrency(product.total_revenue)}</td>
                        </tr>
                    `;
                    tableBody.innerHTML += row;
                });
            }
        })
        .catch(error => console.error("Error fetching top products:", error));
});
