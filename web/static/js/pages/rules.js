/* Rules management page */
const RulesPage = {
    async render() {
        const content = document.getElementById('content');
        content.innerHTML = `
            <div class="page-header">
                <h2>Alert Rules</h2>
                <button class="btn btn-primary" onclick="RulesPage.showAddModal()">+ Add Rule</button>
            </div>
            <div id="rules-list">
                <div class="loading">Loading...</div>
            </div>
        `;
        await this.refresh();
    },

    async refresh() {
        try {
            const rules = await API.get('/api/rules');
            this._renderRules(rules);
        } catch (err) {
            Toast.error('Failed to load rules: ' + err.message);
        }
    },

    _renderRules(rules) {
        if (!rules || rules.length === 0) {
            document.getElementById('rules-list').innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">&#9889;</div>
                    <h3>No alert rules</h3>
                    <p>Create rules to get Slack alerts when MQTT messages match your conditions.</p>
                </div>
            `;
            return;
        }

        const cards = rules.map(r => `
            <div class="card" style="margin-bottom: 12px;">
                <div class="flex justify-between items-center" style="margin-bottom: 12px;">
                    <div class="flex items-center gap-8">
                        <span class="badge badge-${r.severity}">${r.severity}</span>
                        <strong>${API.escapeHtml(r.name)}</strong>
                    </div>
                    <label class="toggle">
                        <input type="checkbox" ${r.enabled ? 'checked' : ''}
                               onchange="RulesPage.toggleEnabled(${r.id}, this.checked)">
                        <span class="toggle-slider"></span>
                    </label>
                </div>
                <div style="font-size: 13px; color: var(--color-text-muted); margin-bottom: 8px;">
                    <span class="text-mono">${API.escapeHtml(r.topic_pattern)}</span>
                    &nbsp;&mdash;&nbsp;
                    <strong>${r.condition_type}</strong>
                    ${r.condition_type !== 'any' ? ': ' + API.escapeHtml(r.condition_value) : ''}
                    ${r.condition_type === 'json_path' || r.condition_type === 'threshold' ? ' (' + r.condition_operator + ')' : ''}
                </div>
                <div style="font-size: 12px; color: var(--color-text-muted);">
                    Channel: ${API.escapeHtml(r.slack_channel || 'default')}
                    &nbsp;|&nbsp; Cooldown: ${r.cooldown_seconds}s
                    ${r.last_triggered ? '&nbsp;|&nbsp; Last triggered: ' + API.timeAgo(r.last_triggered) : ''}
                </div>
                <div style="margin-top: 12px; display: flex; gap: 8px;">
                    <button class="btn btn-sm" onclick="RulesPage.showTestModal(${r.id})">Test</button>
                    <button class="btn btn-sm" onclick="RulesPage.showEditModal(${r.id})">Edit</button>
                    <button class="btn btn-sm btn-danger" onclick="RulesPage.deleteRule(${r.id}, '${API.escapeJsString(r.name)}')">Delete</button>
                </div>
            </div>
        `).join('');

        document.getElementById('rules-list').innerHTML = cards;
    },

    _ruleFormHtml(rule = {}) {
        const ct = rule.condition_type || 'any';
        return `
            <div class="form-group">
                <label>Rule Name</label>
                <input type="text" class="form-input" id="rule-name" value="${API.escapeHtml(rule.name || '')}" placeholder="e.g. High Temperature Alert">
            </div>
            <div class="form-group">
                <label>Topic Pattern</label>
                <input type="text" class="form-input" id="rule-topic" value="${API.escapeHtml(rule.topic_pattern || '')}" placeholder="e.g. sensors/#">
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Condition Type</label>
                    <select class="form-select" id="rule-condition-type" onchange="RulesPage._toggleConditionFields()">
                        <option value="any" ${ct === 'any' ? 'selected' : ''}>Any Message</option>
                        <option value="contains" ${ct === 'contains' ? 'selected' : ''}>Contains Text</option>
                        <option value="regex" ${ct === 'regex' ? 'selected' : ''}>Regex Match</option>
                        <option value="json_path" ${ct === 'json_path' ? 'selected' : ''}>JSON Path</option>
                        <option value="threshold" ${ct === 'threshold' ? 'selected' : ''}>Threshold</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Severity</label>
                    <select class="form-select" id="rule-severity">
                        <option value="info" ${(rule.severity || 'info') === 'info' ? 'selected' : ''}>Info</option>
                        <option value="warning" ${rule.severity === 'warning' ? 'selected' : ''}>Warning</option>
                        <option value="critical" ${rule.severity === 'critical' ? 'selected' : ''}>Critical</option>
                    </select>
                </div>
            </div>
            <div id="condition-fields" class="${ct === 'any' ? 'hidden' : ''}">
                <div class="form-group" id="condition-value-group">
                    <label id="condition-value-label">Condition Value</label>
                    <input type="text" class="form-input" id="rule-condition-value" value="${API.escapeHtml(rule.condition_value || '')}"
                           placeholder="Value to match">
                    <div class="form-hint" id="condition-hint"></div>
                </div>
                <div class="form-group" id="condition-operator-group" style="display:${ct === 'json_path' || ct === 'threshold' ? 'block' : 'none'}">
                    <label>Operator</label>
                    <select class="form-select" id="rule-condition-operator">
                        <option value="==" ${(rule.condition_operator || '==') === '==' ? 'selected' : ''}>=  (equals)</option>
                        <option value="!=" ${rule.condition_operator === '!=' ? 'selected' : ''}>!= (not equals)</option>
                        <option value=">" ${rule.condition_operator === '>' ? 'selected' : ''}>> (greater than)</option>
                        <option value="<" ${rule.condition_operator === '<' ? 'selected' : ''}>< (less than)</option>
                        <option value=">=" ${rule.condition_operator === '>=' ? 'selected' : ''}>>=</option>
                        <option value="<=" ${rule.condition_operator === '<=' ? 'selected' : ''}><=</option>
                    </select>
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Slack Channel (optional)</label>
                    <input type="text" class="form-input" id="rule-channel" value="${API.escapeHtml(rule.slack_channel || '')}" placeholder="Leave empty for default">
                </div>
                <div class="form-group">
                    <label>Cooldown (seconds)</label>
                    <input type="number" class="form-input" id="rule-cooldown" value="${rule.cooldown_seconds || 60}" min="0">
                </div>
            </div>
            <div class="form-group">
                <label>Custom Message Template (optional)</label>
                <textarea class="form-textarea" id="rule-template" placeholder="Use {topic}, {payload}, {rule}, {severity}, {details}, {timestamp}">${API.escapeHtml(rule.message_template || '')}</textarea>
            </div>
        `;
    },

    _toggleConditionFields() {
        const type = document.getElementById('rule-condition-type').value;
        const fields = document.getElementById('condition-fields');
        const opGroup = document.getElementById('condition-operator-group');
        const hint = document.getElementById('condition-hint');
        const label = document.getElementById('condition-value-label');

        if (type === 'any') {
            fields.classList.add('hidden');
            return;
        }

        fields.classList.remove('hidden');
        opGroup.style.display = (type === 'json_path' || type === 'threshold') ? 'block' : 'none';

        const hints = {
            contains: 'Text to search for in the message payload',
            regex: 'Regular expression pattern to match against the payload',
            json_path: 'Format: field.path|target_value (e.g. temperature|30)',
            threshold: 'Numeric value to compare against the raw payload',
        };
        hint.textContent = hints[type] || '';

        const labels = {
            contains: 'Search Text',
            regex: 'Regex Pattern',
            json_path: 'JSON Path | Target',
            threshold: 'Threshold Value',
        };
        label.textContent = labels[type] || 'Condition Value';
    },

    _collectFormData() {
        return {
            name: document.getElementById('rule-name').value.trim(),
            topic_pattern: document.getElementById('rule-topic').value.trim(),
            condition_type: document.getElementById('rule-condition-type').value,
            condition_value: document.getElementById('rule-condition-value')?.value.trim() || '',
            condition_operator: document.getElementById('rule-condition-operator')?.value || '==',
            severity: document.getElementById('rule-severity').value,
            slack_channel: document.getElementById('rule-channel').value.trim(),
            cooldown_seconds: parseInt(document.getElementById('rule-cooldown').value) || 60,
            message_template: document.getElementById('rule-template').value.trim(),
            enabled: true,
        };
    },

    showAddModal() {
        Modal.open('Add Alert Rule', this._ruleFormHtml(), `
            <button class="btn" onclick="Modal.close()">Cancel</button>
            <button class="btn btn-primary" onclick="RulesPage.addRule()">Create Rule</button>
        `);
        this._toggleConditionFields();
    },

    async addRule() {
        const data = this._collectFormData();
        if (!data.name || !data.topic_pattern) {
            Toast.warning('Name and topic pattern are required');
            return;
        }
        try {
            await API.post('/api/rules', data);
            Modal.close();
            Toast.success(`Rule "${data.name}" created`);
            await this.refresh();
        } catch (err) {
            Toast.error('Failed to create rule: ' + err.message);
        }
    },

    async showEditModal(id) {
        try {
            const rule = await API.get(`/api/rules/${id}`);
            Modal.open('Edit Rule', this._ruleFormHtml(rule), `
                <button class="btn" onclick="Modal.close()">Cancel</button>
                <button class="btn btn-primary" onclick="RulesPage.updateRule(${id})">Save</button>
            `);
            this._toggleConditionFields();
        } catch (err) {
            Toast.error('Failed to load rule: ' + err.message);
        }
    },

    async updateRule(id) {
        const data = this._collectFormData();
        try {
            await API.put(`/api/rules/${id}`, data);
            Modal.close();
            Toast.success('Rule updated');
            await this.refresh();
        } catch (err) {
            Toast.error('Failed to update rule: ' + err.message);
        }
    },

    async toggleEnabled(id, enabled) {
        try {
            await API.put(`/api/rules/${id}`, { enabled });
            Toast.success(`Rule ${enabled ? 'enabled' : 'disabled'}`);
        } catch (err) {
            Toast.error('Failed to update rule: ' + err.message);
            await this.refresh();
        }
    },

    deleteRule(id, name) {
        Modal.confirm('Delete Rule', `Are you sure you want to delete rule "${name}"?`, async () => {
            try {
                await API.delete(`/api/rules/${id}`);
                Toast.success('Rule deleted');
                await this.refresh();
            } catch (err) {
                Toast.error('Failed to delete rule: ' + err.message);
            }
        });
    },

    showTestModal(id) {
        Modal.open('Test Rule', `
            <div class="form-group">
                <label>Topic</label>
                <input type="text" class="form-input" id="test-topic" placeholder="e.g. sensors/temp">
            </div>
            <div class="form-group">
                <label>Payload</label>
                <textarea class="form-textarea" id="test-payload" placeholder='e.g. {"temperature": 42}'></textarea>
            </div>
            <div id="test-result" style="margin-top: 12px;"></div>
        `, `
            <button class="btn" onclick="Modal.close()">Close</button>
            <button class="btn btn-primary" onclick="RulesPage.runTest(${id})">Run Test</button>
        `);
    },

    async runTest(id) {
        const topic = document.getElementById('test-topic').value.trim();
        const payload = document.getElementById('test-payload').value;
        if (!topic) {
            Toast.warning('Topic is required');
            return;
        }
        try {
            const result = await API.post(`/api/rules/${id}/test`, { topic, payload });
            const resultEl = document.getElementById('test-result');
            if (result.matched) {
                resultEl.innerHTML = `
                    <div class="badge badge-success" style="margin-bottom: 8px;">MATCHED</div>
                    <div style="font-size: 13px;">${API.escapeHtml(result.details)}</div>
                `;
            } else {
                resultEl.innerHTML = `
                    <div class="badge badge-critical" style="margin-bottom: 8px;">NO MATCH</div>
                    <div style="font-size: 13px; color: var(--color-text-muted);">${API.escapeHtml(result.details)}</div>
                `;
            }
        } catch (err) {
            Toast.error('Test failed: ' + err.message);
        }
    }
};
