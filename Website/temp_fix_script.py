filepath = r"C:\Users\KBishop\code\deploy_box\Website\main_site\templates\accounts\signup.html"

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_script = '''<script>
// Multi-step form navigation
let currentStep = 1;
const totalSteps = 2;

function updateStep(step) {
    currentStep = step;

    // Update visibility
    document.getElementById('step-1').classList.toggle('hidden', step !== 1);
    document.getElementById('step-2').classList.toggle('hidden', step !== 2);

    // Update progress bar
    const progress = (step / totalSteps) * 100;
    document.getElementById('progress-bar').style.width = progress + '%';

    // Update step indicator
    document.getElementById('step-indicator').textContent = `Step ${step} of ${totalSteps}`;
    document.getElementById('step-title').textContent = step === 1 ? 'Account Details' : 'Personal Information';
}

function showError(message) {
    const errorEl = document.getElementById('error-message');
    if (errorEl) errorEl.textContent = message;

    const bannerEl = document.getElementById('error-banner');
    if (bannerEl) bannerEl.classList.remove('hidden');

    // Scroll to top to show error
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function hideError() {
    const bannerEl = document.getElementById('error-banner');
    if (bannerEl) bannerEl.classList.add('hidden');
}

function validateStep1() {
    const username = document.querySelector('[name="username"]').value;
    const email = document.querySelector('[name="email"]').value;
    const password1 = document.querySelector('[name="password1"]').value;
    const password2 = document.querySelector('[name="password2"]').value;

    if (!username || !email || !password1 || !password2) {
        showError('Please fill in all fields before continuing.');
        return false;
    }

    if (password1 !== password2) {
        showError('Passwords do not match.');
        return false;
    }

    if (password1.length < 8) {
        showError('Password must be at least 8 characters long.');
        return false;
    }

    hideError();
    return true;
}

// Next button - Step 1 to Step 2
document.getElementById('next-btn').addEventListener('click', function() {
    if (validateStep1()) {
        updateStep(2);
    }
});

// Back button - Step 2 to Step 1
document.getElementById('back-btn').addEventListener('click', function() {
    updateStep(1);
});

// Form submission
document.getElementById('signup-form').addEventListener('submit', function(e) {
    e.preventDefault();

    const formData = new FormData(this);
    const submitBtn = document.getElementById('submit-btn');
    const originalText = submitBtn.innerHTML;

    // Show loading state
    submitBtn.innerHTML = '<span class="inline-block mr-2">' +
        '{% if transfer_data %}' +
            'Creating Account & Accepting Project...' +
        '{% elif invite_data %}' +
            'Joining Organization...' +
        '{% else %}' +
            'Creating Account...' +
        '{% endif %}' +
        '</span><svg class="animate-spin w-4 h-4 inline-block text-zinc-950" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>';
    submitBtn.disabled = true;

    // Remove any existing error messages
    const existingErrors = document.querySelectorAll('.error-message');
    existingErrors.forEach(error => error.remove());

    // Prepare request data
    const requestData = {
        username: formData.get('username'),
        email: formData.get('email'),
        first_name: formData.get('first_name'),
        last_name: formData.get('last_name'),
        birthdate: formData.get('birthdate'),
        password1: formData.get('password1'),
        password2: formData.get('password2')
    };

    if (formData.get('invite_id')) {
        requestData.invite_id = formData.get('invite_id');
    }

    if (formData.get('transfer_id')) {
        requestData.transfer_id = formData.get('transfer_id');
    }

    fetch(this.action, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        },
        body: JSON.stringify(requestData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.message) {
            // Success - redirect to login
            window.location.href = "{% url 'main_site:login' %}";
        } else {
            // Show validation errors
            let errorMessage = 'Please fix the following errors: ';

            if (data.user_errors) {
                const errors = [];
                Object.keys(data.user_errors).forEach(field => {
                    errors.push(`${field}: ${data.user_errors[field].join(', ')}`);
                });
                errorMessage += errors.join(' | ');
            } else {
                errorMessage = 'Please check your input and try again.';
            }

            showError(errorMessage);
        }
    })
    .catch(error => {
        console.error('Signup error:', error);
        showError('An error occurred while creating your account. Please try again.');
    })
    .finally(() => {
        // Reset button state
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    });
});
</script>'''

new_script = r'''<script>
// Multi-step form navigation
let currentStep = 1;
const totalSteps = 2;

// Fields that belong to each step (used for error routing)
const step1Fields = ['username', 'email', 'password1', 'password2', 'password'];
const step2Fields = ['first_name', 'last_name', 'birthdate'];

// --- Error helpers ---

function showFieldError(fieldName, message) {
    const el = document.querySelector(`.field-error[data-field="${fieldName}"]`);
    if (!el) return;
    el.textContent = message;
    el.classList.remove('hidden');

    // Also highlight the input border
    const input = document.querySelector(`[name="${fieldName}"]`);
    if (input) {
        input.classList.remove('border-zinc-700');
        input.classList.add('border-red-500/70');
    }
}

function clearFieldError(fieldName) {
    const el = document.querySelector(`.field-error[data-field="${fieldName}"]`);
    if (el) {
        el.textContent = '';
        el.classList.add('hidden');
    }
    const input = document.querySelector(`[name="${fieldName}"]`);
    if (input) {
        input.classList.remove('border-red-500/70');
        input.classList.add('border-zinc-700');
    }
}

function clearAllFieldErrors() {
    document.querySelectorAll('.field-error').forEach(el => {
        el.textContent = '';
        el.classList.add('hidden');
    });
    document.querySelectorAll('input.border-red-500\\/70').forEach(input => {
        input.classList.remove('border-red-500/70');
        input.classList.add('border-zinc-700');
    });
}

function showBanner(message) {
    const errorEl = document.getElementById('error-message');
    if (errorEl) errorEl.textContent = message;

    const bannerEl = document.getElementById('error-banner');
    if (bannerEl) bannerEl.classList.remove('hidden');

    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function hideBanner() {
    const bannerEl = document.getElementById('error-banner');
    if (bannerEl) bannerEl.classList.add('hidden');
}

// --- Step navigation ---

function updateStep(step) {
    currentStep = step;

    document.getElementById('step-1').classList.toggle('hidden', step !== 1);
    document.getElementById('step-2').classList.toggle('hidden', step !== 2);

    const progress = (step / totalSteps) * 100;
    document.getElementById('progress-bar').style.width = progress + '%';

    document.getElementById('step-indicator').textContent = `Step ${step} of ${totalSteps}`;
    document.getElementById('step-title').textContent = step === 1 ? 'Account Details' : 'Personal Information';
}

// --- Client-side validation ---

function validateStep1() {
    let valid = true;
    clearAllFieldErrors();
    hideBanner();

    const username = document.querySelector('[name="username"]').value.trim();
    const email    = document.querySelector('[name="email"]').value.trim();
    const password1 = document.querySelector('[name="password1"]').value;
    const password2 = document.querySelector('[name="password2"]').value;

    if (!username) {
        showFieldError('username', 'Username is required.');
        valid = false;
    }
    if (!email) {
        showFieldError('email', 'Email is required.');
        valid = false;
    }
    if (!password1) {
        showFieldError('password1', 'Password is required.');
        valid = false;
    } else if (password1.length < 8) {
        showFieldError('password1', 'Password must be at least 8 characters long.');
        valid = false;
    }
    if (!password2) {
        showFieldError('password2', 'Please confirm your password.');
        valid = false;
    } else if (password1 && password2 && password1 !== password2) {
        showFieldError('password2', 'Passwords do not match.');
        valid = false;
    }

    if (!valid) {
        showBanner('Please fix the errors below before continuing.');
    }
    return valid;
}

function validateStep2() {
    let valid = true;
    // Only clear step-2 field errors (keep step-1 state intact)
    step2Fields.forEach(f => clearFieldError(f));
    hideBanner();

    const firstName = document.querySelector('[name="first_name"]').value.trim();
    const lastName  = document.querySelector('[name="last_name"]').value.trim();
    const birthdate = document.querySelector('[name="birthdate"]').value;

    if (!firstName) {
        showFieldError('first_name', 'First name is required.');
        valid = false;
    }
    if (!lastName) {
        showFieldError('last_name', 'Last name is required.');
        valid = false;
    }
    if (!birthdate) {
        showFieldError('birthdate', 'Birthdate is required.');
        valid = false;
    }

    if (!valid) {
        showBanner('Please fix the errors below before continuing.');
    }
    return valid;
}

// --- Display server errors on individual fields ---

function displayServerErrors(userErrors) {
    clearAllFieldErrors();
    hideBanner();

    let hasStep1Error = false;

    Object.keys(userErrors).forEach(field => {
        const messages = Array.isArray(userErrors[field])
            ? userErrors[field].join(' ')
            : String(userErrors[field]);

        // Map 'password' errors (from serializer validate()) to password1 field
        const mappedField = field === 'password' ? 'password1' : field;

        showFieldError(mappedField, messages);

        if (step1Fields.includes(mappedField)) {
            hasStep1Error = true;
        }
    });

    // If errors are on step-1 fields but we are on step 2, go back
    if (hasStep1Error && currentStep === 2) {
        updateStep(1);
    }

    showBanner('Please fix the errors below and try again.');
}

// --- Clear individual field error on user input ---

document.querySelectorAll('#signup-form input:not([type="hidden"])').forEach(input => {
    input.addEventListener('input', function() {
        clearFieldError(this.name);
        // If no visible field errors remain, also hide the banner
        const anyVisible = document.querySelector('.field-error:not(.hidden)');
        if (!anyVisible) hideBanner();
    });
});

// --- Button handlers ---

// Next button - Step 1 to Step 2
document.getElementById('next-btn').addEventListener('click', function() {
    if (validateStep1()) {
        updateStep(2);
    }
});

// Back button - Step 2 to Step 1
document.getElementById('back-btn').addEventListener('click', function() {
    updateStep(1);
});

// --- Form submission ---

document.getElementById('signup-form').addEventListener('submit', function(e) {
    e.preventDefault();

    // Client-side check on step 2 fields before submitting
    if (!validateStep2()) return;

    const formData = new FormData(this);
    const submitBtn = document.getElementById('submit-btn');
    const originalText = submitBtn.innerHTML;

    // Show loading state
    submitBtn.innerHTML = '<span class="inline-block mr-2">' +
        '{% if transfer_data %}' +
            'Creating Account & Accepting Project...' +
        '{% elif invite_data %}' +
            'Joining Organization...' +
        '{% else %}' +
            'Creating Account...' +
        '{% endif %}' +
        '</span><svg class="animate-spin w-4 h-4 inline-block text-zinc-950" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>';
    submitBtn.disabled = true;

    const requestData = {
        username: formData.get('username'),
        email: formData.get('email'),
        first_name: formData.get('first_name'),
        last_name: formData.get('last_name'),
        birthdate: formData.get('birthdate'),
        password1: formData.get('password1'),
        password2: formData.get('password2')
    };

    if (formData.get('invite_id')) {
        requestData.invite_id = formData.get('invite_id');
    }
    if (formData.get('transfer_id')) {
        requestData.transfer_id = formData.get('transfer_id');
    }

    fetch(this.action, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        },
        body: JSON.stringify(requestData)
    })
    .then(response => {
        return response.json().then(data => ({ ok: response.ok, data }));
    })
    .then(({ ok, data }) => {
        if (ok && data.message) {
            // Success - redirect to login
            window.location.href = "{% url 'main_site:login' %}";
        } else if (data.user_errors) {
            displayServerErrors(data.user_errors);
        } else {
            showBanner('Please check your input and try again.');
        }
    })
    .catch(error => {
        console.error('Signup error:', error);
        showBanner('An error occurred while creating your account. Please try again.');
    })
    .finally(() => {
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    });
});
</script>'''

if old_script in content:
    content = content.replace(old_script, new_script)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS: Script block replaced")
else:
    print("ERROR: Could not find exact old script block")
    # Debug: find where <script> starts and ends
    start = content.find('<script>')
    end = content.find('</script>')
    if start != -1 and end != -1:
        print(f"Script block found from char {start} to {end + len('</script>')}")
        print(f"Script length: {end + len('</script>') - start}")
        print(f"Old script length: {len(old_script)}")
