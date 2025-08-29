/* Website Library JavaScript */

document.addEventListener('DOMContentLoaded', function() {
    
    // Add to cart animation
    const addToCartButtons = document.querySelectorAll('form[action="/library/cart/add"] button[type="submit"]');
    addToCartButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            const originalText = this.innerHTML;
            this.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Adding...';
            this.disabled = true;
            
            // Re-enable after form submission
            setTimeout(() => {
                this.innerHTML = originalText;
                this.disabled = false;
            }, 2000);
        });
    });
    
    // Search form enhancement
    const searchForm = document.querySelector('.library-search-form');
    if (searchForm) {
        const searchInput = searchForm.querySelector('input[name="search"]');
        if (searchInput) {
            searchInput.addEventListener('keyup', function(e) {
                if (e.key === 'Enter') {
                    searchForm.submit();
                }
            });
        }
    }
    
    // Category filter highlighting
    const categoryButtons = document.querySelectorAll('.library-category-filter .btn');
    categoryButtons.forEach(button => {
        button.addEventListener('click', function() {
            categoryButtons.forEach(btn => btn.classList.remove('active'));
            this.classList.add('active');
        });
    });
    
    // Book card hover effects
    const bookCards = document.querySelectorAll('.library-book-card');
    bookCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-5px)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });
    
    // Cart update notifications
    if (window.location.pathname === '/library/cart') {
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('added') === '1') {
            showNotification('Book added to cart successfully!', 'success');
        }
    }
    
    function showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        notification.style.top = '20px';
        notification.style.right = '20px';
        notification.style.zIndex = '9999';
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }
});