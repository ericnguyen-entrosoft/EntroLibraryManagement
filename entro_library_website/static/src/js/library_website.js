/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";

publicWidget.registry.LibraryBookDetail = publicWidget.Widget.extend({
    selector: '.js_library_book',
    events: {
        'click .btn_add_to_cart': '_onAddToCart',
    },

    /**
     * Handle add to borrowing cart button click
     */
    _onAddToCart: function (ev) {
        ev.preventDefault();
        const $btn = $(ev.currentTarget);
        const bookId = $btn.data('book-id');

        // Disable button and show loading
        $btn.prop('disabled', true).html('<i class="fa fa-spinner fa-spin me-2"></i>Đang thêm...');

        // Call server
        rpc('/thu-vien/them-vao-gio', {
            book_id: bookId,
        }).then((result) => {
            if (result.success) {
                // Show success message with simple alert
                this._showNotification('success', result.message);

                // Update button
                $btn.removeClass('btn-primary').addClass('btn-success')
                    .html('<i class="fa fa-check me-2"></i>Đã thêm vào giỏ');

                // Reset after 2 seconds
                setTimeout(() => {
                    $btn.removeClass('btn-success').addClass('btn-primary')
                        .html('<i class="fa fa-shopping-cart me-2"></i>Thêm vào giỏ mượn')
                        .prop('disabled', false);
                }, 2000);

            } else {
                // Show error message
                this._showNotification('error', result.message);

                // Reset button
                $btn.prop('disabled', false)
                    .html('<i class="fa fa-shopping-cart me-2"></i>Thêm vào giỏ mượn');
            }
        }).catch((error) => {
            // Show error message
            this._showNotification('error', 'Đã xảy ra lỗi khi thêm sách vào giỏ. Vui lòng thử lại.');

            // Reset button
            $btn.prop('disabled', false)
                .html('<i class="fa fa-shopping-cart me-2"></i>Thêm vào giỏ mượn');
        });
    },

    /**
     * Show notification toast
     */
    _showNotification: function (type, message) {
        // Create notification element
        const bgColor = type === 'success' ? '#591202' : '#dc3545';
        const icon = type === 'success' ? 'check-circle' : 'exclamation-triangle';

        const $notification = $(`
            <div class="alert alert-dismissible fade show position-fixed"
                 style="top: 20px; right: 20px; z-index: 9999; min-width: 300px; max-width: 500px;
                        background-color: ${bgColor}; color: white; border: none; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
                <i class="fa fa-${icon} me-2"></i>
                <strong>${message}</strong>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="alert"></button>
            </div>
        `);

        // Append to body
        $('body').append($notification);

        // Auto remove after 4 seconds
        setTimeout(() => {
            $notification.alert('close');
        }, 4000);
    },
});

export default publicWidget.registry.LibraryBookDetail;
