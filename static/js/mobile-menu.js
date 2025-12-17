/**
 * Mobile drawer menu functionality.
 */

document.addEventListener('DOMContentLoaded', function() {
    const menuToggle = document.getElementById('mobile-menu-toggle');
    const drawer = document.getElementById('mobile-drawer');
    const drawerContent = drawer?.querySelector('.drawer-content');
    const drawerOverlay = document.getElementById('drawer-overlay');
    const drawerClose = document.getElementById('drawer-close');
    const body = document.body;
    
    // Sync username display
    const usernameDisplay = document.getElementById('username-display');
    const drawerUsernameDisplay = document.getElementById('drawer-username-display');
    if (usernameDisplay && drawerUsernameDisplay) {
        const username = usernameDisplay.textContent || 'User';
        drawerUsernameDisplay.textContent = username;
    }
    
    // Sync logout button
    const logoutBtn = document.getElementById('logout-btn');
    const drawerLogoutBtn = document.getElementById('drawer-logout-btn');
    if (logoutBtn && drawerLogoutBtn) {
        drawerLogoutBtn.addEventListener('click', function() {
            if (logoutBtn.onclick) {
                logoutBtn.onclick();
            } else if (typeof logout === 'function') {
                logout();
            }
            closeDrawer();
        });
    }
    
    function openDrawer() {
        if (!drawer || !drawerContent || !drawerOverlay) return;
        
        drawerContent.classList.add('active');
        drawerOverlay.classList.add('active');
        menuToggle?.classList.add('active');
        body.classList.add('drawer-open');
    }
    
    function closeDrawer() {
        if (!drawer || !drawerContent || !drawerOverlay) return;
        
        drawerContent.classList.remove('active');
        drawerOverlay.classList.remove('active');
        menuToggle?.classList.remove('active');
        body.classList.remove('drawer-open');
    }
    
    // Open drawer
    if (menuToggle) {
        menuToggle.addEventListener('click', function(e) {
            e.stopPropagation();
            openDrawer();
        });
    }
    
    // Close drawer
    if (drawerClose) {
        drawerClose.addEventListener('click', closeDrawer);
    }
    
    if (drawerOverlay) {
        drawerOverlay.addEventListener('click', closeDrawer);
    }
    
    // Close drawer when clicking drawer links
    const drawerLinks = drawer?.querySelectorAll('.drawer-link');
    if (drawerLinks) {
        drawerLinks.forEach(link => {
            link.addEventListener('click', function() {
                // Small delay to allow navigation
                setTimeout(closeDrawer, 100);
            });
        });
    }
    
    // Close drawer on escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && drawerContent?.classList.contains('active')) {
            closeDrawer();
        }
    });
    
    // Handle window resize
    window.addEventListener('resize', function() {
        if (window.innerWidth > 768) {
            closeDrawer();
        }
    });
    
    // Prevent body scroll when drawer is open (iOS fix)
    let lastScrollTop = 0;
    if (drawerOverlay) {
        drawerOverlay.addEventListener('touchmove', function(e) {
            if (drawerContent?.classList.contains('active')) {
                e.preventDefault();
            }
        }, { passive: false });
    }
});

