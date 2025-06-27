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
                    // Redirect to home page or login page
                    window.location.href = '/';
                } else {
                    throw new Error('Logout failed');
                }
            })
            .catch(error => {
                console.error('Logout error:', error);
                // Reset button state
                this.textContent = originalText;
                this.style.opacity = '1';
                this.style.pointerEvents = 'auto';
                
                // Show error message
                alert('Logout failed. Please try again.');
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
                    alert('Profile updated successfully!');
                } else {
                    alert('Profile update failed: ' + (data.error || 'Unknown error'));
                }
            })
            .catch(error => {
                console.error('Profile update error:', error);
                alert('Profile update failed. Please try again.');
            })
            .finally(() => {
                // Reset button state
                submitButton.textContent = originalText;
                submitButton.disabled = false;
            });
        });
    }
    
    // Password reset functionality
    const resetPasswordButton = document.getElementById('resetPassword');
    if (resetPasswordButton) {
        resetPasswordButton.addEventListener('click', function(e) {
            e.preventDefault();
            
            const resetEmail = document.getElementById('resetEmail').value;
            if (!resetEmail) {
                alert('Please enter your email address.');
                return;
            }
            
            const originalText = this.textContent;
            
            // Show loading state
            this.textContent = 'Sending...';
            this.disabled = true;
            
            fetch('/api/v1/accounts/password-reset/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    email: resetEmail
                }),
                credentials: 'same-origin'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('Password reset email sent successfully!');
                    document.getElementById('resetEmail').value = '';
                } else {
                    alert('Password reset failed: ' + (data.error || 'Unknown error'));
                }
            })
            .catch(error => {
                console.error('Password reset error:', error);
                alert('Password reset failed. Please try again.');
            })
            .finally(() => {
                // Reset button state
                this.textContent = originalText;
                this.disabled = false;
            });
        });
    }
    
    // Load current user data
    loadUserData();
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
            const resetEmailField = document.getElementById('resetEmail');
            
            if (usernameField && data.user.username) {
                usernameField.value = data.user.username;
            }
            if (emailField && data.user.email) {
                emailField.value = data.user.email;
            }
            if (resetEmailField && data.user.email) {
                resetEmailField.value = data.user.email;
            }
        }
    })
    .catch(error => {
        console.error('Error loading user data:', error);
    });
}
