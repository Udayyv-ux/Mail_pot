/**
 * Landing Page Logic
 */
document.addEventListener('DOMContentLoaded', async () => {
    // Navbar scroll effect
    window.addEventListener('scroll', () => {
        if (window.scrollY > 50) {
            document.querySelector('.navbar').classList.add('scrolled');
        } else {
            document.querySelector('.navbar').classList.remove('scrolled');
        }
    });

    // Check if logged in
    const user = await auth.getCurrentUser();
    if (user) {
        document.getElementById('nav-login').style.display = 'none';
        document.getElementById('nav-signup').style.display = 'none';
        document.getElementById('nav-admin-login').style.display = 'none';
        const portalBtn = document.getElementById('nav-portal');
        portalBtn.style.display = 'inline-block';
        portalBtn.href = user.role === 'admin' ? '/admin/' : '/client/';
    } else {
        const loginBtn = document.getElementById('nav-login');
        const signupBtn = document.getElementById('nav-signup');
        const adminBtn = document.getElementById('nav-admin-login');
        
        loginBtn.style.display = 'inline-block';
        signupBtn.style.display = 'inline-block';
        adminBtn.style.display = 'inline-block';
        
        const handleAuth = (e) => { e.preventDefault(); auth.login(); };
        loginBtn.addEventListener('click', handleAuth);
        signupBtn.addEventListener('click', handleAuth);
        adminBtn.addEventListener('click', handleAuth);
    }

    // Load Settings
    try {
        const settings = await api.get('/public/settings');
        if (settings.app_name) document.getElementById('app-name').textContent = settings.app_name;
        if (settings.hero_title) document.getElementById('hero-title').textContent = settings.hero_title;
        if (settings.hero_subtitle) document.getElementById('hero-subtitle').textContent = settings.hero_subtitle;
        if (settings.hero_cta_text) document.getElementById('hero-cta').textContent = settings.hero_cta_text;
        
        if (settings.features_json) {
            const features = JSON.parse(settings.features_json);
            const grid = document.getElementById('features-grid');
            grid.innerHTML = '';
            features.forEach(f => {
                grid.innerHTML += `
                    <div class="feature-card glass">
                        <div class="feature-icon">${f.icon}</div>
                        <h3>${f.title}</h3>
                        <p>${f.desc}</p>
                    </div>
                `;
            });
        }
    } catch (e) {
        console.error("Failed to load settings", e);
    }

    // Load Plans
    try {
        const plans = await api.get('/public/plans');
        const grid = document.getElementById('pricing-grid');
        grid.innerHTML = '';
        plans.forEach(plan => {
            let features = [];
            try { features = JSON.parse(plan.features_json); } catch(e){}
            
            let featureHtml = features.map(f => `<li>${f}</li>`).join('');
            
            grid.innerHTML += `
                <div class="pricing-card glass ${plan.is_featured ? 'featured' : ''}">
                    ${plan.is_featured ? '<div class="featured-badge">Most Popular</div>' : ''}
                    <h3>${plan.name}</h3>
                    <p class="text-secondary">${plan.description}</p>
                    <div class="price">₹${plan.price_monthly}<span>/mo</span></div>
                    <ul class="pricing-features">${featureHtml}</ul>
                    <button class="btn btn-primary w-100" onclick="auth.login()">Choose ${plan.name}</button>
                </div>
            `;
        });
    } catch (e) {
        console.error("Failed to load plans", e);
    }

    // Demo Form
    document.getElementById('demo-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = e.target.querySelector('button');
        btn.textContent = 'Sending...';
        btn.disabled = true;

        const data = {
            name: document.getElementById('demo-name').value,
            email: document.getElementById('demo-email').value,
            company: document.getElementById('demo-company').value,
            message: document.getElementById('demo-message').value
        };

        try {
            await api.post('/public/demo-request', data);
            e.target.innerHTML = '<div class="alert alert-success">Thank you! Our team will contact you shortly.</div>';
        } catch (err) {
            components.showToast(err.message, 'error');
            btn.textContent = 'Request Demo';
            btn.disabled = false;
        }
    });
});
