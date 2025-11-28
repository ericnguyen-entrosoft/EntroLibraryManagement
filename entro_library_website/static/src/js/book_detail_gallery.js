/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.BookDetailGallery = publicWidget.Widget.extend({
    selector: '.js_library_book',
    events: {
        'click .thumbnail-item': '_onThumbnailClick',
        'click #main-image-container': '_onMainImageClick',
        'click #thumb-prev': '_onThumbPrev',
        'click #thumb-next': '_onThumbNext',
    },

    start: function () {
        this._super.apply(this, arguments);
        this._initializeGallery();
        this.currentIndex = 0;
        this.totalImages = this.$('.thumbnail-item').length;
    },

    _initializeGallery: function () {
        // Initialize lightGallery
        const $lightgallery = this.$('#lightgallery-book-media');

        if ($lightgallery.length && typeof lightGallery !== 'undefined') {
            lightGallery(document.getElementById('lightgallery-book-media'), {
                speed: 300,
                selector: '.include-in-gallery',
                download: false,
                thumbnail: true,
                animateThumb: true,
                zoomFromOrigin: false,
                allowMediaOverlap: true,
                toggleThumb: true,
            });
        }
    },

    _onThumbnailClick: function (ev) {
        ev.preventDefault();
        const $thumb = $(ev.currentTarget);
        const index = parseInt($thumb.data('index'));

        // Update main image
        this._updateMainImage(index);

        // Update active state
        this.$('.thumbnail-item').removeClass('active');
        $thumb.addClass('active');

        this.currentIndex = index;
    },

    _updateMainImage: function (index) {
        const $galleryItem = this.$(`#lightgallery-item-${index}`);
        const newSrc = $galleryItem.attr('href');

        if (newSrc) {
            this.$('#main-book-image').attr('src', newSrc);
        }
    },

    _onMainImageClick: function (ev) {
        // Open lightGallery at current index
        const $galleryItem = this.$(`#lightgallery-item-${this.currentIndex}`);
        if ($galleryItem.length) {
            $galleryItem.trigger('click');
        }
    },

    _onThumbPrev: function (ev) {
        ev.preventDefault();
        if (this.currentIndex > 0) {
            this.currentIndex--;
            this._updateMainImage(this.currentIndex);
            this.$('.thumbnail-item').removeClass('active');
            this.$(`.thumbnail-item[data-index="${this.currentIndex}"]`).addClass('active');
            this._scrollThumbnailIntoView(this.currentIndex);
        }
    },

    _onThumbNext: function (ev) {
        ev.preventDefault();
        if (this.currentIndex < this.totalImages - 1) {
            this.currentIndex++;
            this._updateMainImage(this.currentIndex);
            this.$('.thumbnail-item').removeClass('active');
            this.$(`.thumbnail-item[data-index="${this.currentIndex}"]`).addClass('active');
            this._scrollThumbnailIntoView(this.currentIndex);
        }
    },

    _scrollThumbnailIntoView: function (index) {
        const $track = this.$('.thumbnail-slider-track');
        const thumbWidth = 56 + 8; // width + gap
        const containerWidth = this.$('.thumbnail-content').width();
        const visibleThumbs = Math.floor(containerWidth / thumbWidth);

        let translateX = 0;
        if (index >= visibleThumbs) {
            translateX = -(index - visibleThumbs + 1) * thumbWidth;
        }

        $track.css('transform', `translateX(${translateX}px)`);

        // Update prev/next button states
        this.$('#thumb-prev').toggleClass('disabled', index === 0);
        this.$('#thumb-next').toggleClass('disabled', index === this.totalImages - 1);
    },
});

export default publicWidget.registry.BookDetailGallery;
