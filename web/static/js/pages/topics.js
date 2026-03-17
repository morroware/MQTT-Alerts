/* Topics management page */
const TopicsPage = {
    async render() {
        const content = document.getElementById('content');
        content.innerHTML = `
            <div class="page-header">
                <h2>Topics</h2>
                <button class="btn btn-primary" onclick="TopicsPage.showAddModal()">+ Add Topic</button>
            </div>
            <div class="table-container" id="topics-table">
                <div class="loading">Loading...</div>
            </div>
        `;
        await this.refresh();
    },

    async refresh() {
        try {
            const topics = await API.get('/api/topics');
            this._renderTable(topics);
        } catch (err) {
            Toast.error('Failed to load topics: ' + err.message);
        }
    },

    _renderTable(topics) {
        if (!topics || topics.length === 0) {
            document.getElementById('topics-table').innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">&#9993;</div>
                    <h3>No topics configured</h3>
                    <p>Add MQTT topics to start monitoring messages.</p>
                </div>
            `;
            return;
        }

        const rows = topics.map(t => `
            <tr>
                <td class="text-mono">${API.escapeHtml(t.topic_pattern)}</td>
                <td>${API.escapeHtml(t.description || '—')}</td>
                <td>
                    <label class="toggle">
                        <input type="checkbox" ${t.enabled ? 'checked' : ''}
                               onchange="TopicsPage.toggleEnabled(${t.id}, this.checked)">
                        <span class="toggle-slider"></span>
                    </label>
                </td>
                <td class="text-muted">${API.formatDate(t.created_at)}</td>
                <td>
                    <button class="btn btn-sm" onclick="TopicsPage.showEditModal(${t.id})">Edit</button>
                    <button class="btn btn-sm btn-danger" onclick="TopicsPage.deleteTopic(${t.id}, '${API.escapeJsString(t.topic_pattern)}')">Delete</button>
                </td>
            </tr>
        `).join('');

        document.getElementById('topics-table').innerHTML = `
            <table>
                <thead>
                    <tr>
                        <th>Topic Pattern</th>
                        <th>Description</th>
                        <th>Enabled</th>
                        <th>Created</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>${rows}</tbody>
            </table>
        `;
    },

    showAddModal() {
        Modal.open('Add Topic', `
            <div class="form-group">
                <label>Topic Pattern</label>
                <input type="text" class="form-input" id="topic-pattern" placeholder="e.g. sensors/# or home/+/temperature">
                <div class="form-hint">Use + for single-level wildcard, # for multi-level wildcard</div>
            </div>
            <div class="form-group">
                <label>Description</label>
                <input type="text" class="form-input" id="topic-description" placeholder="Optional description">
            </div>
        `, `
            <button class="btn" onclick="Modal.close()">Cancel</button>
            <button class="btn btn-primary" onclick="TopicsPage.addTopic()">Add Topic</button>
        `);
    },

    async addTopic() {
        const pattern = document.getElementById('topic-pattern').value.trim();
        const desc = document.getElementById('topic-description').value.trim();

        if (!pattern) {
            Toast.warning('Topic pattern is required');
            return;
        }

        try {
            await API.post('/api/topics', {
                topic_pattern: pattern,
                description: desc,
                enabled: true,
            });
            Modal.close();
            Toast.success(`Topic "${pattern}" added`);
            await this.refresh();
        } catch (err) {
            Toast.error('Failed to add topic: ' + err.message);
        }
    },

    async showEditModal(id) {
        try {
            const topic = await API.get(`/api/topics/${id}`);
            Modal.open('Edit Topic', `
                <div class="form-group">
                    <label>Topic Pattern</label>
                    <input type="text" class="form-input" id="edit-topic-pattern" value="${API.escapeHtml(topic.topic_pattern)}">
                </div>
                <div class="form-group">
                    <label>Description</label>
                    <input type="text" class="form-input" id="edit-topic-description" value="${API.escapeHtml(topic.description || '')}">
                </div>
            `, `
                <button class="btn" onclick="Modal.close()">Cancel</button>
                <button class="btn btn-primary" onclick="TopicsPage.updateTopic(${id})">Save</button>
            `);
        } catch (err) {
            Toast.error('Failed to load topic: ' + err.message);
        }
    },

    async updateTopic(id) {
        const pattern = document.getElementById('edit-topic-pattern').value.trim();
        const desc = document.getElementById('edit-topic-description').value.trim();

        try {
            await API.put(`/api/topics/${id}`, {
                topic_pattern: pattern,
                description: desc,
            });
            Modal.close();
            Toast.success('Topic updated');
            await this.refresh();
        } catch (err) {
            Toast.error('Failed to update topic: ' + err.message);
        }
    },

    async toggleEnabled(id, enabled) {
        try {
            await API.put(`/api/topics/${id}`, { enabled });
            Toast.success(`Topic ${enabled ? 'enabled' : 'disabled'}`);
        } catch (err) {
            Toast.error('Failed to update topic: ' + err.message);
            await this.refresh();
        }
    },

    deleteTopic(id, name) {
        Modal.confirm('Delete Topic', `Are you sure you want to delete topic "${name}"?`, async () => {
            try {
                await API.delete(`/api/topics/${id}`);
                Toast.success('Topic deleted');
                await this.refresh();
            } catch (err) {
                Toast.error('Failed to delete topic: ' + err.message);
            }
        });
    }
};
