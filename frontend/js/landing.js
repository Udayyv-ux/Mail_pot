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
    try {
        const user = await auth.getCurrentUser();
        const loginBtn = document.getElementById('nav-login');
        const signupBtn = document.getElementById('nav-signup');
        const adminBtn = document.getElementById('nav-admin-login');
        const portalBtn = document.getElementById('nav-portal');
        
        if (user) {
            if(loginBtn) loginBtn.style.display = 'none';
            if(signupBtn) signupBtn.style.display = 'none';
            if(adminBtn) adminBtn.style.display = 'none';
            if(portalBtn) {
                portalBtn.style.display = 'inline-block';
                portalBtn.href = user.role === 'admin' ? '/admin/' : '/client/';
            }
        } else {
            if(loginBtn) loginBtn.style.display = 'inline-block';
            if(signupBtn) signupBtn.style.display = 'inline-block';
            if(adminBtn) adminBtn.style.display = 'inline-block';
            
            const handleAuth = (e) => { e.preventDefault(); auth.login(); };
            if(loginBtn) loginBtn.addEventListener('click', handleAuth);
            if(signupBtn) signupBtn.addEventListener('click', handleAuth);
            if(adminBtn) adminBtn.addEventListener('click', handleAuth);
        }
    } catch(e) {
        console.error("Auth check failed:", e);
    }

    // Load Dynamic Settings (Steps, FAQ, Footer)
    try {
        const settings = await api.get('/public/settings');
        
        let stepsData = null;
        let faqData = null;
        let footerData = null;

        if (settings.LANDING_STEPS) stepsData = JSON.parse(settings.LANDING_STEPS);
        if (settings.LANDING_FAQ) faqData = JSON.parse(settings.LANDING_FAQ);
        if (settings.LANDING_FOOTER) footerData = JSON.parse(settings.LANDING_FOOTER);

        // Fallbacks if not configured yet
        if(!stepsData) stepsData = [
            {step_num: "01", title: "Connect your Google Sheet", description: "Paste your Google Sheet URL. We automatically read your leads instantly without complex setup."},
            {step_num: "02", title: "Define your templates", description: "Create various email templates for different types of clients or outreach scenarios."},
            {step_num: "03", title: "AI matches the message", description: "Our AI engine analyzes each lead's notes and automatically selects the most relevant email template."},
            {step_num: "04", title: "Review & Send", description: "Approve the AI-selected templates and send them. We throttle sending speeds to protect your domain."},
            {step_num: "05", title: "Track in your Sheet", description: "We log the email status and replies right back into your original Google Sheet."}
        ];
        
        if(!faqData) faqData = [
            {question: "What is Sheetx.io?", answer: "Sheetx.io is an intelligent outreach platform that syncs with Google Sheets and uses AI to match the perfect email template to your leads."},
            {question: "Is there a free trial?", answer: "Yes, we offer a 14-day free trial on all paid plans so you can test our AI matching engine."},
            {question: "Do I need to import my leads?", answer: "No importing required! Just paste your Google Sheet URL, and we sync directly with your live data."},
            {question: "Will this affect my domain reputation?", answer: "We use smart sending features like built-in delays and throttling to ensure your domain reputation stays protected while scaling."},
            {question: "Can I bring my own email account?", answer: "Yes! You can connect your existing email accounts via SMTP to send directly from your own domain."}
        ];

        if(!footerData) footerData = {
            "Product": [{name: "Features", url: "#features"}, {name: "Pricing", url: "#pricing"}],
            "Company": [{name: "About Us", url: "#"}, {name: "Blog", url: "#"}, {name: "Careers", url: "#"}],
            "Resources": [{name: "Documentation", url: "#"}, {name: "Help Centre", url: "#"}, {name: "API Docs", url: "#"}],
            "Support": [{name: "Privacy Policy", url: "#"}, {name: "Terms & Conditions", url: "#"}, {name: "Refund Policy", url: "#"}]
        };

        // Render Steps
        const stepsContainer = document.getElementById('landing-steps-container');
        if(stepsContainer && stepsData) {
            stepsContainer.innerHTML = '';
            stepsData.forEach(step => {
                stepsContainer.innerHTML += `
                    <div class="card bg-base-200 border border-white/5 shadow-lg p-6 flex flex-col sm:flex-row items-start gap-4 sm:gap-6 hover:border-primary/30 transition-colors">
                        <div class="flex-shrink-0 w-12 h-12 rounded-xl bg-dark/50 border border-white/10 flex items-center justify-center font-mono font-bold text-primary">
                            ${step.step_num}
                        </div>
                        <div>
                            <h3 class="text-xl font-bold mb-2">${step.title}</h3>
                            <p class="text-gray-400 text-sm">${step.description}</p>
                        </div>
                    </div>
                `;
            });
        }

        // Render FAQ
        const faqContainer = document.getElementById('landing-faq-container');
        if(faqContainer && faqData) {
            faqContainer.innerHTML = '';
            faqData.forEach((faq, idx) => {
                faqContainer.innerHTML += `
                    <div class="collapse collapse-arrow bg-base-200 border border-white/5">
                        <input type="radio" name="faq-accordion" ${idx === 0 ? 'checked="checked"' : ''} /> 
                        <div class="collapse-title text-lg font-bold">
                            ${faq.question}
                        </div>
                        <div class="collapse-content text-gray-400"> 
                            <p>${faq.answer}</p>
                        </div>
                    </div>
                `;
            });
        }

        // Render Footer
        const footerGrid = document.getElementById('landing-footer-grid');
        if(footerGrid && footerData) {
            footerGrid.innerHTML = '';
            Object.keys(footerData).forEach(colName => {
                const links = footerData[colName];
                const linksHtml = links.map(l => `<li><a href="${l.url}" class="text-gray-400 hover:text-white text-sm transition-colors">${l.name}</a></li>`).join('');
                footerGrid.innerHTML += `
                    <div>
                        <h4 class="text-xs font-bold text-gray-500 tracking-wider uppercase mb-4">${colName}</h4>
                        <ul class="space-y-3">
                            ${linksHtml}
                        </ul>
                    </div>
                `;
            });
        }

        // Fetch and Render CMS Policies
        try {
            const policies = await api.get('/public/policies');
            const policiesContainer = document.getElementById('footer-policies');
            if(policiesContainer && policies.length > 0) {
                const links = policies.map(p => `<a href="javascript:void(0)" onclick="viewPolicy('${p.slug}')" class="hover:text-white transition-colors ml-4">${p.title}</a>`);
                policiesContainer.innerHTML = links.join('');
            }
        } catch(e) {
            console.error("Failed to load policies", e);
        }

    } catch (e) {
        console.error("Failed to load landing settings", e);
    }

    // Global function to open policy modal
    window.viewPolicy = async (slug) => {
        try {
            const p = await api.get(`/public/policies/${slug}`);
            document.getElementById('policy-view-title').textContent = p.title;
            document.getElementById('policy-view-content').innerHTML = p.content_html;
            document.getElementById('policy-view-modal').showModal();
        } catch(e) {
            alert("Failed to load policy.");
        }
    };

    // Load Plans
    try {
        const plans = await api.get('/public/plans');
        const grid = document.getElementById('public-plans');
        if(grid) {
            grid.innerHTML = '';
            plans.forEach(plan => {
                let features = [];
                try { features = JSON.parse(plan.features_json); } catch(e){}
                
                let featureHtml = features.map(f => `<li class="flex items-center gap-2"><svg class="w-4 h-4 text-green-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg> ${f}</li>`).join('');
                
                grid.innerHTML += `
                    <div class="card bg-base-200 border border-white/5 hover:border-white/20 transition-all ${plan.is_featured ? 'shadow-primary/20 shadow-2xl scale-105' : ''}">
                        <div class="card-body">
                            ${plan.is_featured ? '<div class="absolute -top-3 left-1/2 -translate-x-1/2 bg-gradient-to-r from-primary to-secondary text-white text-xs font-bold px-3 py-1 rounded-full">Most Popular</div>' : ''}
                            <h3 class="text-xl font-bold">${plan.name}</h3>
                            <div class="my-4"><span class="text-4xl font-extrabold">$${plan.price_monthly}</span><span class="text-gray-400">/mo</span></div>
                            <ul class="text-sm text-gray-300 space-y-3 mb-8 flex-1">
                                <li class="flex items-center gap-2"><svg class="w-4 h-4 text-primary shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path></svg> <b>${plan.email_limit_daily}</b> daily emails</li>
                                ${featureHtml}
                            </ul>
                            <button class="btn btn-primary w-full text-white" onclick="document.getElementById('register-modal').showModal()">Get Started</button>
                        </div>
                    </div>
                `;
            });
        }
    } catch (e) {
        console.error("Failed to load plans", e);
    }
});
