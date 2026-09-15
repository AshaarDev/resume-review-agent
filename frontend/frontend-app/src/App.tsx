import { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import ResumeBuilder from './components/ResumeBuilder';
import { analyzeResume, artifactUrl, createResume } from './services/api';
import type { ReviewAgentResult, WorkflowResponse } from './types';
import './App.css';

type Route = 'landing' | 'signin' | 'workspace';
type WorkspaceMode = 'review' | 'create';

const SAMPLE_CREATOR_FACTS = [
  'Worked at Northstar Labs as a Software Engineer from January 2023 to Present in Toronto, Ontario.',
  'Reduced API response time by 42% by introducing Redis caching and optimizing PostgreSQL queries.',
  'Automated the deployment workflow with GitHub Actions, reducing release time from 45 minutes to 12 minutes.',
  'Led a team of 5 developers to deliver a customer analytics dashboard used by 18 internal stakeholders.',
  'Built a document-processing service with Python and FastAPI that processed more than 10,000 files per month.',
  'Earned a Bachelor of Science in Computer Science from Toronto Metropolitan University in 2022.',
  'Technical skills include Python, TypeScript, React, FastAPI, PostgreSQL, Redis, Docker, GitHub Actions, and AWS.',
  'Created an open-source expense tracking application in 2024 using React, FastAPI, and PostgreSQL.',
].join('\n');

const buildSourceFacts = (input: string): string[] => {
  const segments = input
    .replace(/\r\n/g, '\n')
    .split(/\n{2,}|\n/)
    .map((segment) => segment.trim())
    .filter(Boolean);
  const grouped: string[] = [];
  let current = '';

  for (const segment of segments) {
    if (segment.length > 1000) {
      if (current) {
        grouped.push(current);
        current = '';
      }
      for (let offset = 0; offset < segment.length; offset += 900) {
        grouped.push(segment.slice(offset, offset + 900));
      }
      continue;
    }
    const candidate = current ? `${current}\n${segment}` : segment;
    if (candidate.length <= 900) {
      current = candidate;
    } else {
      grouped.push(current);
      current = segment;
    }
  }
  if (current) grouped.push(current);
  return grouped;
};

const MOCK_WORKFLOW: WorkflowResponse = {
  workflow_id: 'demo-review-85',
  policy_id: 'resume-review',
  policy_version: '1.0',
  intent: 'review',
  status: 'completed',
  final_message:
    'Your resume is clear and professionally structured. Prioritize measurable outcomes and align dates consistently.',
  summary: {
    overall_assessment:
      'A strong foundation with relevant experience, clear hierarchy, and specific opportunities to improve impact.',
    top_strengths: ['Clear information hierarchy', 'Relevant technical experience'],
    priority_actions: [
      {
        priority: 1,
        source: 'content',
        issue_code: 'LOW_XYZ_BULLET_COVERAGE',
        title: 'Strengthen achievement bullets',
        recommendation:
          'State what you accomplished, quantify the result, and explain how you achieved it.',
      },
      {
        priority: 2,
        source: 'visual',
        issue_code: 'INCONSISTENT_ALIGNMENT',
        title: 'Align dates consistently',
        recommendation: 'Use one right-aligned date column throughout the resume.',
      },
    ],
    next_step: 'Apply the two priority changes and run the review again.',
  },
  review: {
    status: 'completed',
    content_review: {
      status: 'available',
      response:
        '## Content review\n\nThe experience is relevant and readable. Add credible metrics to demonstrate the scale and outcome of your strongest contributions.',
      analysis: null,
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
            recommendation: 'Align dates to a single right margin.',
          },
        ],
        metric_emphasis: {
          eligible_metric_count: 4,
          emphasized_metric_count: 2,
          coverage: 0.5,
          confidence: 0.9,
          unbolded_metrics: ['42% reduction', '10,000 files'],
        },
      },
      error_code: null,
      error_message: null,
      page_count: 1,
    },
    layout_analysis: {
      status: 'available',
      page_count: 1,
      pages: [
        {
          page_number: 1,
          width_points: 612,
          height_points: 792,
          text_density: 0.42,
          font_sizes: [9.5, 10, 11, 14],
          min_font_size: 9.5,
          max_font_size: 14,
          median_font_size: 10,
          dominant_font_size: 10,
        },
      ],
      error_code: null,
      error_message: null,
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
        description: 'Page length matches the estimated experience.',
        measured_value: 1,
        target_value: 1,
        evidence: ['One nonblank page'],
        recommendation: 'Keep the resume to one page.',
      },
    ],
    proposed_actions: [],
    warnings: [],
    errors: [],
  },
  creation: null,
  agent_statuses: {
    resume_review_agent: 'completed',
    resume_creator_agent: 'not_invoked',
  },
  warnings: [],
  errors: [],
};

const MOCK_CREATOR_PREVIEW = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(`
  <svg xmlns="http://www.w3.org/2000/svg" width="816" height="1056" viewBox="0 0 816 1056">
    <rect width="816" height="1056" fill="#ffffff"/>
    <style>
      .name{font:700 30px Arial;fill:#111827}.role{font:15px Arial;fill:#4b5563}
      .heading{font:700 14px Arial;fill:#111827;letter-spacing:1.5px}
      .title{font:700 13px Arial;fill:#111827}.meta{font:12px Arial;fill:#4b5563}
      .body{font:12px Arial;fill:#1f2937}.small{font:11px Arial;fill:#374151}
    </style>
    <text x="408" y="62" text-anchor="middle" class="name">JORDAN LEE</text>
    <text x="408" y="88" text-anchor="middle" class="role">Software Engineer</text>
    <text x="408" y="111" text-anchor="middle" class="small">Toronto, Ontario · jordan.lee@example.com · github.com/jordanlee</text>
    <line x1="62" y1="132" x2="754" y2="132" stroke="#111827" stroke-width="2"/>
    <text x="62" y="169" class="heading">PROFESSIONAL EXPERIENCE</text>
    <line x1="62" y1="179" x2="754" y2="179" stroke="#9ca3af"/>
    <text x="62" y="207" class="title">Software Engineer · Northstar Labs</text>
    <text x="754" y="207" text-anchor="end" class="meta">Jan 2023 – Present</text>
    <circle cx="72" cy="235" r="3" fill="#111827"/>
    <text x="86" y="239" class="body">Reduced API response time by 42% by introducing Redis caching and optimizing PostgreSQL queries.</text>
    <circle cx="72" cy="263" r="3" fill="#111827"/>
    <text x="86" y="267" class="body">Cut release time from 45 to 12 minutes by automating delivery workflows with GitHub Actions.</text>
    <circle cx="72" cy="291" r="3" fill="#111827"/>
    <text x="86" y="295" class="body">Led 5 developers to deliver an analytics dashboard used by 18 internal stakeholders.</text>
    <text x="62" y="345" class="heading">PROJECTS</text>
    <line x1="62" y1="355" x2="754" y2="355" stroke="#9ca3af"/>
    <text x="62" y="383" class="title">Open-source Expense Tracker</text>
    <text x="754" y="383" text-anchor="end" class="meta">2024</text>
    <circle cx="72" cy="411" r="3" fill="#111827"/>
    <text x="86" y="415" class="body">Built a full-stack expense platform using React, FastAPI, and PostgreSQL.</text>
    <text x="62" y="465" class="heading">EDUCATION</text>
    <line x1="62" y1="475" x2="754" y2="475" stroke="#9ca3af"/>
    <text x="62" y="503" class="title">Toronto Metropolitan University</text>
    <text x="754" y="503" text-anchor="end" class="meta">2022</text>
    <text x="62" y="526" class="body">Bachelor of Science in Computer Science</text>
    <text x="62" y="576" class="heading">TECHNICAL SKILLS</text>
    <line x1="62" y1="586" x2="754" y2="586" stroke="#9ca3af"/>
    <text x="62" y="614" class="body"><tspan font-weight="700">Languages:</tspan> Python, TypeScript, SQL</text>
    <text x="62" y="639" class="body"><tspan font-weight="700">Frameworks:</tspan> React, FastAPI</text>
    <text x="62" y="664" class="body"><tspan font-weight="700">Infrastructure:</tspan> Docker, AWS, GitHub Actions, Redis</text>
  </svg>
`)}`;

const MOCK_CREATOR_WORKFLOW: WorkflowResponse = {
  workflow_id: 'mock-creator-workflow',
  policy_id: 'resume-review',
  policy_version: '1.0',
  intent: 'create',
  status: 'completed',
  final_message:
    'Your grounded resume draft was created successfully. Review each claim before using it.',
  summary: null,
  review: null,
  creation: {
    status: 'completed',
    model: 'mock-creator-model',
    policy_id: 'resume-review',
    policy_version: '1.0',
    document: {
      professional_summary:
        'Software engineer focused on scalable APIs, responsive applications, and delivery automation.',
      professional_summary_source_fact_ids: ['fact-1', 'fact-2'],
      experiences: [{
        organization: 'Northstar Labs',
        role: 'Software Engineer',
        location: 'Toronto, Ontario',
        date_range: 'Jan 2023 – Present',
        source_fact_ids: ['fact-1', 'fact-2', 'fact-3'],
        bullets: [
          { text: 'Reduced API response time by 42% by introducing Redis caching and optimizing PostgreSQL queries.', bold_phrases: ['42%'], source_fact_ids: ['fact-2'] },
          { text: 'Cut release time from 45 to 12 minutes by automating delivery workflows with GitHub Actions.', bold_phrases: ['45 to 12 minutes'], source_fact_ids: ['fact-3'] },
        ],
      }],
      projects: [],
      education: [{
        institution: 'Toronto Metropolitan University',
        degree: 'Bachelor of Science in Computer Science',
        location: 'Toronto, Ontario',
        date_range: '2022',
        details: [],
        source_fact_ids: ['fact-6'],
      }],
      skill_groups: [{
        label: 'Technical',
        skills: ['Python', 'TypeScript', 'React', 'FastAPI', 'PostgreSQL', 'Docker'],
        source_fact_ids: ['fact-7'],
      }],
      missing_information: ['Confirm the preferred LinkedIn URL.'],
      estimated_relevant_experience_years: 3,
      experience_estimate_confidence: 0.9,
    },
    claims_ledger: [
      { section: 'experience', generated_text: 'Reduced API response time by 42%.', source_fact_ids: ['fact-2'] },
      { section: 'experience', generated_text: 'Cut release time from 45 to 12 minutes.', source_fact_ids: ['fact-3'] },
      { section: 'education', generated_text: 'Bachelor of Science in Computer Science.', source_fact_ids: ['fact-6'] },
    ],
    artifact: null,
    requires_user_review: true,
    quality_status: 'passed',
    quality_notes: [],
    warnings: [{
      code: 'CREATOR_MISSING_INFORMATION',
      message: 'Confirm the preferred LinkedIn URL.',
      source: 'resume_creator_agent',
    }],
    errors: [],
  },
  agent_statuses: {
    resume_review_agent: 'not_invoked',
    resume_creator_agent: 'completed',
  },
  warnings: [{
    code: 'CREATOR_MISSING_INFORMATION',
    message: 'Confirm the preferred LinkedIn URL.',
    source: 'resume_creator_agent',
  }],
  errors: [],
};

function routeFromPath(pathname: string): Route {
  if (pathname.startsWith('/signin')) return 'signin';
  if (pathname.startsWith('/app')) return 'workspace';
  return 'landing';
}

function Logo({ onClick }: { onClick: () => void }) {
  return (
    <button className="logo" type="button" onClick={onClick} aria-label="ResumeAI home">
      <span className="logo-icon" aria-hidden="true">◆</span>
      <span className="logo-text">ResumeAI</span>
    </button>
  );
}

function LandingPage({ navigate }: { navigate: (path: string) => void }) {
  return (
    <div className="landing-page">
      <div className="landing-aurora-field" aria-hidden="true">
        <span className="landing-orb landing-orb-one" />
        <span className="landing-orb landing-orb-two" />
        <span className="landing-orb landing-orb-three" />
        <span className="landing-orb landing-orb-four" />
        <span className="landing-orb landing-orb-five" />
      </div>
      <nav className="landing-nav">
        <div className="nav-container">
          <Logo onClick={() => navigate('/')} />
          <div className="nav-links">
            <a href="#features">Features</a>
            <a href="#how-it-works">How It Works</a>
          </div>
          <div className="nav-actions">
            <button className="btn btn-ghost" onClick={() => navigate('/signin')}>Sign In</button>
            <button className="btn btn-primary" onClick={() => navigate('/app')}>Get Started</button>
          </div>
        </div>
      </nav>

      <main>
        <section className="hero">
          <div className="hero-content">
            <div className="hero-badge"><span>✦</span> Multi-model resume intelligence</div>
            <h1>Your Resume, <span className="gradient-text">Perfected</span></h1>
            <p className="hero-subtitle">
              Review your content, visual design, and document layout—or generate a
              grounded, downloadable resume from your verified experience.
            </p>
            <div className="hero-actions">
              <button className="btn btn-primary btn-lg" onClick={() => navigate('/app')}>
                Start Free Analysis <span>→</span>
              </button>
              <a className="btn btn-secondary btn-lg" href="#how-it-works">See How It Works</a>
            </div>
            <div className="hero-stats">
              <div className="stat"><strong>3</strong><span>Review Branches</span></div>
              <div className="stat-divider" />
              <div className="stat"><strong>2</strong><span>Specialized Agents</span></div>
              <div className="stat-divider" />
              <div className="stat"><strong>1</strong><span>Unified Workflow</span></div>
            </div>
          </div>

          <div className="hero-visual" aria-label="Example resume analysis">
            <div className="preview-card">
              <div className="preview-header">
                <div className="preview-dots"><span /><span /><span /></div>
                <span>Resume Analysis</span>
              </div>
              <div className="preview-content">
                <div className="preview-score">
                  <div className="score-ring"><span>85</span></div>
                  <small>Visual Score</small>
                </div>
                <div className="preview-branches">
                  {[
                    ['Aa', 'Content'],
                    ['◉', 'Visual'],
                    ['⌗', 'Layout'],
                  ].map(([icon, label]) => (
                    <div className="branch" key={label}>
                      <span className="branch-icon">{icon}</span>
                      <span>{label}</span>
                      <span className="branch-status">Available</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </section>

        <section id="features" className="features landing-section">
          <div className="section-heading">
            <span className="section-kicker">INTELLIGENT REVIEW</span>
            <h2>Three-Branch Analysis</h2>
            <p>Independent reviewers work together for comprehensive feedback.</p>
          </div>
          <div className="features-grid">
            {[
              ['Aa', 'Content Review', 'GPT evaluates clarity, evidence, XYZ bullets, quantification, and job relevance.', ['Achievement quality', 'Metric coverage', 'Role alignment']],
              ['◉', 'Visual Review', 'Gemini evaluates the rendered pages and returns a visual score with stable issue codes.', ['Visual hierarchy', 'Alignment consistency', 'Metric emphasis']],
              ['⌗', 'Layout Analysis', 'Deterministic measurements verify the document before the AI recommendations are combined.', ['Font sizes', 'Text density', 'Nonblank page count']],
            ].map(([icon, title, description, bullets], index) => (
              <article className={`feature-card ${index === 1 ? 'featured' : ''}`} key={title as string}>
                {index === 1 && <span className="feature-badge">VISION AI</span>}
                <div className="feature-icon">{icon as string}</div>
                <h3>{title as string}</h3>
                <p>{description as string}</p>
                <ul>{(bullets as string[]).map((bullet) => <li key={bullet}>{bullet}</li>)}</ul>
              </article>
            ))}
          </div>
        </section>

        <section id="how-it-works" className="how-it-works landing-section">
          <div className="section-heading">
            <span className="section-kicker">THE WORKFLOW</span>
            <h2>How It Works</h2>
            <p>From source material to actionable output in one guided workspace.</p>
          </div>
          <div className="steps">
            {[
              ['01', 'Choose a workflow', 'Review an existing resume or create a new one.'],
              ['02', 'Provide context', 'Add a job description and your instructions.'],
              ['03', 'AI agents work', 'Specialized models analyze or draft your resume.'],
              ['04', 'Act on results', 'Improve your resume or download the generated PDF.'],
            ].map(([number, title, description]) => (
              <article className="step" key={number}>
                <div className="step-number">{number}</div>
                <h3>{title}</h3>
                <p>{description}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="cta-section">
          <div>
            <span className="section-kicker">YOUR NEXT APPLICATION</span>
            <h2>Ready to build a stronger resume?</h2>
            <p>Use the complete review and creation workflow from one workspace.</p>
            <button className="btn btn-primary btn-lg" onClick={() => navigate('/app')}>
              Open ResumeAI <span>→</span>
            </button>
          </div>
        </section>
      </main>

      <footer className="landing-footer">
        <Logo onClick={() => navigate('/')} />
        <p>AI-powered resume analysis and creation.</p>
        <span>Built with OpenAI, Gemini, and LangGraph.</span>
      </footer>
    </div>
  );
}

function SignInPage({ navigate }: { navigate: (path: string) => void }) {
  const submitDemo = (event: React.FormEvent) => {
    event.preventDefault();
    navigate('/app');
  };

  return (
    <div className="auth-page">
      <div className="auth-container">
        <section className="auth-card">
          <Logo onClick={() => navigate('/')} />
          <div className="auth-heading">
            <span className="demo-pill">DEMO SCREEN</span>
            <h1>Welcome back</h1>
            <p>Sign in to continue to your resume workspace.</p>
          </div>
          <form className="auth-form" onSubmit={submitDemo}>
            <label>Email address<input type="email" placeholder="you@example.com" /></label>
            <div className="label-row"><label htmlFor="password">Password</label><button type="button">Forgot password?</button></div>
            <input id="password" type="password" placeholder="Enter your password" />
            <label className="checkbox-label"><input type="checkbox" /> Remember me for 30 days</label>
            <button className="btn btn-primary w-full" type="submit">Continue to demo <span>→</span></button>
          </form>
          <div className="auth-divider"><span>or continue with</span></div>
          <div className="social-buttons">
            <button className="btn btn-secondary" type="button" onClick={() => navigate('/app')}>Google</button>
            <button className="btn btn-secondary" type="button" onClick={() => navigate('/app')}>GitHub</button>
          </div>
          <p className="auth-note">Authentication is intentionally mocked. No account is created and no credentials are stored.</p>
        </section>
        <aside className="auth-visual">
          <div className="visual-orb" />
          <div className="visual-content">
            {[
              ['01', 'Three-branch review', 'Content, visual, and layout checks combine into one result.'],
              ['02', 'Priority actions', 'Fix the most important issues first with stable issue codes.'],
              ['03', 'Resume creation', 'Generate a grounded LaTeX resume and download the PDF.'],
            ].map(([number, title, description]) => (
              <article className="visual-card" key={number}>
                <span>{number}</span><div><h3>{title}</h3><p>{description}</p></div>
              </article>
            ))}
          </div>
        </aside>
      </div>
    </div>
  );
}

function WorkspacePage({ navigate }: { navigate: (path: string) => void }) {
  const [buildMode, setBuildMode] = useState(false);
  const [mode, setMode] = useState<WorkspaceMode>('review');
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [contexts, setContexts] = useState<
    Record<WorkspaceMode, { jobDescription: string; instructions: string }>
  >({
    review: { jobDescription: '', instructions: '' },
    create: { jobDescription: '', instructions: '' },
  });
  const [workflows, setWorkflows] = useState<
    Record<WorkspaceMode, WorkflowResponse | null>
  >({ review: null, create: null });
  const [loadingStates, setLoadingStates] = useState<
    Record<WorkspaceMode, boolean>
  >({ review: false, create: false });
  const [errors, setErrors] = useState<Record<WorkspaceMode, string>>({
    review: '',
    create: '',
  });
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [location, setLocation] = useState('');
  const [links, setLinks] = useState('');
  const [targetRole, setTargetRole] = useState('');
  const [facts, setFacts] = useState('');
  const fileInput = useRef<HTMLInputElement>(null);
  const resultsRef = useRef<HTMLDivElement>(null);
  const activeModeRef = useRef<WorkspaceMode | 'build'>(mode);
  const [resultRevealSequence, setResultRevealSequence] = useState(0);
  const workflow = workflows[mode];
  const loading = loadingStates[mode];
  const error = errors[mode];
  const { jobDescription, instructions } = contexts[mode];

  const setWorkflowFor = (
    target: WorkspaceMode,
    value: WorkflowResponse | null,
  ) => setWorkflows((current) => ({ ...current, [target]: value }));
  const setLoadingFor = (target: WorkspaceMode, value: boolean) =>
    setLoadingStates((current) => ({ ...current, [target]: value }));
  const setErrorFor = (target: WorkspaceMode, value: string) =>
    setErrors((current) => ({ ...current, [target]: value }));
  const setContextFor = (
    target: WorkspaceMode,
    field: 'jobDescription' | 'instructions',
    value: string,
  ) =>
    setContexts((current) => ({
      ...current,
      [target]: { ...current[target], [field]: value },
    }));

  useEffect(() => {
    activeModeRef.current = buildMode ? 'build' : mode;
  }, [mode, buildMode]);

  useEffect(() => {
    if (resultRevealSequence === 0) return;
    const frame = window.requestAnimationFrame(() => {
      window.requestAnimationFrame(() => {
        resultsRef.current?.scrollIntoView({
          behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches
            ? 'auto'
            : 'smooth',
          block: 'start',
        });
      });
    });
    return () => window.cancelAnimationFrame(frame);
  }, [resultRevealSequence]);

  const revealWorkflow = (
    target: WorkspaceMode,
    value: WorkflowResponse,
  ) => {
    setWorkflowFor(target, value);
    if (activeModeRef.current === target) {
      setResultRevealSequence((current) => current + 1);
    }
  };

  const changeMode = (next: WorkspaceMode) => {
    setBuildMode(false);
    setMode(next);
  };

  const reviewFile = async (candidate: File) => {
    setLoadingFor('review', true);
    setWorkflowFor('review', null);
    setErrorFor('review', '');
    try {
      revealWorkflow(
        'review',
        await analyzeResume(
          candidate,
          contexts.review.jobDescription,
          contexts.review.instructions,
        ),
      );
    } catch (reason) {
      setErrorFor('review', reason instanceof Error ? reason.message : 'The review workflow could not be completed.');
    } finally {
      setLoadingFor('review', false);
    }
  };

  const runReview = async () => {
    if (!file) return setErrorFor('review', 'Choose a PDF, DOCX, PNG, or JPG resume first.');
    await reviewFile(file);
  };

  const reviewBuilderResume = async (candidate: File) => {
    setFile(candidate);
    activeModeRef.current = 'review';
    setBuildMode(false);
    setMode('review');
    await reviewFile(candidate);
  };

  const runCreation = async () => {
    const sourceFacts = buildSourceFacts(facts);
    if (!name.trim() || !sourceFacts.length) {
      return setErrorFor('create', 'Add your full name and at least one verified fact.');
    }
    if (name.trim().length > 120) {
      return setErrorFor('create', 'Full name must be 120 characters or fewer.');
    }
    if (sourceFacts.length > 80) {
      return setErrorFor('create', 'Use no more than 80 verified facts.');
    }
    const oversizedFact = sourceFacts.findIndex((fact) => fact.length > 1000);
    if (oversizedFact >= 0) {
      return setErrorFor('create', `Verified fact ${oversizedFact + 1} must be 1,000 characters or fewer.`);
    }
    const parsedLinks = links.split('\n').map((link) => link.trim()).filter(Boolean);
    if (parsedLinks.length > 6) {
      return setErrorFor('create', 'Use no more than six links.');
    }
    setLoadingFor('create', true);
    setWorkflowFor('create', null);
    setErrorFor('create', '');
    try {
      revealWorkflow(
        'create',
        await createResume({
          full_name: name.trim(),
          email: email.trim() || undefined,
          phone: phone.trim() || undefined,
          location: location.trim() || undefined,
          links: parsedLinks,
          target_role: targetRole.trim() || undefined,
          source_facts: sourceFacts.map((text, index) => ({ fact_id: `fact-${index + 1}`, text })),
        }, contexts.create.jobDescription, contexts.create.instructions),
      );
    } catch (reason) {
      setErrorFor('create', reason instanceof Error ? reason.message : 'The creation workflow could not be completed.');
    } finally {
      setLoadingFor('create', false);
    }
  };

  const fillSample = () => {
    setName('Jordan Lee');
    setEmail('jordan.lee@example.com');
    setPhone('+1 416 555 0142');
    setLocation('Toronto, Ontario');
    setLinks('https://linkedin.com/in/jordanlee\nhttps://github.com/jordanlee');
    setTargetRole('Software Engineer');
    setFacts(SAMPLE_CREATOR_FACTS);
    setContextFor('create', 'jobDescription', 'Seeking a Software Engineer with experience building scalable APIs, React applications, cloud infrastructure, and automated delivery pipelines.');
    setContextFor('create', 'instructions', 'Create a concise one-page resume emphasizing measurable technical impact.');
    setWorkflowFor('create', null);
    setErrorFor('create', '');
  };

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-header"><Logo onClick={() => navigate('/')} /></div>
        <nav className="sidebar-nav" aria-label="Resume workflows">
          <span className="nav-section-title">WORKSPACE</span>
          <button className={`nav-item ${!buildMode && mode === 'review' ? 'active' : ''}`} onClick={() => changeMode('review')}>
            <span className="nav-item-icon">◎</span><span>Review Resume</span>{workflows.review && <small>SAVED</small>}
          </button>
          <button className={`nav-item ${!buildMode && mode === 'create' ? 'active' : ''}`} onClick={() => changeMode('create')}>
            <span className="nav-item-icon">✦</span><span>Create Resume</span><small>{workflows.create ? 'SAVED' : 'NEW'}</small>
          </button>
          <button className={`nav-item ${buildMode ? 'active' : ''}`} onClick={() => setBuildMode(true)}>
            <span className="nav-item-icon">+</span><span>BUILD YOUR OWN</span><small>NEW</small>
          </button>
        </nav>
        <div className="sidebar-footer">
          <div className="user-avatar">JD</div>
          <div><strong>Demo User</strong><span>Local workspace</span></div>
        </div>
      </aside>

      <main className="main-content">
        <header className="app-header">
          <div><span className="header-kicker">RESUME WORKSPACE</span><h1>{buildMode ? 'Build Your Own' : mode === 'review' ? 'Review Resume' : 'Create Resume'}</h1></div>
          <div className="system-status"><span /> {buildMode ? 'Manual resume studio' : 'AI workflow online'}</div>
        </header>

        <div className="page-content">
          <div hidden={!buildMode}><ResumeBuilder onSendToReview={reviewBuilderResume} /></div>
          <div hidden={buildMode}>
          <div className="page-intro">
            <div>
              <span className="section-kicker">{mode === 'review' ? 'MULTI-MODEL ANALYSIS' : 'GROUNDED GENERATION'}</span>
              <h2>{mode === 'review' ? 'Get a complete resume review' : 'Create from verified facts'}</h2>
              <p>{mode === 'review'
                ? 'Upload your resume. Content, visual, and layout branches run independently and combine into prioritized actions.'
                : 'Provide only facts you can verify. The creator agent turns them into a polished LaTeX resume without inventing experience.'}</p>
            </div>
            {mode === 'create' && <button className="btn btn-secondary" type="button" onClick={fillSample}>Autofill sample</button>}
          </div>

          {mode === 'review' ? (
            <section className="workspace-card upload-section">
              <div
                className={`upload-box ${dragging ? 'drag-over' : ''} ${file ? 'has-file' : ''}`}
                role="button"
                tabIndex={0}
                onClick={() => fileInput.current?.click()}
                onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') fileInput.current?.click(); }}
                onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
                onDragLeave={() => setDragging(false)}
                onDrop={(event) => {
                  event.preventDefault();
                  setDragging(false);
                  setFile(event.dataTransfer.files[0] || null);
                }}
              >
                <input
                  ref={fileInput}
                  hidden
                  type="file"
                  accept=".pdf,.docx,.png,.jpg,.jpeg"
                  onChange={(event) => setFile(event.target.files?.[0] || null)}
                />
                <div className="upload-icon">{file ? '✓' : '↑'}</div>
                <h3>{file ? file.name : 'Drop your resume here'}</h3>
                <p>{file ? `${(file.size / 1024 / 1024).toFixed(2)} MB · click to replace` : 'or click to browse your files'}</p>
                <div className="upload-formats"><span>PDF</span><span>DOCX</span><span>PNG</span><span>JPG</span></div>
                <small>Maximum file size and page limits are enforced by the API.</small>
              </div>
              <div className="branch-info">
                {[
                  ['Aa', 'Content', 'GPT text analysis'],
                  ['◉', 'Visual', 'Gemini page review'],
                  ['⌗', 'Layout', 'Deterministic metrics'],
                ].map(([icon, title, text]) => <div key={title}><span>{icon}</span><p><strong>{title}</strong><small>{text}</small></p></div>)}
              </div>
            </section>
          ) : (
            <section className="workspace-card creator-form">
                <div className="form-section-title"><span>01</span><div><h3>Identity and target</h3><p>Basic information for the resume header.</p></div></div>
                <div className="form-grid">
                  <label>Full name *<input value={name} onChange={(e) => setName(e.target.value)} placeholder="Jordan Lee" /></label>
                  <label>Target role<input value={targetRole} onChange={(e) => setTargetRole(e.target.value)} placeholder="Software Engineer" /></label>
                  <label>Email<input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="jordan@example.com" /></label>
                  <label>Phone<input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+1 416 555 0142" /></label>
                  <label>Location<input value={location} onChange={(e) => setLocation(e.target.value)} placeholder="Toronto, Ontario" /></label>
                  <label>Links, one per line<textarea rows={2} value={links} onChange={(e) => setLinks(e.target.value)} placeholder="https://linkedin.com/in/..." /></label>
                </div>
                <div className="form-section-title second"><span>02</span><div><h3>Verified source facts</h3><p>Paste individual facts or a complete LinkedIn/profile export. Related lines are grouped safely.</p></div></div>
                <label>Career, project, education, and skill facts *<textarea rows={11} value={facts} onChange={(e) => setFacts(e.target.value)} placeholder={'Paste verified profile text or enter one fact per line.\nExample: Reduced processing time by 40% by adding Redis caching.'} /></label>
            </section>
          )}

          <section className="workspace-card context-card">
            <div className="form-section-title"><span>{mode === 'review' ? '02' : '03'}</span><div><h3>Target and instructions</h3><p>Optional context helps tailor the output to your goal.</p></div></div>
            <div className="context-grid">
              <label>Job description <span>Optional</span><textarea rows={6} value={jobDescription} onChange={(e) => setContextFor(mode, 'jobDescription', e.target.value)} placeholder="Paste the target job description..." /></label>
              <label>Additional instructions <span>Optional</span><textarea rows={6} value={instructions} onChange={(e) => setContextFor(mode, 'instructions', e.target.value)} placeholder="What should the workflow prioritize?" /></label>
            </div>
          </section>

          <div className="run-actions">
            <button
              className="btn btn-primary btn-lg"
              type="button"
              disabled={loading || (mode === 'review' ? !file : !name.trim() || !facts.trim())}
              onClick={mode === 'review' ? runReview : runCreation}
            >
              {loading ? 'Running workflow…' : mode === 'review' ? 'Analyze Resume →' : 'Create Resume →'}
            </button>
            {mode === 'review' && <button className="btn btn-secondary" type="button" disabled={loading} onClick={() => { setErrorFor('review', ''); revealWorkflow('review', MOCK_WORKFLOW); }}>Preview sample result</button>}
            {mode === 'create' && <button className="btn btn-secondary" type="button" disabled={loading} onClick={() => { setErrorFor('create', ''); revealWorkflow('create', MOCK_CREATOR_WORKFLOW); }}>Preview creator result</button>}
          </div>

          {loading && <ProcessingPanel mode={mode} />}
          {error && <div className="error-banner" role="alert"><strong>Workflow error</strong><span>{error}</span></div>}
          {workflow && (
            <div
              className="result-anchor"
              ref={resultsRef}
              key={`${workflow.workflow_id}-${resultRevealSequence}`}
            >
              <WorkflowResults workflow={workflow} />
            </div>
          )}
          </div>
        </div>
      </main>
    </div>
  );
}

function ProcessingPanel({ mode }: { mode: WorkspaceMode }) {
  const stages = mode === 'review'
    ? ['Secure document preparation', 'Content, visual, and layout review', 'Priority synthesis']
    : ['Grounding source facts', 'Drafting structured resume', 'Compiling LaTeX and PDF'];
  return (
    <section className="processing-card" aria-live="polite">
      <div className="spinner" />
      <div><h3>{mode === 'review' ? 'Analyzing your resume' : 'Creating your resume'}</h3><p>{stages.join(' · ')}</p></div>
    </section>
  );
}

function BranchCard({ name, icon, status, children }: { name: string; icon: string; status: string; children: React.ReactNode }) {
  return (
    <article className="result-card branch-result">
      <div className="result-card-header"><div className="result-title"><span>{icon}</span><h3>{name}</h3></div><StatusBadge status={status} /></div>
      {children}
    </article>
  );
}

function StatusBadge({ status }: { status: string }) {
  return <span className={`status-badge status-${status}`}>{status.replaceAll('_', ' ')}</span>;
}

function WorkflowResults({ workflow }: { workflow: WorkflowResponse }) {
  const review = workflow.review;
  const creation = workflow.creation;
  return (
    <section className="results-section" aria-live="polite">
      <div className="results-heading">
        <div><span className="section-kicker">WORKFLOW {workflow.workflow_id.slice(0, 8).toUpperCase()}</span><h2>{creation ? 'Your generated resume' : 'Your review results'}</h2></div>
        <StatusBadge status={workflow.status} />
      </div>

      <article className="result-card summary-result">
        <div className="summary-mark">✦</div>
        <div>
          <span className="result-label">COMBINED ASSESSMENT</span>
          <h3>{workflow.summary?.overall_assessment || workflow.final_message}</h3>
          {workflow.summary?.top_strengths.length ? <div className="strength-chips">{workflow.summary.top_strengths.map((item) => <span key={item}>✓ {item}</span>)}</div> : null}
        </div>
      </article>

      {workflow.summary?.priority_actions.length ? (
        <article className="result-card">
          <div className="result-card-header"><div><span className="result-label">NEXT MOVES</span><h3>Priority actions</h3></div><span className="count-badge">{workflow.summary.priority_actions.length}</span></div>
          <ol className="priority-actions">
            {workflow.summary.priority_actions.map((action) => (
              <li key={`${action.priority}-${action.issue_code}`}>
                <span className="priority-number">{String(action.priority).padStart(2, '0')}</span>
                <div><div className="action-meta"><span>{action.source}</span>{action.issue_code && <code>{action.issue_code}</code>}</div><h4>{action.title}</h4><p>{action.recommendation}</p></div>
              </li>
            ))}
          </ol>
          <p className="next-step"><strong>Next step:</strong> {workflow.summary.next_step}</p>
        </article>
      ) : null}

      {review && <ReviewResults review={review} />}
      {creation && <CreationResults workflow={workflow} />}

      {(workflow.warnings.length > 0 || workflow.errors.length > 0) && (
        <article className="result-card warning-card">
          <h3>Workflow notices</h3>
          {[...workflow.warnings, ...workflow.errors].map((message, index) => <p key={`${message.code}-${index}`}><code>{message.code}</code> {message.message}</p>)}
        </article>
      )}
    </section>
  );
}

function ReviewResults({ review }: { review: ReviewAgentResult }) {
  const visual = review.visual_review.result;
  const layout = review.layout_analysis;
  return (
    <>
      <div className="review-branches">
        <BranchCard name="Content Review" icon="Aa" status={review.content_review.status}>
          {review.content_review.response
            ? <div className="markdown-content"><ReactMarkdown>{review.content_review.response}</ReactMarkdown></div>
            : <Unavailable message={review.content_review.error_message} />}
        </BranchCard>
        <BranchCard name="Visual Review" icon="◉" status={review.visual_review.status}>
          {visual ? (
            <>
              <div className="visual-score-row"><div className="mini-score" role="img" aria-label={`Visual score ${visual.visual_score} out of 100`} style={{ '--score': `${visual.visual_score * 3.6}deg` } as React.CSSProperties}><div className="score-number"><strong>{visual.visual_score}</strong><span>/100</span></div></div><div><strong>{visual.pass_status ? 'Visual review passed' : 'Visual improvements needed'}</strong><p>{review.visual_review.page_count} nonblank page{review.visual_review.page_count === 1 ? '' : 's'} reviewed</p></div></div>
              {visual.issues.map((issue) => <div className={`visual-issue severity-${issue.severity}`} key={issue.code}><code>{issue.code}</code><strong>{issue.description}</strong><p>{issue.recommendation}</p></div>)}
            </>
          ) : <Unavailable message={review.visual_review.error_message} />}
        </BranchCard>
        <BranchCard name="Layout Analysis" icon="⌗" status={layout.status}>
          {layout.status === 'available' ? (
            <div className="metric-grid">
              <div><strong>{layout.page_count ?? '—'}</strong><span>Nonblank pages</span></div>
              <div><strong>{layout.pages[0]?.dominant_font_size ?? '—'}{layout.pages[0]?.dominant_font_size ? 'pt' : ''}</strong><span>Dominant font</span></div>
              <div><strong>{layout.pages[0] ? `${Math.round(layout.pages[0].text_density * 100)}%` : '—'}</strong><span>Text density</span></div>
              <div><strong>{layout.pages[0] ? `${Math.round(layout.pages[0].width_points)} × ${Math.round(layout.pages[0].height_points)}` : '—'}</strong><span>Page points</span></div>
            </div>
          ) : <Unavailable message={layout.error_message} />}
        </BranchCard>
      </div>
      {review.policy_findings.length > 0 && (
        <article className="result-card">
          <div className="result-card-header"><div><span className="result-label">RESUME STANDARDS</span><h3>Policy scorecard</h3></div><span className="version-badge">v{review.policy_version}</span></div>
          <div className="policy-grid">
            {review.policy_findings.map((finding) => (
              <div className={`policy-finding policy-${finding.status}`} key={finding.code}>
                <div><code>{finding.code}</code><h4>{finding.description}</h4></div>
                <StatusBadge status={finding.status} />
                <p>{finding.recommendation}</p>
              </div>
            ))}
          </div>
        </article>
      )}
    </>
  );
}

function Unavailable({ message }: { message: string | null }) {
  return <div className="unavailable"><strong>This branch is unavailable.</strong><p>{message || 'No result was returned. Other successful branches remain valid.'}</p></div>;
}

function CreationResults({ workflow }: { workflow: WorkflowResponse }) {
  const creation = workflow.creation;
  if (!creation) return null;
  const pdfDownloadUrl = creation.artifact?.pdf_download_url
    ? artifactUrl(creation.artifact.pdf_download_url)
    : null;
  const previewImageUrl = workflow.workflow_id === 'mock-creator-workflow'
    ? MOCK_CREATOR_PREVIEW
    : creation.artifact?.pdf_download_url && creation.artifact.artifact_id
      ? artifactUrl(
          `/api/artifact-previews/${creation.artifact.artifact_id}.png`,
        )
      : null;
  return (
    <article className="result-card creation-result">
      <div className="creation-result-layout">
        <div className="creation-result-details">
          <div className="result-card-header"><div><span className="result-label">RESUME CREATOR AGENT</span><h3>Grounded LaTeX draft</h3></div><StatusBadge status={creation.status} /></div>
          <p>{workflow.final_message}</p>
          {creation.artifact && (
            <div className="artifact-area">
              <div><span>COMPILATION</span><strong>{creation.artifact.compilation_status.replaceAll('_', ' ')}</strong></div>
              <div className="artifact-actions">
                {pdfDownloadUrl && <a className="btn btn-primary" href={pdfDownloadUrl} download>Download PDF</a>}
                <a className="btn btn-secondary" href={artifactUrl(creation.artifact.tex_download_url)} download>Download LaTeX</a>
              </div>
            </div>
          )}
          <div className="creation-stats">
            <div><strong>{creation.claims_ledger.length}</strong><span>Grounded claims</span></div>
            <div><strong>{creation.document?.missing_information.length ?? 0}</strong><span>Missing details</span></div>
            <div><strong>{creation.quality_status === 'passed' ? 'Passed' : 'Review'}</strong><span>Resume standards</span></div>
          </div>
          {creation.quality_notes.length > 0 && <div className="missing-info"><h4>Standards needing more evidence</h4><ul>{creation.quality_notes.map((item) => <li key={item}>{item}</li>)}</ul></div>}
          {(creation.document?.missing_information.length ?? 0) > 0 && <div className="missing-info"><h4>Information to add next</h4><ul>{creation.document?.missing_information.map((item) => <li key={item}>{item}</li>)}</ul></div>}
        </div>
        {previewImageUrl ? (
          <GeneratedResumePreview
            key={previewImageUrl}
            imageUrl={previewImageUrl}
          />
        ) : (
          <aside className="preview-unavailable">
            <strong>PDF preview unavailable</strong>
            <p>The structured draft is complete, but a compiled PDF was not returned. Download the LaTeX source to inspect the document.</p>
          </aside>
        )}
      </div>
    </article>
  );
}

function GeneratedResumePreview({
  imageUrl,
}: {
  imageUrl: string;
}) {
  const [previewLoaded, setPreviewLoaded] = useState(false);
  const [previewError, setPreviewError] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [retryKey, setRetryKey] = useState(0);

  const renderedImageUrl = imageUrl.startsWith('data:')
    ? imageUrl
    : `${imageUrl}${imageUrl.includes('?') ? '&' : '?'}render=3&retry=${retryKey}`;

  useEffect(() => {
    if (!modalOpen) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setModalOpen(false);
    };
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    window.addEventListener('keydown', closeOnEscape);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener('keydown', closeOnEscape);
    };
  }, [modalOpen]);

  return (
    <aside className="generated-preview-side">
      <div className="generated-preview-header">
        <div>
          <span className="result-label">GENERATED DOCUMENT</span>
          <h3>Resume preview</h3>
        </div>
        <button type="button" onClick={() => setModalOpen(true)} disabled={!previewLoaded}>Expand</button>
      </div>
      {!previewError && (
        <button className={`preview-image-link ${previewLoaded ? 'is-loaded' : 'is-loading'}`} type="button" onClick={() => previewLoaded && setModalOpen(true)} aria-label="Open resume preview">
          <img
            src={renderedImageUrl}
            alt="First page of the generated resume"
            onLoad={() => setPreviewLoaded(true)}
            onError={() => setPreviewError('The generated preview could not be rendered. The PDF may have expired or the preview service may be unavailable.')}
          />
        </button>
      )}
      {previewError ? (
        <div className="preview-load-state preview-load-error">
          <strong>Preview could not load</strong>
          <p>{previewError}</p>
          <button
            className="btn btn-secondary"
            type="button"
            onClick={() => {
              setPreviewLoaded(false);
              setPreviewError('');
              setRetryKey((value) => value + 1);
            }}
          >
            Retry preview
          </button>
        </div>
      ) : !previewLoaded ? (
        <div className="preview-load-state">
          <div className="spinner" />
          <p>Rendering PDF preview…</p>
        </div>
      ) : null}
      <p className="preview-caption">Rendered from the compiled PDF. Select the preview to expand it.</p>
      {modalOpen && previewLoaded && (
        <div
          className="resume-modal-backdrop"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) setModalOpen(false);
          }}
        >
          <section
            className="resume-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="resume-preview-title"
          >
            <header className="resume-modal-header">
              <div>
                <span className="result-label">GENERATED DOCUMENT</span>
                <h2 id="resume-preview-title">Resume preview</h2>
              </div>
              <button type="button" onClick={() => setModalOpen(false)} aria-label="Close resume preview">×</button>
            </header>
            <div className="resume-modal-canvas">
              <img src={renderedImageUrl} alt="Generated resume" />
            </div>
            <footer className="resume-modal-footer">
              <span>Press Esc or select outside the window to close.</span>
              <button className="btn btn-secondary" type="button" onClick={() => setModalOpen(false)}>Close preview</button>
            </footer>
          </section>
        </div>
      )}
    </aside>
  );
}

function App() {
  const [route, setRoute] = useState<Route>(() => routeFromPath(window.location.pathname));
  useEffect(() => {
    const handlePopState = () => setRoute(routeFromPath(window.location.pathname));
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);
  const navigate = (path: string) => {
    window.history.pushState({}, '', path);
    setRoute(routeFromPath(path));
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  if (route === 'signin') return <SignInPage navigate={navigate} />;
  if (route === 'workspace') return <WorkspacePage navigate={navigate} />;
  return <LandingPage navigate={navigate} />;
}

export default App;
