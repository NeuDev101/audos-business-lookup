// Status panel management
let statusPanel = null;
let statusPanelContent = null;

function initStatusPanel() {
    statusPanel = document.getElementById('validation-status-panel');
    statusPanelContent = document.getElementById('validation-status-content');
}

function showStatusPanel() {
    if (statusPanel) {
        statusPanel.style.display = 'block';
    }
}

function hideStatusPanel() {
    if (statusPanel) {
        statusPanel.style.display = 'none';
    }
}

function setStatusMessage(type, message) {
    if (!statusPanelContent) return;
    
    // Remove existing status classes
    statusPanelContent.className = 'status-content';
    statusPanelContent.classList.add(type);
    
    // Update message
    const messageEl = statusPanelContent.querySelector('.status-message');
    if (messageEl) {
        messageEl.textContent = message;
    }
}

function updateStatusChecklist(steps) {
    const checklist = document.getElementById('formatting-checklist');
    if (!checklist) return;
    
    checklist.innerHTML = '';
    steps.forEach(step => {
        const li = document.createElement('li');
        li.textContent = step;
        checklist.appendChild(li);
    });
}

// Full form validation
async function validateFullForm(formData) {
    const fields = [
        'issuer_name', 'buyer', 'invoice_number', 'date', 
        'issuer_id', 'email', 'phone', 'address', 'tax_rate'
    ];
    
    const results = {};
    let hasErrors = false;
    let hasWarnings = false;
    let missingRequired = [];
    
    // Show processing state
    showStatusPanel();
    setStatusMessage('processing', 'Auto-formatting your invoice…');
    updateStatusChecklist([
        'Checking required fields',
        'Validating formats',
        'Normalizing data',
        'Applying corrections'
    ]);
    
    // Validate each field
    for (const fieldName of fields) {
        const field = document.querySelector(`[name="${fieldName}"]`);
        if (!field) continue;
        
        const value = field.value.trim();
        
        // Check if required field is missing
        const requiredFields = ['issuer_name', 'buyer', 'invoice_number'];
        if (requiredFields.includes(fieldName) && !value) {
            missingRequired.push(fieldName);
            hasErrors = true;
            continue;
        }
        
        // Skip validation if empty (except required fields)
        if (!value && !requiredFields.includes(fieldName)) {
            continue;
        }
        
        try {
            const response = await fetch("/validate_field", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({ field: fieldName, value: value })
            });
            
            const data = await response.json();
            results[fieldName] = data.status;
            
            if (data.status === "fail") {
                if (requiredFields.includes(fieldName)) {
                    hasErrors = true;
                } else {
                    hasWarnings = true;
                }
            }
        } catch (err) {
            console.error(`Validation error for ${fieldName}:`, err);
            if (requiredFields.includes(fieldName)) {
                hasErrors = true;
            }
        }
    }
    
    // Determine final status
    if (hasErrors || missingRequired.length > 0) {
        // Red error - required fields missing
        const missingFields = missingRequired.map(f => {
            const labels = {
                'issuer_name': 'Issuer Name',
                'buyer': 'Buyer',
                'invoice_number': 'Invoice Number'
            };
            return labels[f] || f;
        }).join(', ');
        
        setStatusMessage('error', `Required fields missing: ${missingFields}. Please fill in all required fields.`);
        updateStatusChecklist([
            '❌ Required fields are missing',
            '⚠️ Please complete all required fields',
            '⚠️ Some formats may need correction'
        ]);
    } else if (hasWarnings) {
        // Yellow warning - some fields need correction
        setStatusMessage('warning', 'Some fields need correction. The form will still be processed, but please review highlighted fields.');
        updateStatusChecklist([
            '✓ Required fields present',
            '⚠️ Some formats need correction',
            '⚠️ Review highlighted fields'
        ]);
    } else {
        // Green success - all good
        setStatusMessage('success', 'All fields validated successfully. Your invoice is ready to generate.');
        updateStatusChecklist([
            '✓ Required fields present',
            '✓ Formats validated',
            '✓ Data normalized',
            '✓ Ready to generate PDF'
        ]);
    }
    
    return { hasErrors, hasWarnings, missingRequired, results };
}

// Intercept form submission
document.addEventListener('DOMContentLoaded', () => {
    initStatusPanel();
    
    const form = document.querySelector('form[action="/generate"]');
    if (!form) return;
    
    let isSubmitting = false;
    let shouldSubmit = false;
    
    form.addEventListener('submit', async (e) => {
        // If we've already validated and should submit, allow it
        if (shouldSubmit) {
            shouldSubmit = false;
            return; // Let form submit naturally
        }
        
        if (isSubmitting) {
            e.preventDefault();
            return;
        }
        
        e.preventDefault();
        isSubmitting = true;
        
        // Validate form
        const validation = await validateFullForm(new FormData(form));
        
        // If critical errors, don't submit
        if (validation.hasErrors && validation.missingRequired.length > 0) {
            // Keep panel visible to show errors
            isSubmitting = false;
            return;
        }
        
        // If warnings or success, submit after showing status
        setTimeout(() => {
            isSubmitting = false;
            shouldSubmit = true;
            // Trigger form submission
            form.requestSubmit();
        }, 2000);
    });
});

