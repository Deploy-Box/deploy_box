document.addEventListener('DOMContentLoaded', function() {
    // Logout functionality
    const logoutButton = document.querySelector('a[href*="logout"]');
    if (logoutButton) {
        logoutButton.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Show loading state
            const originalText = this.textContent;
            this.textContent = 'Logging out...';
            this.style.opacity = '0.7';
            this.style.pointerEvents = 'none';
            
            // Make POST request to logout endpoint
            fetch('/api/v1/accounts/logout/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                credentials: 'same-origin'
            })
            .then(response => {
                if (response.ok) {
                    return response.json();
                } else {
                    throw new Error('Logout failed');
                }
            })
            .then(data => {
                // Redirect to WorkOS logout URL to clear AuthKit session,
                // or fall back to home page if not available
                if (data.logout_url) {
                    window.location.href = data.logout_url;
                } else {
                    window.location.href = '/';
                }
            })
            .catch(error => {
                console.error('Logout error:', error);
                // Reset button state
                this.textContent = originalText;
                this.style.opacity = '1';
                this.style.pointerEvents = 'auto';
                
                // Show error message
                showToast('Logout failed. Please try again.', 'error');
            });
        });
    }
    
    // Profile update functionality
    const userForm = document.getElementById('userForm');
    if (userForm) {
        userForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const submitButton = this.querySelector('button[type="submit"]');
            const originalText = submitButton.textContent;
            
            // Show loading state
            submitButton.textContent = 'Updating...';
            submitButton.disabled = true;
            
            fetch('/api/v1/accounts/profile/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    username: formData.get('username'),
                    email: formData.get('email')
                }),
                credentials: 'same-origin'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showToast('Profile updated successfully!', 'success');
                } else {
                    showToast('Profile update failed: ' + (data.error || 'Unknown error'), 'error');
                }
            })
            .catch(error => {
                console.error('Profile update error:', error);
                showToast('Profile update failed. Please try again.', 'error');
            })
            .finally(() => {
                // Reset button state
                submitButton.textContent = originalText;
                submitButton.disabled = false;
            });
        });
    }
    
    // Load current user data
    loadUserData();

    // Unlink GitHub functionality
    const unlinkGitHubBtn = document.getElementById('unlinkGitHubBtn');
    if (unlinkGitHubBtn) {
        unlinkGitHubBtn.addEventListener('click', function(e) {
            e.preventDefault();

            if (!confirm('Are you sure you want to unlink your GitHub account? This will also disconnect any repositories linked to your stacks.')) {
                return;
            }

            const originalText = this.textContent;
            this.textContent = 'Unlinking...';
            this.disabled = true;
            this.style.opacity = '0.7';

            fetch('/api/v1/github/unlink/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                credentials: 'same-origin'
            })
            .then(response => {
                if (response.ok) {
                    return response.json();
                }
                throw new Error('Failed to unlink GitHub');
            })
            .then(data => {
                // Reload to reflect the updated state
                window.location.reload();
            })
            .catch(error => {
                console.error('GitHub unlink error:', error);
                showToast('Failed to unlink GitHub. Please try again.', 'error');
                this.textContent = originalText;
                this.disabled = false;
                this.style.opacity = '1';
            });
        });
    }
    
    // Delete account functionality
    const deleteAccountBtn = document.getElementById('deleteAccountBtn');
    const deleteModal = document.getElementById('deleteModal');
    const confirmDelete = document.getElementById('confirmDelete');
    const cancelDelete = document.getElementById('cancelDelete');
    
    if (deleteAccountBtn) {
        deleteAccountBtn.addEventListener('click', function(e) {
            e.preventDefault();
            // Show the confirmation modal
            deleteModal.classList.remove('hidden');
            deleteModal.classList.add('flex');
        });
    }
    
    if (cancelDelete) {
        cancelDelete.addEventListener('click', function(e) {
            e.preventDefault();
            // Hide the modal
            deleteModal.classList.add('hidden');
            deleteModal.classList.remove('flex');
        });
    }
    
    if (confirmDelete) {
        confirmDelete.addEventListener('click', function(e) {
            e.preventDefault();
            
            const originalText = this.textContent;
            
            // Show loading state
            this.textContent = 'Deleting...';
            this.disabled = true;
            
            fetch('/api/v1/accounts/delete-account/', {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                credentials: 'same-origin'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showToast('Account deleted successfully. You will be redirected to the home page.', 'success');
                    // Redirect to home page
                    window.location.href = '/';
                } else {
                    showToast('Account deletion failed: ' + (data.error || 'Unknown error'), 'error');
                }
            })
            .catch(error => {
                console.error('Account deletion error:', error);
                showToast('Account deletion failed. Please try again.', 'error');
            })
            .finally(() => {
                // Reset button state
                this.textContent = originalText;
                this.disabled = false;
                
                // Hide the modal
                deleteModal.classList.add('hidden');
                deleteModal.classList.remove('flex');
            });
        });
    }
    
    // Close modal when clicking outside
    if (deleteModal) {
        deleteModal.addEventListener('click', function(e) {
            if (e.target === this) {
                this.classList.add('hidden');
                this.classList.remove('flex');
            }
        });
    }
});

// Helper function to get CSRF token from cookies
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

// Function to load current user data
function loadUserData() {
    fetch('/api/v1/accounts/profile/', {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        credentials: 'same-origin'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Populate form fields with current user data
            const usernameField = document.getElementById('username');
            const emailField = document.getElementById('email');
            
            if (usernameField && data.user.username) {
                usernameField.value = data.user.username;
            }
            if (emailField && data.user.email) {
                emailField.value = data.user.email;
            }
        }
    })
    .catch(error => {
        console.error('Error loading user data:', error);
    });
}
