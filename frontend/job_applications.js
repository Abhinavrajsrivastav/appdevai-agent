// Job Applications Management
let currentResume = null;

function applyWithAI(button) {
    // Get job data from data attribute
    let jobData;
    try {
        jobData = JSON.parse(button.getAttribute('data-job'));
        console.log('Apply with AI clicked for job:', jobData);
    } catch (error) {
        console.error('Error parsing job data:', error);
        alert('Error processing job data. Please try again.');
        return;
    }
    
    // Disable the button to prevent duplicate clicks
    button.disabled = true;
    button.innerHTML = '<i class="fas fa-circle-notch fa-spin"></i> Applying...';
    
    // Check if we have a resume
    if (!currentResume) {
        // Ask the user to upload a resume
        const jobCard = button.closest('.job-card');
        const jobTitle = jobCard.querySelector('.job-title').textContent;
        const company = jobCard.querySelector('.job-company').textContent.replace('Company: ', '');
        
        // Reset the button
        button.disabled = false;
        button.innerHTML = '<i class="fas fa-robot"></i> Apply with AI';
        
        // Switch to the applications tab
        tabBtns.forEach(btn => {
            if (btn.dataset.tab === 'applications') {
                btn.click();
            }
        });
        
        // Show dialog
        alert(`Please upload your resume in the Jobs tab before applying to ${jobTitle} at ${company}`);
        
        return;
    }
    
    // Create FormData with resume and job data
    const formData = new FormData();
    formData.append('resume', currentResume);
    formData.append('job_data', JSON.stringify(jobData));
    
    // Add a message to the chat
    addMessageToChat('user', `Apply to job: ${jobData.job_title || jobData.title} at ${jobData.company_name || jobData.company}`);
    
    // Show typing indicator
    addMessageToChat('bot', '<div class="typing-indicator"><span></span><span></span><span></span></div>', false);
    
    // Call the API to apply for the job
    callApi(`${API_BASE_URL}/tools/job_applicator`, 'POST', formData)
        .then(response => {
            console.log('Job application response:', response);
            
            removeTypingIndicator();
            
            if (response.error) {
                addMessageToChat('bot', `<p>I encountered an error while applying for the job: ${response.error}</p>`);
                return;
            }
            
            // Process the response
            if (response.status === 'success' || response.status === 'initiated' || response.status === 'redirected') {
                addMessageToChat('bot', `
                    <p>I've started the application process for <strong>${jobData.job_title}</strong> at <strong>${jobData.company_name || jobData.company}</strong>.</p>
                    <p>${response.message || 'The application has been submitted successfully.'}</p>
                    <p>You can track the status in the Applications tab.</p>
                `);
                
                // Switch to the applications tab
                tabBtns.forEach(btn => {
                    if (btn.dataset.tab === 'applications') {
                        btn.click();
                    }
                });
                
                // Refresh the applications list
                loadApplications();
            } else if (response.status === 'already_applied') {
                addMessageToChat('bot', `
                    <p>You've already applied to <strong>${jobData.job_title}</strong> at <strong>${jobData.company_name || jobData.company}</strong>.</p>
                    <p>You can track the status in the Applications tab.</p>
                `);
                
                // Switch to the applications tab
                tabBtns.forEach(btn => {
                    if (btn.dataset.tab === 'applications') {
                        btn.click();
                    }
                });
            } else {
                addMessageToChat('bot', `
                    <p>I wasn't able to complete the application for <strong>${jobData.job_title}</strong> at <strong>${jobData.company_name || jobData.company}</strong>.</p>
                    <p>Reason: ${response.reason || 'Unknown error'}</p>
                    <p>You can try applying manually by clicking the "Apply Now" button.</p>
                `);
            }
        })
        .catch(error => {
            console.error('Error applying for job:', error);
            removeTypingIndicator();
            addMessageToChat('bot', `
                <p>Sorry, I encountered an error while trying to apply for the job.</p>
                <p>Error: ${error.message}</p>
                <p>You can try applying manually by clicking the "Apply Now" button.</p>
            `);
        })
        .finally(() => {
            // Reset the button
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-robot"></i> Apply with AI';
        });
}

async function loadApplications() {
    // Show loading state
    applicationsResult.innerHTML = `
        <div class="loading-container">
            <div class="spinner"></div>
            <p class="loading-text">Loading applications...</p>
        </div>
    `;
    
    try {
        // Call the API to get applications
        const formData = new FormData();
        formData.append('tool_name', 'application_status');
        
        const data = await callApi(`${API_BASE_URL}/tools/application_status`, 'POST', formData);
        console.log('Applications data:', data);
        
        displayApplications(data);
        
    } catch (error) {
        console.error('Error loading applications:', error);
        applicationsResult.innerHTML = `
            <div class="error-message">
                Sorry, there was an error loading your applications. Please try again.<br>
                Error details: ${error.message || 'Unknown error'}
            </div>
        `;
    }
}

function displayApplications(data) {
    if (data.error) {
        applicationsResult.innerHTML = `
            <div class="error-message">
                ${data.error}
            </div>
        `;
        return;
    }
    
    // Check if we have applications
    const applications = data.applications || [];
    
    if (applications.length === 0) {
        applicationsResult.innerHTML = `
            <div class="info-message">
                <p>You haven't applied to any jobs yet.</p>
                <p>Go to the Job Finder tab to find and apply to jobs.</p>
            </div>
        `;
        return;
    }
    
    // Generate HTML for applications
    let html = `
        <div class="applications-summary">
            <p>Found ${applications.length} application${applications.length !== 1 ? 's' : ''}.</p>
        </div>
        <div class="applications-list">
    `;
    
    // Sort applications by date (newest first)
    applications.sort((a, b) => {
        return new Date(b.application_date) - new Date(a.application_date);
    });
    
    // Generate application cards
    applications.forEach(app => {
        const applicationDate = new Date(app.application_date).toLocaleDateString();
        
        // Determine status badge color
        let statusClass = 'status-pending';
        if (app.status === 'completed' || app.status === 'success') {
            statusClass = 'status-success';
        } else if (app.status === 'failed') {
            statusClass = 'status-failed';
        } else if (app.status === 'initiated') {
            statusClass = 'status-initiated';
        } else if (app.status === 'redirected') {
            statusClass = 'status-redirected';
        } else if (app.status === 'already_applied') {
            statusClass = 'status-duplicate';
        }
        
        html += `
            <div class="application-card">
                <div class="application-header">
                    <h3 class="application-title">${app.job_title}</h3>
                    <div class="application-company"><i class="fas fa-building"></i> ${app.company}</div>
                    <div class="application-date"><i class="fas fa-calendar-alt"></i> Applied on ${applicationDate}</div>
                </div>
                <div class="application-status ${statusClass}">
                    <span class="status-indicator"></span>
                    <span class="status-text">${app.status.charAt(0).toUpperCase() + app.status.slice(1).replace(/_/g, ' ')}</span>
                </div>
                <div class="application-actions">
                    <a href="${app.job_url}" target="_blank" class="view-job-btn" rel="noopener noreferrer">
                        <i class="fas fa-external-link-alt"></i> View Job
                    </a>
                </div>
            </div>
        `;
    });
    
    html += `</div>`;
    applicationsResult.innerHTML = html;
}

// Remember the resume for later use in job applications
jobsForm.addEventListener('change', (e) => {
    if (e.target === jobsResume && jobsResume.files[0]) {
        currentResume = jobsResume.files[0];
        console.log('Resume saved for later use in applications:', currentResume.name);
    }
});

// Applications tab element
const applicationsResult = document.getElementById('applications-result');
const refreshApplicationsBtn = document.getElementById('refresh-applications-btn');

// Refresh applications when the button is clicked
refreshApplicationsBtn.addEventListener('click', loadApplications);

// Load applications when the tab is clicked
tabBtns.forEach(btn => {
    if (btn.dataset.tab === 'applications') {
        btn.addEventListener('click', loadApplications);
    }
});
