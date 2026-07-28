import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { FileUpload } from './components/FileUpload';
import { analyzeResume } from './services/api';
import type { WorkflowResponse } from './types';
import './App.css';

const mockWorkflow: WorkflowResponse = {
  workflow_id: 'mock-workflow',
  policy_id: 'resume-review',
  policy_version: '1.0',
  intent: 'review',
  status: 'partial',
  final_message:
    'Your resume has a clear structure. Focus next on measurable impact and consistent date alignment.',
  summary: {
    overall_assessment:
      'The resume is readable and professionally structured, with opportunities to strengthen evidence of impact.',
    top_strengths: ['Clear hierarchy', 'Relevant technical experience'],
    priority_actions: [
      {
        priority: 1,
        source: 'content',
        issue_code: 'CONTENT_RECOMMENDATION',
        title: 'Quantify achievements',
        recommendation: 'Add measurable outcomes to the strongest experience bullets.',
      },
      {
        priority: 2,
        source: 'visual',
        issue_code: 'INCONSISTENT_ALIGNMENT',
        title: 'Align dates consistently',
        recommendation: 'Use one right-aligned date column.',
      },
    ],
    next_step: 'Apply the priority changes and run the review again.',
  },
  review: {
    status: 'partial',
    content_review: {
      status: 'available',
      response:
        '## Content review\n\nYour experience is relevant. Add metrics to demonstrate scale and business impact.',
      analysis: {
        overall_feedback: 'Relevant experience with room for stronger evidence.',
        strengths: ['Relevant technical experience'],
        recommendations: ['Add credible measures to the strongest achievements.'],
        estimated_relevant_experience_years: 3.5,
        experience_estimate_confidence: 0.9,
        bullets: [],
      },
      error_code: null,
      error_message: null,
    },
    visual_review: {
      status: 'available',
      result: {
        visual_score: 85,
        pass_status: true,
        strengths: ['Consistent font hierarchy', 'Good use of whitespace'],
        issues: [
          {
            code: 'INCONSISTENT_ALIGNMENT',
            description: 'Date alignment varies between sections.',
            severity: 'minor',
            affected_area: 'Experience',
            recommendation: 'Align dates to one right margin.',
          },
        ],
        metric_emphasis: {
          eligible_metric_count: 4,
          emphasized_metric_count: 2,
          coverage: 0.5,
          confidence: 0.9,
          unbolded_metrics: ['40% reduction', '10K users'],
        },
      },
      error_code: null,
      error_message: null,
      page_count: 1,
    },
    layout_analysis: {
      status: 'unavailable',
      page_count: null,
      pages: [],
      error_code: 'LAYOUT_ANALYSIS_FAILED',
      error_message: 'Layout analysis was unavailable for this mock.',
    },
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
        recommendation: 'Add the result, measurement, and method used.',
      },
      {
        code: 'EXCESSIVE_PAGE_COUNT_FOR_EXPERIENCE',
        status: 'passed',
        source: 'review_agent',
        description: 'Page length should match experience.',
        measured_value: 1,
        target_value: 1,
        evidence: ['3.5 estimated years', '1 nonblank page'],
        recommendation: 'Keep the resume to one page.',
      },
    ],
    proposed_actions: [],
    warnings: [],
    errors: [],
  },
  agent_statuses: {
    resume_review_agent: 'partial',
    resume_creator_agent: 'not_invoked',
  },
  warnings: [
    {
      code: 'LAYOUT_ANALYSIS_FAILED',
      message: 'Layout analysis was unavailable for this mock.',
      source: 'layout_analysis',
    },
  ],
  errors: [],
};

function App() {
  const [file, setFile] = useState<File | null>(null);
  const [jobDescription, setJobDescription] = useState('');
  const [userInstructions, setUserInstructions] = useState('');
  const [workflow, setWorkflow] = useState<WorkflowResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleAnalyze = async () => {
    if (!file) {
      setError('Please upload a resume first.');
      return;
    }
    setLoading(true);
    setError('');
    setWorkflow(null);
    try {
      setWorkflow(
        await analyzeResume(file, jobDescription, userInstructions),
      );
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : 'Failed to run the resume review workflow.',
      );
    } finally {
      setLoading(false);
    }
  };

  const review = workflow?.review;

  return (
    <div className="app">
      <header className="app-header">
        <p className="eyebrow">MULTI-MODEL RESUME INTELLIGENCE</p>
        <h1>Resume Review Agent</h1>
        <p>Content, visual, and layout analysis coordinated in one workflow.</p>
      </header>

      <main className="app-main">
        <section className="upload-section">
          <h2>Upload resume</h2>
          <FileUpload
            onFileSelect={(selected) => {
              setFile(selected);
              setError('');
            }}
            disabled={loading}
          />
        </section>

        <section className="job-description-section">
          <h2>Review context</h2>
          <label htmlFor="job-description">Job description</label>
          <textarea
            id="job-description"
            className="job-description-input"
            placeholder="Paste the target job description for tailored feedback."
            value={jobDescription}
            onChange={(event) => setJobDescription(event.target.value)}
            disabled={loading}
            rows={5}
          />
          <label htmlFor="user-instructions">Additional instructions</label>
          <textarea
            id="user-instructions"
            className="job-description-input"
            placeholder="For example: prioritize executive clarity or technical impact."
            value={userInstructions}
            onChange={(event) => setUserInstructions(event.target.value)}
            disabled={loading}
            rows={3}
          />
        </section>

        <button
          className="analyze-btn"
          onClick={handleAnalyze}
          disabled={!file || loading}
        >
          {loading ? 'Running review workflow…' : 'Review resume'}
        </button>
        <button
          className="mock-test-btn"
          onClick={() => {
            setError('');
            setWorkflow(mockWorkflow);
          }}
          disabled={loading}
        >
          Preview workflow result
        </button>

        {error && <div className="error-message" role="alert">{error}</div>}

        {workflow && (
          <section className="analysis-results" aria-live="polite">
            <div className="result-heading">
              <div>
                <p className="eyebrow">WORKFLOW {workflow.workflow_id.slice(0, 8)}</p>
                <h2>Review results</h2>
              </div>
              <span className={`status-badge status-${workflow.status}`}>
                {workflow.status.replace('_', ' ')}
              </span>
            </div>

            <div className="summary-card">
              <h3>Combined assessment</h3>
              <p>{workflow.summary?.overall_assessment || workflow.final_message}</p>
              {workflow.summary?.top_strengths.length ? (
                <>
                  <h4>Top strengths</h4>
                  <ul>
                    {workflow.summary.top_strengths.slice(0, 3).map((strength) => (
                      <li key={strength}>{strength}</li>
                    ))}
                  </ul>
                </>
              ) : null}
              {workflow.summary?.priority_actions.length ? (
                <>
                  <h4>Priority actions</h4>
                  <ol className="priority-list">
                    {workflow.summary.priority_actions.slice(0, 5).map((action, index) => (
                      <li key={`${action.issue_code}-${index}`}>
                        <span className="action-source">{action.source}</span>
                        <strong>{action.title}</strong>
                        <p>{action.recommendation}</p>
                      </li>
                    ))}
                  </ol>
                </>
              ) : null}
              {workflow.summary && (
                <p className="next-step">
                  <strong>Next step:</strong> {workflow.summary.next_step}
                </p>
              )}
            </div>

            {review?.policy_findings.length ? (
              <div className="policy-card">
                <div className="policy-heading">
                  <div>
                    <p className="eyebrow">RESUME STANDARDS</p>
                    <h3>Policy scorecard</h3>
                  </div>
                  <span>v{review.policy_version}</span>
                </div>
                <div className="policy-grid">
                  {review.policy_findings.map((finding) => {
                    const isCoverageRule = [
                      'LOW_XYZ_BULLET_COVERAGE',
                      'INSUFFICIENT_QUANTIFICATION',
                      'UNBOLDED_KEY_METRICS',
                    ].includes(finding.code);
                    const measured =
                      finding.measured_value == null
                        ? 'Not available'
                        : finding.target_value != null && isCoverageRule
                          ? `${Math.round(finding.measured_value * 100)}% / ${Math.round(finding.target_value * 100)}%`
                          : `${finding.measured_value} / ${finding.target_value}`;
                    return (
                      <article
                        className={`policy-finding policy-${finding.status}`}
                        key={finding.code}
                      >
                        <div>
                          <span>{finding.status.replace('_', ' ')}</span>
                          <h4>{finding.description}</h4>
                        </div>
                        <strong>{measured}</strong>
                        {finding.status !== 'passed' && (
                          <p>{finding.recommendation}</p>
                        )}
                      </article>
                    );
                  })}
                </div>
              </div>
            ) : null}

            {workflow.warnings.length > 0 && (
              <div className="warning-panel">
                <strong>Partial results</strong>
                <ul>
                  {workflow.warnings.map((warning, index) => (
                    <li key={`${warning.code}-${index}`}>{warning.message}</li>
                  ))}
                </ul>
              </div>
            )}

            {review && (
              <div className="analysis-content">
                <h3>Content review</h3>
                {review.content_review.status === 'available' ? (
                  <div className="markdown-content">
                    <ReactMarkdown skipHtml>
                      {review.content_review.response || ''}
                    </ReactMarkdown>
                  </div>
                ) : (
                  <p>{review.content_review.error_message}</p>
                )}

                <h3>Visual review</h3>
                {review.visual_review.status === 'available' &&
                review.visual_review.result ? (
                  <>
                    <p className="score">
                      {review.visual_review.result.visual_score}
                      <span>/100 visual score</span>
                    </p>
                    <ul>
                      {review.visual_review.result.issues.map((issue, index) => (
                        <li key={`${issue.code}-${index}`}>
                          <strong>{issue.code}</strong> ({issue.severity}):{' '}
                          {issue.description} {issue.recommendation}
                        </li>
                      ))}
                    </ul>
                  </>
                ) : (
                  <p>{review.visual_review.error_message}</p>
                )}

                <h3>Layout analysis</h3>
                {review.layout_analysis.status === 'available' ? (
                  <ul>
                    {review.layout_analysis.pages.map((page) => (
                      <li key={page.page_number}>
                        Page {page.page_number}: {page.width_points.toFixed(1)} ×{' '}
                        {page.height_points.toFixed(1)} pt,{' '}
                        {(page.text_density * 100).toFixed(1)}% density, median
                        font {page.median_font_size ?? 'not detected'} pt
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p>{review.layout_analysis.error_message}</p>
                )}
              </div>
            )}
          </section>
        )}
      </main>
    </div>
  );
}

export default App;
