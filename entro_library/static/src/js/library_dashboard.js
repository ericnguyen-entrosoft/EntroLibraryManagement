/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class LibraryDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        this.state = useState({
            data: null,
            loading: true,
            filters: {
                date_from: null,
                date_to: null,
            }
        });

        onWillStart(async () => {
            await this.loadDashboardData();
        });
    }

    async loadDashboardData() {
        this.state.loading = true;
        try {
            const data = await this.orm.call(
                'library.dashboard',
                'get_dashboard_data',
                [],
                { filters: this.state.filters }
            );
            this.state.data = data;
        } catch (error) {
            console.error('Error loading dashboard data:', error);
        } finally {
            this.state.loading = false;
        }
    }

    async onFilterChange() {
        await this.loadDashboardData();
    }

    openBorrowings() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Mượn/Trả sách',
            res_model: 'library.borrowing',
            views: [[false, 'list'], [false, 'form']],
            target: 'current',
        });
    }

    openOverdueBorrowings() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Sách quá hạn',
            res_model: 'library.borrowing',
            views: [[false, 'list'], [false, 'form']],
            domain: [['state', '=', 'overdue']],
            target: 'current',
        });
    }

    openBooks() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Sách',
            res_model: 'library.book',
            views: [[false, 'list'], [false, 'form']],
            target: 'current',
        });
    }

    openBorrowers() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Độc giả',
            res_model: 'res.partner',
            views: [[false, 'kanban'], [false, 'list'], [false, 'form']],
            domain: [['is_borrower', '=', true]],
            target: 'current',
        });
    }

    openBook(bookId) {
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'library.book',
            res_id: bookId,
            views: [[false, 'form']],
            target: 'current',
        });
    }

    openBorrowing(borrowingId) {
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'library.borrowing',
            res_id: borrowingId,
            views: [[false, 'form']],
            target: 'current',
        });
    }

    openBorrower(partnerId) {
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'res.partner',
            res_id: partnerId,
            views: [[false, 'form']],
            target: 'current',
        });
    }

    getStateColor(state) {
        const colors = {
            'draft': 'secondary',
            'borrowed': 'primary',
            'returned': 'success',
            'overdue': 'danger',
            'cancelled': 'warning',
            'lost': 'dark'
        };
        return colors[state] || 'secondary';
    }

    getStateLabel(state) {
        const labels = {
            'draft': 'Nháp',
            'borrowed': 'Đang mượn',
            'returned': 'Đã trả',
            'overdue': 'Quá hạn',
            'cancelled': 'Hủy',
            'lost': 'Mất'
        };
        return labels[state] || state;
    }

    formatCurrency(amount) {
        return new Intl.NumberFormat('vi-VN', {
            style: 'currency',
            currency: 'VND'
        }).format(amount);
    }

    formatDate(dateStr) {
        if (!dateStr) return '';
        const date = new Date(dateStr);
        return date.toLocaleDateString('vi-VN');
    }
}

LibraryDashboard.template = "EntroLibrary.Dashboard";

registry.category("actions").add("library_dashboard", LibraryDashboard);
