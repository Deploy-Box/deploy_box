// MERN Stack Dashboard JavaScript
// Extends the base stack dashboard functionality with MERN-specific features

// Import base functionality
// This assumes the base stack_dashboard.js is loaded first

// MERN-specific service monitoring
class MERNDashboard {
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

        this.setupMERNSpecificFeatures();
        this.setupServiceMonitoring();
    }

    setupMERNSpecificFeatures() {
        // MERN-specific UI enhancements
        this.setupServiceCards();
        this.setupServiceSelector();
    }

    setupServiceCards() {
        // Add click handlers to service cards
        const frontendCard = document.querySelector('.bg-gradient-to-br.from-blue-50');
        const backendCard = document.querySelector('.bg-gradient-to-br.from-green-50');
        const databaseCard = document.querySelector('.bg-gradient-to-br.from-emerald-50');

        if (frontendCard) {
            frontendCard.addEventListener('click', () => this.openServiceLogs('frontend'));
        }
        if (backendCard) {
            backendCard.addEventListener('click', () => this.openServiceLogs('backend'));
        }
        if (databaseCard) {
            databaseCard.addEventListener('click', () => this.openServiceLogs('database'));
        }
    }

    setupServiceSelector() {
        const serviceSelector = document.getElementById('service-selector');
        if (serviceSelector) {
            // Add MERN-specific options
            const mernOptions = [
                { value: 'frontend', text: 'React Frontend' },
                { value: 'backend', text: 'Express.js Backend' },
                { value: 'database', text: 'MongoDB Database' }
            ];

            // Clear existing options except "All Services"
            const allServicesOption = serviceSelector.querySelector('option[value="all"]');
            serviceSelector.innerHTML = '';
            if (allServicesOption) {
                serviceSelector.appendChild(allServicesOption);
            }

            // Add MERN-specific options
            mernOptions.forEach(option => {
                const optionElement = document.createElement('option');
                optionElement.value = option.value;
                optionElement.textContent = option.text;
                serviceSelector.appendChild(optionElement);
            });
        }
    }

    setupServiceMonitoring() {
        // Monitor MERN stack services
        this.monitorFrontendService();
        this.monitorBackendService();
        this.monitorDatabaseService();
    }

    monitorFrontendService() {
        // Monitor React frontend service
        console.log('Monitoring React frontend service...');
        // Add specific monitoring logic here
    }

    monitorBackendService() {
        // Monitor Express.js backend service
        console.log('Monitoring Express.js backend service...');
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

    // MERN-specific utility methods
    getFrontendURL() {
        // Get frontend URL from stack data
        const frontendUrlElement = document.querySelector('a[href*="frontend"]');
        return frontendUrlElement ? frontendUrlElement.href : null;
    }

    getBackendURL() {
        // Get backend URL from stack data
        const backendUrlElement = document.querySelector('a[href*="backend"]');
        return backendUrlElement ? backendUrlElement.href : null;
    }

    getDatabaseURI() {
        // Get database URI from stack data
        const databaseUriElement = document.querySelector('[title*="mongodb"]');
        return databaseUriElement ? databaseUriElement.title : null;
    }

    // Health check methods
    async checkFrontendHealth() {
        const frontendUrl = this.getFrontendURL();
        if (!frontendUrl) return false;

        try {
            const response = await fetch(frontendUrl, { method: 'HEAD' });
            return response.ok;
        } catch (error) {
            console.error('Frontend health check failed:', error);
            return false;
        }
    }

    async checkBackendHealth() {
        const backendUrl = this.getBackendURL();
        if (!backendUrl) return false;

        try {
            const response = await fetch(`${backendUrl}/health`, { method: 'GET' });
            return response.ok;
        } catch (error) {
            console.error('Backend health check failed:', error);
            return false;
        }
    }

    async checkDatabaseHealth() {
        // Database health check would typically be done through the backend
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

    // MERN-specific deployment methods
    async redeployFrontend() {
        console.log('Redeploying React frontend...');
        // Add redeployment logic here
    }

    async redeployBackend() {
        console.log('Redeploying Express.js backend...');
        // Add redeployment logic here
    }

    async restartDatabase() {
        console.log('Restarting MongoDB database...');
        // Add database restart logic here
    }
}

// Initialize MERN dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Check if this is a MERN stack dashboard
    const dashboard = document.getElementById('dashboard');
    if (dashboard && dashboard.dataset.stackType === 'mern') {
        new MERNDashboard();
    }
});

// Export for potential use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MERNDashboard;
} 