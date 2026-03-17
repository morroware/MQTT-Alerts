/* Settings page */
const SettingsPage = {
    async render() {
        const content = document.getElementById('content');
        content.innerHTML = `
            <div class="page-header">
                <h2>Settings</h2>
            </div>

            <div class="settings-section">
                <h3>Slack Integration</h3>
                <div id="slack-settings">
                    <div class="loading">Loading...</div>
                </div>
            </div>

            <div class="settings-section">
                <h3>System</h3>
                <div id="system-settings">
                    <div class="loading">Loading...</div>
                </div>
            </div>

            <div class="settings-section">
                <h3>Data Management</h3>
                <div style="display: flex; gap: 12px; flex-wrap: wrap;">
                    <button class="btn" onclick="SettingsPage.exportRules()">Export Rules (JSON)</button>
                    <button class="btn" onclick="document.getElementById('import-file').click()">Import Rules (JSON)</button>
                    <input type="file" id="import-file" accept=".json" style="display:none" onchange="SettingsPage.importRules(this)">
                </div>
            </div>
        `;
        await Promise.all([this._loadSlackSettings(), this._loadSystemHealth()]);
    },

    async _loadSlackSettings() {
        try {
            const settings = await API.get('/api/settings/slack');
            const statusClass = settings.connected ? 'text-success' : 'text-danger';
            const statusText = settings.connected
                ? `Connected (${API.escapeHtml(settings.identity || '')})`
                : settings.bot_token_set ? 'Token set but not connected' : 'Not configured';

            document.getElementById('slack-settings').innerHTML = `
                <div style="margin-bottom: 16px;">
                    <strong>Status:</strong> <span class="${statusClass}">${statusText}</span>
                </div>
                <div class="form-group">
                    <label>Bot Token</label>
                    <input type="password" class="form-input" id="slack-token"
                           value="${settings.bot_token_set ? '••••••••••••' : ''}"
                           placeholder="xoxb-your-bot-token-here"
                           onfocus="if(this.value.startsWith('••'))this.value=''">
                    <div class="form-hint">Create a Slack app at api.slack.com/apps. Required scopes: chat:write, chat:write.public, channels:read</div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>Default Channel</label>
                        <input type="text" class="form-input" id="slack-channel"
                               value="${API.escapeHtml(settings.default_channel || '#alerts')}"
                               placeholder="#alerts">
                    </div>
                    <div class="form-group">
                        <label>Rate Limit (alerts/min)</label>
                        <input type="number" class="form-input" id="slack-rate-limit"
                               value="${settings.rate_limit || 10}" min="1" max="60">
                    </div>
                </div>
                <div style="display: flex; gap: 8px; margin-top: 8px;">
                    <button class="btn btn-primary" onclick="SettingsPage.saveSlackSettings()">Save</button>
                    <button class="btn" onclick="SettingsPage.testSlack()">Send Test Message</button>
                    <button class="btn" onclick="SettingsPage.listChannels()">List Channels</button>
                </div>
                <div id="slack-channels-list" style="margin-top: 16px;"></div>
            `;
        } catch (err) {
            document.getElementById('slack-settings').innerHTML =
                `<div class="text-danger">Failed to load Slack settings: ${API.escapeHtml(err.message)}</div>`;
        }
    },

    async saveSlackSettings() {
        const token = document.getElementById('slack-token').value.trim();
        if (token.startsWith('••')) {
            Toast.warning('Please enter a new token or leave unchanged');
            return;
        }
        const channel = document.getElementById('slack-channel').value.trim();
        const rateLimit = parseInt(document.getElementById('slack-rate-limit').value) || 10;

        try {
            const result = await API.put('/api/settings/slack', {
                bot_token: token,
                default_channel: channel,
                rate_limit: rateLimit,
            });
            if (result.connected) {
                Toast.success('Slack settings saved — connected!');
            } else {
                Toast.warning('Settings saved but bot could not connect. Check your token.');
            }
            await this._loadSlackSettings();
        } catch (err) {
            Toast.error('Failed to save: ' + err.message);
        }
    },

    async testSlack() {
        const channel = document.getElementById('slack-channel').value.trim() || '#alerts';
        try {
            await API.post('/api/settings/slack/test', { channel });
            Toast.success(`Test message sent to ${channel}`);
        } catch (err) {
            Toast.error('Test failed: ' + err.message);
        }
    },

    async listChannels() {
        try {
            const data = await API.get('/api/settings/slack/channels');
            if (!data.channels || data.channels.length === 0) {
                document.getElementById('slack-channels-list').innerHTML =
                    '<div class="text-muted">No channels found. Make sure the bot has channels:read scope.</div>';
                return;
            }
            const list = data.channels.map(ch =>
                `<span class="badge ${ch.is_member ? 'badge-success' : 'badge-info'}" style="margin: 2px;">
                    #${API.escapeHtml(ch.name)} ${ch.is_private ? '(private)' : ''}
                </span>`
            ).join('');
            document.getElementById('slack-channels-list').innerHTML = `
                <label style="font-size: 13px; font-weight: 600; color: var(--color-text-muted);">Available Channels</label>
                <div style="margin-top: 8px;">${list}</div>
            `;
        } catch (err) {
            Toast.error('Failed to list channels: ' + err.message);
        }
    },

    async _loadSystemHealth() {
        try {
            const health = await API.get('/api/dashboard/system-health');
            document.getElementById('system-settings').innerHTML = `
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
                    <div>
                        <label style="font-size: 13px; font-weight: 600; color: var(--color-text-muted);">Alert Service</label>
                        <div class="${health.alert_service === 'running' ? 'text-success' : 'text-danger'}">
                            ${API.escapeHtml(health.alert_service)}
                        </div>
                    </div>
                    <div>
                        <label style="font-size: 13px; font-weight: 600; color: var(--color-text-muted);">MQTT Broker</label>
                        <div class="${health.mqtt_connected ? 'text-success' : 'text-danger'}">
                            ${health.mqtt_connected ? 'Connected' : 'Disconnected'}
                        </div>
                    </div>
                    <div>
                        <label style="font-size: 13px; font-weight: 600; color: var(--color-text-muted);">Disk Usage</label>
                        <div>${health.disk.percent}% (${health.disk.free_gb} GB free)</div>
                    </div>
                </div>
            `;
        } catch (err) {
            document.getElementById('system-settings').innerHTML =
                `<div class="text-danger">Failed to load system health</div>`;
        }
    },

    async exportRules() {
        try {
            const rules = await API.get('/api/rules');
            const blob = new Blob([JSON.stringify(rules, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'mqtt-alerts-rules.json';
            a.click();
            URL.revokeObjectURL(url);
            Toast.success(`Exported ${rules.length} rules`);
        } catch (err) {
            Toast.error('Export failed: ' + err.message);
        }
    },

    async importRules(input) {
        const file = input.files[0];
        if (!file) return;
        try {
            const text = await file.text();
            const rules = JSON.parse(text);
            if (!Array.isArray(rules)) throw new Error('Expected a JSON array of rules');

            let imported = 0;
            for (const rule of rules) {
                await API.post('/api/rules', {
                    name: rule.name || 'Imported Rule',
                    topic_pattern: rule.topic_pattern || '#',
                    condition_type: rule.condition_type || 'any',
                    condition_value: rule.condition_value || '',
                    condition_operator: rule.condition_operator || '==',
                    severity: rule.severity || 'info',
                    slack_channel: rule.slack_channel || '',
                    message_template: rule.message_template || '',
                    cooldown_seconds: rule.cooldown_seconds || 60,
                    enabled: rule.enabled !== false,
                });
                imported++;
            }
            Toast.success(`Imported ${imported} rules`);
            input.value = '';
        } catch (err) {
            Toast.error('Import failed: ' + err.message);
            input.value = '';
        }
    }
};
