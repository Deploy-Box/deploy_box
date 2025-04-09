console.log('Dashboard.html loaded');
document.addEventListener('DOMContentLoaded', function () {
    console.log('DOMContentLoaded');
    // Load organizations and projects when the page loads
    loadOrganizations();
    loadProjects();

    // Add event listeners
    document.getElementById('createOrgBtn').addEventListener('click', createOrganization);
    document.getElementById('createProjectBtn').addEventListener('click', createProject);
});

console.log('DOMContentLoaded');
async function loadOrganizations() {
    try {
        const response = await fetch('/api/accounts/organizations/');
        const data = await response.json();

        console.log(data);

        const organizationsList = document.getElementById('organizationsList');
        organizationsList.innerHTML = '';

        data.organizations.forEach(org => {
            const orgElement = createOrganizationElement(org);
            organizationsList.appendChild(orgElement);
        });
    } catch (error) {
        console.error('Error loading organizations:', error);
    }
}

async function loadProjects() {
    try {
        const response = await fetch('/api/accounts/projects/');
        const data = await response.json();

        console.log(data);

        const projectsList = document.getElementById('projectsList');
        projectsList.innerHTML = '';

        data.projects.forEach(project => {
            const projectElement = createProjectElement(project);
            projectsList.appendChild(projectElement);
        });
    } catch (error) {
        console.error('Error loading projects:', error);
    }
}

function createProjectElement(project) {
    const div = document.createElement('div');
    div.className = 'bg-zinc-50 p-4 rounded-lg';
    div.innerHTML = `
    <div class="flex justify-between items-center">
        <div>
            <h3 class="text-lg font-semibold text-zinc-900">${project.name}</h3>
            <p class="text-sm text-zinc-500">Organization: ${project.organization}</p>
            <p class="text-sm text-zinc-500">Created: ${new Date(project.created_at).toLocaleDateString()}</p>
        </div>
        <div class="space-x-2">
            <button class="text-emerald-400 hover:text-emerald-500" onclick="editProject(${project.id})">
                Edit
            </button>
            <button class="text-red-500 hover:text-red-600" onclick="deleteProject(${project.id})">
                Delete
            </button>
        </div>
    </div>
`;
    return div;
}

function createOrganizationElement(org) {
    const div = document.createElement('div');
    div.className = 'bg-zinc-50 p-4 rounded-lg';
    div.innerHTML = `
    <div class="flex justify-between items-center">
        <div>
            <h3 class="text-lg font-semibold text-zinc-900">${org.name}</h3>
            <p class="text-sm text-zinc-500">Created: ${new Date(org.created_at).toLocaleDateString()}</p>
        </div>
        <div class="space-x-2">
            <button class="text-emerald-400 hover:text-emerald-500" onclick="editOrganization(${org.id})">
                Edit
            </button>
            <button class="text-red-500 hover:text-red-600" onclick="deleteOrganization(${org.id})">
                Delete
            </button>
        </div>
    </div>
`;
    return div;
}

async function createOrganization() {
    // TODO: Implement organization creation
    console.log('Create organization clicked');
}

async function editOrganization(orgId) {
    // TODO: Implement organization editing
    console.log('Edit organization:', orgId);
}

async function deleteOrganization(orgId) {
    // TODO: Implement organization deletion
    console.log('Delete organization:', orgId);
}

async function createProject() {
    // TODO: Implement project creation
    console.log('Create project clicked');
}