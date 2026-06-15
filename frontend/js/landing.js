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
            {step_num: "01", title: "Create your account", description: "Sign up in 60 seconds. No credit card required. Your workspace is provisioned instantly."},
            {step_num: "02", title: "Get 10 free starter credits", description: "Use credits for AI reconciliation, bulk exports, SMS notifications and report generation."},
            {step_num: "03", title: "Set up your workspace", description: "Add your organisation details, care team, clients and funding sources \u2014 guided step-by-step."},
            {step_num: "04", title: "Manage billing & finance", description: "Issue invoices, approve timesheets, run payroll and track expenses \u2014 all in one dashboard."},
            {step_num: "05", title: "Scale with team & subscriptions", description: "Invite your full team, upgrade your plan, add credits and integrate with your existing tools."}
        ];
        
        if(!faqData) faqData = [
            {question: "What is LeadFlow.ai?", answer: "LeadFlow.ai is an intelligent outreach platform that automatically matches templates to your leads using AI."},
            {question: "How does the 10 starter credits work?", answer: "You get 10 free credits upon signup to test out our AI matching engine."},
            {question: "Which countries are supported?", answer: "We support businesses globally for email sending."},
            {question: "Can I manage multiple branches?", answer: "Yes, our enterprise plan supports multi-branch management."},
            {question: "Is there a free trial?", answer: "We offer a 14-day free trial on all paid plans."}
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

    } catch (e) {
        console.error("Failed to load landing settings", e);
    }

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
