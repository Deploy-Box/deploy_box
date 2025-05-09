document.addEventListener('DOMContentLoaded', function () {
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

    // Check GitHub authorization status
    checkGitHubAuth();

    // Repository dropdown functionality
    const repoDropdownBtn = document.getElementById('repo-dropdown-btn');
    const repoDropdown = document.getElementById('repo-dropdown');

    if (repoDropdownBtn && repoDropdown) {
        repoDropdownBtn.addEventListener('click', function () {
            repoDropdown.classList.toggle('hidden');
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', function (event) {
            if (!repoDropdownBtn.contains(event.target) && !repoDropdown.contains(event.target)) {
                repoDropdown.classList.add('hidden');
            }
        });
    }
});

function checkGitHubAuth() {
    fetch('/api/v1/github/repositories/json/')
        .then(response => {
            if (response.ok) {
                // User is authorized, show repository dropdown
                document.getElementById('github-connect').classList.add('hidden');
                document.getElementById('github-repos').classList.remove('hidden');
                return response.json();
            } else {
                // User is not authorized, show connect button
                document.getElementById('github-connect').classList.remove('hidden');
                document.getElementById('github-repos').classList.add('hidden');
                throw new Error('Not authorized');
            }
        })
        .then(data => {
            // Populate repository dropdown
            const repoDropdown = document.getElementById('repo-dropdown');
            if (repoDropdown) {
                const repoList = repoDropdown.querySelector('.py-2');
                repoList.innerHTML = '';

                data.repositories.forEach(repo => {
                    const repoItem = document.createElement('a');
                    repoItem.href = '#';
                    repoItem.className = 'block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100';
                    repoItem.textContent = repo.full_name;
                    repoItem.addEventListener('click', function (e) {
                        e.preventDefault();
                        // Handle repository selection
                        const repoName = repo.full_name;
                        const dashboard = document.getElementById('dashboard');
                        const stack_id = dashboard.getAttribute('data-stack-id');

                        // Create webhook
                        fetch('/api/v1/github/webhook/create/', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({
                                'repo-name': repoName,
                                'stack-id': stack_id
                            })
                        })
                            .then(response => {
                                if (!response.ok) {
                                    throw new Error('Failed to create webhook');
                                }
                                return response.json();
                            })
                            .then(data => {
                                // Show success message
                                alert('Successfully connected repository!');
                                // Update UI to show connected status
                                repoDropdownBtn.textContent = `Connected: ${repo.full_name}`;
                                repoDropdown.classList.add('hidden');
                            })
                            .catch(error => {
                                console.error('Error creating webhook:', error);
                                alert('Failed to connect repository. Please try again.');
                            });
                    });
                    repoList.appendChild(repoItem);
                });
            }
        })
        .catch(error => {
            console.error('Error checking GitHub auth:', error);
        });
}

window.onload = function () {
    // Get the organization_id, project_id, and stack_id from the data attributes
    const dashboard = document.getElementById('dashboard');
    const organizationId = dashboard.dataset.organizationId;
    const projectId = dashboard.dataset.projectId;
    const stackId = dashboard.dataset.stackId;

    // Call the function to fetch and display stack info
    getStackInfo(organizationId, projectId, stackId);

    // Initialize logs functionality
    initLogs(organizationId, projectId, stackId);

    // Set up event listeners for log controls
    setupLogControls();

    // Set up root directory save functionality
    const saveRootDirectoryBtn = document.getElementById('save-root-directory');
    if (saveRootDirectoryBtn) {
        saveRootDirectoryBtn.addEventListener('click', () => {
            const rootDirectory = document.getElementById('root-directory').value;
            saveRootDirectory(organizationId, projectId, stackId, rootDirectory);
        });
    }
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

// Logs functionality
let logsInterval = null;
let isPaused = false;
let lastTimestamp = null; // Track the last timestamp we've seen
let allLogs = {}; // Store logs by service
let selectedService = 'all'; // Default to showing all services

function initLogs(organizationId, projectId, stackId) {
    // Get the logs container
    const logsContainer = document.getElementById('logs-container');
    const serviceSelector = document.getElementById('service-selector');

    // Clear the example logs
    logsContainer.innerHTML = '';

    // Reset the last timestamp when initializing logs
    lastTimestamp = null;

    // Reset the logs storage
    allLogs = {};

    // Fetch logs immediately
    fetchLogs(organizationId, projectId, stackId);

    // Set up interval to fetch logs every 30 seconds
    logsInterval = setInterval(() => {
        if (!isPaused) {
            fetchLogs(organizationId, projectId, stackId);
        }
    }, 30000);

    // Add event listener for service selector
    serviceSelector.addEventListener('change', () => {
        selectedService = serviceSelector.value;
        displayLogs();
    });
}

async function fetchLogs(organizationId, projectId, stackId) {
    try {
        // Fetch logs from the API
        const response = await fetch(`/api/stack/${organizationId}/${projectId}/${stackId}/get-logs/`);

        if (!response.ok) {
            throw new Error('Failed to fetch logs');
        }

        const jsonData = await response.json();

        if (jsonData.status === "error") {
            throw new Error(jsonData.message);
        }

        const logsData = jsonData.data;

        if (!logsData || Object.keys(logsData).length === 0) {
            return; // No logs to display
        }

        // Process logs for each service
        for (const serviceName in logsData) {
            const serviceLogs = logsData[serviceName];

            // Skip if service has no logs
            if (serviceLogs.status !== "success" || !serviceLogs.data) {
                continue;
            }

            // Initialize service logs array if it doesn't exist
            if (!allLogs[serviceName]) {
                allLogs[serviceName] = [];

                // Add service to selector if it's not already there
                const serviceSelector = document.getElementById('service-selector');
                if (!Array.from(serviceSelector.options).some(option => option.value === serviceName)) {
                    const option = document.createElement('option');
                    option.value = serviceName;
                    option.textContent = serviceName;
                    serviceSelector.appendChild(option);
                }
            }

            // Process logs for this service
            let serviceLogEntries = [];

            // Handle different possible formats of the data
            if (Array.isArray(serviceLogs.data)) {
                serviceLogEntries = serviceLogs.data;
            } else if (typeof serviceLogs.data === 'object' && serviceLogs.data !== null) {
                // If it's a single log entry object
                serviceLogEntries = [serviceLogs.data];
            } else {
                console.warn(`Unexpected log format for service ${serviceName}:`, serviceLogs.data);
                continue;
            }

            // Skip if no log entries
            if (serviceLogEntries.length === 0) {
                continue;
            }

            // Sort logs in chronological order (oldest to newest)
            serviceLogEntries.sort((a, b) => {
                return new Date(a.timestamp) - new Date(b.timestamp);
            });

            // Keep track of seen log IDs to avoid duplicates
            const seenLogIds = new Set();

            // Add new logs to the service's log array
            serviceLogEntries.forEach(log => {
                // Skip logs we've already seen by ID
                if (log.id && seenLogIds.has(log.id)) {
                    return; // Skip this log as we've already seen it
                }

                // Add the ID to our set of seen IDs
                if (log.id) {
                    seenLogIds.add(log.id);
                }

                // Skip logs we've already seen by timestamp
                const logTimestamp = new Date(log.timestamp).getTime();
                if (lastTimestamp !== null && logTimestamp <= lastTimestamp) {
                    return; // Skip this log as we've already seen it
                }

                // Add the log to the service's log array
                allLogs[serviceName].push(log);
            });

            // Update the last timestamp to the most recent log
            if (serviceLogEntries.length > 0) {
                const mostRecentLog = serviceLogEntries[serviceLogEntries.length - 1];
                const timestamp = new Date(mostRecentLog.timestamp).getTime();
                if (lastTimestamp === null || timestamp > lastTimestamp) {
                    lastTimestamp = timestamp;
                }
            }
        }

        // Display the logs based on the selected service
        displayLogs();

    } catch (error) {
        console.error('Error fetching logs:', error);

        // Display error message to the user
        const logsContainer = document.getElementById('logs-container');
        const errorMessage = document.createElement('div');
        errorMessage.className = 'text-[#FF0000] flex items-center';
        errorMessage.innerHTML = `
            <i class="fas fa-exclamation-circle mr-2"></i>
            Failed to fetch logs: ${error.message}. Log fetching has been stopped.
        `;
        logsContainer.appendChild(errorMessage);

        // Stop the interval
        if (logsInterval) {
            clearInterval(logsInterval);
            logsInterval = null;
        }

        // Disable the pause button since we're not fetching anymore
        const pauseButton = document.getElementById('pause-logs-btn');
        if (pauseButton) {
            pauseButton.disabled = true;
            pauseButton.textContent = 'Paused';
        }
    }
}

function displayLogs() {
    // Get the logs container
    const logsContainer = document.getElementById('logs-container');

    // Clear the container
    logsContainer.innerHTML = '';

    // If no logs, display a message
    if (Object.keys(allLogs).length === 0) {
        const noLogsMessage = document.createElement('div');
        noLogsMessage.className = 'text-gray-400 text-center py-4';
        noLogsMessage.textContent = 'No logs available yet.';
        logsContainer.appendChild(noLogsMessage);
        return;
    }

    // Display logs based on the selected service
    if (selectedService === 'all') {
        // Display logs from all services
        for (const serviceName in allLogs) {
            displayServiceLogs(serviceName, allLogs[serviceName], logsContainer);
        }
    } else if (allLogs[selectedService]) {
        // Display logs from the selected service
        displayServiceLogs(selectedService, allLogs[selectedService], logsContainer);
    }

    // Scroll to the bottom
    logsContainer.scrollTop = logsContainer.scrollHeight;
}

function displayServiceLogs(serviceName, logs, container) {
    // Add a service header
    const serviceHeader = document.createElement('div');
    serviceHeader.className = 'text-emerald-400 font-bold py-2 border-b border-gray-700';
    serviceHeader.textContent = `Service: ${serviceName}`;
    container.appendChild(serviceHeader);

    // Add each log entry
    logs.forEach(log => {
        // Create a new log entry
        const logEntry = document.createElement('div');

        // Set the class based on severity
        let severityClass = 'text-white';
        let iconClass = 'fas fa-info-circle text-[#00FF00]';

        if (log.severity === 'WARNING') {
            severityClass = 'text-[#FFFF00]';
            iconClass = 'fas fa-exclamation-triangle text-[#FFFF00]';
        } else if (log.severity === 'ERROR') {
            severityClass = 'text-[#FF0000]';
            iconClass = 'fas fa-times-circle text-[#FF0000]';
        } else if (log.severity === 'DEBUG') {
            severityClass = 'text-[#00FFFF]';
            iconClass = 'fas fa-bug text-[#00FFFF]';
        }

        // Get the log message - handle both formats
        let logMessage = '';
        if (log.log) {
            // Original format
            logMessage = log.log;
        } else if (log.textPayload) {
            // New format with textPayload
            logMessage = log.textPayload;
        } else {
            // Fallback if neither format is present
            logMessage = JSON.stringify(log);
        }

        // Format the timestamp
        const timestamp = new Date(log.timestamp).toLocaleString();

        // Create a more structured log entry with HTTP request details if available
        let logContent = '';

        // Add timestamp and severity
        logContent += `<div class="flex items-center mb-1">
            <i class="${iconClass} mr-2"></i>
            <span class="font-bold">[${timestamp}] ${log.severity}:</span>
        </div>`;

        // Add the main log message if it exists
        if (logMessage) {
            logContent += `<div class="ml-6 mb-1">${logMessage}</div>`;
        }

        // Add HTTP request details if available
        if (log.http_request && Object.keys(log.http_request).length > 0) {
            logContent += `<div class="ml-6 mb-1 text-sm">
                <div class="font-semibold">HTTP Request:</div>
                <div class="ml-4">`;

            // Add request method and URL
            if (log.http_request.requestMethod && log.http_request.requestUrl) {
                logContent += `<div><span class="font-medium">${log.http_request.requestMethod}</span> ${log.http_request.requestUrl}</div>`;
            }

            // Add status code if available
            if (log.http_request.status) {
                const statusClass = log.http_request.status >= 400 ? 'text-red-500' : 'text-green-500';
                logContent += `<div>Status: <span class="${statusClass}">${log.http_request.status}</span></div>`;
            }

            // Add user agent if available
            if (log.http_request.userAgent) {
                logContent += `<div>User Agent: ${log.http_request.userAgent}</div>`;
            }

            // Add remote IP if available
            if (log.http_request.remoteIp) {
                logContent += `<div>Remote IP: ${log.http_request.remoteIp}</div>`;
            }

            // Add latency if available
            if (log.http_request.latency) {
                logContent += `<div>Latency: ${log.http_request.latency}</div>`;
            }

            logContent += `</div></div>`;
        }

        // Set the log entry HTML
        logEntry.className = `${severityClass} p-2 border-b border-gray-700`;
        logEntry.innerHTML = logContent;

        // Add the log entry to the container
        container.appendChild(logEntry);
    });
}

function setupLogControls() {
    // Get the clear and pause buttons
    const clearButton = document.getElementById('clear-logs-btn');
    const pauseButton = document.getElementById('pause-logs-btn');

    // Add event listener for clear button
    clearButton.addEventListener('click', () => {
        const logsContainer = document.getElementById('logs-container');
        logsContainer.innerHTML = '';
        allLogs = {}; // Clear the stored logs

        // Reset the service selector
        const serviceSelector = document.getElementById('service-selector');
        serviceSelector.innerHTML = '<option value="all">All Services</option>';
    });

    // Add event listener for pause button
    pauseButton.addEventListener('click', () => {
        isPaused = !isPaused;
        pauseButton.textContent = isPaused ? 'Resume' : 'Pause';
    });
}

function deleteStack(stackId) {
    if (confirm('Are you sure you want to delete this stack? This action cannot be undone.')) {
        fetch(`/api/v1/stacks/${stackId}/`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
            },
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    window.location.href = '/dashboard'; // Redirect to dashboard after successful deletion
                } else {
                    alert('Failed to delete stack: ' + (data.error || 'Unknown error'));
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred while deleting the stack');
            });
    }
}

const deleteStackBtn = document.getElementById('delete-stack-btn');
deleteStackBtn.addEventListener('click', () => {
    deleteStack(deleteStackBtn.dataset.stackId);
});

async function saveRootDirectory(organizationId, projectId, stackId, rootDirectory) {
    try {
        const response = await fetch(`/api/v1/stacks/${stackId}/`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                root_directory: rootDirectory
            })
        });

        if (!response.ok) {
            throw new Error('Failed to update root directory');
        }

        const data = await response.json();

        // Show success message
        const saveButton = document.getElementById('save-root-directory');
        const originalText = saveButton.textContent;
        saveButton.textContent = 'Saved!';
        saveButton.classList.remove('bg-emerald-400', 'hover:bg-emerald-500');
        saveButton.classList.add('bg-green-600');

        // Reset button after 2 seconds
        setTimeout(() => {
            saveButton.textContent = originalText;
            saveButton.classList.remove('bg-green-600');
            saveButton.classList.add('bg-emerald-400', 'hover:bg-emerald-500');
        }, 2000);

    } catch (error) {
        console.error('Error saving root directory:', error);
        alert('Failed to update root directory. Please try again.');
    }
}
