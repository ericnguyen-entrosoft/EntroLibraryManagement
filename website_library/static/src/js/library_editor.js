/* Website Library Editor Extensions */

odoo.define('website_library.editor', function (require) {
'use strict';

var options = require('web_editor.snippets.options');
var wUtils = require('website.utils');

/**
 * Library Book Snippet Options
 */
options.registry.LibraryBookSnippet = options.Class.extend({
    
    /**
     * Set book display mode
     */
    setDisplayMode: function (previewMode, widgetValue, params) {
        var mode = widgetValue || 'grid';
        this.$target.removeClass('display-grid display-list display-card');
        this.$target.addClass('display-' + mode);
    },

    /**
     * Set number of books per row
     */
    setBooksPerRow: function (previewMode, widgetValue, params) {
        var booksPerRow = parseInt(widgetValue) || 4;
        this.$target.removeClass('books-per-row-1 books-per-row-2 books-per-row-3 books-per-row-4 books-per-row-6');
        this.$target.addClass('books-per-row-' + booksPerRow);
    },

    /**
     * Set book category filter
     */
    setCategoryFilter: function (previewMode, widgetValue, params) {
        var categoryId = widgetValue || '';
        this.$target.attr('data-category-filter', categoryId);
        this._refreshBooks();
    },

    /**
     * Set availability filter
     */
    setAvailabilityFilter: function (previewMode, widgetValue, params) {
        var availability = widgetValue || '';
        this.$target.attr('data-availability-filter', availability);
        this._refreshBooks();
    },

    /**
     * Set sort order
     */
    setSortOrder: function (previewMode, widgetValue, params) {
        var sortOrder = widgetValue || 'name';
        this.$target.attr('data-sort-order', sortOrder);
        this._refreshBooks();
    },

    /**
     * Refresh books display based on current filters
     */
    _refreshBooks: function () {
        if (this.isDestroyed()) {
            return;
        }
        
        var self = this;
        var categoryFilter = this.$target.attr('data-category-filter') || '';
        var availabilityFilter = this.$target.attr('data-availability-filter') || '';
        var sortOrder = this.$target.attr('data-sort-order') || 'name';
        
        // AJAX call to get filtered books
        this._rpc({
            route: '/library/snippet/books',
            params: {
                category: categoryFilter,
                availability: availabilityFilter,
                order: sortOrder,
                limit: 12, // Limit for snippet display
            }
        }).then(function (data) {
            if (data && data.books) {
                self._renderBooks(data.books);
            }
        });
    },

    /**
     * Render books in snippet
     */
    _renderBooks: function (books) {
        var $booksContainer = this.$target.find('.books-container');
        $booksContainer.empty();
        
        books.forEach(function (book) {
            var $bookCard = $('<div class="book-card">')
                .append($('<div class="book-image">')
                    .append($('<img>').attr('src', book.image_url || '/web/static/img/placeholder.png'))
                )
                .append($('<div class="book-info">')
                    .append($('<h5 class="book-title">').text(book.name))
                    .append($('<p class="book-author">').text(book.author || ''))
                    .append($('<div class="book-availability">')
                        .append($('<span class="badge">')
                            .addClass(book.availability === 'available' ? 'bg-success' : 'bg-danger')
                            .text(book.availability === 'available' ? 'Available' : 'Not Available')
                        )
                    )
                );
            $booksContainer.append($bookCard);
        });
    },

    /**
     * Clean for save
     */
    cleanForSave: function () {
        // Remove editor-specific attributes
        this.$target.removeAttr('data-category-filter data-availability-filter data-sort-order');
    },
});

/**
 * Library Search Snippet Options
 */
options.registry.LibrarySearchSnippet = options.Class.extend({
    
    /**
     * Set search placeholder text
     */
    setPlaceholder: function (previewMode, widgetValue, params) {
        var placeholder = widgetValue || 'Search books...';
        this.$target.find('.search-input').attr('placeholder', placeholder);
    },

    /**
     * Show/hide category filter
     */
    toggleCategoryFilter: function (previewMode, widgetValue, params) {
        var show = widgetValue === 'true';
        this.$target.find('.category-filter').toggle(show);
    },

    /**
     * Show/hide author filter
     */
    toggleAuthorFilter: function (previewMode, widgetValue, params) {
        var show = widgetValue === 'true';
        this.$target.find('.author-filter').toggle(show);
    },

    /**
     * Set search form action
     */
    setSearchAction: function (previewMode, widgetValue, params) {
        var action = widgetValue || '/library';
        this.$target.find('.search-form').attr('action', action);
    },
});

/**
 * Library Statistics Snippet Options
 */
options.registry.LibraryStatsSnippet = options.Class.extend({
    
    /**
     * Refresh statistics
     */
    refreshStats: function (previewMode, widgetValue, params) {
        var self = this;
        
        this._rpc({
            route: '/library/snippet/stats',
            params: {}
        }).then(function (data) {
            if (data) {
                self._updateStats(data);
            }
        });
    },

    /**
     * Update statistics display
     */
    _updateStats: function (stats) {
        this.$target.find('.stat-total-books').text(stats.total_books || 0);
        this.$target.find('.stat-available-books').text(stats.available_books || 0);
        this.$target.find('.stat-borrowed-books').text(stats.borrowed_books || 0);
        this.$target.find('.stat-total-users').text(stats.total_users || 0);
    },

    /**
     * Set display style
     */
    setDisplayStyle: function (previewMode, widgetValue, params) {
        var style = widgetValue || 'cards';
        this.$target.removeClass('style-cards style-counters style-progress');
        this.$target.addClass('style-' + style);
    },
});

return {
    LibraryBookSnippet: options.registry.LibraryBookSnippet,
    LibrarySearchSnippet: options.registry.LibrarySearchSnippet,
    LibraryStatsSnippet: options.registry.LibraryStatsSnippet,
};

});