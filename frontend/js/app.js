/**
 * Lead Extractor Pro - Frontend Application
 */

// State
let state = {
    licenseKey: '',
    isActivated: false,
    tier: '',
    email: '',
    currentSearchId: null,
    totalEmails: 0,
    totalLeads: 0,
    searchCount: 0,
    remaining: 0,
};

const API_BASE = '';  // Same origin

// ========== License Activation ==========

async function activateLicense() {
    const input = document.getElementById('licenseInput');
    const errorEl = document.getElementById('licenseError');
    const key = input.value.trim();
    
    errorEl.classList.add('hidden');
    
    try {
        const response = await fetch(`${API_BASE}/api/validate-license`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ license_key: key }),
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || 'Invalid license key');
        }
        
        // Success!
        state.licenseKey = key;
        state.isActivated = true;
        state.tier = data.tier;
        state.email = data.email;
        state.searchCount = data.today_usage;
        state.remaining = data.remaining;
        
        // Update UI
        document.getElementById('licenseSection').classList.add('hidden');
        document.getElementById('searchSection').classList.remove('hidden');
        
        // Update status badge
        const tierClass = `tier-${state.tier}`;
        document.getElementById('licenseStatus').innerHTML = `
            <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold ${tierClass}">
                ${state.tier.toUpperCase()}
            </span>
            <span class="text-sm text-gray-500">${state.email}</span>
        `;
        
        updateStats();
        showToast('License activated successfully!', 'success');
        
        // Focus search input
        document.getElementById('searchInput').focus();
        
    } catch (error) {
        errorEl.textContent = error.message;
        errorEl.classList.remove('hidden');
    }
}

// ========== Search ==========

async function searchLeads() {
    const keyword = document.getElementById('searchInput').value.trim();
    if (!keyword) {
        showToast('Please enter a search keyword', 'error');
        return;
    }
    
    const numResults = parseInt(document.getElementById('numResults').value);
    const searchBtn = document.getElementById('searchBtn');
    
    // Show loading
    searchBtn.disabled = true;
    document.getElementById('loadingState').classList.remove('hidden');
    document.getElementById('resultsSection').classList.add('hidden');
    document.getElementById('emptyState').classList.add('hidden');
    
    try {
        const response = await fetch(`${API_BASE}/api/search`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                keyword: keyword,
                license_key: state.licenseKey,
                num_results: numResults,
                include_contact_pages: true,
            }),
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || 'Search failed');
        }
        
        // Update state
        state.currentSearchId = data.search_id;
        state.searchCount = data.usage?.today || state.searchCount + 1;
        state.remaining = data.usage?.remaining ?? state.remaining;
        
        // Count totals
        let emailCount = 0;
        data.leads.forEach(l => emailCount += (l.emails || []).length);
        state.totalEmails += emailCount;
        state.totalLeads += data.total_leads;
        
        updateStats();
        
        // Show results
        if (data.leads.length > 0) {
            renderResults(data);
            document.getElementById('resultsSection').classList.remove('hidden');
            showToast(`Found ${data.total_leads} leads with ${emailCount} emails!`, 'success');
        } else {
            document.getElementById('emptyState').classList.remove('hidden');
            showToast('No leads found. Try a different keyword.', 'info');
        }
        
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        searchBtn.disabled = false;
        document.getElementById('loadingState').classList.add('hidden');
    }
}

// ========== Render Results ==========

function renderResults(data) {
    const keyword = data.keyword;
    const leads = data.leads;
    
    document.getElementById('resultsKeyword').textContent = keyword;
    document.getElementById('resultsSummary').textContent = 
        `${data.pages_scraped} pages scraped • ${data.total_leads} leads found • ${data.total_urls} URLs searched`;
    
    const tbody = document.getElementById('resultsBody');
    tbody.innerHTML = '';
    
    leads.forEach((lead, index) => {
        const tr = document.createElement('tr');
        tr.className = 'hover:bg-gray-50';
        
        // Emails HTML
        const emailsHtml = (lead.emails || [])
            .map(e => `<span class="email-badge" title="Click to copy" onclick="copyToClipboard('${e}')">${e}</span>`)
            .join('') || '<span class="text-gray-300 text-xs">None found</span>';
        
        // Names HTML
        const namesHtml = (lead.contact_names || [])
            .map(n => `<span class="name-badge">${escapeHtml(n)}</span>`)
            .join('') || '<span class="text-gray-300 text-xs">-</span>';
        
        // Phones HTML
        const phonesHtml = (lead.phones || [])
            .map(p => `<span class="phone-badge">${escapeHtml(p)}</span>`)
            .join('') || '<span class="text-gray-300 text-xs">-</span>';
        
        // Source URL
        const domain = getDomain(lead.source_url);
        
        tr.innerHTML = `
            <td class="px-6 py-4 text-sm text-gray-400 font-mono">${index + 1}</td>
            <td class="px-6 py-4">
                <div class="font-medium text-gray-900 text-sm">${escapeHtml(lead.business_name || 'Unknown')}</div>
            </td>
            <td class="px-6 py-4">
                <div class="flex flex-wrap">${emailsHtml}</div>
            </td>
            <td class="px-6 py-4">
                <div class="flex flex-wrap">${namesHtml}</div>
            </td>
            <td class="px-6 py-4">
                <div class="flex flex-wrap">${phonesHtml}</div>
            </td>
            <td class="px-6 py-4">
                <a href="${escapeHtml(lead.source_url)}" target="_blank" class="source-url" title="${escapeHtml(lead.source_url)}">
                    ${escapeHtml(domain)}
                </a>
            </td>
        `;
        
        tbody.appendChild(tr);
    });
}

// ========== Export ==========

async function exportLeads(format) {
    if (!state.currentSearchId) {
        showToast('No results to export', 'error');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/api/export`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                license_key: state.licenseKey,
                search_id: state.currentSearchId,
                format: format,
            }),
        });
        
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.detail || 'Export failed');
        }
        
        // Download file
        const blob = await response.blob();
        const ext = format === 'excel' ? 'xlsx' : 'csv';
        const filename = `leads_${state.currentSearchId}.${ext}`;
        
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        showToast(`Exported as ${filename}`, 'success');
        
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// ========== Helpers ==========

function updateStats() {
    document.getElementById('statSearches').textContent = state.searchCount;
    document.getElementById('statEmails').textContent = state.totalEmails;
    document.getElementById('statLeads').textContent = state.totalLeads;
    document.getElementById('statRemaining').textContent = state.remaining;
}

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function getDomain(url) {
    try {
        return new URL(url).hostname;
    } catch {
        return url;
    }
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast(`Copied: ${text}`, 'info');
    });
}

function showToast(message, type = 'info') {
    // Remove existing toasts
    document.querySelectorAll('.toast').forEach(t => t.remove());
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    
    // Animate in
    requestAnimationFrame(() => {
        toast.classList.add('show');
    });
    
    // Auto remove
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ========== Keyboard Shortcuts ==========

document.addEventListener('keydown', (e) => {
    // Ctrl/Cmd + Enter to search
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        if (state.isActivated) {
            searchLeads();
        }
    }
});

