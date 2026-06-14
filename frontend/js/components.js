/**
 * Reusable UI Components
 */
const components = {
    showToast(message, type = 'info') {
        let container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            document.body.appendChild(container);
        }

        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        const icons = { success: '✅', error: '❌', info: 'ℹ️' };
        toast.innerHTML = `<span>${icons[type] || 'ℹ️'}</span> ${message}`;
        
        container.appendChild(toast);
        
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    },

    showModal(title, contentHTML, onConfirm = null) {
        let overlay = document.getElementById('generic-modal-overlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.className = 'modal-overlay';
            overlay.id = 'generic-modal-overlay';
            overlay.innerHTML = `
                <div class="modal-content">
                    <div class="modal-header">
                        <h3 id="modal-title"></h3>
                        <button class="modal-close">&times;</button>
                    </div>
                    <div class="modal-body" id="modal-body"></div>
                    <div class="modal-footer" id="modal-footer">
                        <button class="btn btn-secondary modal-cancel">Cancel</button>
                        <button class="btn btn-primary modal-confirm">Confirm</button>
                    </div>
                </div>
            `;
            document.body.appendChild(overlay);

            overlay.querySelector('.modal-close').addEventListener('click', () => this.hideModal());
            overlay.querySelector('.modal-cancel').addEventListener('click', () => this.hideModal());
        }

        document.getElementById('modal-title').textContent = title;
        document.getElementById('modal-body').innerHTML = contentHTML;
        
        const confirmBtn = overlay.querySelector('.modal-confirm');
        if (onConfirm) {
            confirmBtn.style.display = 'block';
            confirmBtn.onclick = () => {
                onConfirm();
                this.hideModal();
            };
        } else {
            confirmBtn.style.display = 'none';
            overlay.querySelector('.modal-cancel').textContent = 'Close';
        }

        setTimeout(() => overlay.classList.add('active'), 10);
    },

    hideModal() {
        const overlay = document.getElementById('generic-modal-overlay');
        if (overlay) {
            overlay.classList.remove('active');
        }
    },

    createBadge(text, colorType) {
        return `<span class="badge badge-${colorType}">${text}</span>`;
    },

    formatDate(dateString) {
        if (!dateString) return '-';
        return new Date(dateString).toLocaleString();
    }
};
