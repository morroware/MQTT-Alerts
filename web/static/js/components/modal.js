/* Modal dialog system */
const Modal = {
    open(title, bodyHtml, footerHtml = '') {
        document.getElementById('modal-title').textContent = title;
        document.getElementById('modal-body').innerHTML = bodyHtml;
        document.getElementById('modal-footer').innerHTML = footerHtml;
        document.getElementById('modal-overlay').classList.remove('hidden');
    },

    close() {
        document.getElementById('modal-overlay').classList.add('hidden');
    },

    confirm(title, message, onConfirm) {
        this.open(
            title,
            `<p>${message}</p>`,
            `<button class="btn" onclick="Modal.close()">Cancel</button>
             <button class="btn btn-danger" id="modal-confirm-btn">Confirm</button>`
        );
        document.getElementById('modal-confirm-btn').onclick = () => {
            this.close();
            onConfirm();
        };
    }
};

// Close modal on overlay click
document.getElementById('modal-overlay').addEventListener('click', (e) => {
    if (e.target === e.currentTarget) Modal.close();
});

// Close modal on Escape
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') Modal.close();
});
