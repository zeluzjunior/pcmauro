// Main JavaScript file for Django Project

document.addEventListener('DOMContentLoaded', function() {
    // Sidebar Toggle Functionality
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebar = document.querySelector('.sidebar');
    const sidebarWrapper = document.getElementById('sidebar');
    const mainContent = document.getElementById('mainContent');
    
    // Check localStorage for saved sidebar state
    const sidebarCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
    
    function toggleSidebar() {
        if (sidebar && sidebarWrapper) {
            console.log('Toggling sidebar...', { sidebar, sidebarWrapper });
            sidebar.classList.toggle('collapsed');
            sidebarWrapper.classList.toggle('collapsed');
            const isCollapsed = sidebar.classList.contains('collapsed');
            
            console.log('Sidebar collapsed:', isCollapsed);
            
            // Update localStorage
            localStorage.setItem('sidebarCollapsed', isCollapsed);
        } else {
            console.error('Sidebar elements not found:', { sidebar, sidebarWrapper });
        }
    }
    
    function initializeSidebar() {
        if (sidebar && sidebarWrapper && sidebarCollapsed) {
            sidebar.classList.add('collapsed');
            sidebarWrapper.classList.add('collapsed');
        }
        
        // Handle responsive behavior on window resize
        function handleResize() {
            if (window.innerWidth < 768) {
                // Mobile: sidebar should be hidden by default
                if (sidebarWrapper) {
                    sidebarWrapper.classList.remove('show');
                    sidebarWrapper.classList.remove('collapsed');
                }
                if (sidebar) {
                    sidebar.classList.remove('collapsed');
                }
            } else {
                // Desktop: restore saved state
                if (sidebarCollapsed && sidebar && sidebarWrapper) {
                    sidebar.classList.add('collapsed');
                    sidebarWrapper.classList.add('collapsed');
                }
            }
        }
        
        // Initial resize check
        handleResize();
        
        // Listen for resize events
        window.addEventListener('resize', handleResize);
    }
    
    // Initialize sidebar on page load
    initializeSidebar();
    
    // Add click event to toggle button
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('Sidebar toggle clicked');
            
            if (window.innerWidth < 768) {
                // Mobile: toggle show class
                if (sidebarWrapper) {
                    sidebarWrapper.classList.toggle('show');
                }
            } else {
                // Desktop: toggle collapsed state
                toggleSidebar();
            }
        });
    } else {
        console.error('Sidebar toggle button not found!');
    }
    
    // Close sidebar on mobile when clicking outside
    if (window.innerWidth < 768) {
        document.addEventListener('click', function(event) {
            if (sidebarWrapper && !sidebarWrapper.contains(event.target) && 
                !sidebarToggle.contains(event.target) && 
                sidebarWrapper.classList.contains('show')) {
                sidebarWrapper.classList.remove('show');
            }
        });
    }
    
    // Initialize sidebar collapse buttons - use Bootstrap's built-in events
    const collapseButtons = document.querySelectorAll('[data-bs-toggle="collapse"]');
    collapseButtons.forEach(function(button) {
        const targetId = button.getAttribute('data-bs-target');
        const targetElement = document.querySelector(targetId);
        
        if (targetElement) {
            // Set initial state based on current visibility
            if (targetElement.classList.contains('show')) {
                button.classList.remove('collapsed');
                button.setAttribute('aria-expanded', 'true');
            } else {
                button.classList.add('collapsed');
                button.setAttribute('aria-expanded', 'false');
            }
            
            // Update button state when collapse is shown/hidden
            targetElement.addEventListener('show.bs.collapse', function() {
                button.classList.remove('collapsed');
                button.setAttribute('aria-expanded', 'true');
            });
            
            targetElement.addEventListener('hide.bs.collapse', function() {
                button.classList.add('collapsed');
                button.setAttribute('aria-expanded', 'false');
            });
        }
    });
    
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Add fade-in animation to cards
    const cards = document.querySelectorAll('.card');
    cards.forEach(card => {
        card.classList.add('fade-in');
    });

    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Form validation enhancement - ONLY for forms with .needs-validation class
    // Forms without this class will submit normally without any JavaScript interference
    const forms = document.querySelectorAll('.needs-validation');
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            // Check if form has novalidate attribute
            const hasNovalidate = form.hasAttribute('novalidate');
            
            console.log('Form submit event (needs-validation):', {
                form: form.id || form.className,
                hasNovalidate: hasNovalidate,
                action: form.action,
                method: form.method
            });
            
            if (hasNovalidate) {
                // Forms with novalidate: just add styling, DON'T prevent submission
                // Let Django handle server-side validation
                console.log('Form has novalidate - allowing submission');
                form.classList.add('was-validated');
                // CRITICAL: Don't call preventDefault() - allow form to submit
                // Just return without preventing - form will submit normally
                return; // Exit early, form will submit normally
            } else {
                // Forms without novalidate: use HTML5 client-side validation
                console.log('Form without novalidate - checking validity');
                if (!form.checkValidity()) {
                    console.log('Form validation failed - preventing submission');
                    event.preventDefault();
                    event.stopPropagation();
                } else {
                    console.log('Form validation passed - allowing submission');
                }
                form.classList.add('was-validated');
            }
        });
    });

    // Auto-hide alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // Gallery item hover effects with enhanced interactions
    const galleryItems = document.querySelectorAll('.gallery-item');
    galleryItems.forEach(item => {
        const image = item.querySelector('.gallery-image');
        const overlay = item.querySelector('.gallery-overlay');
        const link = item.querySelector('.gallery-link');
        
        // Add smooth cursor tracking effect
        item.addEventListener('mouseenter', function() {
            // Add a class to track hover state
            this.classList.add('gallery-hovered');
            
            // Enhance the overlay appearance
            if (overlay) {
                overlay.style.transition = 'opacity 0.3s ease, background-color 0.3s ease';
            }
            
            // Add glow effect to link
            if (link) {
                link.style.transition = 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
            }
        });
        
        // Add mouse move effect for parallax-like interaction
        item.addEventListener('mousemove', function(e) {
            if (this.classList.contains('gallery-hovered') && image) {
                const rect = this.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;
                const centerX = rect.width / 2;
                const centerY = rect.height / 2;
                const moveX = (x - centerX) / centerX * 5;
                const moveY = (y - centerY) / centerY * 5;
                
                // Subtle image movement on hover
                image.style.transform = `scale(1.05) translate(${moveX}px, ${moveY}px)`;
            }
        });
        
        item.addEventListener('mouseleave', function() {
            this.classList.remove('gallery-hovered');
            
            // Reset image transform
            if (image) {
                image.style.transform = 'scale(1) translate(0, 0)';
            }
            
            // Reset styles
            if (overlay) {
                overlay.style.transition = 'opacity 0.3s ease';
            }
            
            if (link) {
                link.style.transition = 'all 0.3s ease';
            }
        });
    });

    // Handle navbar links that toggle sidebar sections
    document.querySelectorAll('[data-sidebar-toggle]').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const collapseId = this.getAttribute('data-sidebar-toggle');
            const sidebarButton = document.querySelector(`[data-bs-target="#${collapseId}"]`);
            if (sidebarButton) {
                sidebarButton.click();
                // Close mobile navbar if open
                const navbarCollapse = document.getElementById('navbarNav');
                if (navbarCollapse && navbarCollapse.classList.contains('show')) {
                    const bsCollapse = new bootstrap.Collapse(navbarCollapse);
                    bsCollapse.hide();
                }
            }
        });
    });

    // Handle "Consultar" dropdown items
    const consultarMap = {
        'plano': 'plano-collapse',
        'preventiva': 'preventiva-collapse',
        'corretiva': 'corretiva-collapse',
        'terceiro': 'terceiro-collapse',
        'ordens': 'ordens-collapse',
        'maquinas': 'maquinas-collapse',
        'manutentor': 'manutentor-collapse',
        'local': 'local-collapse',
        'itens': 'itens-collapse',
        'visitas': 'visitas-collapse'
    };

    function highlightConsultarLink(collapseId) {
        const collapseElement = document.getElementById(collapseId);
        if (!collapseElement) return;
        
        const consultarLinks = collapseElement.querySelectorAll('a');
        consultarLinks.forEach(sidebarLink => {
            if (sidebarLink.textContent.trim().includes('Consultar')) {
                sidebarLink.scrollIntoView({ behavior: 'smooth', block: 'center' });
                sidebarLink.style.backgroundColor = 'rgba(255, 152, 0, 0.3)';
                sidebarLink.style.transition = 'background-color 0.3s ease';
                sidebarLink.style.borderRadius = '4px';
                sidebarLink.style.padding = '0.25rem 0.5rem';
                
                setTimeout(() => {
                    sidebarLink.style.backgroundColor = '';
                }, 2000);
            }
        });
    }

    document.querySelectorAll('[data-consultar]').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const consultarType = this.getAttribute('data-consultar');
            const collapseId = consultarMap[consultarType];
            
            if (collapseId) {
                const collapseElement = document.getElementById(collapseId);
                const sidebarButton = document.querySelector(`[data-bs-target="#${collapseId}"]`);
                
                if (sidebarButton && collapseElement) {
                    // Check if section is collapsed
                    const isCollapsed = !collapseElement.classList.contains('show');
                    
                    if (isCollapsed) {
                        // Open the section first
                        sidebarButton.click();
                        
                        // Wait for collapse animation to complete, then highlight
                        collapseElement.addEventListener('shown.bs.collapse', function() {
                            highlightConsultarLink(collapseId);
                        }, { once: true });
                    } else {
                        // Section already open, just highlight
                        highlightConsultarLink(collapseId);
                    }
                }
                
                // Close mobile navbar if open
                const navbarCollapse = document.getElementById('navbarNav');
                if (navbarCollapse && navbarCollapse.classList.contains('show')) {
                    const bsCollapse = new bootstrap.Collapse(navbarCollapse);
                    bsCollapse.hide();
                }
            }
        });
    });

    // Loading state for buttons - ONLY disable AFTER form starts submitting
    // Don't disable immediately as it can prevent form submission
    const submitButtons = document.querySelectorAll('button[type="submit"]');
    submitButtons.forEach(button => {
        const form = button.closest('form');
        if (form) {
            // Only disable button AFTER form submit event fires
            form.addEventListener('submit', function() {
                const originalText = button.innerHTML;
                button.innerHTML = '<span class="loading me-2"></span>Enviando...';
                button.disabled = true;
                
                // Re-enable after 5 seconds (in case of error)
                setTimeout(() => {
                    button.innerHTML = originalText;
                    button.disabled = false;
                }, 5000);
            }, false); // Use bubble phase, not capture
        }
    });
});

// Utility functions
function showNotification(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    const container = document.querySelector('.container');
    if (container) {
        container.insertBefore(alertDiv, container.firstChild);
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alertDiv);
            bsAlert.close();
        }, 5000);
    }
}

// AJAX helper function
function makeAjaxRequest(url, method = 'GET', data = null) {
    return fetch(url, {
        method: method,
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        },
        body: data ? JSON.stringify(data) : null
    })
    .then(response => response.json())
    .catch(error => {
        console.error('Error:', error);
        showNotification('Erro na requisição', 'danger');
    });
}
