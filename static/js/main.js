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

        // Sidebar toggle (mobile / tablet)
        var sidebarToggle = document.getElementById('sidebarToggle');
        var sidebar = document.getElementById('sidebar');
        var sidebarOverlay = document.getElementById('sidebarOverlay');

        function closeSidebar() {
            if (!sidebar) return;
            sidebar.classList.remove('open');
            if (sidebarOverlay) sidebarOverlay.classList.remove('active');
            document.body.classList.remove('nav-open');
            document.body.style.overflow = '';
            if (sidebarToggle) sidebarToggle.setAttribute('aria-expanded', 'false');
        }

        function openSidebar() {
            if (!sidebar) return;
            sidebar.classList.add('open');
            if (sidebarOverlay) sidebarOverlay.classList.add('active');
            document.body.classList.add('nav-open');
            document.body.style.overflow = 'hidden';
            if (sidebarToggle) sidebarToggle.setAttribute('aria-expanded', 'true');
        }

        if (sidebarToggle && sidebar) {
            sidebarToggle.addEventListener('click', function() {
                if (sidebar.classList.contains('open')) {
                    closeSidebar();
                } else {
                    openSidebar();
                }
            });

            // Close after tapping a navigation link on touch devices.
            sidebar.querySelectorAll('a[href]').forEach(function(link) {
                link.addEventListener('click', function() {
                    if (window.innerWidth <= 768) closeSidebar();
                });
            });

            document.addEventListener('keydown', function(e) {
                if (e.key === 'Escape') closeSidebar();
            });
        }

        if (sidebarOverlay) {
            sidebarOverlay.addEventListener('click', closeSidebar);
        }

        // Reset off-canvas state when the viewport grows to desktop size.
        var lastIsMobile = null;
        function handleViewportChange() {
            var isMobile = window.innerWidth <= 768;
            if (lastIsMobile !== null && lastIsMobile !== isMobile && !isMobile) {
                closeSidebar();
            }
            lastIsMobile = isMobile;
        }
        handleViewportChange();
        window.addEventListener('resize', handleViewportChange);
        window.addEventListener('orientationchange', handleViewportChange);

        // Public nav toggle (mobile)
        var navToggle = document.getElementById('navToggle');
        var navLinks = document.getElementById('navLinks');
        if (navToggle && navLinks) {
            navToggle.addEventListener('click', function() {
                var isOpen = navLinks.classList.toggle('active');
                navToggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
            });
            navLinks.querySelectorAll('a').forEach(function(link) {
                link.addEventListener('click', function() {
                    navLinks.classList.remove('active');
                    navToggle.setAttribute('aria-expanded', 'false');
                });
            });
        }

        // Copy table headers onto cells so the mobile card layout can show
        // readable labels (the header row is hidden on small screens).
        document.querySelectorAll('.table-responsive table').forEach(function(table) {
            var headers = Array.prototype.map.call(
                table.querySelectorAll('thead th'),
                function(th) { return th.textContent.trim(); }
            );
            if (!headers.length) return;
            table.querySelectorAll('tbody tr').forEach(function(row) {
                Array.prototype.forEach.call(row.children, function(cell, index) {
                    if (!cell.hasAttribute('data-label') && headers[index]) {
                        cell.setAttribute('data-label', headers[index]);
                    }
                });
            });
        });

        // Turn raw enum values such as "Potential_match" into readable labels.
        document.querySelectorAll('.badge').forEach(function(badge) {
            var text = badge.textContent.trim();
            if (text.indexOf('_') === -1) return;
            var pretty = text.replace(/_+/g, ' ').toLowerCase().replace(/\b\w/g, function(ch) {
                return ch.toUpperCase();
            });
            // Keep the badge element (and its icon) intact, only swap the text.
            var icon = badge.querySelector('i');
            if (icon) {
                badge.textContent = '';
                badge.appendChild(icon);
                badge.appendChild(document.createTextNode(' ' + pretty));
            } else {
                badge.textContent = pretty;
            }
        });

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

        // Form submit loading state (POST forms only; GET searches should not
        // show a fake "Processing..." label).
        document.querySelectorAll('form').forEach(function(form) {
            var method = (form.getAttribute('method') || 'get').toLowerCase();
            if (method !== 'post') return;
            form.addEventListener('submit', function() {
                var submitBtn = form.querySelector('button[type="submit"]');
                if (!submitBtn || submitBtn.disabled) return;
                submitBtn.disabled = true;
                var originalText = submitBtn.innerHTML;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
                submitBtn.classList.add('btn-loading');
                // If the user navigates back, the browser restores the disabled
                // button from the cache - restore it when the page is shown.
                setTimeout(function() {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalText;
                    submitBtn.classList.remove('btn-loading');
                }, 15000);
            });
        });

        // Restore buttons if a bfcache page is shown again.
        window.addEventListener('pageshow', function(event) {
            if (!event.persisted) return;
            document.querySelectorAll('button[type="submit"].btn-loading').forEach(function(btn) {
                btn.disabled = false;
                btn.classList.remove('btn-loading');
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
