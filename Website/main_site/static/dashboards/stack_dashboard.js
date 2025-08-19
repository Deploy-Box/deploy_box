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
    // const ctx = document.getElementById('cpuUsageChart').getContext('2d');

    // Create the chart
    // new Chart(ctx, {
    //     type: 'line',
    //     data: {
    //         labels: timeLabels,
    //         datasets: [{
    //             label: 'CPU Usage (%)',
    //             data: cpuData,
    //             borderColor: 'rgb(16, 185, 129)', // emerald-500
    //             backgroundColor: 'rgba(16, 185, 129, 0.1)',
    //             tension: 0.4,
    //             fill: true
    //         }]
    //     },
    //     options: {
    //         responsive: true,
    //         maintainAspectRatio: false,
    //         plugins: {
    //             legend: {
    //                 display: true,
    //                 position: 'top',
    //             },
    //             tooltip: {
    //                 mode: 'index',
    //                 intersect: false,
    //             }
    //         },
    //         scales: {
    //             y: {
    //                 beginAtZero: true,
    //                 max: 100,
    //                 title: {
    //                     display: true,
    //                     text: 'CPU Usage (%)'
    //                 }
    //             },
    //             x: {
    //                 title: {
    //                     display: true,
    //                     text: 'Time'
    //                 }
    //             }
    //         }
    //     }
    // });

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

    // Add event listener for download button
    const downloadButton = document.querySelector('[data-download-url]');
    if (downloadButton) {
        downloadButton.addEventListener('click', async function (e) {
            e.preventDefault();

            // Get elements
            const buttonText = this.querySelector('.button-text');
            const loadingSpinner = this.querySelector('.loading-spinner');
            const downloadIcon = this.querySelector('svg:not(.loading-spinner)');

            // Show loading state
            this.disabled = true;
            buttonText.textContent = 'Downloading...';
            downloadIcon.classList.add('hidden');
            loadingSpinner.classList.remove('hidden');

            try {
                // Get the download URL
                const downloadUrl = this.getAttribute('data-download-url');

                // Fetch the file
                const response = await fetch(downloadUrl);
                if (!response.ok) throw new Error('Download failed');

                // Get the blob from the response
                const blob = await response.blob();

                // Create a download link
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'stack.zip'; // or whatever the filename should be
                document.body.appendChild(a);
                a.click();

                // Clean up
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);

                // Show success state briefly
                buttonText.textContent = 'Downloaded!';
                setTimeout(() => {
                    // Reset button state
                    this.disabled = false;
                    buttonText.textContent = 'Download Stack';
                    downloadIcon.classList.remove('hidden');
                    loadingSpinner.classList.add('hidden');
                }, 2000);
            } catch (error) {
                console.error('Download error:', error);
                // Show error state
                buttonText.textContent = 'Download Failed';
                this.classList.add('bg-red-500', 'hover:bg-red-600');
                this.classList.remove('bg-zinc-500', 'hover:bg-zinc-600');

                // Reset after 2 seconds
                setTimeout(() => {
                    this.disabled = false;
                    buttonText.textContent = 'Download Stack';
                    downloadIcon.classList.remove('hidden');
                    loadingSpinner.classList.add('hidden');
                    this.classList.remove('bg-red-500', 'hover:bg-red-600');
                    this.classList.add('bg-zinc-500', 'hover:bg-zinc-600');
                }, 2000);
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
                document.getElementById('github-remove').classList.add('hidden');
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
                                updateRepoButtonText(repo.full_name);
                                repoDropdown.classList.add('hidden');
                                // Show remove button since repository is now connected
                                document.getElementById('github-remove').classList.remove('hidden');
                                // Reload the page to show the repository name in the overview
                                location.reload();
                            })
                            .catch(error => {
                                console.error('Error creating webhook:', error);
                                alert('Failed to connect repository. Please try again.');
                            });
                    });
                    repoList.appendChild(repoItem);
                });
            }
            
            // Check if there's already a webhook for this stack
            checkWebhookStatus();
        })
        .catch(error => {
            console.error('Error checking GitHub auth:', error);
        });
}

function checkWebhookStatus() {
    const dashboard = document.getElementById('dashboard');
    const stack_id = dashboard.getAttribute('data-stack-id');
    
    fetch(`/api/v1/github/webhook/status/?stack-id=${stack_id}`)
        .then(response => {
            if (response.ok) {
                return response.json();
            }
            throw new Error('Failed to check webhook status');
        })
        .then(data => {
            if (data.connected) {
                // Repository is connected, show remove button and update dropdown text
                document.getElementById('github-remove').classList.remove('hidden');
                updateRepoButtonText(data.repository);
            } else {
                // No repository connected, hide remove button
                document.getElementById('github-remove').classList.add('hidden');
            }
        })
        .catch(error => {
            console.error('Error checking webhook status:', error);
        });
}

function removeRepositoryConnection() {
    if (confirm('Are you sure you want to remove this repository connection? This will disconnect the webhook for this stack.')) {
        const dashboard = document.getElementById('dashboard');
        const stack_id = dashboard.getAttribute('data-stack-id');
        
        fetch('/api/v1/github/webhook/disconnect/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                'stack-id': stack_id
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to remove repository connection');
            }
            return response.json();
        })
        .then(data => {
            alert('Repository connection removed successfully!');
            // Update UI to show repository dropdown again
            document.getElementById('github-repos').classList.remove('hidden');
            document.getElementById('github-remove').classList.add('hidden');
            // Reset the dropdown button text
            const repoDropdownBtn = document.getElementById('repo-dropdown-btn');
            if (repoDropdownBtn) {
                repoDropdownBtn.innerHTML = `
                    <svg class="w-5 h-5 mr-2" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
                    </svg>
                    Select Repository
                    <svg class="w-4 h-4 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                    </svg>
                `;
            }
            // Reload the page to reflect changes
            location.reload();
        })
        .catch(error => {
            console.error('Error removing repository connection:', error);
            alert('Failed to remove repository connection. Please try again.');
        });
    }
}

function updateRepoButtonText(repoName) {
    const repoDropdownBtn = document.getElementById('repo-dropdown-btn');
    if (repoDropdownBtn) {
        const icon = repoDropdownBtn.querySelector('svg:first-child');
        const text = repoDropdownBtn.querySelector('span') || document.createElement('span');
        const dropdownIcon = repoDropdownBtn.querySelector('svg:last-child');
        
        // Clear existing content
        repoDropdownBtn.innerHTML = '';
        
        // Add back the GitHub icon
        repoDropdownBtn.appendChild(icon);
        
        // Add the repository name
        text.textContent = repoName;
        text.className = 'ml-2';
        repoDropdownBtn.appendChild(text);
        
        // Add back the dropdown icon
        repoDropdownBtn.appendChild(dropdownIcon);
    }
}

function checkExistingRepository() {
    // Check if there's a repository name displayed in the overview section
    const repoElement = document.querySelector('a[data-repository-name]');
    if (repoElement) {
        const repoName = repoElement.getAttribute('data-repository-name');
        updateRepoButtonText(repoName);
    }
}

window.onload = function () {
    // Get the organization_id, project_id, and stack_id from the data attributes
    const dashboard = document.getElementById('dashboard');
    const organizationId = dashboard.dataset.organizationId;
    const projectId = dashboard.dataset.projectId;
    const stackId = dashboard.dataset.stackId;
    const serviceName = dashboard.dataset.serviceName;

    // Check if there's already a repository connected and update the button text
    checkExistingRepository();



    // Set up root directory save functionality
    const saveRootDirectoryBtn = document.getElementById('save-root-directory');
    if (saveRootDirectoryBtn) {
        saveRootDirectoryBtn.addEventListener('click', () => {
            const rootDirectory = document.getElementById('root-directory').value;
            saveRootDirectory(organizationId, projectId, stackId, rootDirectory);
        });
    }

    // Set up refresh stack functionality
    const refreshStackBtn = document.getElementById('refresh-stack-btn');
    if (refreshStackBtn) {
        refreshStackBtn.addEventListener('click', () => {
            refreshStack(stackId);
        });
    }

    // Set up remove repository connection functionality
    const removeRepoBtn = document.getElementById('remove-repo-btn');
    if (removeRepoBtn) {
        removeRepoBtn.addEventListener('click', removeRepositoryConnection);
    }

    // Root Directory Input Handler
    const rootDirectoryInput = document.getElementById('root-directory');
    const stackIdMetadata = document.getElementById('metadata').dataset.stackId;

    if (saveRootDirectoryBtn && rootDirectoryInput) {
        saveRootDirectoryBtn.addEventListener('click', async function () {
            const rootDirectory = rootDirectoryInput.value.trim();
            if (rootDirectory) {
                await saveRootDirectory(stackIdMetadata, rootDirectory);
            }
        });

        // Also save on Enter key press
        rootDirectoryInput.addEventListener('keypress', async function (e) {
            if (e.key === 'Enter') {
                const rootDirectory = rootDirectoryInput.value.trim();
                if (rootDirectory) {
                    await saveRootDirectory(stackIdMetadata, rootDirectory);
                }
            }
        });
    }
};







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

async function saveRootDirectory(stackId, rootDirectory) {
    try {
        // Ensure the root directory starts with ./
        const formattedRootDirectory = rootDirectory.startsWith('./') ? rootDirectory : `./${rootDirectory}`;

        const response = await fetch(`/api/v1/stacks/${stackId}/`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                root_directory: formattedRootDirectory
            })
        });

        if (!response.ok) {
            throw new Error('Failed to update root directory');
        }

        const data = await response.json();

        // Show success message and indicator
        const saveButton = document.getElementById('save-root-directory');
        const saveIndicator = document.getElementById('save-indicator');
        const originalText = saveButton.textContent;

        // Show the checkmark indicator
        saveIndicator.classList.remove('hidden');

        // Change button text and style
        saveButton.textContent = 'Saved!';
        saveButton.classList.remove('bg-emerald-400', 'hover:bg-emerald-500');
        saveButton.classList.add('bg-green-600');

        // Reset button and hide indicator after 2 seconds
        setTimeout(() => {
            saveButton.textContent = originalText;
            saveButton.classList.remove('bg-green-600');
            saveButton.classList.add('bg-emerald-400', 'hover:bg-emerald-500');
            saveIndicator.classList.add('hidden');
        }, 2000);

    } catch (error) {
        console.error('Error saving root directory:', error);
        alert('Failed to update root directory. Please try again.');
    }
}

async function refreshStack(stackId) {
    const refreshButton = document.getElementById('refresh-stack-btn');
    const buttonText = refreshButton.querySelector('.button-text');
    const refreshIcon = refreshButton.querySelector('svg:not(.loading-spinner)');
    const loadingSpinner = refreshButton.querySelector('.loading-spinner');

    // Show loading state
    refreshButton.disabled = true;
    buttonText.textContent = 'Refreshing...';
    refreshIcon.classList.add('hidden');
    loadingSpinner.classList.remove('hidden');

    try {
        const response = await fetch(`/api/v1/stacks/${stackId}/refresh/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            }
        });

        if (!response.ok) {
            throw new Error('Failed to refresh stack');
        }

        const data = await response.json();
        
        if (data.success) {
            // Show success state
            buttonText.textContent = 'Refreshed!';
            refreshButton.classList.remove('bg-blue-500', 'hover:bg-blue-600');
            refreshButton.classList.add('bg-green-500', 'hover:bg-green-600');
            
            setTimeout(() => {
                // Reset button state
                refreshButton.disabled = false;
                buttonText.textContent = 'Refresh Stack';
                refreshIcon.classList.remove('hidden');
                loadingSpinner.classList.add('hidden');
                refreshButton.classList.remove('bg-green-500', 'hover:bg-green-600');
                refreshButton.classList.add('bg-blue-500', 'hover:bg-blue-600');
            }, 2000);
        } else {
            throw new Error(data.error || 'Failed to refresh stack');
        }
    } catch (error) {
        console.error('Error refreshing stack:', error);
        
        // Show error state
        buttonText.textContent = 'Refresh Failed';
        refreshButton.classList.remove('bg-blue-500', 'hover:bg-blue-600');
        refreshButton.classList.add('bg-red-500', 'hover:bg-red-600');

        setTimeout(() => {
            // Reset button state
            refreshButton.disabled = false;
            buttonText.textContent = 'Refresh Stack';
            refreshIcon.classList.remove('hidden');
            loadingSpinner.classList.add('hidden');
            refreshButton.classList.remove('bg-red-500', 'hover:bg-red-600');
            refreshButton.classList.add('bg-blue-500', 'hover:bg-blue-600');
        }, 2000);
    }
}

// Utility function to get CSRF token from cookies
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}


