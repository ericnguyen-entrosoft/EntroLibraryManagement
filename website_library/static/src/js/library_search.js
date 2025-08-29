/* Library Search and Filter */

odoo.define('website_library.search', function (require) {
'use strict';

var publicWidget = require('web.public.widget');
var core = require('web.core');

var _t = core._t;

publicWidget.registry.LibrarySearch = publicWidget.Widget.extend({
    selector: '.library-search-widget',
    events: {
        'input .library-search-input': '_onSearchInput',
        'click .library-category-filter': '_onCategoryFilter',
        'click .library-author-filter': '_onAuthorFilter',
        'change .library-availability-filter': '_onAvailabilityFilter',
        'click .library-sort-option': '_onSortChange',
        'click .library-view-mode': '_onViewModeChange',
        'click .library-clear-filters': '_onClearFilters',
    },

    init: function () {
        this._super.apply(this, arguments);
        this.searchTimeout = null;
        this.activeFilters = {
            search: '',
            category: '',
            author: '',
            availability: '',
            sort: 'name',
        };
    },

    start: function () {
        var def = this._super.apply(this, arguments);
        this._initializeFilters();
        this._setupSearchTypeahead();
        return def;
    },

    /**
     * Initialize filters from URL parameters
     */
    _initializeFilters: function () {
        var urlParams = new URLSearchParams(window.location.search);
        
        this.activeFilters.search = urlParams.get('search') || '';
        this.activeFilters.category = urlParams.get('category') || '';
        this.activeFilters.author = urlParams.get('author') || '';
        this.activeFilters.availability = urlParams.get('availability') || '';
        this.activeFilters.sort = urlParams.get('order') || 'name';

        // Update UI to reflect current filters
        this._updateFilterUI();
    },

    /**
     * Handle search input with debouncing
     */
    _onSearchInput: function (ev) {
        var query = $(ev.currentTarget).val();
        
        clearTimeout(this.searchTimeout);
        this.searchTimeout = setTimeout(function () {
            this.activeFilters.search = query;
            this._applyFilters();
        }.bind(this), 500); // 500ms debounce
    },

    /**
     * Handle category filter selection
     */
    _onCategoryFilter: function (ev) {
        ev.preventDefault();
        var $btn = $(ev.currentTarget);
        var categoryId = $btn.data('category-id') || '';
        
        // Update active state
        $('.library-category-filter').removeClass('active');
        $btn.addClass('active');
        
        this.activeFilters.category = categoryId;
        this._applyFilters();
    },

    /**
     * Handle author filter selection
     */
    _onAuthorFilter: function (ev) {
        ev.preventDefault();
        var $btn = $(ev.currentTarget);
        var authorId = $btn.data('author-id') || '';
        
        // Update active state
        $('.library-author-filter').removeClass('active');
        $btn.addClass('active');
        
        this.activeFilters.author = authorId;
        this._applyFilters();
    },

    /**
     * Handle availability filter change
     */
    _onAvailabilityFilter: function (ev) {
        var availability = $(ev.currentTarget).val();
        this.activeFilters.availability = availability;
        this._applyFilters();
    },

    /**
     * Handle sort option change
     */
    _onSortChange: function (ev) {
        ev.preventDefault();
        var $btn = $(ev.currentTarget);
        var sortOrder = $btn.data('sort') || 'name';
        
        // Update active state
        $('.library-sort-option').removeClass('active');
        $btn.addClass('active');
        
        this.activeFilters.sort = sortOrder;
        this._applyFilters();
    },

    /**
     * Handle view mode change (grid/list)
     */
    _onViewModeChange: function (ev) {
        ev.preventDefault();
        var $btn = $(ev.currentTarget);
        var viewMode = $btn.data('view-mode');
        
        // Update active state
        $('.library-view-mode').removeClass('active');
        $btn.addClass('active');
        
        // Apply view mode
        var $productGrid = $('.library-products-grid');
        $productGrid.removeClass('view-grid view-list').addClass('view-' + viewMode);
        
        // Store preference in localStorage
        localStorage.setItem('library_view_mode', viewMode);
    },

    /**
     * Clear all filters
     */
    _onClearFilters: function (ev) {
        ev.preventDefault();
        
        // Reset all filters
        this.activeFilters = {
            search: '',
            category: '',
            author: '',
            availability: '',
            sort: 'name',
        };
        
        // Clear UI
        $('.library-search-input').val('');
        $('.library-category-filter, .library-author-filter, .library-sort-option').removeClass('active');
        $('.library-category-filter[data-category-id=""], .library-sort-option[data-sort="name"]').addClass('active');
        $('.library-availability-filter').val('');
        
        this._applyFilters();
    },

    /**
     * Apply current filters by updating URL
     */
    _applyFilters: function () {
        var params = new URLSearchParams();
        
        // Add non-empty filters to URL
        Object.keys(this.activeFilters).forEach(function (key) {
            var value = this.activeFilters[key];
            if (value) {
                if (key === 'sort') {
                    params.set('order', value);
                } else {
                    params.set(key, value);
                }
            }
        }.bind(this));
        
        // Update URL and reload page
        var newUrl = window.location.pathname + (params.toString() ? '?' + params.toString() : '');
        window.location.href = newUrl;
    },

    /**
     * Update filter UI to reflect current state
     */
    _updateFilterUI: function () {
        // Update search input
        $('.library-search-input').val(this.activeFilters.search);
        
        // Update category filter
        $('.library-category-filter').removeClass('active');
        $('.library-category-filter[data-category-id="' + this.activeFilters.category + '"]').addClass('active');
        
        // Update author filter
        $('.library-author-filter').removeClass('active');
        $('.library-author-filter[data-author-id="' + this.activeFilters.author + '"]').addClass('active');
        
        // Update availability filter
        $('.library-availability-filter').val(this.activeFilters.availability);
        
        // Update sort option
        $('.library-sort-option').removeClass('active');
        $('.library-sort-option[data-sort="' + this.activeFilters.sort + '"]').addClass('active');
        
        // Update filter count badge
        var filterCount = Object.values(this.activeFilters).filter(function (v) { return v; }).length;
        var $filterBadge = $('.filter-count-badge');
        if (filterCount > 0) {
            $filterBadge.text(filterCount).show();
        } else {
            $filterBadge.hide();
        }
    },

    /**
     * Setup search typeahead/autocomplete
     */
    _setupSearchTypeahead: function () {
        var $searchInput = $('.library-search-input');
        
        if ($searchInput.length && typeof $searchInput.typeahead === 'function') {
            $searchInput.typeahead({
                source: function (query, process) {
                    return $.ajax({
                        url: '/library/search/autocomplete',
                        type: 'GET',
                        data: { query: query },
                        dataType: 'json',
                        success: function (data) {
                            return process(data.suggestions || []);
                        }
                    });
                },
                items: 8,
                minLength: 2,
                showHintOnFocus: true,
            });
        }
    },
});

return publicWidget.registry.LibrarySearch;

});