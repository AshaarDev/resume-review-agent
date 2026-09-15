// DOM Elements
const uploadBox = document.getElementById('uploadBox');
const fileInput = document.getElementById('fileInput');
const fileInfo = document.getElementById('fileInfo');
const fileName = document.getElementById('fileName');
const fileSize = document.getElementById('fileSize');
const removeFileBtn = document.getElementById('removeFile');
const analyzeBtn = document.getElementById('analyzeBtn');
const jobDescription = document.getElementById('jobDescription');
const userInstructions = document.getElementById('userInstructions');
const resultsSection = document.getElementById('resultsSection');
const loading = document.getElementById('loading');
const resultsContent = document.getElementById('resultsContent');
const reviewModeBtn = document.getElementById('reviewModeBtn');
const createModeBtn = document.getElementById('createModeBtn');
const reviewInput = document.getElementById('reviewInput');
const creatorInput = document.getElementById('creatorInput');
const creatorName = document.getElementById('creatorName');
const creatorEmail = document.getElementById('creatorEmail');
const creatorPhone = document.getElementById('creatorPhone');
const creatorLocation = document.getElementById('creatorLocation');
const creatorTargetRole = document.getElementById('creatorTargetRole');
const creatorLinks = document.getElementById('creatorLinks');
const creatorFacts = document.getElementById('creatorFacts');
const sampleCreatorBtn = document.getElementById('sampleCreatorBtn');

let selectedFile = null;
let workflowMode = 'review';

function setWorkflowMode(mode) {
    workflowMode = mode;
    const isReview = mode === 'review';
    reviewModeBtn.classList.toggle('active', isReview);
    createModeBtn.classList.toggle('active', !isReview);
    reviewInput.style.display = isReview ? 'block' : 'none';
    creatorInput.style.display = isReview ? 'none' : 'block';
    testMockBtn.style.display = isReview ? 'block' : 'none';
    analyzeBtn.textContent = isReview ? 'Review Resume' : 'Create Resume Draft';
    updatePrimaryButton();
    resultsSection.style.display = 'none';
}

function updatePrimaryButton() {
    analyzeBtn.disabled = workflowMode === 'review'
        ? !selectedFile
        : !creatorName.value.trim() || !creatorFacts.value.trim();
}

reviewModeBtn.addEventListener('click', () => setWorkflowMode('review'));
createModeBtn.addEventListener('click', () => setWorkflowMode('create'));
[creatorName, creatorFacts].forEach((field) => {
    field.addEventListener('input', updatePrimaryButton);
});

sampleCreatorBtn.addEventListener('click', () => {
    creatorName.value = 'Jordan Lee';
    creatorTargetRole.value = 'Software Engineer';
    creatorEmail.value = 'jordan.lee@example.com';
    creatorPhone.value = '+1 416 555 0142';
    creatorLocation.value = 'Toronto, Ontario';
    creatorLinks.value = [
        'https://linkedin.com/in/jordanlee',
        'https://github.com/jordanlee'
    ].join('\n');
    creatorFacts.value = [
        'Worked at Northstar Labs as a Software Engineer from January 2023 to Present in Toronto, Ontario.',
        'Reduced API response time by 42% by introducing Redis caching and optimizing PostgreSQL queries.',
        'Automated the deployment workflow with GitHub Actions, reducing release time from 45 minutes to 12 minutes.',
        'Led a team of 5 developers to deliver a customer analytics dashboard used by 18 internal stakeholders.',
        'Built a document-processing service with Python and FastAPI that processed more than 10,000 files per month.',
        'Earned a Bachelor of Science in Computer Science from Toronto Metropolitan University in 2022.',
        'Technical skills include Python, TypeScript, React, FastAPI, PostgreSQL, Redis, Docker, GitHub Actions, and AWS.',
        'Created an open-source expense tracking application in 2024 using React, FastAPI, and PostgreSQL.'
    ].join('\n');
    jobDescription.value = 'Seeking a Software Engineer with experience building scalable APIs, React applications, cloud infrastructure, and automated delivery pipelines.';
    userInstructions.value = 'Create a concise one-page resume emphasizing measurable technical impact.';
    updatePrimaryButton();
    resultsSection.style.display = 'none';
});

// Upload box click handler
uploadBox.addEventListener('click', () => {
    fileInput.click();
});

// File input change handler
fileInput.addEventListener('change', (e) => {
    handleFile(e.target.files[0]);
});

// Drag and drop handlers
uploadBox.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadBox.classList.add('drag-over');
});

uploadBox.addEventListener('dragleave', () => {
    uploadBox.classList.remove('drag-over');
});

uploadBox.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadBox.classList.remove('drag-over');
    handleFile(e.dataTransfer.files[0]);
});

// Handle file selection
function handleFile(file) {
    if (!file) return;

    const validTypes = [
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'image/jpeg',
        'image/png',
        'image/jpg'
    ];

    if (!validTypes.includes(file.type)) {
        alert('Please upload a PDF, DOCX, or image file');
        return;
    }
    if (file.size > 10 * 1024 * 1024) {
        alert('Please upload a file no larger than 10MB');
        return;
    }

    selectedFile = file;
    
    // Display file info
    fileName.textContent = file.name;
    fileSize.textContent = formatFileSize(file.size);
    
    uploadBox.style.display = 'none';
    fileInfo.style.display = 'flex';
    updatePrimaryButton();
}

// Remove file handler
removeFileBtn.addEventListener('click', () => {
    selectedFile = null;
    fileInput.value = '';
    uploadBox.style.display = 'block';
    fileInfo.style.display = 'none';
    updatePrimaryButton();
    resultsSection.style.display = 'none';
});

// Test mock button handler
const testMockBtn = document.getElementById('testMockBtn');
testMockBtn.addEventListener('click', () => {
    // Show results section
    resultsSection.style.display = 'block';
    loading.style.display = 'none';
    resultsContent.style.display = 'block';
    
    // Create mock response with rich markdown
    const mockResponse = {
        content_review: {
            status: 'available',
            response: `## Resume Analysis Summary

Your resume shows **strong technical foundation** with room for strategic improvements.

### Key Strengths

- **Clear technical skills section** with relevant technologies
- Well-organized work experience with *consistent formatting*
- Good use of action verbs in bullet points
- Clean, professional layout

### Areas for Improvement

#### 1. Quantify Your Achievements

Instead of:
> "Improved application performance"

Try:
> "Improved application performance by **40%**, reducing load time from 3s to 1.8s"

#### 2. Add Impact Metrics

Current bullet points lack measurable outcomes. Consider adding:

- Revenue impact: \`$500K+ in cost savings\`
- Scale: \`Serving 10M+ daily active users\`
- Team size: \`Led team of 5 engineers\`

#### 3. Technical Projects Section

Create a dedicated section showcasing:

1. **Personal projects** with GitHub links
2. **Open source contributions**
3. **Technical blog posts** or publications

### Recommended Action Items

| Priority | Action | Expected Impact |
|----------|--------|-----------------|
| High | Add quantifiable metrics to top 3 achievements | Immediate credibility boost |
| High | Include 2-3 technical projects | Demonstrates passion |
| Medium | Add certifications section | Professional validation |
| Low | Update skills with latest frameworks | Shows continuous learning |

### Code Example Format

When describing technical work, use this structure:

\`\`\`
Problem → Solution → Result
\`\`\`

**Example:**
- **Problem**: Legacy monolith causing deployment delays
- **Solution**: Migrated to microservices architecture using Docker/K8s
- **Result**: Reduced deployment time from 2 hours to 15 minutes

### Next Steps

1. ✅ Add metrics to your top 5 achievements
2. ✅ Create a projects section
3. ✅ Include links to GitHub/portfolio
4. ⚠️ Keep total length to 1-2 pages

---

**Overall Score**: 7.5/10

With these improvements, your resume will stand out to technical recruiters and hiring managers.`,
            error_code: null,
            error_message: null
        },
        visual_review: {
            status: 'available',
            result: {
                visual_score: 85,
                pass_status: true,
                strengths: [
                    'Consistent font hierarchy throughout',
                    'Good use of whitespace for readability',
                    'Professional color scheme'
                ],
                issues: [
                    {
                        code: 'INCONSISTENT_ALIGNMENT',
                        description: 'Date alignment varies between sections',
                        severity: 'minor',
                        affected_area: 'Work Experience section',
                        recommendation: 'Align all dates to the right margin'
                    },
                    {
                        code: 'INCONSISTENT_SPACING',
                        description: 'Spacing between sections is not uniform',
                        severity: 'minor',
                        affected_area: 'Multiple sections',
                        recommendation: 'Use consistent 12pt spacing between sections'
                    }
                ]
            },
            error_code: null,
            error_message: null,
            page_count: 1
        },
        layout_analysis: {
            status: 'available',
            page_count: 1,
            pages: [
                {
                    page_number: 1,
                    width_points: 612.0,
                    height_points: 792.0,
                    text_density: 0.45,
                    font_sizes: [10.0, 11.0, 12.0, 14.0, 16.0],
                    min_font_size: 10.0,
                    max_font_size: 16.0,
                    median_font_size: 11.0,
                    dominant_font_size: 11.0
                }
            ],
            error_code: null,
            error_message: null
        },
        metadata: {
            file_type: 'pdf',
            file_size_bytes: 45678,
            page_count: 1,
            processing_time_ms: 1234.56
        }
    };
    
    displayResults({
        workflow_id: 'mock-workflow',
        policy_id: 'resume-review',
        policy_version: '1.0',
        intent: 'review',
        status: 'completed',
        final_message: 'The resume has a strong foundation. Address the priority actions, then review it again.',
        summary: {
            overall_assessment: 'The resume is clear and professional, with opportunities to make achievements more measurable.',
            top_strengths: ['Clear technical focus', 'Professional visual hierarchy'],
            priority_actions: [
                {
                    priority: 1,
                    source: 'content',
                    issue_code: 'CONTENT_RECOMMENDATION',
                    title: 'Quantify achievements',
                    recommendation: 'Add measurable outcomes to the strongest experience bullets.'
                },
                {
                    priority: 2,
                    source: 'visual',
                    issue_code: 'INCONSISTENT_ALIGNMENT',
                    title: 'Align dates consistently',
                    recommendation: 'Use one right-aligned date column.'
                }
            ],
            next_step: 'Apply the priority changes and run the workflow again.'
        },
        review: {
            status: 'completed',
            ...mockResponse,
            policy_id: 'resume-review',
            policy_version: '1.0',
            policy_findings: [
                {
                    code: 'LOW_XYZ_BULLET_COVERAGE',
                    status: 'minor_issue',
                    source: 'content_review',
                    description: 'Achievement bullets should follow the XYZ method.',
                    measured_value: 0.55,
                    target_value: 0.7,
                    evidence: ['Built internal tools for the team.'],
                    recommendation: 'Add the result, measurement, and method used.'
                },
                {
                    code: 'EXCESSIVE_PAGE_COUNT_FOR_EXPERIENCE',
                    status: 'passed',
                    source: 'review_agent',
                    description: 'Page length should match experience.',
                    measured_value: 1,
                    target_value: 1,
                    evidence: ['3.5 estimated years', '1 nonblank page'],
                    recommendation: 'Keep the resume to one page.'
                }
            ],
            proposed_actions: [],
            warnings: [],
            errors: []
        },
        agent_statuses: {
            resume_review_agent: 'completed',
            resume_creator_agent: 'not_invoked'
        },
        warnings: [],
        errors: []
    });
    
    // Scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth' });
});

// Analyze button handler
analyzeBtn.addEventListener('click', async () => {
    if (workflowMode === 'review' && !selectedFile) return;
    if (
        workflowMode === 'create' &&
        (!creatorName.value.trim() || !creatorFacts.value.trim())
    ) return;

    // Show results section with loading
    resultsSection.style.display = 'block';
    loading.style.display = 'block';
    resultsContent.style.display = 'none';
    resultsContent.innerHTML = '';

    try {
        let requestData;
        if (workflowMode === 'review') {
            const base64Data = await fileToBase64(selectedFile);
            requestData = {
                intent: 'review',
                file_base64: base64Data,
                file_type: getFileExtension(selectedFile.name),
                job_description: jobDescription.value.trim(),
                user_instructions: userInstructions.value.trim()
            };
        } else {
            const facts = creatorFacts.value
                .split('\n')
                .map((fact) => fact.trim())
                .filter(Boolean);
            requestData = {
                intent: 'create',
                creation_brief: {
                    full_name: creatorName.value.trim(),
                    email: creatorEmail.value.trim() || null,
                    phone: creatorPhone.value.trim() || null,
                    location: creatorLocation.value.trim() || null,
                    target_role: creatorTargetRole.value.trim() || null,
                    links: creatorLinks.value
                        .split('\n')
                        .map((link) => link.trim())
                        .filter(Boolean),
                    source_facts: facts.map((text, index) => ({
                        fact_id: `fact-${index + 1}`,
                        text
                    }))
                },
                job_description: jobDescription.value.trim(),
                user_instructions: userInstructions.value.trim()
            };
        }

        // Call API
        const response = await fetch('/api/resume-workflows', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestData)
        });

        if (!response.ok) {
            const payload = await response.json().catch(() => null);
            const detail = payload?.detail;
            const message = typeof detail === 'string'
                ? detail
                : detail?.message || `Workflow request failed (${response.status})`;
            throw new Error(message);
        }

        const result = await response.json();

        // Display results
        loading.style.display = 'none';
        resultsContent.style.display = 'block';
        displayResults(result);

    } catch (error) {
        loading.style.display = 'none';
        resultsContent.style.display = 'block';
        resultsContent.innerHTML = `
            <div class="error">
                <strong>Error:</strong> ${error.message}
                <br><br>
                <small>Make sure the backend server is running on http://localhost:8001</small>
            </div>
        `;
    }
});

// Helper: Convert file to base64
function fileToBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.readAsDataURL(file);
        reader.onload = () => {
            // Remove the data:*/*;base64, prefix
            const base64 = reader.result.split(',')[1];
            resolve(base64);
        };
        reader.onerror = error => reject(error);
    });
}

// Helper: Get file extension
function getFileExtension(filename) {
    return filename.split('.').pop().toLowerCase();
}

// Helper: Format file size
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// Helper: Render markdown safely
function renderMarkdown(text) {
    if (!text) return '';
    
    // Configure marked for safe rendering
    marked.setOptions({
        breaks: true,
        gfm: true,
        headerIds: false,
        mangle: false
    });
    
    return marked.parse(escapeHtml(text));
}

function escapeHtml(value) {
    return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#039;');
}

// Helper: Display workflow and raw branch results
function displayResults(result) {
    const review = result.review;
    const creation = result.creation;
    const summary = result.summary;

    if (creation) {
        const artifact = creation.artifact;
        const downloads = artifact ? `
            <div class="artifact-actions">
                ${artifact.pdf_download_url ? `
                    <a class="artifact-link primary" href="${escapeHtml(artifact.pdf_download_url)}" download>Download PDF</a>
                ` : ''}
                <a class="artifact-link" href="${escapeHtml(artifact.tex_download_url)}" download>Download LaTeX source</a>
            </div>
            <p class="field-note">Compilation status: ${escapeHtml(artifact.compilation_status).replaceAll('_', ' ')}. Review every fact before using this resume.</p>
        ` : '';
        const missing = (creation.document?.missing_information || [])
            .map((item) => `<li>${escapeHtml(item)}</li>`)
            .join('');
        const errors = (creation.errors || [])
            .map((item) => `<li>${escapeHtml(item.message)}</li>`)
            .join('');
        resultsContent.innerHTML = `
            <div class="workflow-header">
                <div>
                    <p class="workflow-id">Workflow ${escapeHtml(result.workflow_id).slice(0, 8)}</p>
                    <h3>Grounded LaTeX resume draft</h3>
                </div>
                <span class="status-badge status-${escapeHtml(result.status)}">
                    ${escapeHtml(result.status).replaceAll('_', ' ')}
                </span>
            </div>
            <div class="creation-card">
                <p>${escapeHtml(result.final_message)}</p>
                ${downloads}
                <div class="creation-stats">
                    <span>${creation.claims_ledger.length} grounded claims</span>
                    <span>${creation.document?.missing_information.length || 0} missing details</span>
                    <span>${escapeHtml(creation.model)}</span>
                </div>
                ${missing ? `<h4>Information to add next</h4><ul>${missing}</ul>` : ''}
                ${errors ? `<div class="error"><ul>${errors}</ul></div>` : ''}
            </div>
        `;
        return;
    }

    if (!review) {
        resultsContent.innerHTML = `
            <div class="workflow-header">
                <span class="status-badge status-${escapeHtml(result.status)}">
                    ${escapeHtml(result.status)}
                </span>
            </div>
            <div class="error">${escapeHtml(result.final_message || 'No review result was returned.')}</div>
        `;
        return;
    }

    const content = review.content_review;
    const visual = review.visual_review;
    const layout = review.layout_analysis;

    const strengthsHtml = (summary?.top_strengths || [])
        .slice(0, 3)
        .map((strength) => `<li>${escapeHtml(strength)}</li>`)
        .join('');
    const actionsHtml = (summary?.priority_actions || [])
        .slice(0, 5)
        .map((action) => `
            <li>
                <span class="action-source">${escapeHtml(action.source)}</span>
                <strong>${escapeHtml(action.title)}</strong>
                <p>${escapeHtml(action.recommendation)}</p>
            </li>
        `)
        .join('');
    const warningsHtml = (result.warnings || [])
        .map((warning) => `<li>${escapeHtml(warning.message)}</li>`)
        .join('');
    const policyFindingsHtml = (review.policy_findings || [])
        .map((finding) => {
            let measured = 'Not available';
            if (finding.measured_value != null) {
                const coverageRules = [
                    'LOW_XYZ_BULLET_COVERAGE',
                    'INSUFFICIENT_QUANTIFICATION',
                    'UNBOLDED_KEY_METRICS',
                ];
                measured = finding.target_value != null && coverageRules.includes(finding.code)
                    ? `${Math.round(finding.measured_value * 100)}% / ${Math.round(finding.target_value * 100)}%`
                    : `${finding.measured_value} / ${finding.target_value}`;
            }
            return `
                <article class="policy-finding policy-${escapeHtml(finding.status)}">
                    <div>
                        <span>${escapeHtml(finding.status).replaceAll('_', ' ')}</span>
                        <h4>${escapeHtml(finding.description)}</h4>
                    </div>
                    <strong>${escapeHtml(measured)}</strong>
                    ${finding.status !== 'passed' ? `<p>${escapeHtml(finding.recommendation)}</p>` : ''}
                </article>
            `;
        })
        .join('');

    // Render content review with markdown support
    const contentHtml = content.status === 'available'
        ? `<div class="markdown-content">${renderMarkdown(content.response)}</div>`
        : `<div class="error">${escapeHtml(content.error_message)}</div>`;

    let visualHtml = `<div class="error">${escapeHtml(visual.error_message)}</div>`;
    if (visual.status === 'available' && visual.result) {
        const strengths = visual.result.strengths
            .map((item) => `<li>${escapeHtml(item)}</li>`)
            .join('');
        const issues = visual.result.issues
            .map((issue) => `<li><strong>${escapeHtml(issue.code)}</strong>
                (${escapeHtml(issue.severity)}): ${escapeHtml(issue.description)}
                <br>Recommendation: ${escapeHtml(issue.recommendation)}</li>`)
            .join('');
        visualHtml = `
            <p><strong>Score:</strong> ${visual.result.visual_score}/100</p>
            ${strengths ? `<h4>Strengths</h4><ul>${strengths}</ul>` : ''}
            ${issues ? `<h4>Issues</h4><ul>${issues}</ul>` : ''}
        `;
    }

    let layoutHtml = `<div class="error">${escapeHtml(layout.error_message)}</div>`;
    if (layout.status === 'available') {
        const pages = layout.pages
            .map((page) => `<li>Page ${page.page_number}:
                ${page.width_points.toFixed(1)} × ${page.height_points.toFixed(1)} pt,
                ${(page.text_density * 100).toFixed(1)}% text density,
                median font ${page.median_font_size ?? 'not detected'} pt</li>`)
            .join('');
        layoutHtml = `<p>${layout.page_count} page(s)</p><ul>${pages}</ul>`;
    }

    resultsContent.innerHTML = `
        <div class="workflow-header">
            <div>
                <p class="workflow-id">Workflow ${escapeHtml(result.workflow_id).slice(0, 8)}</p>
                <h3>Combined assessment</h3>
            </div>
            <span class="status-badge status-${escapeHtml(result.status)}">
                ${escapeHtml(result.status).replaceAll('_', ' ')}
            </span>
        </div>
        <div class="summary-card">
            <p>${escapeHtml(summary?.overall_assessment || result.final_message)}</p>
            ${strengthsHtml ? `<h4>Top strengths</h4><ul>${strengthsHtml}</ul>` : ''}
            ${actionsHtml ? `<h4>Priority actions</h4><ol class="priority-list">${actionsHtml}</ol>` : ''}
            ${summary?.next_step ? `<p class="next-step"><strong>Next step:</strong> ${escapeHtml(summary.next_step)}</p>` : ''}
        </div>
        ${policyFindingsHtml ? `
            <div class="policy-card">
                <div class="policy-heading">
                    <div>
                        <p class="workflow-id">Resume standards</p>
                        <h3>Policy scorecard</h3>
                    </div>
                    <span>v${escapeHtml(review.policy_version)}</span>
                </div>
                <div class="policy-grid">${policyFindingsHtml}</div>
            </div>
        ` : ''}
        ${warningsHtml ? `<div class="warning-panel"><strong>Partial results</strong><ul>${warningsHtml}</ul></div>` : ''}
        <h3>Content review</h3>${contentHtml}
        <h3>Visual review</h3>${visualHtml}
        <h3>Layout analysis</h3>${layoutHtml}
    `;
}
