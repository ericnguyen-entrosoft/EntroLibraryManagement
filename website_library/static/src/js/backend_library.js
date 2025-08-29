/* Backend Library Management */

odoo.define('website_library.backend', function (require) {
'use strict';

var AbstractAction = require('web.AbstractAction');
var core = require('web.core');
var framework = require('web.framework');

var _t = core._t;

var LibraryDashboard = AbstractAction.extend({
    template: 'website_library.Dashboard',
    
    init: function (parent, context) {
        this._super(parent, context);
        this.dashboardData = {};
    },

    start: function () {
        var self = this;
        return this._super().then(function () {
            return self._loadDashboardData();
        });
    },

    _loadDashboardData: function () {
        var self = this;
        return this._rpc({
            route: '/library/dashboard/data',
            params: {}
        }).then(function (data) {
            self.dashboardData = data;
            self._renderDashboard();
        });
    },

    _renderDashboard: function () {
        var $dashboard = this.$('.library-dashboard-content');
        
        // Render statistics cards
        this._renderStatsCards();
        
        // Render charts
        this._renderCharts();
        
        // Render recent activities
        this._renderRecentActivities();
    },

    _renderStatsCards: function () {
        var stats = this.dashboardData.stats || {};
        
        var cardsData = [
            {
                title: _t('Total Books'),
                value: stats.total_books || 0,
                icon: 'fa-book',
                color: 'primary'
            },
            {
                title: _t('Available Books'),
                value: stats.available_books || 0,
                icon: 'fa-check-circle',
                color: 'success'
            },
            {
                title: _t('Borrowed Books'),
                value: stats.borrowed_books || 0,
                icon: 'fa-hand-paper',
                color: 'warning'
            },
            {
                title: _t('Overdue Books'),
                value: stats.overdue_books || 0,
                icon: 'fa-exclamation-triangle',
                color: 'danger'
            }
        ];

        var $statsContainer = this.$('.dashboard-stats');
        cardsData.forEach(function (card) {
            var $card = $('<div class="col-md-3 mb-4">')
                .append($('<div class="card border-left-' + card.color + ' shadow h-100 py-2">')
                    .append($('<div class="card-body">')
                        .append($('<div class="row no-gutters align-items-center">')
                            .append($('<div class="col mr-2">')
                                .append($('<div class="text-xs font-weight-bold text-' + card.color + ' text-uppercase mb-1">').text(card.title))
                                .append($('<div class="h5 mb-0 font-weight-bold text-gray-800">').text(card.value))
                            )
                            .append($('<div class="col-auto">')
                                .append($('<i class="fas ' + card.icon + ' fa-2x text-gray-300">'))
                            )
                        )
                    )
                );
            $statsContainer.append($card);
        });
    },

    _renderCharts: function () {
        // Borrowing trends chart
        if (this.dashboardData.borrowing_trends) {
            this._renderBorrowingTrendsChart();
        }
        
        // Popular books chart
        if (this.dashboardData.popular_books) {
            this._renderPopularBooksChart();
        }
    },

    _renderBorrowingTrendsChart: function () {
        var data = this.dashboardData.borrowing_trends;
        var ctx = this.$('#borrowingTrendsChart')[0].getContext('2d');
        
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [{
                    label: _t('Books Borrowed'),
                    data: data.values,
                    borderColor: 'rgb(75, 192, 192)',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: _t('Borrowing Trends')
                    }
                }
            }
        });
    },

    _renderPopularBooksChart: function () {
        var data = this.dashboardData.popular_books;
        var ctx = this.$('#popularBooksChart')[0].getContext('2d');
        
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: [{
                    label: _t('Times Borrowed'),
                    data: data.values,
                    backgroundColor: 'rgba(54, 162, 235, 0.2)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: _t('Most Popular Books')
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    },

    _renderRecentActivities: function () {
        var activities = this.dashboardData.recent_activities || [];
        var $container = this.$('.recent-activities-list');
        
        activities.forEach(function (activity) {
            var $item = $('<div class="d-flex mb-3">')
                .append($('<div class="flex-shrink-0">')
                    .append($('<i class="fas ' + activity.icon + ' text-' + activity.type + '">'))
                )
                .append($('<div class="flex-grow-1 ms-3">')
                    .append($('<h6 class="mb-1">').text(activity.title))
                    .append($('<p class="mb-1 text-muted">').text(activity.description))
                    .append($('<small class="text-muted">').text(activity.time))
                );
            $container.append($item);
        });
    },
});

core.action_registry.add('library_dashboard', LibraryDashboard);

return LibraryDashboard;

});