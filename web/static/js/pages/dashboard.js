/* Dashboard page */
const DashboardPage = {
    async render() {
        const content = document.getElementById('content');
        content.innerHTML = `
            <div class="page-header">
                <h2>Dashboard</h2>
                <button class="btn btn-sm" onclick="DashboardPage.refresh()">Refresh</button>
            </div>
            <div class="card-grid" id="stats-grid">
                <div class="card stat-card"><div class="loading">Loading...</div></div>
            </div>
            <div class="page-header mt-16">
                <h2 style="font-size:18px;">Recent Alerts</h2>
            </div>
            <div class="table-container" id="recent-alerts">
                <div class="loading">Loading...</div>
            </div>
        `;
        await this.refresh();
    },

    async refresh() {
        try {
            const [stats, health, alerts] = await Promise.all([
                API.get('/api/dashboard/stats'),
                API.get('/api/dashboard/system-health'),
                API.get('/api/dashboard/recent-alerts?limit=10'),
            ]);
            this._renderStats(stats, health);
            this._renderAlerts(alerts);

            // Update sidebar status
            const statusEl = document.getElementById('connection-status');
            if (health.mqtt_connected) {
                statusEl.className = 'status-indicator status-connected';
                statusEl.querySelector('.status-text').textContent = 'MQTT Connected';
            } else if (health.alert_service === 'running') {
                statusEl.className = 'status-indicator status-disconnected';
                statusEl.querySelector('.status-text').textContent = 'MQTT Disconnected';
            } else {
                statusEl.className = 'status-indicator status-disconnected';
                statusEl.querySelector('.status-text').textContent = 'Service Stopped';
            }
        } catch (err) {
            Toast.error('Failed to load dashboard: ' + err.message);
        }
    },

    _renderStats(stats, health) {
        const mqttStatus = health.mqtt_connected
            ? '<span class="text-success">Connected</span>'
            : '<span class="text-danger">Disconnected</span>';

        const serviceStatus = health.alert_service === 'running'
            ? '<span class="text-success">Running</span>'
            : '<span class="text-danger">' + API.escapeHtml(health.alert_service) + '</span>';

        document.getElementById('stats-grid').innerHTML = `
            <div class="card stat-card">
                <div class="card-title">MQTT Broker</div>
                <div class="card-value" style="font-size:20px;">${mqttStatus}</div>
                <div class="card-subtitle">Alert Service: ${serviceStatus}</div>
            </div>
            <div class="card stat-card">
                <div class="card-title">Active Topics</div>
                <div class="card-value">${stats.topics.active}</div>
                <div class="card-subtitle">${stats.topics.total} total</div>
            </div>
            <div class="card stat-card">
                <div class="card-title">Messages (24h)</div>
                <div class="card-value">${stats.messages.last_24h.toLocaleString()}</div>
                <div class="card-subtitle">${stats.messages.last_hour} in last hour</div>
            </div>
            <div class="card stat-card">
                <div class="card-title">Alerts (24h)</div>
                <div class="card-value">${stats.alerts.last_24h}</div>
                <div class="card-subtitle">${this._severitySummary(stats.alerts.by_severity)}</div>
            </div>
            <div class="card stat-card">
                <div class="card-title">Rules</div>
                <div class="card-value">${stats.rules.total}</div>
                <div class="card-subtitle">alert rules configured</div>
            </div>
            <div class="card stat-card">
                <div class="card-title">Disk Usage</div>
                <div class="card-value" style="font-size:20px;">${health.disk.percent}%</div>
                <div class="card-subtitle">${health.disk.free_gb} GB free of ${health.disk.total_gb} GB</div>
            </div>
        `;
    },

    _severitySummary(bySeverity) {
        if (!bySeverity || Object.keys(bySeverity).length === 0) return 'No alerts';
        return Object.entries(bySeverity)
            .map(([sev, count]) => `${count} ${sev}`)
            .join(', ');
    },

    _renderAlerts(alerts) {
        if (!alerts || alerts.length === 0) {
            document.getElementById('recent-alerts').innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">&#9889;</div>
                    <h3>No recent alerts</h3>
                    <p>Alerts will appear here when rules are triggered.</p>
                </div>
            `;
            return;
        }

        const rows = alerts.map(a => `
            <tr>
                <td><span class="badge badge-${a.severity}">${a.severity}</span></td>
                <td>${API.escapeHtml(a.rule_name || '—')}</td>
                <td class="text-mono">${API.escapeHtml(a.topic || '—')}</td>
                <td>${API.escapeHtml(a.slack_response || '—')}</td>
                <td class="text-muted">${API.timeAgo(a.sent_at)}</td>
            </tr>
        `).join('');

        document.getElementById('recent-alerts').innerHTML = `
            <table>
                <thead>
                    <tr>
                        <th>Severity</th>
                        <th>Rule</th>
                        <th>Topic</th>
                        <th>Status</th>
                        <th>Time</th>
                    </tr>
                </thead>
                <tbody>${rows}</tbody>
            </table>
        `;
    }
};
