/* ═══════════════════════════════════════════════════════════
   FINDME – MAIN JAVASCRIPT
   Theme Switcher, Sidebar, Micro-interactions
   ═══════════════════════════════════════════════════════════ */

(function() {
    'use strict';

    /* ── Theme Switcher ── */
    var THEME_KEY = 'findme-theme';

    function getPreferredTheme() {
        var stored = localStorage.getItem(THEME_KEY);
        if (stored) return stored;
        return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }

    function setTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem(THEME_KEY, theme);
        updateThemeIcon(theme);
    }

    function updateThemeIcon(theme) {
        document.querySelectorAll('.theme-toggle').forEach(function(btn) {
            var icon = btn.querySelector('i');
            if (icon) {
                icon.className = theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
            }
        });
    }

    function toggleTheme() {
        var current = document.documentElement.getAttribute('data-theme') || 'light';
        setTheme(current === 'dark' ? 'light' : 'dark');
    }

    // Apply theme immediately
    setTheme(getPreferredTheme());

    /* ── DOM Ready ── */
    document.addEventListener('DOMContentLoaded', function() {

        // Theme toggle buttons
        document.querySelectorAll('.theme-toggle').forEach(function(btn) {
            btn.addEventListener('click', toggleTheme);
        });

        // Sidebar toggle (mobile)
        var sidebarToggle = document.getElementById('sidebarToggle');
        var sidebar = document.getElementById('sidebar');
        var sidebarOverlay = document.getElementById('sidebarOverlay');

        if (sidebarToggle && sidebar) {
            sidebarToggle.style.display = 'flex';
            sidebarToggle.addEventListener('click', function() {
                sidebar.classList.toggle('open');
                if (sidebarOverlay) sidebarOverlay.classList.toggle('active');
                document.body.style.overflow = sidebar.classList.contains('open') ? 'hidden' : '';
            });
            if (sidebarOverlay) {
                sidebarOverlay.addEventListener('click', function() {
                    sidebar.classList.remove('open');
                    sidebarOverlay.classList.remove('active');
                    document.body.style.overflow = '';
                });
            }
        }

        // Show sidebar toggle on mobile
        function checkSidebarToggle() {
            var st = document.getElementById('sidebarToggle');
            if (st) {
                st.style.display = window.innerWidth <= 768 ? 'flex' : 'none';
            }
        }
        checkSidebarToggle();
        window.addEventListener('resize', checkSidebarToggle);

        // Public nav toggle (mobile)
        var navToggle = document.getElementById('navToggle');
        var navLinks = document.getElementById('navLinks');
        if (navToggle && navLinks) {
            navToggle.addEventListener('click', function() {
                navLinks.classList.toggle('active');
            });
        }

        // Dropdown toggle
        document.querySelectorAll('.nav-dropdown > .dropdown-toggle').forEach(function(toggle) {
            toggle.addEventListener('click', function(e) {
                e.preventDefault();
                this.parentElement.classList.toggle('active');
            });
        });
        document.addEventListener('click', function(e) {
            document.querySelectorAll('.nav-dropdown.active').forEach(function(drop) {
                if (!drop.contains(e.target)) drop.classList.remove('active');
            });
        });

        // Navbar scroll effect
        var navbar = document.getElementById('publicNavbar');
        if (navbar) {
            window.addEventListener('scroll', function() {
                navbar.classList.toggle('scrolled', window.scrollY > 20);
            });
        }

        // Flash message auto-dismiss
        document.querySelectorAll('.flash-message').forEach(function(msg) {
            setTimeout(function() {
                msg.style.opacity = '0';
                msg.style.transform = 'translateY(-10px)';
                msg.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                setTimeout(function() {
                    if (msg.parentElement) msg.parentElement.removeChild(msg);
                }, 300);
            }, 5000);
        });

        // Form submit loading state
        document.querySelectorAll('form').forEach(function(form) {
            form.addEventListener('submit', function(e) {
                var submitBtn = form.querySelector('button[type="submit"]');
                if (submitBtn && !submitBtn.disabled) {
                    submitBtn.disabled = true;
                    var originalText = submitBtn.innerHTML;
                    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
                    submitBtn.classList.add('btn-loading');
                    // Restore after 10s timeout
                    setTimeout(function() {
                        submitBtn.disabled = false;
                        submitBtn.innerHTML = originalText;
                        submitBtn.classList.remove('btn-loading');
                    }, 10000);
                }
            });
        });

        // Intersection observer for fade-in animations
        if ('IntersectionObserver' in window) {
            var observer = new IntersectionObserver(function(entries) {
                entries.forEach(function(entry) {
                    if (entry.isIntersecting) {
                        entry.target.classList.add('animate-fade-in-up');
                        observer.unobserve(entry.target);
                    }
                });
            }, { threshold: 0.08 });

            document.querySelectorAll('.stat-card, .feature-card, .action-card, .dash-card, .step-card, .ai-match-card').forEach(function(el) {
                observer.observe(el);
            });
        }

        // Active sidebar link highlight
        if (sidebar) {
            var currentPath = window.location.pathname;
            sidebar.querySelectorAll('a[href]').forEach(function(link) {
                if (link.getAttribute('href') === currentPath) {
                    link.classList.add('active');
                }
            });
        }

        // Smooth scroll for anchor links
        document.querySelectorAll('a[href^="#"]').forEach(function(anchor) {
            anchor.addEventListener('click', function(e) {
                var target = document.querySelector(this.getAttribute('href'));
                if (target) {
                    e.preventDefault();
                    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            });
        });
    });

    // Global functions
    window.toggleTheme = toggleTheme;

})();

// ── Image preview ──
function previewImage(event) {
    var preview = document.getElementById('imagePreview');
    var img = document.getElementById('previewImg');
    if (event.target.files && event.target.files[0]) {
        var reader = new FileReader();
        reader.onload = function(e) {
            img.src = e.target.result;
            preview.style.display = 'block';
            preview.style.animation = 'fadeIn 0.3s ease';
        };
        reader.readAsDataURL(event.target.files[0]);
    } else {
        preview.style.display = 'none';
        img.src = '';
    }
}
