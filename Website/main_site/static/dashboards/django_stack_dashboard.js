// Django Stack Dashboard JavaScript
// Extends the base stack dashboard functionality with Django-specific features

// Import base functionality
// This assumes the base stack_dashboard.js is loaded first

// Django-specific service monitoring
class DjangoDashboard {
    constructor() {
        this.organizationId = null;
        this.projectId = null;
        this.stackId = null;
        this.serviceName = null;
        this.init();
    }

    init() {
        // Get dashboard data
        const dashboard = document.getElementById('dashboard');
        if (dashboard) {
            this.organizationId = dashboard.dataset.organizationId;
            this.projectId = dashboard.dataset.projectId;
            this.stackId = dashboard.dataset.stackId;
            this.serviceName = dashboard.dataset.serviceName;
        }

        this.setupDjangoSpecificFeatures();
        this.setupServiceMonitoring();
    }

    setupDjangoSpecificFeatures() {
        // Django-specific UI enhancements
        this.setupServiceCards();
        this.setupServiceSelector();
        this.setupAdminPanel();
    }

    setupServiceCards() {
        // Add click handlers to service cards
        const djangoCard = document.querySelector('.bg-gradient-to-br.from-green-50');
        const databaseCard = document.querySelector('.bg-gradient-to-br.from-emerald-50');

        if (djangoCard) {
            djangoCard.addEventListener('click', () => this.openServiceLogs('django'));
        }
        if (databaseCard) {
            databaseCard.addEventListener('click', () => this.openServiceLogs('database'));
        }
    }

    setupServiceSelector() {
        const serviceSelector = document.getElementById('service-selector');
        if (serviceSelector) {
            // Add Django-specific options
            const djangoOptions = [
                { value: 'django', text: 'Django Application' },
                { value: 'database', text: 'MongoDB Database' }
            ];

            // Clear existing options except "All Services"
            const allServicesOption = serviceSelector.querySelector('option[value="all"]');
            serviceSelector.innerHTML = '';
            if (allServicesOption) {
                serviceSelector.appendChild(allServicesOption);
            }

            // Add Django-specific options
            djangoOptions.forEach(option => {
                const optionElement = document.createElement('option');
                optionElement.value = option.value;
                optionElement.textContent = option.text;
                serviceSelector.appendChild(optionElement);
            });
        }
    }

    setupAdminPanel() {
        // Setup Django admin panel functionality
        const adminButton = document.querySelector('a[href*="/admin/"]');
        if (adminButton) {
            adminButton.addEventListener('click', (e) => {
                // Add any admin panel specific logic here
                console.log('Opening Django admin panel...');
            });
        }
    }

    setupServiceMonitoring() {
        // Monitor Django stack services
        this.monitorDjangoService();
        this.monitorDatabaseService();
    }

    monitorDjangoService() {
        // Monitor Django web application
        console.log('Monitoring Django web application...');
        // Add specific monitoring logic here
    }

    monitorDatabaseService() {
        // Monitor MongoDB database service
        console.log('Monitoring MongoDB database service...');
        // Add specific monitoring logic here
    }

    openServiceLogs(serviceType) {
        const serviceSelector = document.getElementById('service-selector');
        if (serviceSelector) {
            serviceSelector.value = serviceType;
            // Trigger logs update
            const event = new Event('change');
            serviceSelector.dispatchEvent(event);
        }
    }

    // Django-specific utility methods
    getDjangoURL() {
        // Get Django URL from stack data
        const djangoUrlElement = document.querySelector('a[href*="django"]');
        return djangoUrlElement ? djangoUrlElement.href : null;
    }

    getAdminURL() {
        // Get Django admin URL
        const djangoUrl = this.getDjangoURL();
        return djangoUrl ? `${djangoUrl}/admin/` : null;
    }

    getDatabaseURI() {
        // Get database URI from stack data
        const databaseUriElement = document.querySelector('[title*="mongodb"]');
        return databaseUriElement ? databaseUriElement.title : null;
    }

    // Health check methods
    async checkDjangoHealth() {
        const djangoUrl = this.getDjangoURL();
        if (!djangoUrl) return false;

        try {
            const response = await fetch(djangoUrl, { method: 'HEAD' });
            return response.ok;
        } catch (error) {
            console.error('Django health check failed:', error);
            return false;
        }
    }

    async checkAdminHealth() {
        const adminUrl = this.getAdminURL();
        if (!adminUrl) return false;

        try {
            const response = await fetch(adminUrl, { method: 'HEAD' });
            return response.ok;
        } catch (error) {
            console.error('Django admin health check failed:', error);
            return false;
        }
    }

    async checkDatabaseHealth() {
        // Database health check would typically be done through Django
        // This is a placeholder for database-specific health checks
        console.log('Checking MongoDB database health...');
        return true;
    }

    // Update service status indicators
    updateServiceStatus(serviceType, isHealthy) {
        const statusElement = document.querySelector(`[data-service="${serviceType}"] .status-indicator`);
        if (statusElement) {
            if (isHealthy) {
                statusElement.className = 'status-indicator bg-green-500';
                statusElement.textContent = 'Healthy';
            } else {
                statusElement.className = 'status-indicator bg-red-500';
                statusElement.textContent = 'Unhealthy';
            }
        }
    }

    // Django-specific management commands
    async runDjangoCommand(command) {
        console.log(`Running Django command: ${command}`);
        // Add Django management command execution logic here
    }

    async collectStatic() {
        console.log('Running Django collectstatic...');
        return this.runDjangoCommand('collectstatic --noinput');
    }

    async runMigrations() {
        console.log('Running Django migrations...');
        return this.runDjangoCommand('migrate');
    }

    async createSuperuser() {
        console.log('Creating Django superuser...');
        // This would typically open a modal or redirect to a form
        return this.runDjangoCommand('createsuperuser');
    }

    // Django-specific deployment methods
    async redeployDjango() {
        console.log('Redeploying Django application...');
        // Add redeployment logic here
    }

    async restartDatabase() {
        console.log('Restarting MongoDB database...');
        // Add database restart logic here
    }

    // Django settings management
    async updateDjangoSettings(settings) {
        console.log('Updating Django settings...', settings);
        // Add settings update logic here
    }

    async getDjangoSettings() {
        console.log('Getting Django settings...');
        // Add settings retrieval logic here
    }

    // Django app management
    async listDjangoApps() {
        console.log('Listing Django apps...');
        // Add app listing logic here
    }

    async installDjangoApp(appName) {
        console.log(`Installing Django app: ${appName}`);
        // Add app installation logic here
    }

    // Django model management
    async listDjangoModels() {
        console.log('Listing Django models...');
        // Add model listing logic here
    }

    async createDjangoModel(modelDefinition) {
        console.log('Creating Django model...', modelDefinition);
        // Add model creation logic here
    }
}

// Initialize Django dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Check if this is a Django stack dashboard
    const dashboard = document.getElementById('dashboard');
    if (dashboard && dashboard.dataset.stackType === 'django') {
        new DjangoDashboard();
    }
});

// Export for potential use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DjangoDashboard;
} 