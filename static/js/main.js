// In static/js/main.js
document.addEventListener('DOMContentLoaded', function() {

    // Check if productId was defined by the template (in product_detail.html) and is not null
    if (typeof productId !== 'undefined' && productId !== null) {
        const chartCanvas = document.getElementById('priceHistoryChart');

        if (chartCanvas) {
            // Proceed with fetching data for the chart and drawing it
            fetch(`/api/product/${productId}/prices`)
                .then(response => {
                    if (!response.ok) {
                        // If response is not ok (e.g., 404, 500), throw an error to be caught by .catch()
                        throw new Error(`HTTP error! status: ${response.status}, URL: ${response.url}`);
                    }
                    return response.json(); // Attempt to parse JSON
                })
                .then(data => {
                    if (data && Array.isArray(data) && data.length > 0) {
                        const labels = data.map(p => new Date(p.timestamp).toLocaleString());
                        const prices = data.map(p => p.price);

                        new Chart(chartCanvas, {
                            type: 'line', // Or 'bar'
                            data: {
                                labels: labels,
                                datasets: [{
                                    label: 'Price (₹)',
                                    data: prices,
                                    borderColor: 'rgb(75, 192, 192)',
                                    tension: 0.1, // Makes the line a bit curved
                                    fill: false
                                }]
                            },
                            options: {
                                responsive: true,
                                maintainAspectRatio: false, // Allows chart to fill container height/width better
                                scales: {
                                    y: {
                                        beginAtZero: false, // Price charts usually don't start at 0
                                        ticks: {
                                            // Format Y-axis ticks as currency
                                            callback: function(value, index, values) {
                                                return '₹' + value.toFixed(2); // Ensure two decimal places
                                            }
                                        }
                                    },
                                    x: {
                                        // Optional: configure x-axis if needed, e.g., for time series
                                    }
                                },
                                plugins: {
                                    legend: {
                                        display: true // Show legend
                                    },
                                    tooltip: {
                                        enabled: true // Show tooltips on hover
                                    }
                                }
                            }
                        });
                    } else {
                        console.log("No price data (or empty data array) received to draw the chart for product ID:", productId);
                        const ctx = chartCanvas.getContext('2d');
                        ctx.clearRect(0, 0, chartCanvas.width, chartCanvas.height); // Clear canvas
                        ctx.font = "16px Arial";
                        ctx.fillStyle = "#888";
                        ctx.textAlign = 'center';
                        ctx.fillText('No price data available for this product yet.', chartCanvas.width / 2, chartCanvas.height / 2);
                    }
                })
                .catch(error => {
                    console.error('Error fetching or processing price data for chart:', error);
                    if (chartCanvas) { // Check again in case error happened before canvas was confirmed
                        const ctx = chartCanvas.getContext('2d');
                        ctx.clearRect(0, 0, chartCanvas.width, chartCanvas.height); // Clear canvas
                        ctx.font = "16px Arial";
                        ctx.fillStyle = "red";
                        ctx.textAlign = 'center';
                        ctx.fillText('Could not load price data for the chart.', chartCanvas.width / 2, chartCanvas.height / 2);
                    }
                });
        } else {
            // This case should not happen if product_detail.html includes the canvas
            // console.log("Chart canvas ('priceHistoryChart') not found on this page, though productId was available.");
        }
    } else {
        // This will log if productId is not defined or is null (e.g., on index.html or other pages)
        // console.log("Product ID is not available on this page, or this is not the product detail page. Skipping chart generation.");
    }

    // You can add other general JavaScript code for your site below this line,
    // for example, event listeners for other buttons or dynamic behaviors
    // not specific to the product chart.

});