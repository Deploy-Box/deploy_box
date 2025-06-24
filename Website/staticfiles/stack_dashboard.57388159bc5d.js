document.addEventListener('DOMContentLoaded', function() {
    // Example data - in a real application, this would come from your backend
    const timeLabels = [];
    const cpuData = [];
    
    // Generate example data for the last 24 hours
    const now = new Date();
    for (let i = 23; i >= 0; i--) {
        const time = new Date(now);
        time.setHours(now.getHours() - i);
        timeLabels.push(time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
        
        // Generate random CPU usage between 30% and 60%
        cpuData.push(Math.floor(Math.random() * (60 - 30 + 1)) + 30);
    }

    // Get the chart canvas
    const ctx = document.getElementById('cpuUsageChart').getContext('2d');

    // Create the chart
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: timeLabels,
            datasets: [{
                label: 'CPU Usage (%)',
                data: cpuData,
                borderColor: 'rgb(16, 185, 129)', // emerald-500
                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    title: {
                        display: true,
                        text: 'CPU Usage (%)'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Time'
                    }
                }
            }
        }
    });
}); 


window.onload = function() {
    // Get the organization_id, project_id, and stack_id from the data attributes
    const dashboard = document.getElementById('dashboard');
    const organizationId = dashboard.dataset.organizationId;
    const projectId = dashboard.dataset.projectId;
    const stackId = dashboard.dataset.stackId;

    // Call the function to fetch and display stack info
    getStackInfo(organizationId, projectId, stackId);
};

async function getStackInfo(organizationId, projectId, stackId) {
    try {
        const response = await fetch(`/api/stack/${organizationId}/${projectId}/${stackId}/`);

        if (!response.ok) {
            throw new Error('Stack not found');
        }

        const stack = await response.json();

        // Populate the HTML with the stack information
        const stackInfoDiv = document.getElementById('stack-info');
        
        if (stack.error) {
            stackInfoDiv.innerHTML = `<p>Error: ${stack.error}</p>`;
        } else {
            stackInfoDiv.innerHTML = `
                <h2>${stack.name}</h2>
                <p><strong>Description:</strong> ${stack.description}</p>
                <p><strong>Project:</strong> ${stack.project}</p>
                <p><strong>Created At:</strong> ${stack.created_at}</p>
                <p><strong>Updated At:</strong> ${stack.updated_at}</p>
            `;
        }
    } catch (error) {
        console.error('Error fetching stack info:', error);
        const stackInfoDiv = document.getElementById('stack-info');
        stackInfoDiv.innerHTML = `<p class="text-red-500">Error: ${error.message}</p>`;
    }
}