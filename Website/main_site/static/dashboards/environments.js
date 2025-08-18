// Environment Management Page
class EnvironmentManager {
    constructor() {
        this.environments = [
            {
                id: 'dev',
                name: 'Development',
                type: 'development',
                description: 'Local development and testing environment',
                url: '',
                database: '',
                color: 'emerald',
                status: 'active'
            },
            {
                id: 'staging',
                name: 'Staging',
                type: 'staging',
                description: 'Pre-production testing and validation environment',
                url: '',
                database: '',
                color: 'yellow',
                status: 'active'
            },
            {
                id: 'prod',
                name: 'Production',
                type: 'production',
                description: 'Live production environment for end users',
                url: '',
                database: '',
                color: 'red',
                status: 'active'
            }
        ];
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.updateStatistics();
    }

    setupEventListeners() {
        // Add environment modal
        const openAddModal = document.getElementById('open-add-modal');
        const addModal = document.getElementById('add-modal');
        const closeAddModal = document.getElementById('close-add-modal');
        const cancelAdd = document.getElementById('cancel-add');
        const createFirstBtn = document.getElementById('create-first-env');

        if (openAddModal) {
            openAddModal.addEventListener('click', () => {
                this.openAddModal();
            });
        }

        if (closeAddModal) {
            closeAddModal.addEventListener('click', () => {
                this.closeAddModal();
            });
        }

        if (cancelAdd) {
            cancelAdd.addEventListener('click', () => {
                this.closeAddModal();
            });
        }

        if (createFirstBtn) {
            createFirstBtn.addEventListener('click', () => {
                this.openAddModal();
            });
        }

        // Close add modal when clicking outside
        if (addModal) {
            addModal.addEventListener('click', (e) => {
                if (e.target === addModal) {
                    this.closeAddModal();
                }
            });
        }

        // Form submission
        const form = document.getElementById('environment-form');
        if (form) {
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                this.addEnvironment();
            });
        }

        // Delete environment buttons
        const deleteBtns = document.querySelectorAll('.delete-env-btn');
        deleteBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const envId = e.currentTarget.getAttribute('data-env-id');
                this.deleteEnvironment(envId);
            });
        });

        // Clone environment buttons
        const cloneBtns = document.querySelectorAll('.clone-env-btn');
        cloneBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const envId = e.currentTarget.getAttribute('data-env-id');
                const envName = e.currentTarget.getAttribute('data-env-name');
                this.openCloneModal(envId, envName);
            });
        });

        // Clone modal functionality
        const cloneModal = document.getElementById('clone-modal');
        const closeCloneModal = document.getElementById('close-clone-modal');
        const cancelClone = document.getElementById('cancel-clone');
        const cloneForm = document.getElementById('clone-form');

        if (closeCloneModal) {
            closeCloneModal.addEventListener('click', () => {
                this.closeCloneModal();
            });
        }

        if (cancelClone) {
            cancelClone.addEventListener('click', () => {
                this.closeCloneModal();
            });
        }

        if (cloneForm) {
            cloneForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.cloneEnvironment();
            });
        }

        // Clone mode radio button handling
        const cloneModeNew = document.getElementById('clone-mode-new');
        const cloneModeOverwrite = document.getElementById('clone-mode-overwrite');
        const newEnvFields = document.getElementById('new-env-fields');
        const overwriteEnvFields = document.getElementById('overwrite-env-fields');

        if (cloneModeNew && cloneModeOverwrite) {
            cloneModeNew.addEventListener('change', () => {
                newEnvFields.classList.remove('hidden');
                overwriteEnvFields.classList.add('hidden');
                this.updateFormValidation();
            });

            cloneModeOverwrite.addEventListener('change', () => {
                newEnvFields.classList.add('hidden');
                overwriteEnvFields.classList.remove('hidden');
                this.updateFormValidation();
            });
        }

        // Close modal when clicking outside
        if (cloneModal) {
            cloneModal.addEventListener('click', (e) => {
                if (e.target === cloneModal) {
                    this.closeCloneModal();
                }
            });
        }
    }

    addEnvironment() {
        const form = document.getElementById('environment-form');
        const formData = new FormData(form);
        
        const newEnv = {
            id: this.generateId(),
            name: formData.get('name'),
            type: formData.get('type'),
            description: formData.get('description'),
            url: formData.get('url'),
            database: formData.get('database'),
            color: formData.get('color'),
            status: 'active'
        };

        // Validate required fields
        if (!newEnv.name || !newEnv.type) {
            this.showNotification('Please fill in all required fields', 'error');
            return;
        }

        // Prevent creating production environments
        if (newEnv.type === 'production') {
            this.showNotification('Production environments cannot be created manually', 'error');
            return;
        }

        // Add to environments array
        this.environments.push(newEnv);

        // Add to DOM
        this.addEnvironmentToDOM(newEnv);

        // Update statistics
        this.updateStatistics();

        // Close modal
        this.closeAddModal();

        this.showNotification(`Environment "${newEnv.name}" created successfully!`, 'success');
    }

    addEnvironmentToDOM(env) {
        const environmentsList = document.getElementById('environments-list');
        const emptyState = document.getElementById('empty-state');

        // Hide empty state if visible
        if (emptyState) {
            emptyState.classList.add('hidden');
        }

        // Create environment item
        const envItem = document.createElement('div');
        envItem.className = `env-item bg-gradient-to-r from-${env.color}-50 to-${env.color}-100 p-4 rounded-lg border border-${env.color}-200`;
        envItem.setAttribute('data-env-id', env.id);

        const colorClasses = {
            'emerald': 'emerald',
            'blue': 'blue', 
            'yellow': 'yellow',
            'red': 'red',
            'purple': 'purple'
        };

        const colorClass = colorClasses[env.color] || 'emerald';

        envItem.innerHTML = `
            <div class="flex items-center justify-between">
                <div class="flex items-center space-x-3">
                    <div class="bg-${colorClass}-500 p-2 rounded-lg">
                        <svg class="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z" clip-rule="evenodd"></path>
                        </svg>
                    </div>
                    <div>
                        <h3 class="text-lg font-semibold text-${colorClass}-900">${env.name}</h3>
                        <p class="text-sm text-${colorClass}-700">${env.description}</p>
                        ${env.url ? `<p class="text-xs text-${colorClass}-600 mt-1">URL: ${env.url}</p>` : ''}
                    </div>
                </div>
                <div class="flex items-center space-x-2">
                    <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-${colorClass}-100 text-${colorClass}-800">
                        <span class="h-2 w-2 rounded-full bg-${colorClass}-500 mr-1"></span>
                        ${env.status}
                    </span>
                    <button class="clone-env-btn p-2 text-${colorClass}-600 hover:text-${colorClass}-800 hover:bg-${colorClass}-200 rounded-lg transition-all duration-300" data-env-id="${env.id}" data-env-name="${env.name}">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path>
                        </svg>
                    </button>
                    <button class="delete-env-btn p-2 text-${colorClass}-600 hover:text-${colorClass}-800 hover:bg-${colorClass}-200 rounded-lg transition-all duration-300" data-env-id="${env.id}">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                        </svg>
                    </button>
                </div>
            </div>
        `;

        // Add event listener to delete button
        const deleteBtn = envItem.querySelector('.delete-env-btn');
        deleteBtn.addEventListener('click', (e) => {
            const envId = e.currentTarget.getAttribute('data-env-id');
            this.deleteEnvironment(envId);
        });

        // Add event listener to clone button
        const cloneBtn = envItem.querySelector('.clone-env-btn');
        cloneBtn.addEventListener('click', (e) => {
            const envId = e.currentTarget.getAttribute('data-env-id');
            const envName = e.currentTarget.getAttribute('data-env-name');
            this.openCloneModal(envId, envName);
        });

        environmentsList.appendChild(envItem);
    }

    updateEnvironmentInDOM(envId, updatedEnv) {
        const envItem = document.querySelector(`[data-env-id="${envId}"]`);
        if (!envItem) return;

        const colorClasses = {
            'emerald': 'emerald',
            'blue': 'blue', 
            'yellow': 'yellow',
            'red': 'red',
            'purple': 'purple'
        };

        const colorClass = colorClasses[updatedEnv.color] || 'emerald';

        // Update the environment item with new data
        envItem.className = `env-item bg-gradient-to-r from-${updatedEnv.color}-50 to-${updatedEnv.color}-100 p-4 rounded-lg border border-${updatedEnv.color}-200`;
        envItem.setAttribute('data-env-id', updatedEnv.id);

        envItem.innerHTML = `
            <div class="flex items-center justify-between">
                <div class="flex items-center space-x-3">
                    <div class="bg-${colorClass}-500 p-2 rounded-lg">
                        <svg class="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z" clip-rule="evenodd"></path>
                        </svg>
                    </div>
                    <div>
                        <h3 class="text-lg font-semibold text-${colorClass}-900">${updatedEnv.name}</h3>
                        <p class="text-sm text-${colorClass}-700">${updatedEnv.description}</p>
                        ${updatedEnv.url ? `<p class="text-xs text-${colorClass}-600 mt-1">URL: ${updatedEnv.url}</p>` : ''}
                    </div>
                </div>
                <div class="flex items-center space-x-2">
                    <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-${colorClass}-100 text-${colorClass}-800">
                        <span class="h-2 w-2 rounded-full bg-${colorClass}-500 mr-1"></span>
                        ${updatedEnv.status}
                    </span>
                    <button class="clone-env-btn p-2 text-${colorClass}-600 hover:text-${colorClass}-800 hover:bg-${colorClass}-200 rounded-lg transition-all duration-300" data-env-id="${updatedEnv.id}" data-env-name="${updatedEnv.name}">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path>
                        </svg>
                    </button>
                    <button class="delete-env-btn p-2 text-${colorClass}-600 hover:text-${colorClass}-800 hover:bg-${colorClass}-200 rounded-lg transition-all duration-300" data-env-id="${updatedEnv.id}">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                        </svg>
                    </button>
                </div>
            </div>
        `;

        // Re-add event listeners
        const deleteBtn = envItem.querySelector('.delete-env-btn');
        deleteBtn.addEventListener('click', (e) => {
            const envId = e.currentTarget.getAttribute('data-env-id');
            this.deleteEnvironment(envId);
        });

        const cloneBtn = envItem.querySelector('.clone-env-btn');
        cloneBtn.addEventListener('click', (e) => {
            const envId = e.currentTarget.getAttribute('data-env-id');
            const envName = e.currentTarget.getAttribute('data-env-name');
            this.openCloneModal(envId, envName);
        });
    }

    deleteEnvironment(envId) {
        // Don't allow deletion of production environment
        if (envId === 'prod') {
            this.showNotification('Production environment cannot be deleted', 'error');
            return;
        }

        // Don't allow deletion of other default environments
        if (['dev', 'staging'].includes(envId)) {
            this.showNotification('Cannot delete default environments', 'error');
            return;
        }

        if (confirm('Are you sure you want to delete this environment? This action cannot be undone.')) {
            // Remove from array
            this.environments = this.environments.filter(env => env.id !== envId);

            // Remove from DOM
            const envItem = document.querySelector(`[data-env-id="${envId}"]`);
            if (envItem) {
                envItem.remove();
            }

            // Update statistics
            this.updateStatistics();

            // Show empty state if no environments left
            const envItems = document.querySelectorAll('.env-item');
            const emptyState = document.getElementById('empty-state');
            if (envItems.length === 0 && emptyState) {
                emptyState.classList.remove('hidden');
            }

            this.showNotification('Environment deleted successfully!', 'success');
        }
    }

    updateStatistics() {
        const total = this.environments.length;
        const active = this.environments.filter(env => env.status === 'active').length;
        const inactive = this.environments.filter(env => env.status === 'inactive').length;
        const custom = this.environments.filter(env => !['dev', 'staging', 'prod'].includes(env.id)).length;

        // Update statistics display
        const totalEl = document.getElementById('total-environments');
        const activeEl = document.getElementById('active-environments');
        const inactiveEl = document.getElementById('inactive-environments');
        const customEl = document.getElementById('custom-environments');

        if (totalEl) totalEl.textContent = total;
        if (activeEl) activeEl.textContent = active;
        if (inactiveEl) inactiveEl.textContent = inactive;
        if (customEl) customEl.textContent = custom;
    }

    resetForm() {
        const form = document.getElementById('environment-form');
        if (form) {
            form.reset();
        }
    }

    generateId() {
        return 'env_' + Math.random().toString(36).substr(2, 9);
    }

    openAddModal() {
        const modal = document.getElementById('add-modal');
        if (modal) {
            modal.classList.remove('hidden');
        }
    }

    closeAddModal() {
        const modal = document.getElementById('add-modal');
        if (modal) {
            modal.classList.add('hidden');
        }
        
        // Reset form
        this.resetForm();
    }

    openCloneModal(sourceEnvId, sourceEnvName) {
        const modal = document.getElementById('clone-modal');
        const sourceEnvIcon = document.getElementById('source-env-icon');
        const sourceEnvNameEl = document.getElementById('source-env-name');
        const targetEnvName = document.getElementById('target-env-name');
        const targetEnvType = document.getElementById('target-env-type');
        const targetEnvDescription = document.getElementById('target-env-description');
        const overwriteEnvSelect = document.getElementById('overwrite-env-select');

        // Set source environment info
        sourceEnvNameEl.textContent = sourceEnvName;
        
        // Set source environment icon based on type
        const sourceEnv = this.environments.find(env => env.id === sourceEnvId);
        if (sourceEnv) {
            const iconColor = sourceEnv.color;
            sourceEnvIcon.innerHTML = `
                <svg class="w-5 h-5 text-${iconColor}-500" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z" clip-rule="evenodd"></path>
                </svg>
            `;
        }

        // Set default target name
        targetEnvName.value = `${sourceEnvName} Copy`;
        
        // Set default type (same as source)
        if (sourceEnv) {
            targetEnvType.value = sourceEnv.type;
        }
        
        // Set default description
        targetEnvDescription.value = `Cloned from ${sourceEnvName} environment`;

        // Populate overwrite dropdown (exclude source environment)
        this.populateOverwriteDropdown(sourceEnvId);

        // Store source environment ID for cloning
        modal.setAttribute('data-source-env-id', sourceEnvId);

        // Show modal
        modal.classList.remove('hidden');
    }

    populateOverwriteDropdown(sourceEnvId) {
        const overwriteEnvSelect = document.getElementById('overwrite-env-select');
        if (!overwriteEnvSelect) return;

        // Clear existing options
        overwriteEnvSelect.innerHTML = '<option value="">Choose an environment...</option>';

        // Add all environments except the source
        this.environments.forEach(env => {
            if (env.id !== sourceEnvId) {
                const option = document.createElement('option');
                option.value = env.id;
                option.textContent = env.name;
                overwriteEnvSelect.appendChild(option);
            }
        });
    }

    updateFormValidation() {
        const cloneModeNew = document.getElementById('clone-mode-new');
        const targetEnvName = document.getElementById('target-env-name');
        const targetEnvType = document.getElementById('target-env-type');
        const overwriteEnvSelect = document.getElementById('overwrite-env-select');

        if (cloneModeNew && cloneModeNew.checked) {
            // New environment mode - require name and type
            targetEnvName.required = true;
            targetEnvType.required = true;
            overwriteEnvSelect.required = false;
        } else {
            // Overwrite mode - require target environment selection
            targetEnvName.required = false;
            targetEnvType.required = false;
            overwriteEnvSelect.required = true;
        }
    }

    closeCloneModal() {
        const modal = document.getElementById('clone-modal');
        modal.classList.add('hidden');
        
        // Reset form and show new environment fields by default
        const form = document.getElementById('clone-form');
        const newEnvFields = document.getElementById('new-env-fields');
        const overwriteEnvFields = document.getElementById('overwrite-env-fields');
        
        if (form) {
            form.reset();
        }
        
        // Reset to new environment mode
        if (newEnvFields && overwriteEnvFields) {
            newEnvFields.classList.remove('hidden');
            overwriteEnvFields.classList.add('hidden');
        }
        
        // Reset form validation
        this.updateFormValidation();
    }

    cloneEnvironment() {
        const modal = document.getElementById('clone-modal');
        const sourceEnvId = modal.getAttribute('data-source-env-id');
        const form = document.getElementById('clone-form');
        const formData = new FormData(form);

        // Get source environment
        const sourceEnv = this.environments.find(env => env.id === sourceEnvId);
        if (!sourceEnv) {
            this.showNotification('Source environment not found', 'error');
            return;
        }

        // Get clone mode
        const cloneMode = formData.get('clone_mode');

        if (cloneMode === 'new') {
            this.cloneToNewEnvironment(sourceEnv, formData);
        } else if (cloneMode === 'overwrite') {
            this.cloneToOverwriteEnvironment(sourceEnv, formData);
        } else {
            this.showNotification('Please select a clone mode', 'error');
        }
    }

    cloneToNewEnvironment(sourceEnv, formData) {
        // Validate form
        const targetName = formData.get('target_name');
        const targetType = formData.get('target_type');
        const targetDescription = formData.get('target_description');

        if (!targetName || !targetType) {
            this.showNotification('Please fill in all required fields', 'error');
            return;
        }

        // Prevent creating production environments
        if (targetType === 'production') {
            this.showNotification('Production environments cannot be created manually', 'error');
            return;
        }

        // Check if target name already exists
        const existingEnv = this.environments.find(env => env.name.toLowerCase() === targetName.toLowerCase());
        if (existingEnv) {
            this.showNotification('An environment with this name already exists', 'error');
            return;
        }

        // Create cloned environment
        const clonedEnv = {
            id: this.generateId(),
            name: targetName,
            type: targetType,
            description: targetDescription,
            url: sourceEnv.url,
            database: sourceEnv.database,
            color: sourceEnv.color,
            status: 'active'
        };

        // Add to environments array
        this.environments.push(clonedEnv);

        // Add to DOM
        this.addEnvironmentToDOM(clonedEnv);

        // Update statistics
        this.updateStatistics();

        // Close modal
        this.closeCloneModal();

        // Show success notification
        this.showNotification(`Environment "${targetName}" cloned successfully from "${sourceEnv.name}"!`, 'success');
    }

    cloneToOverwriteEnvironment(sourceEnv, formData) {
        // Validate form
        const overwriteEnvId = formData.get('overwrite_env_id');

        if (!overwriteEnvId) {
            this.showNotification('Please select an environment to overwrite', 'error');
            return;
        }

        // Get target environment
        const targetEnvIndex = this.environments.findIndex(env => env.id === overwriteEnvId);
        if (targetEnvIndex === -1) {
            this.showNotification('Target environment not found', 'error');
            return;
        }

        const targetEnv = this.environments[targetEnvIndex];
        const originalName = targetEnv.name;

        // Update target environment with source environment's configuration
        this.environments[targetEnvIndex] = {
            ...targetEnv,
            name: sourceEnv.name,
            type: sourceEnv.type,
            description: sourceEnv.description,
            url: sourceEnv.url,
            database: sourceEnv.database,
            color: sourceEnv.color
        };

        // Update DOM
        this.updateEnvironmentInDOM(overwriteEnvId, this.environments[targetEnvIndex]);

        // Update statistics
        this.updateStatistics();

        // Close modal
        this.closeCloneModal();

        // Show success notification
        this.showNotification(`Environment "${originalName}" overwritten successfully with "${sourceEnv.name}" configuration!`, 'success');
    }

    showNotification(message, type = 'info') {
        // Remove any existing notifications
        const existingNotification = document.querySelector('.env-notification');
        if (existingNotification) {
            existingNotification.remove();
        }

        // Create notification element
        const notification = document.createElement('div');
        const bgColor = type === 'success' ? 'bg-green-500' : type === 'error' ? 'bg-red-500' : 'bg-blue-500';
        const iconColor = type === 'success' ? 'text-green-500' : type === 'error' ? 'text-red-500' : 'text-blue-500';
        
        notification.className = `env-notification fixed top-4 right-4 bg-white border border-gray-200 rounded-lg shadow-lg p-4 z-50 transform transition-all duration-300 translate-x-full`;
        notification.innerHTML = `
            <div class="flex items-center">
                <svg class="w-5 h-5 mr-2 ${iconColor}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                </svg>
                <span class="text-sm font-medium">${message}</span>
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
}

// Initialize environment manager when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.environmentManager = new EnvironmentManager();
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = EnvironmentManager;
} 