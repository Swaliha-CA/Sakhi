// Notifications Component
const NotificationsComponent = {
    notifications: [],

    render() {
        return `
            <div class="section-container">
                <div class="row">
                    <div class="col-lg-8 mx-auto">
                        <div class="card">
                            <div class="card-header d-flex justify-content-between align-items-center">
                                <h3><i class="fas fa-bell"></i> Notifications</h3>
                                <div>
                                    <button class="btn btn-sm btn-outline-light" id="showAllBtn">All</button>
                                    <button class="btn btn-sm btn-outline-light" id="showUnreadBtn">Unread</button>
                                </div>
                            </div>
                            <div class="card-body">
                                <div id="notificationsList">
                                    <div class="text-center text-muted py-5">
                                        <i class="fas fa-bell-slash fa-3x mb-3"></i>
                                        <p>Loading notifications...</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    },

    init() {
        document.getElementById('showAllBtn').addEventListener('click', () => this.loadNotifications(false));
        document.getElementById('showUnreadBtn').addEventListener('click', () => this.loadNotifications(true));
        this.loadNotifications(false);
    },

    async loadNotifications(unreadOnly = false) {
        utils.showLoading();

        try {
            this.notifications = await api.getNotifications(APP_CONFIG.USER_ID, unreadOnly);
            this.displayNotifications();
        } catch (error) {
            console.error('Load notifications error:', error);
            utils.showToast('Failed to load notifications', 'error');
            document.getElementById('notificationsList').innerHTML = `
                <div class="text-center text-muted py-5">
                    <i class="fas fa-exclamation-triangle fa-3x mb-3"></i>
                    <p>Failed to load notifications</p>
                </div>
            `;
        } finally {
            utils.hideLoading();
        }
    },

    displayNotifications() {
        const container = document.getElementById('notificationsList');

        if (this.notifications.length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted py-5">
                    <i class="fas fa-bell-slash fa-3x mb-3"></i>
                    <p>No notifications</p>
                </div>
            `;
            return;
        }

        container.innerHTML = this.notifications.map(notif => `
            <div class="notification-item ${!notif.read ? 'unread' : ''}" 
                 onclick="NotificationsComponent.markAsRead(${notif.id})">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <div class="d-flex align-items-center mb-2">
                            <i class="fas ${this.getNotificationIcon(notif.notification_type)} text-primary me-2"></i>
                            <strong>${notif.title}</strong>
                            ${!notif.read ? '<span class="badge bg-primary ms-2">New</span>' : ''}
                        </div>
                        <p class="mb-2">${notif.message}</p>
                        ${notif.product ? `
                            <div class="mb-2">
                                <span class="badge bg-success">
                                    ${notif.product.name} - Score: ${notif.product.hormonal_health_score}
                                </span>
                            </div>
                        ` : ''}
                        <small class="text-muted">
                            <i class="fas fa-clock"></i> ${utils.formatDate(notif.created_at)}
                        </small>
                    </div>
                </div>
            </div>
        `).join('');
    },

    getNotificationIcon(type) {
        const icons = {
            'new_product': 'fa-box',
            'price_drop': 'fa-tag',
            'health_alert': 'fa-exclamation-triangle',
            'reminder': 'fa-bell'
        };
        return icons[type] || 'fa-info-circle';
    },

    async markAsRead(notificationId) {
        try {
            await api.markNotificationRead(APP_CONFIG.USER_ID, notificationId);
            
            // Update local state
            const notif = this.notifications.find(n => n.id === notificationId);
            if (notif) {
                notif.read = true;
                this.displayNotifications();
            }
        } catch (error) {
            console.error('Mark as read error:', error);
        }
    }
};

window.NotificationsComponent = NotificationsComponent;
