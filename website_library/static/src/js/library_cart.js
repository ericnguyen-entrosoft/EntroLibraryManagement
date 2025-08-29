/* Library Cart Management */

odoo.define('website_library.cart', function (require) {
'use strict';

var publicWidget = require('web.public.widget');
var core = require('web.core');
var ajax = require('web.ajax');

var _t = core._t;

publicWidget.registry.LibraryCart = publicWidget.Widget.extend({
    selector: '.library-cart',
    events: {
        'click .js_library_add_cart': '_onAddToCart',
        'click .js_library_remove_cart': '_onRemoveFromCart',
        'change .js_library_lot_select': '_onLotChange',
        'click .js_library_checkout': '_onCheckout',
    },

    /**
     * Add book to cart
     */
    _onAddToCart: function (ev) {
        ev.preventDefault();
        var $btn = $(ev.currentTarget);
        var $form = $btn.closest('form');
        var productId = $form.find('input[name="product_id"]').val();
        var lotId = $form.find('select[name="lot_id"]').val();

        if (!productId) {
            this._showNotification(_t('Please select a book'), 'danger');
            return;
        }

        // Disable button and show loading
        $btn.prop('disabled', true);
        var originalText = $btn.html();
        $btn.html('<i class="fa fa-spinner fa-spin"></i> ' + _t('Adding...'));

        // Submit form via AJAX for better UX
        ajax.post('/library/cart/add', {
            product_id: productId,
            lot_id: lotId || false,
            add_qty: 1,
        }).then(function (data) {
            if (data.success) {
                // Update cart counter
                $('.library-cart-counter').text(data.cart_count || 0);
                
                // Show success message
                this._showNotification(_t('Book added to cart successfully!'), 'success');
                
                // Redirect to cart or show cart preview
                if (data.redirect_url) {
                    window.location.href = data.redirect_url;
                } else {
                    window.location.href = '/library/cart';
                }
            } else {
                this._showNotification(data.error || _t('Failed to add book to cart'), 'danger');
            }
        }.bind(this)).fail(function () {
            this._showNotification(_t('Error adding book to cart'), 'danger');
        }.bind(this)).always(function () {
            // Re-enable button
            $btn.prop('disabled', false);
            $btn.html(originalText);
        });
    },

    /**
     * Remove book from cart
     */
    _onRemoveFromCart: function (ev) {
        ev.preventDefault();
        var $btn = $(ev.currentTarget);
        var lineId = $btn.data('line-id');

        if (!lineId) {
            return;
        }

        if (!confirm(_t('Are you sure you want to remove this book from your cart?'))) {
            return;
        }

        ajax.post('/library/cart/remove', {
            line_id: lineId,
        }).then(function () {
            // Remove the line from DOM
            $btn.closest('.cart-line').fadeOut(function () {
                $(this).remove();
                // Update cart totals
                this._updateCartTotals();
            }.bind(this));
            
            this._showNotification(_t('Book removed from cart'), 'info');
        }.bind(this)).fail(function () {
            this._showNotification(_t('Error removing book from cart'), 'danger');
        }.bind(this));
    },

    /**
     * Handle lot/serial selection change
     */
    _onLotChange: function (ev) {
        var $select = $(ev.currentTarget);
        var lotId = $select.val();
        var $form = $select.closest('form');
        
        // Update form data
        $form.find('input[name="lot_id"]').val(lotId);
        
        // Show selected serial info
        if (lotId) {
            var lotName = $select.find('option:selected').text();
            $form.find('.selected-serial-info').html(
                '<small class="text-muted">' + _t('Selected: ') + lotName + '</small>'
            ).show();
        } else {
            $form.find('.selected-serial-info').hide();
        }
    },

    /**
     * Handle checkout process
     */
    _onCheckout: function (ev) {
        ev.preventDefault();
        var $btn = $(ev.currentTarget);
        
        // Check if user is logged in
        if ($('body').hasClass('o_public_user')) {
            // Redirect to login
            window.location.href = '/web/login?redirect=' + encodeURIComponent('/library/borrow');
            return;
        }

        // Proceed to checkout
        window.location.href = '/library/borrow';
    },

    /**
     * Update cart totals and counters
     */
    _updateCartTotals: function () {
        var $cartLines = $('.cart-line:visible');
        var totalBooks = $cartLines.length;
        
        // Update counters
        $('.library-cart-counter').text(totalBooks);
        $('.cart-total-books').text(totalBooks);
        
        // Show/hide empty cart message
        if (totalBooks === 0) {
            $('.cart-content').hide();
            $('.empty-cart-message').show();
        }
    },

    /**
     * Show notification message
     */
    _showNotification: function (message, type) {
        type = type || 'info';
        var $notification = $('<div class="alert alert-' + type + ' alert-dismissible fade show library-notification">')
            .append('<button type="button" class="btn-close" data-bs-dismiss="alert"></button>')
            .append('<span>' + message + '</span>')
            .css({
                'position': 'fixed',
                'top': '20px',
                'right': '20px',
                'z-index': '9999',
                'min-width': '300px'
            });

        $('body').append($notification);

        // Auto-remove after 5 seconds
        setTimeout(function () {
            $notification.fadeOut(function () {
                $(this).remove();
            });
        }, 5000);
    },
});

return publicWidget.registry.LibraryCart;

});