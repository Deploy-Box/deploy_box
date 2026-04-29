/**
 * Custom Stack Dashboard
 *
 * Dynamically renders resource cards from the API, supports adding/removing
 * resources, and triggers IaC deployment.
 */
(function () {
    const dashboard = document.getElementById("dashboard");
    if (!dashboard || dashboard.dataset.stackType !== "custom") return;

    const stackId = dashboard.dataset.stackId;

    // ── Category metadata ──────────────────────────────────────────────
    const CATEGORY_ICONS = {
        Compute:        { emoji: "⚡", color: "emerald" },
        Storage:        { emoji: "💾", color: "blue" },
        Networking:     { emoji: "🌐", color: "violet" },
        Database:       { emoji: "🗄️", color: "amber" },
        Security:       { emoji: "🔒", color: "red" },
        Monitoring:     { emoji: "📊", color: "cyan" },
        Authentication: { emoji: "🔐", color: "orange" },
        Infrastructure: { emoji: "☁️", color: "slate" },
        Other:          { emoji: "📦", color: "gray" },
    };

    const CATALOG_COLORS = {
        Compute:        { bg: "bg-emerald-50", border: "border-emerald-200", hover: "hover:border-emerald-400 hover:bg-emerald-100", text: "text-emerald-700", btn: "bg-emerald-500 hover:bg-emerald-600" },
        Storage:        { bg: "bg-blue-50",    border: "border-blue-200",    hover: "hover:border-blue-400 hover:bg-blue-100",       text: "text-blue-700",    btn: "bg-blue-500 hover:bg-blue-600" },
        Networking:     { bg: "bg-violet-50",  border: "border-violet-200",  hover: "hover:border-violet-400 hover:bg-violet-100",   text: "text-violet-700",  btn: "bg-violet-500 hover:bg-violet-600" },
        Database:       { bg: "bg-amber-50",   border: "border-amber-200",   hover: "hover:border-amber-400 hover:bg-amber-100",     text: "text-amber-700",   btn: "bg-amber-500 hover:bg-amber-600" },
        Security:       { bg: "bg-red-50",     border: "border-red-200",     hover: "hover:border-red-400 hover:bg-red-100",         text: "text-red-700",     btn: "bg-red-500 hover:bg-red-600" },
        Monitoring:     { bg: "bg-cyan-50",    border: "border-cyan-200",    hover: "hover:border-cyan-400 hover:bg-cyan-100",       text: "text-cyan-700",    btn: "bg-cyan-500 hover:bg-cyan-600" },
        Authentication: { bg: "bg-orange-50",  border: "border-orange-200",  hover: "hover:border-orange-400 hover:bg-orange-100",   text: "text-orange-700",  btn: "bg-orange-500 hover:bg-orange-600" },
        Infrastructure: { bg: "bg-slate-50",   border: "border-slate-200",   hover: "hover:border-slate-400 hover:bg-slate-100",     text: "text-slate-700",   btn: "bg-slate-500 hover:bg-slate-600" },
        Other:          { bg: "bg-gray-50",    border: "border-gray-200",    hover: "hover:border-gray-400 hover:bg-gray-100",       text: "text-gray-700",    btn: "bg-gray-500 hover:bg-gray-600" },
    };

    // ── State ──────────────────────────────────────────────────────────
    let availableTypes = [];
    let currentResources = [];
    let pendingChanges = 0;

    // ── Helpers ────────────────────────────────────────────────────────
    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(";").shift();
    }

    async function apiCall(url, method = "GET", body = null) {
        const headers = { "Content-Type": "application/json" };
        const csrftoken = getCookie("csrftoken");
        if (csrftoken) headers["X-CSRFToken"] = csrftoken;

        const opts = { method, headers };
        if (body) opts.body = JSON.stringify(body);

        const resp = await fetch(url, opts);
        if (!resp.ok) {
            const text = await resp.text().catch(() => resp.statusText);
            throw new Error(text || `HTTP ${resp.status}`);
        }
        return resp.json();
    }

    // ── Deploy bar ─────────────────────────────────────────────────────
    const deployBar = document.getElementById("deploy-bar");
    const pendingCountEl = document.getElementById("pending-count");

    function showDeployBar() {
        pendingChanges++;
        pendingCountEl.textContent = pendingChanges;
        deployBar.classList.remove("translate-y-full");
        deployBar.classList.add("translate-y-0");
    }

    function hideDeployBar() {
        pendingChanges = 0;
        pendingCountEl.textContent = "0";
        deployBar.classList.add("translate-y-full");
        deployBar.classList.remove("translate-y-0");
    }

    // ── Catalog rendering ──────────────────────────────────────────────
    async function loadCatalog() {
        const container = document.getElementById("resource-catalog");
        try {
            availableTypes = await apiCall(`/api/v1/stacks/available-resource-types/`);
            renderCatalog(availableTypes);
            populateCategoryFilter(availableTypes);
        } catch (err) {
            container.innerHTML = `
                <div class="col-span-full text-center py-8 text-red-400">
                    Failed to load resource catalog: ${err.message}
                </div>`;
        }
    }

    function renderCatalog(types) {
        const container = document.getElementById("resource-catalog");
        if (!types.length) {
            container.innerHTML = `<div class="col-span-full text-center py-8 text-gray-400">No resource types available</div>`;
            return;
        }

        container.innerHTML = types.map(t => {
            const cat = t.category || "Other";
            const c = CATALOG_COLORS[cat] || CATALOG_COLORS.Other;
            const icon = CATEGORY_ICONS[cat] || CATEGORY_ICONS.Other;
            return `
                <div class="catalog-card ${c.bg} ${c.border} ${c.hover} border rounded-lg p-4 transition-all duration-200 cursor-pointer group"
                     data-resource-type="${t.resource_type}" data-category="${cat}">
                    <div class="flex items-start justify-between">
                        <div class="flex items-center">
                            <span class="text-xl mr-2">${icon.emoji}</span>
                            <div>
                                <h3 class="text-sm font-semibold ${c.text}">${t.display_name}</h3>
                                <p class="text-xs text-gray-400 mt-0.5">${cat}</p>
                            </div>
                        </div>
                        <button class="add-resource-btn opacity-0 group-hover:opacity-100 ${c.btn} text-white text-xs px-2.5 py-1 rounded-md transition-all duration-200 flex items-center"
                                data-resource-type="${t.resource_type}">
                            <svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
                            </svg>
                            Add
                        </button>
                    </div>
                </div>`;
        }).join("");

        // Attach event listeners
        container.querySelectorAll(".add-resource-btn").forEach(btn => {
            btn.addEventListener("click", e => {
                e.stopPropagation();
                addResource(btn.dataset.resourceType);
            });
        });

        container.querySelectorAll(".catalog-card").forEach(card => {
            card.addEventListener("click", () => {
                addResource(card.dataset.resourceType);
            });
        });
    }

    function populateCategoryFilter(types) {
        const filter = document.getElementById("category-filter");
        const categories = [...new Set(types.map(t => t.category))].sort();
        categories.forEach(cat => {
            const opt = document.createElement("option");
            opt.value = cat;
            opt.textContent = cat;
            filter.appendChild(opt);
        });

        filter.addEventListener("change", () => {
            const val = filter.value;
            document.querySelectorAll(".catalog-card").forEach(card => {
                card.style.display = val === "all" || card.dataset.category === val ? "" : "none";
            });
        });
    }

    // ── Resource cards ─────────────────────────────────────────────────
    function loadExistingResources() {
        const raw = document.getElementById("stack-resources-data");
        if (raw) {
            try {
                currentResources = JSON.parse(raw.textContent);
            } catch { currentResources = []; }
        }
        renderResourceCards();
    }

    function renderResourceCards() {
        const container = document.getElementById("resource-cards");
        const empty = document.getElementById("empty-resources");
        const countEl = document.getElementById("resource-count");
        countEl.textContent = `(${currentResources.length})`;

        if (!currentResources.length) {
            empty.classList.remove("hidden");
            container.innerHTML = "";
            return;
        }

        empty.classList.add("hidden");
        container.innerHTML = currentResources.map(r => buildResourceCard(r)).join("");

        // Attach remove listeners
        container.querySelectorAll(".remove-resource-btn").forEach(btn => {
            btn.addEventListener("click", () => removeResource(btn.dataset.resourceId));
        });
    }

    function buildResourceCard(resource) {
        const typeName = resource.name || "Unknown";
        // Match resource type from the catalog for display name / category
        const typeKey = findTypeKeyFromId(resource.id);
        const typeInfo = availableTypes.find(t => t.resource_type === typeKey) || {};
        const cat = typeInfo.category || "Other";
        const displayName = typeInfo.display_name || typeName;
        const c = CATALOG_COLORS[cat] || CATALOG_COLORS.Other;
        const icon = CATEGORY_ICONS[cat] || CATEGORY_ICONS.Other;

        // Build key-value fields from the resource data, excluding internal fields
        const skipFields = new Set(["id", "stack", "created_at", "updated_at", "index", "type"]);
        const fields = Object.entries(resource)
            .filter(([k, v]) => !skipFields.has(k) && v !== null && v !== "" && typeof v !== "object")
            .slice(0, 6); // Show up to 6 fields

        const fieldRows = fields.map(([k, v]) => {
            const label = k.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
            const displayVal = typeof v === "string" && v.length > 40 ? v.substring(0, 37) + "…" : v;
            return `
                <div class="flex justify-between items-center py-1.5 border-b border-gray-100 last:border-0">
                    <span class="text-xs text-gray-500 truncate mr-2">${label}</span>
                    <span class="text-xs font-mono ${c.text} truncate max-w-[200px]" title="${v}">${displayVal}</span>
                </div>`;
        }).join("");

        return `
            <div class="resource-card ${c.bg} border ${c.border} rounded-lg p-4 transition-all duration-200 hover:shadow-md" data-resource-id="${resource.id}">
                <div class="flex items-center justify-between mb-3">
                    <div class="flex items-center">
                        <span class="text-lg mr-2">${icon.emoji}</span>
                        <div>
                            <h3 class="text-sm font-semibold ${c.text}">${displayName}</h3>
                            <p class="text-xs text-gray-400">${cat} · ${resource.id}</p>
                        </div>
                    </div>
                    <button class="remove-resource-btn p-1.5 text-red-400 hover:text-red-600 hover:bg-red-50 rounded-md transition"
                            data-resource-id="${resource.id}" title="Remove resource">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                        </svg>
                    </button>
                </div>
                <div class="space-y-0">${fieldRows || '<p class="text-xs text-gray-400 italic">No configuration yet</p>'}</div>
            </div>`;
    }

    /** Map resource prefix ID back to RESOURCE_MANAGER_MAPPING key. */
    const PREFIX_TO_TYPE = {
        res000: "AZURERM_RESOURCE_GROUP",
        res002: "AZURERM_STORAGE_ACCOUNT",
        res003: "AZURERM_STORAGE_CONTAINER",
        res005: "AZURERM_DNS_CNAME_RECORD",
        res006: "AZURERM_CONTAINER_APP_ENVIRONMENT",
        res007: "AZURERM_CONTAINER_APP",
        res008: "DEPLOYBOXRM_WORKOS_INTEGRATION",
        res009: "THENILERM_DATABASE",
        res00A: "AZURERM_STORAGE_ACCOUNT_STATIC_WEBSITE",
        res00B: "DEPLOYBOXRM_EDGE",
        res00C: "AZURERM_LOG_ANALYTICS_WORKSPACE",
        res00D: "AZURERM_KEY_VAULT",
        res00E: "DEPLOYBOXRM_POSTGRES_DATABASE",
        res00F: "AZURERM_PUBLIC_IP",
        res010: "AZURERM_NETWORK_SECURITY_GROUP",
        res011: "AZURERM_VIRTUAL_NETWORK",
        res012: "AZURERM_NETWORK_INTERFACE",
        res013: "AZURERM_LINUX_VIRTUAL_MACHINE",
    };

    function findTypeKeyFromId(resourceId) {
        const prefix = (resourceId || "").split("_")[0];
        return PREFIX_TO_TYPE[prefix] || "";
    }

    // ── Add / Remove actions ───────────────────────────────────────────
    async function addResource(resourceType) {
        const card = document.querySelector(`.catalog-card[data-resource-type="${resourceType}"]`);
        const btn = card ? card.querySelector(".add-resource-btn") : null;

        if (btn) {
            btn.disabled = true;
            btn.innerHTML = `<svg class="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>`;
        }

        try {
            const result = await apiCall(`/api/v1/stacks/${stackId}/add-resource/`, "POST", {
                resource_type: resourceType,
            });
            currentResources.push(result);
            renderResourceCards();
            showDeployBar();
            showToast(`Added ${resourceType.replace(/_/g, " ").toLowerCase()}`, "success");
        } catch (err) {
            showToast(`Failed to add resource: ${err.message}`, "error");
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = `<svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg> Add`;
            }
        }
    }

    async function removeResource(resourceId) {
        if (!confirm("Remove this resource from your stack?")) return;

        const card = document.querySelector(`.resource-card[data-resource-id="${resourceId}"]`);
        if (card) card.style.opacity = "0.5";

        try {
            await apiCall(`/api/v1/stacks/${stackId}/remove-resource/`, "POST", {
                resource_id: resourceId,
            });
            currentResources = currentResources.filter(r => r.id !== resourceId);
            renderResourceCards();
            showDeployBar();
            showToast("Resource removed", "success");
        } catch (err) {
            if (card) card.style.opacity = "1";
            showToast(`Failed to remove resource: ${err.message}`, "error");
        }
    }

    // ── Deploy ─────────────────────────────────────────────────────────
    document.getElementById("deploy-btn").addEventListener("click", async () => {
        const btn = document.getElementById("deploy-btn");
        const spinner = btn.querySelector(".deploy-spinner");
        btn.disabled = true;
        spinner.classList.remove("hidden");

        try {
            await apiCall(`/api/v1/stacks/${stackId}/trigger-iac-update/`, "POST");
            hideDeployBar();
            showToast("Deployment triggered — your infrastructure is being provisioned", "success");
        } catch (err) {
            showToast(`Deploy failed: ${err.message}`, "error");
        } finally {
            btn.disabled = false;
            spinner.classList.add("hidden");
        }
    });

    // ── Delete stack ───────────────────────────────────────────────────
    const deleteBtn = document.getElementById("delete-stack-btn");
    if (deleteBtn) {
        deleteBtn.addEventListener("click", async () => {
            if (!confirm("Are you sure you want to delete this stack? This action cannot be undone.")) return;
            try {
                await apiCall(`/api/v1/stacks/${stackId}/`, "DELETE");
                const meta = document.getElementById("metadata");
                const orgId = meta.dataset.organizationId;
                const projId = meta.dataset.projectId;
                window.location.href = `/dashboard/organizations/${orgId}/projects/${projId}/`;
            } catch (err) {
                showToast(`Delete failed: ${err.message}`, "error");
            }
        });
    }

    // ── Bootstrap ──────────────────────────────────────────────────────
    loadCatalog();
    loadExistingResources();
})();
