/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.HeroSlider = publicWidget.Widget.extend({
    selector: '.carousel-section',

    start() {
        const self = this;
        return this._super(...arguments).then(function () {
            // Wait a bit for DOM to be fully ready
            setTimeout(() => {
                self._initSlider();
            }, 100);
        });
    },

    _initSlider() {
        console.log('Banner Carousel: Initializing...');
        console.log('Banner Carousel element:', this.el);

        const carouselEl = this.el;
        const slideElements = carouselEl.querySelectorAll('.carousel-item');
        const indicatorElements = carouselEl.querySelectorAll('.carousel-indicators li');

        let currentSlide = 0;
        let slideInterval;

        console.log('Banner Carousel: Found ' + slideElements.length + ' slides');
        console.log('Banner Carousel: Found ' + indicatorElements.length + ' indicators');

        if (slideElements.length > 1) {
            const showSlide = (index) => {
                console.log('Showing slide ' + index);
                // Remove active class from all slides and indicators
                slideElements.forEach(slide => slide.classList.remove('active'));
                indicatorElements.forEach(indicator => indicator.classList.remove('active'));

                // Add active class to current slide and indicator
                slideElements[index].classList.add('active');
                if (indicatorElements[index]) {
                    indicatorElements[index].classList.add('active');
                }
            };

            const nextSlide = () => {
                currentSlide = (currentSlide + 1) % slideElements.length;
                showSlide(currentSlide);
            };

            const prevSlide = () => {
                currentSlide = (currentSlide - 1 + slideElements.length) % slideElements.length;
                showSlide(currentSlide);
            };

            const startSlideshow = () => {
                console.log('Starting carousel auto-advance');
                stopSlideshow();
                slideInterval = setInterval(nextSlide, 5000);
            };

            const stopSlideshow = () => {
                if (slideInterval) {
                    console.log('Stopping carousel');
                    clearInterval(slideInterval);
                    slideInterval = null;
                }
            };

            // Event listeners for indicators
            indicatorElements.forEach((indicator, index) => {
                indicator.addEventListener('click', () => {
                    stopSlideshow();
                    currentSlide = index;
                    showSlide(currentSlide);
                    startSlideshow();
                });
            });

            // Pause on hover
            carouselEl.addEventListener('mouseenter', stopSlideshow);
            carouselEl.addEventListener('mouseleave', startSlideshow);

            // Start the slideshow
            startSlideshow();
        } else {
            console.log('Banner Carousel: Not enough slides for auto-advance');
        }
    },
});

export default publicWidget.registry.HeroSlider;
