document.addEventListener('DOMContentLoaded', async () => {
    const gridLoader = document.getElementById('policy-grid-loader');
    const gridContainer = document.getElementById('policy-grid-container');
    const gridView = document.getElementById('policy-grid-view');
    const headerEl = document.getElementById('legal-header');
    
    const readerLoader = document.getElementById('policy-reader-loader');
    const readerView = document.getElementById('policy-reader-view');
    const readerBody = document.getElementById('policy-body');
    const titleEl = document.getElementById('policy-title');
    const textEl = document.getElementById('policy-text');

    let allPolicies = [];

    // Get policy slug from URL query params (e.g. ?policy=privacy-policy)
    const urlParams = new URLSearchParams(window.location.search);
    const requestedSlug = urlParams.get('policy');

    try {
        allPolicies = await api.get('/public/policies');
        
        if (!allPolicies || allPolicies.length === 0) {
            gridLoader.classList.add('hidden');
            gridContainer.classList.remove('hidden');
            gridContainer.innerHTML = '<div class="col-span-3 text-center text-gray-500 py-12">No policies have been published yet.</div>';
            return;
        }

        // Render Grid
        gridContainer.innerHTML = '';
        allPolicies.forEach(policy => {
            const card = document.createElement('a');
            card.href = `/regulations?policy=${policy.slug}`;
            card.className = "bg-base-100 hover:bg-base-200 border border-white/5 hover:border-primary/50 transition-all rounded-3xl p-8 flex flex-col items-center text-center group shadow-xl hover:shadow-primary/10 cursor-pointer";
            
            card.innerHTML = `
                <div class="text-5xl mb-6 transform group-hover:scale-110 transition-transform">${policy.icon || '📜'}</div>
                <h3 class="text-2xl font-bold text-white mb-4 group-hover:text-primary transition-colors">${policy.title}</h3>
                <p class="text-gray-400 text-sm leading-relaxed mb-8 flex-grow">${policy.description || 'Read our ' + policy.title}</p>
                <div class="text-primary mt-auto">
                    <svg class="w-6 h-6 inline-block transform group-hover:translate-x-2 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"></path></svg>
                </div>
            `;
            gridContainer.appendChild(card);
        });

        gridLoader.classList.add('hidden');
        gridContainer.classList.remove('hidden');

        // If a specific policy is requested, show reader view
        if (requestedSlug) {
            const targetPolicy = allPolicies.find(p => p.slug === requestedSlug);
            if (targetPolicy) {
                showReaderView(targetPolicy);
            }
        }

    } catch (error) {
        console.error("Failed to load policies:", error);
        gridLoader.classList.add('hidden');
        gridContainer.classList.remove('hidden');
        gridContainer.innerHTML = '<div class="col-span-3 text-center text-red-500 py-12">Error loading legal documents. Please try again later.</div>';
    }

    function showReaderView(policy) {
        // Hide Grid and Header
        gridView.classList.add('hidden');
        headerEl.classList.add('hidden');
        
        // Show Reader
        readerView.classList.remove('hidden');
        readerLoader.classList.add('hidden');
        readerBody.classList.remove('hidden');
        
        titleEl.textContent = policy.title;
        textEl.innerHTML = policy.content_html;
        
        // Scroll to top
        window.scrollTo({ top: 0, behavior: 'instant' });
    }
});
