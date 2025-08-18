// Environment Switcher Component
class EnvironmentSwitcher {
    constructor() {
        this.currentEnv = 'dev';
        this.environments = {
            'dev': {
                name: 'Development',
                description: 'This is your active development environment where you can test changes before deploying to production.',
                bgColor: 'bg-emerald-50',
                borderColor: 'border-emerald-200',
                textColor: 'text-emerald-800',
                iconColor: 'text-emerald-500'
            },
            'test': {
                name: 'Testing',
                description: 'This is your testing environment for staging and quality assurance before production deployment.',
                bgColor: 'bg-blue-50',
                borderColor: 'border-blue-200',
                textColor: 'text-blue-800',
                iconColor: 'text-blue-500'
            },
            'prod': {
                name: 'Production',
                description: 'This is your production environment serving live traffic. Changes here affect your users directly.',
                bgColor: 'bg-red-50',
                borderColor: 'border-red-200',
                textColor: 'text-red-800',
                iconColor: 'text-red-500'
            }
        };
        
        this.init();
    }

    init() {
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Check if we have the new dropdown format
        const dropdownBtn = document.getElementById('env-dropdown-btn');
        const dropdown = document.getElementById('env-dropdown');
        
        if (dropdownBtn && dropdown) {
            // New dropdown format
            this.setupDropdownFormat();
        } else {
            // Legacy button group format
            this.setupButtonGroupFormat();
        }
    }

    setupDropdownFormat() {
        const dropdownBtn = document.getElementById('env-dropdown-btn');
        const dropdown = document.getElementById('env-dropdown');
        const envOptions = document.querySelectorAll('.env-option');

        // Toggle dropdown
        dropdownBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            dropdown.classList.toggle('hidden');
        });

        // Handle option selection
        envOptions.forEach(option => {
            option.addEventListener('click', (e) => {
                e.stopPropagation();
                const envType = option.getAttribute('data-env');
                this.switchEnvironmentDropdown(envType);
                dropdown.classList.add('hidden');
            });
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!dropdownBtn.contains(e.target) && !dropdown.contains(e.target)) {
                dropdown.classList.add('hidden');
            }
        });
    }

    setupButtonGroupFormat() {
        const envButtons = document.querySelectorAll('.env-btn');
        
        envButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                const envType = e.target.id.replace('env-', '');
                this.switchEnvironmentButtonGroup(envType);
            });
        });
    }

    switchEnvironmentDropdown(envType) {
        const envText = document.getElementById('env-text');
        const envIcon = document.getElementById('env-icon');
        
        if (!envText || !envIcon) return;

        const env = this.environments[envType];
        if (!env) return;

        // Update current environment
        this.currentEnv = envType;
        
        // Update button text
        envText.textContent = env.name;
        
        // Update icon color
        envIcon.className = `w-4 h-4 ${env.iconColor}`;
        
        // Add visual feedback
        this.showEnvironmentChangeNotification(envType);
    }

    switchEnvironmentButtonGroup(envType) {
        const envButtons = document.querySelectorAll('.env-btn');
        const currentEnvSpan = document.getElementById('current-env');
        const envDescription = document.querySelector('.bg-emerald-50 p, .bg-blue-50 p, .bg-red-50 p');

        if (!envDescription) return;

        // Update button styles
        envButtons.forEach(btn => {
            btn.classList.remove('bg-emerald-500', 'text-white', 'shadow-md');
            btn.classList.add('text-zinc-600', 'hover:text-zinc-900', 'hover:bg-zinc-200');
        });
        
        // Activate clicked button
        const activeButton = document.getElementById(`env-${envType}`);
        if (activeButton) {
            activeButton.classList.remove('text-zinc-600', 'hover:text-zinc-900', 'hover:bg-zinc-200');
            activeButton.classList.add('bg-emerald-500', 'text-white', 'shadow-md');
        }
        
        // Update current environment display
        this.currentEnv = envType;
        if (currentEnvSpan) {
            currentEnvSpan.textContent = this.environments[envType].name;
        }
        
        // Update description
        const env = this.environments[envType];
        if (envDescription) {
            envDescription.innerHTML = `<strong>${env.name} Environment:</strong> ${env.description}`;
        }
        
        // Update description container styling
        const descriptionContainer = envDescription?.parentElement;
        if (descriptionContainer) {
            // Remove existing environment-specific classes
            descriptionContainer.className = descriptionContainer.className
                .replace(/bg-(emerald|blue|red)-50/g, '')
                .replace(/border-(emerald|blue|red)-200/g, '');
            
            // Add new classes
            descriptionContainer.className = `mt-4 p-3 ${env.bgColor} border ${env.borderColor} rounded-lg`;
            envDescription.className = `text-sm ${env.textColor}`;
        }
        
        // Add visual feedback
        this.showEnvironmentChangeNotification(envType);
    }

    showEnvironmentChangeNotification(envType) {
        // Remove any existing notifications
        const existingNotification = document.querySelector('.env-notification');
        if (existingNotification) {
            existingNotification.remove();
        }

        // Create notification element
        const notification = document.createElement('div');
        notification.className = 'env-notification fixed top-4 right-4 bg-white border border-gray-200 rounded-lg shadow-lg p-4 z-50 transform transition-all duration-300 translate-x-full';
        notification.innerHTML = `
            <div class="flex items-center">
                <svg class="w-5 h-5 mr-2 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                </svg>
                <span class="text-sm font-medium">Switched to ${envType.charAt(0).toUpperCase() + envType.slice(1)} environment</span>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Animate in
        setTimeout(() => {
            notification.classList.remove('translate-x-full');
        }, 100);
        
        // Remove after 3 seconds
        setTimeout(() => {
            notification.classList.add('translate-x-full');
            setTimeout(() => {
                if (notification.parentElement) {
                    notification.remove();
                }
            }, 300);
        }, 3000);
    }

    getCurrentEnvironment() {
        return this.currentEnv;
    }

    setEnvironment(envType) {
        if (this.environments[envType]) {
            // Check which format is being used
            const dropdownBtn = document.getElementById('env-dropdown-btn');
            if (dropdownBtn) {
                this.switchEnvironmentDropdown(envType);
            } else {
                this.switchEnvironmentButtonGroup(envType);
            }
        }
    }
}

// Initialize environment switcher when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Check if environment switcher exists on the page
    const envButtons = document.querySelectorAll('.env-btn');
    const dropdownBtn = document.getElementById('env-dropdown-btn');
    
    if (envButtons.length > 0 || dropdownBtn) {
        window.environmentSwitcher = new EnvironmentSwitcher();
    }
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = EnvironmentSwitcher;
} 