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

        // Initialize PDF viewer handling for mobile
        this._initPDFViewer();

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

    /**
     * Initialize PDF viewer with mobile support
     */
    _initPDFViewer: function () {
        const $pdfContainers = this.$('.pdf-container');
        if ($pdfContainers.length === 0) {
            return;
        }

        // Detect mobile devices
        const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
        const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);

        $pdfContainers.each((index, container) => {
            const $container = $(container);
            const $object = $container.find('.pdf-object');
            const $iframe = $container.find('.pdf-iframe');

            if (isMobile) {
                // For mobile devices, especially iOS which has poor PDF iframe support
                // Add touch event handling to improve scrolling
                $iframe.css({
                    'overflow': 'auto',
                    '-webkit-overflow-scrolling': 'touch',
                    'height': '100%'
                });

                // For iOS, try to use object tag with proper fallback
                if (isIOS) {
                    // iOS Safari doesn't handle PDFs in iframes well
                    // The object tag works better, but still limited
                    $iframe.css('display', 'none');

                    // Add a helper message for users
                    const pdfUrl = $object.attr('data') || $iframe.attr('src');
                    if (pdfUrl && !$container.find('.mobile-pdf-hint').length) {
                        $container.append(`
                            <div class="mobile-pdf-hint" style="position: absolute; top: 10px; right: 10px; z-index: 100;">
                                <a href="${pdfUrl}" target="_blank" class="btn btn-sm btn-primary">
                                    <i class="fa fa-external-link"></i> Open in New Tab
                                </a>
                            </div>
                        `);
                    }
                }
            }

            // Handle object load errors
            $object.on('error', function() {
                // If object fails to load, show iframe
                $object.hide();
                $iframe.show();
            });
        });
    },
});

export default publicWidget.registry.LibraryMedia;
