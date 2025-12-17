/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import publicWidget from "@web/legacy/js/public/public_widget";

/**
 * Library Media Widget
 * Handles interactions for media pages
 */
publicWidget.registry.LibraryMedia = publicWidget.Widget.extend({
    selector: '.js_library_media, .js_library_media_detail',
    events: {
    },

    /**
     * @override
     */
    start: function () {
        // Initialize lightGallery for images
        if (typeof lightGallery !== 'undefined') {
            this._initLightGallery();
        }

        return this._super.apply(this, arguments);
    },

    /**
     * Initialize lightGallery for image viewing
     */
    _initLightGallery: function () {
        const $lightgallery = this.$('#lightgallery');
        if ($lightgallery.length) {
            try {
                lightGallery($lightgallery[0], {
                    speed: 500,
                    plugins: [lgZoom, lgThumbnail],
                    thumbnail: true,
                    zoom: true,
                    download: false,
                });
            } catch (e) {
                console.warn('lightGallery initialization failed:', e);
            }
        }
    },
});

export default publicWidget.registry.LibraryMedia;
