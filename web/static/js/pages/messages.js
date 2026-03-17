/* Message log page */
const MessagesPage = {
    _offset: 0,
    _limit: 50,
    _topic: '',
    _search: '',

    async render() {
        const content = document.getElementById('content');
        content.innerHTML = `
            <div class="page-header">
                <h2>Message Log</h2>
            </div>
            <div class="toolbar">
                <input type="text" class="form-input" id="msg-topic-filter"
                       placeholder="Filter by topic..." oninput="MessagesPage.applyFilter()">
                <input type="text" class="form-input" id="msg-search"
                       placeholder="Search payload..." oninput="MessagesPage.applyFilter()">
                <button class="btn btn-sm" onclick="MessagesPage.refresh()">Refresh</button>
            </div>
            <div class="table-container" id="messages-table">
                <div class="loading">Loading...</div>
            </div>
        `;
        this._offset = 0;
        await this.refresh();
    },

    applyFilter() {
        clearTimeout(this._filterTimeout);
        this._filterTimeout = setTimeout(() => {
            this._topic = document.getElementById('msg-topic-filter').value.trim();
            this._search = document.getElementById('msg-search').value.trim();
            this._offset = 0;
            this.refresh();
        }, 300);
    },

    async refresh() {
        try {
            let url = `/api/messages?limit=${this._limit}&offset=${this._offset}`;
            if (this._topic) url += `&topic=${encodeURIComponent(this._topic)}`;
            if (this._search) url += `&search=${encodeURIComponent(this._search)}`;

            const data = await API.get(url);
            this._renderTable(data);
        } catch (err) {
            Toast.error('Failed to load messages: ' + err.message);
        }
    },

    _renderTable(data) {
        if (!data.messages || data.messages.length === 0) {
            document.getElementById('messages-table').innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">&#9776;</div>
                    <h3>No messages</h3>
                    <p>${this._topic || this._search ? 'No messages match your filter.' : 'Messages will appear here once topics are subscribed and receiving data.'}</p>
                </div>
            `;
            return;
        }

        // Store messages for detail view lookup
        this._currentMessages = {};
        data.messages.forEach(m => { this._currentMessages[m.id] = m; });

        const rows = data.messages.map(m => {
            const payloadPreview = m.payload.length > 120
                ? API.escapeHtml(m.payload.substring(0, 120)) + '...'
                : API.escapeHtml(m.payload);
            return `
                <tr onclick="MessagesPage.showDetailById(${m.id})" style="cursor:pointer;">
                    <td class="text-mono" style="max-width:200px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
                        ${API.escapeHtml(m.topic)}
                    </td>
                    <td style="max-width: 400px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
                        ${payloadPreview}
                    </td>
                    <td>${m.qos}</td>
                    <td>${m.retained ? 'Yes' : 'No'}</td>
                    <td class="text-muted">${API.timeAgo(m.received_at)}</td>
                </tr>
            `;
        }).join('');

        const start = data.offset + 1;
        const end = data.offset + data.messages.length;
        const hasPrev = data.offset > 0;
        const hasNext = data.offset + data.limit < data.total;

        document.getElementById('messages-table').innerHTML = `
            <table>
                <thead>
                    <tr>
                        <th>Topic</th>
                        <th>Payload</th>
                        <th>QoS</th>
                        <th>Retained</th>
                        <th>Time</th>
                    </tr>
                </thead>
                <tbody>${rows}</tbody>
            </table>
            <div class="pagination">
                <span>Showing ${start}–${end} of ${data.total}</span>
                <div class="pagination-buttons">
                    <button class="btn btn-sm" ${hasPrev ? '' : 'disabled'} onclick="MessagesPage.prevPage()">Previous</button>
                    <button class="btn btn-sm" ${hasNext ? '' : 'disabled'} onclick="MessagesPage.nextPage()">Next</button>
                </div>
            </div>
        `;
    },

    showDetailById(id) {
        const m = this._currentMessages && this._currentMessages[id];
        if (!m) return;
        this.showDetail(m);
    },

    showDetail(m) {
        Modal.open('Message Detail', `
            <div class="form-group">
                <label>Topic</label>
                <div class="text-mono">${API.escapeHtml(m.topic)}</div>
            </div>
            <div class="form-group">
                <label>Payload</label>
                <pre style="background: var(--color-bg); padding: 12px; border-radius: var(--radius-sm); overflow-x: auto; font-size: 13px; white-space: pre-wrap; word-break: break-all; max-height: 300px; overflow-y: auto;">${API.escapeHtml(m.payload)}</pre>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>QoS</label>
                    <div>${m.qos}</div>
                </div>
                <div class="form-group">
                    <label>Retained</label>
                    <div>${m.retained ? 'Yes' : 'No'}</div>
                </div>
            </div>
            <div class="form-group">
                <label>Received</label>
                <div>${API.formatDate(m.received_at)}</div>
            </div>
        `, `<button class="btn" onclick="Modal.close()">Close</button>`);
    },

    prevPage() {
        this._offset = Math.max(0, this._offset - this._limit);
        this.refresh();
    },

    nextPage() {
        this._offset += this._limit;
        this.refresh();
    }
};
