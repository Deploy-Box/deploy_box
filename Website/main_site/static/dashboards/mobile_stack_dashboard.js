// Mobile Stack Dashboard JavaScript
// Handles resource display, inline editing, and bulk-update via API

class MobileDashboard {
    constructor() {
        this.organizationId = null;
        this.projectId = null;
        this.stackId = null;
        this.resources = {}; // keyed by resource_type (name from model)
        this.pendingChanges = {}; // { resourceId: { field: newValue, ... } }
        this.originalValues = {}; // { "resourceType.field": originalValue }
        this.fqdn = null;
        this.init();
    }

    // ──────────────────────────────────────────────
    //  Initialization
    // ──────────────────────────────────────────────
    init() {
        const dashboard = document.getElementById("dashboard");
        if (dashboard) {
            this.organizationId = dashboard.dataset.organizationId;
            this.projectId = dashboard.dataset.projectId;
            this.stackId = dashboard.dataset.stackId;
            this.fqdn = dashboard.dataset.fqdn;
        }

        this.loadResourcesFromPage();
        this.populateFields();
        this.setupEditButtons();
        this.setupEnvVars();
        this.setupBuildEnvVars();
        this.setupInfraToggle();
        this.setupSaveBar();
        this.setupVisibilityToggles();
    }

    // ──────────────────────────────────────────────
    //  Load serialized resources from <script> tag
    // ──────────────────────────────────────────────
    loadResourcesFromPage() {
        const el = document.getElementById("stack-resources-data");
        if (!el) return;
        try {
            const resourceList = JSON.parse(el.textContent);
            // Index resources by their `name` field (e.g. "azurerm_container_app_0")
            // but also provide a lookup by resource_type stem
            for (const r of resourceList) {
                // The `name` field is like "azurerm_container_app_0"
                // Derive the resource type by stripping trailing _N
                const typeName = r.name ? r.name.replace(/_\d+$/, "") : null;
                if (typeName) {
                    this.resources[typeName] = r;
                }
            }
        } catch (e) {
            console.error("Failed to parse stack resources:", e);
        }
    }

    // ──────────────────────────────────────────────
    //  Populate all .resource-field inputs from data
    // ──────────────────────────────────────────────
    populateFields() {
        document.querySelectorAll(".resource-field").forEach((fieldEl) => {
            const resourceType = fieldEl.dataset.resourceType;
            const fieldName = fieldEl.dataset.field;
            const input = fieldEl.querySelector(".resource-input");
            if (!input || !resourceType || !fieldName) return;

            const resource = this.resources[resourceType];
            if (!resource) return;

            const value = resource[fieldName];
            input.value = value !== null && value !== undefined ? value : "";

            // Store original value for change detection
            this.originalValues[`${resourceType}.${fieldName}`] = input.value;
        });

        // Populate edge router links
        const edge = this.resources["deployboxrm_edge"];
        if (edge) {
            const frontendLink = document.getElementById("edge-frontend-link");
            const frontendText = document.getElementById("edge-frontend-text");
            if (frontendLink && edge.subdomain && edge.resolved_root_base_url) {
                frontendLink.href = 'https://' + edge.subdomain + '.' + this.fqdn;
            }
            if (frontendText && edge.subdomain && edge.resolved_root_base_url) {
                frontendText.value = frontendLink.href;
            }

            const apiLink = document.getElementById("edge-api-link");
            const apiText = document.getElementById("edge-api-text");
            if (apiLink && edge.subdomain && edge.resolved_api_base_url) {
                apiLink.href = 'https://' + edge.subdomain + '.' + this.fqdn + '/api/';
            }
            if (apiText && edge.subdomain && edge.resolved_api_base_url) {
                apiText.value = apiLink.href;
            }
        }

        // Update database status badge
        const db = this.resources["thenilerm_database"];
        if (db) {
            const statusText = document.querySelector(".db-status-text");
            if (statusText) {
                statusText.textContent = db.status || "Unknown";
            }
        }
    }

    // ──────────────────────────────────────────────
    //  Inline edit buttons
    // ──────────────────────────────────────────────
    setupEditButtons() {
        document.querySelectorAll(".edit-field-btn").forEach((btn) => {
            btn.addEventListener("click", (e) => {
                const fieldEl = btn.closest(".resource-field");
                const input = fieldEl.querySelector(".resource-input");
                if (!input) return;

                if (input.readOnly) {
                    // Enter edit mode
                    input.readOnly = false;
                    input.classList.add(
                        "ring-2",
                        "ring-emerald-400",
                        "border-emerald-400",
                    );
                    input.focus();
                    btn.innerHTML = `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>`;
                    btn.classList.remove("opacity-0");
                } else {
                    // Confirm edit
                    input.readOnly = true;
                    input.classList.remove(
                        "ring-2",
                        "ring-emerald-400",
                        "border-emerald-400",
                    );
                    btn.innerHTML = `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"/></svg>`;

                    // Track change
                    const resourceType = fieldEl.dataset.resourceType;
                    const fieldName = fieldEl.dataset.field;
                    const originalKey = `${resourceType}.${fieldName}`;
                    const newValue = input.value;

                    if (newValue !== this.originalValues[originalKey]) {
                        this.trackChange(resourceType, fieldName, newValue);
                    } else {
                        this.untrackChange(resourceType, fieldName);
                    }
                }
            });
        });

        // Also allow Enter key to confirm
        document.querySelectorAll(".resource-input").forEach((input) => {
            input.addEventListener("keydown", (e) => {
                if (e.key === "Enter" && !input.readOnly) {
                    const btn = input
                        .closest(".resource-field")
                        .querySelector(".edit-field-btn");
                    if (btn) btn.click();
                }
            });
        });
    }

    // ──────────────────────────────────────────────
    //  Environment Variables (container_app env)
    // ──────────────────────────────────────────────
    setupEnvVars() {
        const container = document.getElementById("container-app-env-vars");
        const addBtn = document.getElementById("add-env-var-btn");
        const addSecretBtn = document.getElementById("add-secret-var-btn");
        if (!container) return;

        const ca = this.resources["azurerm_container_app"];
        const envVars = ca ? ca.template_container_env || [] : [];

        // Store original env vars for comparison
        this.originalEnvVars = JSON.parse(JSON.stringify(envVars));

        envVars.forEach((env, idx) => {
            container.appendChild(
                this.createEnvVarRow(env.name, env.value, idx, false, env.is_secret || false),
            );
        });

        if (addBtn) {
            addBtn.addEventListener("click", () => {
                const idx = container.children.length;
                container.appendChild(this.createEnvVarRow("", "", idx, true, false));
                this.syncEnvVarsChange();
            });
        }

        if (addSecretBtn) {
            addSecretBtn.addEventListener("click", () => {
                const idx = container.children.length;
                container.appendChild(this.createEnvVarRow("", "", idx, true, true));
                this.syncEnvVarsChange();
            });
        }
    }

    createEnvVarRow(name, value, index, isNew = false, isSecret = false) {
        const row = document.createElement("div");
        row.className = "env-var-row flex items-center gap-2";
        row.dataset.index = index;
        row.dataset.isSecret = isSecret ? "true" : "false";

        const secretBtnClasses = isSecret
            ? "text-amber-500 hover:text-amber-700"
            : "text-slate-300 hover:text-amber-500";
        const secretTitle = isSecret ? "Secret (click to make plain)" : "Plain (click to make secret)";
        const valueType = isSecret ? "password" : "text";

        row.innerHTML = `
            <input type="text" class="env-name flex-[2] bg-white border border-slate-300 rounded-md px-2.5 py-1.5 text-xs font-mono text-slate-800 focus:ring-2 focus:ring-emerald-400 focus:border-emerald-400 transition" 
                   value="${this.escapeHtml(name)}" placeholder="KEY" ${isNew ? "" : "readonly"} />
            <span class="text-slate-400 text-xs">=</span>
            <input type="${valueType}" class="env-value flex-[3] bg-white border border-slate-300 rounded-md px-2.5 py-1.5 text-xs font-mono text-slate-800 focus:ring-2 focus:ring-emerald-400 focus:border-emerald-400 transition"
                   value="${this.escapeHtml(value)}" placeholder="value" ${isNew ? "" : "readonly"} />
            <button class="env-secret-btn p-1 ${secretBtnClasses} rounded transition" title="${secretTitle}">
                <svg class="w-3.5 h-3.5 lock-closed ${isSecret ? '' : 'hidden'}" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/></svg>
                <svg class="w-3.5 h-3.5 lock-open ${isSecret ? 'hidden' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 11V7a4 4 0 118 0m-4 8v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2z"/></svg>
            </button>
            <button class="env-edit-btn p-1 text-slate-400 hover:text-emerald-600 rounded transition" title="Edit">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"/></svg>
            </button>
            <button class="env-delete-btn p-1 text-slate-400 hover:text-red-500 rounded transition" title="Remove">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
            </button>
        `;

        const secretBtn = row.querySelector(".env-secret-btn");
        const editBtn = row.querySelector(".env-edit-btn");
        const deleteBtn = row.querySelector(".env-delete-btn");
        const nameInput = row.querySelector(".env-name");
        const valueInput = row.querySelector(".env-value");

        secretBtn.addEventListener("click", () => {
            const currentlySecret = row.dataset.isSecret === "true";
            const newIsSecret = !currentlySecret;
            row.dataset.isSecret = newIsSecret ? "true" : "false";

            const lockClosed = secretBtn.querySelector(".lock-closed");
            const lockOpen = secretBtn.querySelector(".lock-open");

            if (newIsSecret) {
                secretBtn.classList.remove("text-slate-300");
                secretBtn.classList.add("text-amber-500");
                secretBtn.title = "Secret (click to make plain)";
                lockClosed.classList.remove("hidden");
                lockOpen.classList.add("hidden");
                valueInput.type = "password";
            } else {
                secretBtn.classList.remove("text-amber-500");
                secretBtn.classList.add("text-slate-300");
                secretBtn.title = "Plain (click to make secret)";
                lockClosed.classList.add("hidden");
                lockOpen.classList.remove("hidden");
                valueInput.type = "text";
            }

            this.syncEnvVarsChange();
        });

        editBtn.addEventListener("click", () => {
            if (nameInput.readOnly) {
                nameInput.readOnly = false;
                valueInput.readOnly = false;
                nameInput.classList.add("ring-1", "ring-emerald-300");
                valueInput.classList.add("ring-1", "ring-emerald-300");
                nameInput.focus();
                editBtn.innerHTML = `<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>`;
            } else {
                nameInput.readOnly = true;
                valueInput.readOnly = true;
                nameInput.classList.remove("ring-1", "ring-emerald-300");
                valueInput.classList.remove("ring-1", "ring-emerald-300");
                editBtn.innerHTML = `<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"/></svg>`;
                this.syncEnvVarsChange();
            }
        });

        deleteBtn.addEventListener("click", () => {
            row.remove();
            this.syncEnvVarsChange();
        });

        return row;
    }

    syncEnvVarsChange() {
        const container = document.getElementById("container-app-env-vars");
        if (!container) return;

        const envVars = [];
        container.querySelectorAll(".env-var-row").forEach((row) => {
            const name = row.querySelector(".env-name").value.trim();
            const value = row.querySelector(".env-value").value.trim();
            const isSecret = row.dataset.isSecret === "true";
            if (name) {
                envVars.push({ name, value, is_secret: isSecret });
            }
        });

        // Compare with original
        const changed =
            JSON.stringify(envVars) !== JSON.stringify(this.originalEnvVars);
        if (changed) {
            this.trackChange(
                "azurerm_container_app",
                "template_container_env",
                envVars,
            );
        } else {
            this.untrackChange(
                "azurerm_container_app",
                "template_container_env",
            );
        }
    }

    // ──────────────────────────────────────────────
    //  Build Environment Variables (static website)
    // ──────────────────────────────────────────────
    setupBuildEnvVars() {
        const container = document.getElementById("build-env-vars");
        const addBtn = document.getElementById("add-build-env-var-btn");
        if (!container) return;

        const sw = this.resources["azurerm_storage_account_static_website"];
        const buildVars = sw ? sw.build_env_vars || {} : {};

        // Store original for comparison
        this.originalBuildEnvVars = JSON.parse(JSON.stringify(buildVars));

        let idx = 0;
        for (const [key, val] of Object.entries(buildVars)) {
            container.appendChild(this.createBuildEnvVarRow(key, String(val), idx));
            idx++;
        }

        if (addBtn) {
            addBtn.addEventListener("click", () => {
                const newIdx = container.children.length;
                container.appendChild(this.createBuildEnvVarRow("", "", newIdx, true));
                this.syncBuildEnvVarsChange();
            });
        }
    }

    createBuildEnvVarRow(name, value, index, isNew = false) {
        const row = document.createElement("div");
        row.className = "build-env-var-row flex items-center gap-2";
        row.dataset.index = index;

        row.innerHTML = `
            <input type="text" class="build-env-name flex-[2] bg-white border border-violet-300 rounded-md px-2.5 py-1.5 text-xs font-mono text-violet-800 focus:ring-2 focus:ring-violet-400 focus:border-violet-400 transition"
                   value="${this.escapeHtml(name)}" placeholder="REACT_APP_KEY" ${isNew ? "" : "readonly"} />
            <span class="text-violet-400 text-xs">=</span>
            <input type="text" class="build-env-value flex-[3] bg-white border border-violet-300 rounded-md px-2.5 py-1.5 text-xs font-mono text-violet-800 focus:ring-2 focus:ring-violet-400 focus:border-violet-400 transition"
                   value="${this.escapeHtml(value)}" placeholder="value" ${isNew ? "" : "readonly"} />
            <button class="build-env-edit-btn p-1 text-violet-400 hover:text-violet-600 rounded transition" title="Edit">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"/></svg>
            </button>
            <button class="build-env-delete-btn p-1 text-violet-400 hover:text-red-500 rounded transition" title="Remove">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
            </button>
        `;

        const editBtn = row.querySelector(".build-env-edit-btn");
        const deleteBtn = row.querySelector(".build-env-delete-btn");
        const nameInput = row.querySelector(".build-env-name");
        const valueInput = row.querySelector(".build-env-value");

        editBtn.addEventListener("click", () => {
            if (nameInput.readOnly) {
                nameInput.readOnly = false;
                valueInput.readOnly = false;
                nameInput.classList.add("ring-1", "ring-violet-300");
                valueInput.classList.add("ring-1", "ring-violet-300");
                nameInput.focus();
                editBtn.innerHTML = `<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>`;
            } else {
                nameInput.readOnly = true;
                valueInput.readOnly = true;
                nameInput.classList.remove("ring-1", "ring-violet-300");
                valueInput.classList.remove("ring-1", "ring-violet-300");
                editBtn.innerHTML = `<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"/></svg>`;
                this.syncBuildEnvVarsChange();
            }
        });

        deleteBtn.addEventListener("click", () => {
            row.remove();
            this.syncBuildEnvVarsChange();
        });

        return row;
    }

    syncBuildEnvVarsChange() {
        const container = document.getElementById("build-env-vars");
        if (!container) return;

        const buildVars = {};
        container.querySelectorAll(".build-env-var-row").forEach((row) => {
            const name = row.querySelector(".build-env-name").value.trim();
            const value = row.querySelector(".build-env-value").value.trim();
            if (name) {
                buildVars[name] = value;
            }
        });

        // Compare with original
        const changed =
            JSON.stringify(buildVars) !== JSON.stringify(this.originalBuildEnvVars);
        if (changed) {
            this.trackChange(
                "azurerm_storage_account_static_website",
                "build_env_vars",
                buildVars,
            );
        } else {
            this.untrackChange(
                "azurerm_storage_account_static_website",
                "build_env_vars",
            );
        }
    }

    // ──────────────────────────────────────────────
    //  Infrastructure toggle
    // ──────────────────────────────────────────────
    setupInfraToggle() {
        const toggle = document.getElementById("infra-details-toggle");
        const content = document.getElementById("infra-details-content");
        const chevron = document.getElementById("infra-chevron");
        if (toggle && content) {
            toggle.addEventListener("click", () => {
                content.classList.toggle("hidden");
                if (chevron) chevron.classList.toggle("rotate-180");
            });
        }
    }

    // ──────────────────────────────────────────────
    //  Visibility toggles for secret fields
    // ──────────────────────────────────────────────
    setupVisibilityToggles() {
        document.querySelectorAll(".toggle-visibility-btn").forEach((btn) => {
            btn.addEventListener("click", () => {
                const fieldEl = btn.closest(".resource-field");
                const input = fieldEl.querySelector(".resource-input");
                const eyeOpen = btn.querySelector(".eye-open");
                const eyeClosed = btn.querySelector(".eye-closed");
                if (!input) return;

                if (input.type === "password") {
                    input.type = "text";
                    eyeOpen?.classList.add("hidden");
                    eyeClosed?.classList.remove("hidden");
                } else {
                    input.type = "password";
                    eyeOpen?.classList.remove("hidden");
                    eyeClosed?.classList.add("hidden");
                }
            });
        });
    }

    // ──────────────────────────────────────────────
    //  Change tracking & save bar
    // ──────────────────────────────────────────────
    trackChange(resourceType, fieldName, newValue) {
        const resource = this.resources[resourceType];
        if (!resource) return;

        const resourceId = resource.id;
        if (!this.pendingChanges[resourceId]) {
            this.pendingChanges[resourceId] = { id: resourceId };
        }
        this.pendingChanges[resourceId][fieldName] = newValue;
        this.updateSaveBar();
    }

    untrackChange(resourceType, fieldName) {
        const resource = this.resources[resourceType];
        if (!resource) return;

        const resourceId = resource.id;
        if (this.pendingChanges[resourceId]) {
            delete this.pendingChanges[resourceId][fieldName];
            // If only 'id' remains, remove the entry
            if (Object.keys(this.pendingChanges[resourceId]).length <= 1) {
                delete this.pendingChanges[resourceId];
            }
        }
        this.updateSaveBar();
    }

    updateSaveBar() {
        const saveBar = document.getElementById("save-bar");
        const countEl = document.getElementById("changes-count");
        const count = Object.keys(this.pendingChanges).length;

        if (countEl) countEl.textContent = count;

        if (saveBar) {
            if (count > 0) {
                saveBar.classList.remove("translate-y-full");
            } else {
                saveBar.classList.add("translate-y-full");
            }
        }
    }

    setupSaveBar() {
        const saveBtn = document.getElementById("save-changes-btn");
        const discardBtn = document.getElementById("discard-changes-btn");

        if (saveBtn) {
            saveBtn.addEventListener("click", () => this.saveChanges());
        }
        if (discardBtn) {
            discardBtn.addEventListener("click", () => this.discardChanges());
        }
    }

    // ──────────────────────────────────────────────
    //  Save via bulk-update-resources API
    // ──────────────────────────────────────────────
    async saveChanges() {
        if (Object.keys(this.pendingChanges).length === 0) {
            showToast("No changes to save.", "info");
            return;
        }

        const stackId = this.stackId;
        if (!stackId) {
            showToast(
                "Stack ID is missing. Cannot save changes.",
                "error",
            );
            return;
        }

        try {
            const response = await fetch(
                `/api/v1/stacks/${stackId}/update-resources/`,
                {
                    method: "PATCH",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": this.getCsrfToken(),
                    },
                    body: JSON.stringify({
                        resources: Object.values(this.pendingChanges),
                    }),
                },
            );

            if (response.ok) {
                showToast("Changes saved successfully.", "success");

                // Update original values so change tracking resets
                for (const change of Object.values(this.pendingChanges)) {
                    const resourceId = change.id;
                    const resourceType = Object.keys(this.resources).find(
                        (key) => this.resources[key].id === resourceId,
                    );
                    if (resourceType) {
                        for (const [field, value] of Object.entries(change)) {
                            if (field === "id") continue;
                            this.resources[resourceType][field] = value;
                            this.originalValues[`${resourceType}.${field}`] = 
                                typeof value === "string" ? value : JSON.stringify(value);
                        }
                    }
                }

                // Update original env vars if they were changed
                const ca = this.resources["azurerm_container_app"];
                if (ca && ca.template_container_env) {
                    this.originalEnvVars = JSON.parse(
                        JSON.stringify(ca.template_container_env),
                    );
                }

                // Update original build env vars if they were changed
                const sw = this.resources["azurerm_storage_account_static_website"];
                if (sw && sw.build_env_vars) {
                    this.originalBuildEnvVars = JSON.parse(
                        JSON.stringify(sw.build_env_vars),
                    );
                }

                this.pendingChanges = {};
                this.updateSaveBar();

                // Trigger IAC update
                const iacResponse = await fetch(
                    `/api/v1/stacks/${stackId}/trigger-iac-update/`,
                    {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                            "X-CSRFToken": this.getCsrfToken(),
                        },
                        credentials: "include",
                    },
                );

                if (iacResponse.ok) {
                    showToast(
                        "IAC update triggered successfully.",
                        "success",
                    );
                } else {
                    showToast("Failed to trigger IAC update.", "error");
                }
            } else {
                const errorData = await response.json();
                showToast(
                    `Failed to save changes: ${errorData.error || "Unknown error"}`,
                    "error",
                );
            }
        } catch (error) {
            showToast(`Error saving changes: ${error.message}`, "error");
        }
    }

    discardChanges() {
        this.pendingChanges = {};
        this.populateFields();

        // Reset env vars
        const container = document.getElementById("container-app-env-vars");
        if (container) {
            container.innerHTML = "";
            this.originalEnvVars.forEach((env, idx) => {
                container.appendChild(
                    this.createEnvVarRow(env.name, env.value, idx, false, env.is_secret || false),
                );
            });
        }

        // Reset build env vars
        const buildContainer = document.getElementById("build-env-vars");
        if (buildContainer) {
            buildContainer.innerHTML = "";
            let idx = 0;
            for (const [key, val] of Object.entries(this.originalBuildEnvVars || {})) {
                buildContainer.appendChild(this.createBuildEnvVarRow(key, String(val), idx));
                idx++;
            }
        }

        // Reset all inputs to readonly
        document.querySelectorAll(".resource-input").forEach((input) => {
            if (!input.disabled) {
                input.readOnly = true;
                input.classList.remove(
                    "ring-2",
                    "ring-emerald-400",
                    "border-emerald-400",
                );
            }
        });

        // Reset edit buttons
        document.querySelectorAll(".edit-field-btn").forEach((btn) => {
            btn.innerHTML = `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"/></svg>`;
        });

        this.updateSaveBar();
    }

    // ──────────────────────────────────────────────
    //  Utilities
    // ──────────────────────────────────────────────
    getCsrfToken() {
        const cookie = document.cookie
            .split("; ")
            .find((c) => c.startsWith("csrftoken="));
        return cookie ? cookie.split("=")[1] : "";
    }

    escapeHtml(str) {
        if (!str) return "";
        const div = document.createElement("div");
        div.textContent = str;
        return div.innerHTML;
    }
}

// ──────────────────────────────────────────────
//  Bootstrap
// ──────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", function () {
    const dashboard = document.getElementById("dashboard");
    if (dashboard && dashboard.dataset.stackType === "mobile") {
        new MobileDashboard();
    }
});

if (typeof module !== "undefined" && module.exports) {
    module.exports = MobileDashboard;
}
