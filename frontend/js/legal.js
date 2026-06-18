document.addEventListener('DOMContentLoaded', async () => {
    const sidebar = document.getElementById('policy-sidebar');
    const loader = document.getElementById('policy-loader');
    const body = document.getElementById('policy-body');
    const titleEl = document.getElementById('policy-title');
    const textEl = document.getElementById('policy-text');

    let allPolicies = [];

    // Get policy slug from URL query params (e.g. ?policy=privacy-policy)
    const urlParams = new URLSearchParams(window.location.search);
    const requestedSlug = urlParams.get('policy');

    try {
        allPolicies = await api.get('/public/policies');
        
        if (!allPolicies || allPolicies.length === 0) {
            sidebar.innerHTML = '<p class="text-sm text-gray-500 pl-4">No policies found.</p>';
            loader.classList.add('hidden');
            body.classList.remove('hidden');
            titleEl.textContent = 'Legal & Policies';
            textEl.innerHTML = '<p>No policies have been published yet.</p>';
            return;
        }

        // Render Sidebar
        sidebar.innerHTML = '';
        allPolicies.forEach(policy => {
            const btn = document.createElement('button');
            btn.className = `w-full text-left px-4 py-3 rounded-r-lg policy-tab transition-all hover:bg-white/5`;
            btn.dataset.slug = policy.slug;
            btn.textContent = policy.title;
            
            btn.addEventListener('click', () => {
                selectPolicy(policy.slug);
                // Update URL without reloading
                const newUrl = new URL(window.location);
                newUrl.searchParams.set('policy', policy.slug);
                window.history.pushState({}, '', newUrl);
            });
            
            sidebar.appendChild(btn);
        });

        // Determine which policy to show first
        let targetPolicy = allPolicies[0];
        if (requestedSlug) {
            const found = allPolicies.find(p => p.slug === requestedSlug);
            if (found) targetPolicy = found;
        }

        // Show it
        selectPolicy(targetPolicy.slug);

    } catch (error) {
        console.error("Failed to load policies:", error);
        sidebar.innerHTML = '<p class="text-sm text-red-500 pl-4">Error loading policies.</p>';
        loader.classList.add('hidden');
        titleEl.textContent = 'Error';
        textEl.innerHTML = '<p>Failed to load legal documents. Please try again later.</p>';
        body.classList.remove('hidden');
    }

    function selectPolicy(slug) {
        // Find policy
        const policy = allPolicies.find(p => p.slug === slug);
        if (!policy) return;

        // Update sidebar UI
        document.querySelectorAll('.policy-tab').forEach(btn => {
            if (btn.dataset.slug === slug) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });

        // Update content
        loader.classList.add('hidden');
        body.classList.remove('hidden');
        
        titleEl.textContent = policy.title;
        textEl.innerHTML = policy.content_html;

        // Scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
});
