import { useEffect, useMemo, useState } from 'react';
import './ResumeGuide.css';

type Lesson = {
  id: string;
  number: string;
  eyebrow: string;
  title: string;
  summary: string;
  duration: string;
  principles: { title: string; body: string }[];
  before: string;
  after: string;
  question: string;
  choices: string[];
  answer: number;
  explanation: string;
};

const LESSONS: Lesson[] = [
  {
    id: 'blueprint', number: '01', eyebrow: 'Start smart', title: 'Build the right blueprint',
    summary: 'Give recruiters a clear path through your story before you polish a single bullet.', duration: '4 min',
    principles: [
      { title: 'Lead with relevance', body: 'Put the sections that best prove your fit closest to the top. For most early-career candidates, that means skills, experience, projects, then education.' },
      { title: 'Make scanning effortless', body: 'Use familiar headings, consistent dates, and a strong name hierarchy. A recruiter should understand the page in a few seconds.' },
      { title: 'Protect the one-page promise', body: 'Stay on one page with fewer than five years of experience. Use two only when five-plus years of relevant content genuinely earns it.' },
    ],
    before: 'A long objective paragraph, mixed headings, and every role you have ever held.',
    after: 'A focused one-page story with recognizable sections and the strongest proof first.',
    question: 'Which section order is usually easiest for a technical recruiter to scan?',
    choices: ['Relevant skills and evidence first', 'References and hobbies first', 'Everything in chronological order'], answer: 0,
    explanation: 'Lead with the information that helps the reader judge your fit fastest. Relevance matters more than tradition.',
  },
  {
    id: 'xyz', number: '02', eyebrow: 'Write impact', title: 'Master the XYZ bullet',
    summary: 'Turn responsibilities into evidence using: accomplished X, measured by Y, by doing Z.', duration: '6 min',
    principles: [
      { title: 'X — the outcome', body: 'Start with what changed: improved reliability, accelerated delivery, grew adoption, or reduced errors.' },
      { title: 'Y — the evidence', body: 'Prove scale with a number, frequency, team size, volume, percentage, time saved, or audience reached.' },
      { title: 'Z — the method', body: 'Explain how you produced the result with specific tools, decisions, collaboration, or technical work.' },
    ],
    before: 'Responsible for maintaining the company API.',
    after: 'Reduced API response time by 42% by introducing Redis caching and optimizing PostgreSQL queries.',
    question: 'Which bullet provides the strongest evidence?',
    choices: ['Helped with deployments', 'Reduced release time from 45 to 12 minutes by automating CI/CD', 'Worked on a CI/CD pipeline'], answer: 1,
    explanation: 'The strongest version includes an outcome, a measurement, and the method used to achieve it.',
  },
  {
    id: 'metrics', number: '03', eyebrow: 'Prove the scale', title: 'Find metrics hiding in your work',
    summary: 'You have more measurable impact than you think—even when revenue was not involved.', duration: '5 min',
    principles: [
      { title: 'Measure the work', body: 'Count users, tickets, files, releases, features, stakeholders, teammates, requests, or weekly tasks.' },
      { title: 'Measure the change', body: 'Compare before and after: time, accuracy, throughput, cost, reliability, conversion, or manual steps.' },
      { title: 'Stay truthful', body: 'Never invent a number. If an exact figure is unavailable, use honest scope such as “across three teams” or “used weekly.”' },
    ],
    before: 'Created reports for the operations team.',
    after: 'Automated weekly reporting for 3 operations teams, removing 6 hours of manual work per cycle.',
    question: 'What should you do when you do not know an exact percentage?',
    choices: ['Make a conservative estimate', 'Remove all evidence', 'Use a truthful count, frequency, or scope instead'], answer: 2,
    explanation: 'Credibility wins. Team size, frequency, volume, and audience are useful measures when percentages are unavailable.',
  },
  {
    id: 'story', number: '04', eyebrow: 'Shape the story', title: 'Choose what earns space',
    summary: 'A resume is a highlight reel, not an archive. Every line should support the role you want.', duration: '5 min',
    principles: [
      { title: 'Prioritize outcomes', body: 'Give the most space to recent, relevant work. Older or less relevant roles can use fewer bullets.' },
      { title: 'Use projects as proof', body: 'Describe the problem, stack, scale, and result—not just a list of technologies.' },
      { title: 'Cut low-signal language', body: 'Remove “responsible for,” filler adjectives, first-person pronouns, and repeated ideas.' },
    ],
    before: 'Hard-working team player responsible for many important development tasks.',
    after: 'Led 5 developers to deliver a customer analytics dashboard used by 18 stakeholders.',
    question: 'A strong project bullet should focus primarily on…',
    choices: ['Every library installed', 'The problem, technical contribution, and result', 'Why the project was fun'], answer: 1,
    explanation: 'Technology matters, but it becomes persuasive when connected to a problem and a concrete result.',
  },
  {
    id: 'tailor', number: '05', eyebrow: 'Match the role', title: 'Tailor without keyword stuffing',
    summary: 'Mirror the employer’s language naturally while keeping every claim accurate.', duration: '4 min',
    principles: [
      { title: 'Read for signals', body: 'Highlight repeated skills, responsibilities, outcomes, seniority signals, and domain vocabulary in the job description.' },
      { title: 'Match real experience', body: 'Use the same standard term when it accurately describes your work. Never add a tool you cannot discuss.' },
      { title: 'Write for people and ATS', body: 'Use conventional headings and plain text structure. Avoid important information inside graphics, columns, or decorative icons.' },
    ],
    before: 'Built web services and worked with databases.',
    after: 'Built REST APIs with FastAPI and PostgreSQL, supporting 10,000+ monthly document-processing requests.',
    question: 'What is the safest ATS strategy?',
    choices: ['Hide keywords in white text', 'Use relevant job language where it truthfully matches your work', 'Copy the entire job description'], answer: 1,
    explanation: 'Natural, accurate alignment helps both automated screening and the human reader who follows it.',
  },
  {
    id: 'polish', number: '06', eyebrow: 'Ship with confidence', title: 'Run the final quality check',
    summary: 'Treat your resume like a product release: test the content, layout, and exported file.', duration: '5 min',
    principles: [
      { title: 'Check consistency', body: 'Standardize tense, punctuation, date formats, alignment, capitalization, and spacing across every section.' },
      { title: 'Use emphasis carefully', body: 'Bold meaningful metrics and high-value evidence—not entire bullets. Keep body text readable and hierarchy obvious.' },
      { title: 'Test the actual file', body: 'Open the final PDF, confirm links, remove accidental blank pages, select text, and check the filename before sending.' },
    ],
    before: 'resume_final_FINAL_v7.pdf with a blank second page and inconsistent dates.',
    after: 'FirstName_LastName_Resume.pdf — one clean page, working links, consistent formatting.',
    question: 'When should a blank second page count as resume content?',
    choices: ['Always', 'Never—remove it before submitting', 'Only when the first page is full'], answer: 1,
    explanation: 'A blank page is not content, but it is still a document defect. Remove it from the exported file before applying.',
  },
];

const STORAGE_KEY = 'resume-guide-progress-v1';
const INTRO_KEY = 'resume-guide-intro-v1';

const INTRO_STEPS = [
  {
    number: '01', kicker: 'WELCOME TO THE FIELD GUIDE', title: 'A resume course that gets to the point.',
    body: 'This is your practical training space. Six short lessons explain what recruiters look for, show real transformations, and help you apply each idea immediately.',
    accent: 'Learn at your pace', detail: 'About 29 minutes from start to finish', visual: 'map',
  },
  {
    number: '02', kicker: 'FOLLOW THE PATH', title: 'Learn one useful skill at a time.',
    body: 'Use Next and Previous—or your keyboard arrow keys—to move through the guide. You can also jump directly to any lesson from the path on the left.',
    accent: 'Your place is remembered', detail: 'Completed lessons save on this device', visual: 'path',
  },
  {
    number: '03', kicker: 'SEE IT IN ACTION', title: 'Study the makeover, then try it.',
    body: 'Every lesson combines simple principles with weak-versus-strong examples. The XYZ lesson includes a live lab where you can build an achievement bullet piece by piece.',
    accent: 'Practice beats memorizing', detail: 'Write outcomes, evidence, and methods', visual: 'compare',
  },
  {
    number: '04', kicker: 'CHECK YOUR INSTINCTS', title: 'Learn first. Quiz second.',
    body: 'A quick question appears after each lesson—not before it. Answer it, read the explanation, then mark the lesson complete and continue to the next skill.',
    accent: 'No pressure, just feedback', detail: 'Retry any answer and revisit any lesson', visual: 'quiz',
  },
] as const;

function loadCompleted(): string[] {
  try {
    const value = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
    const lessonIds = new Set(LESSONS.map(lesson => lesson.id));
    return Array.isArray(value)
      ? [...new Set(value.filter((item): item is string => typeof item === 'string' && lessonIds.has(item)))]
      : [];
  } catch {
    return [];
  }
}

function shouldShowIntro(): boolean {
  try { return localStorage.getItem(INTRO_KEY) !== 'seen'; }
  catch { return true; }
}

function XyzLab() {
  const [outcome, setOutcome] = useState('Reduced API response time');
  const [measure, setMeasure] = useState('by 42%');
  const [method, setMethod] = useState('introducing Redis caching and optimizing PostgreSQL queries');
  const bullet = [outcome.trim(), measure.trim(), method.trim() && `by ${method.trim().replace(/^by\s+/i, '')}`].filter(Boolean).join(' ');

  return <section className="guide-lab" aria-labelledby="xyz-lab-title">
    <div className="guide-lab-heading"><span>TRY IT</span><div><h3 id="xyz-lab-title">The XYZ bullet lab</h3><p>Build one line and watch the pieces click together.</p></div></div>
    <div className="guide-lab-fields">
      <label><span><b>X</b> What changed?</span><input value={outcome} onChange={event => setOutcome(event.target.value)} placeholder="Improved onboarding completion" /></label>
      <label><span><b>Y</b> How much?</span><input value={measure} onChange={event => setMeasure(event.target.value)} placeholder="by 24%" /></label>
      <label><span><b>Z</b> How?</span><input value={method} onChange={event => setMethod(event.target.value)} placeholder="by simplifying the signup flow" /></label>
    </div>
    <div className="guide-lab-result"><span>YOUR BULLET</span><p>{bullet || 'Your finished XYZ bullet will appear here.'}</p></div>
  </section>;
}

export default function ResumeGuide({ onOpenBuilder, onOpenReview }: { onOpenBuilder: () => void; onOpenReview: () => void }) {
  const [activeId, setActiveId] = useState(LESSONS[0].id);
  const [completed, setCompleted] = useState<string[]>(loadCompleted);
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [showIntro, setShowIntro] = useState(shouldShowIntro);
  const [introStep, setIntroStep] = useState(0);
  const activeIndex = LESSONS.findIndex(lesson => lesson.id === activeId);
  const lesson = LESSONS[activeIndex];
  const progress = Math.round((completed.length / LESSONS.length) * 100);
  const totalMinutes = useMemo(() => LESSONS.reduce((sum, item) => sum + Number.parseInt(item.duration, 10), 0), []);

  useEffect(() => {
    if (!showIntro) return;
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === 'ArrowRight') {
        event.preventDefault();
        if (introStep === INTRO_STEPS.length - 1) finishIntro();
        else setIntroStep(current => Math.min(INTRO_STEPS.length - 1, current + 1));
      }
      if (event.key === 'ArrowLeft') {
        event.preventDefault();
        setIntroStep(current => Math.max(0, current - 1));
      }
      if (event.key === 'Escape') finishIntro();
    };
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    window.addEventListener('keydown', handleKey);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener('keydown', handleKey);
    };
  }, [showIntro, introStep]);

  function finishIntro() {
    setShowIntro(false);
    setIntroStep(0);
    try { localStorage.setItem(INTRO_KEY, 'seen'); } catch { /* The walkthrough can still close for this session. */ }
  }

  function selectLesson(id: string) {
    setActiveId(id);
    window.requestAnimationFrame(() => document.querySelector('.guide-lesson')?.scrollIntoView({ behavior: 'smooth', block: 'start' }));
  }

  function completeLesson() {
    const next = completed.includes(lesson.id) ? completed : [...completed, lesson.id];
    setCompleted(next);
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(next)); } catch { /* Progress remains available for this session. */ }
    if (activeIndex < LESSONS.length - 1) selectLesson(LESSONS[activeIndex + 1].id);
  }

  const selectedAnswer = answers[lesson.id];
  const answered = selectedAnswer !== undefined;
  const correct = selectedAnswer === lesson.answer;

  return <div className="guide-shell">
    <section className="guide-hero">
      <div className="guide-hero-copy">
        <span className="section-kicker">RESUME FIELD GUIDE</span>
        <h2>Learn the craft.<br /><em>Build the proof.</em></h2>
        <p>Six short, practical lessons take you from an empty page to a focused resume recruiters can scan, trust, and remember.</p>
        <div className="guide-hero-actions"><div className="guide-hero-buttons"><button className="btn btn-primary" type="button" onClick={() => selectLesson(LESSONS[Math.min(completed.length, LESSONS.length - 1)].id)}>{completed.length ? 'Continue learning' : 'Start the field guide'}</button><button className="btn btn-ghost" type="button" onClick={() => { setIntroStep(0); setShowIntro(true); }}>How it works</button></div><span>{totalMinutes} minutes total · progress saves automatically</span></div>
      </div>
      <div className="guide-progress-card">
        <div className="guide-progress-ring" style={{ '--guide-progress': `${progress * 3.6}deg` } as React.CSSProperties}><div><strong>{progress}%</strong><span>complete</span></div></div>
        <div><span>YOUR PROGRESS</span><strong>{completed.length} of {LESSONS.length} lessons</strong><p>{progress === 100 ? 'Field guide complete. Your resume is ready for a final review.' : 'Small lessons. Practical examples. No filler.'}</p></div>
      </div>
    </section>

    <div className="guide-layout">
      <aside className="guide-path" aria-label="Course lessons">
        <div className="guide-path-heading"><span>YOUR PATH</span><small>{completed.length}/{LESSONS.length}</small></div>
        {LESSONS.map(item => <button key={item.id} type="button" className={`${item.id === lesson.id ? 'active' : ''} ${completed.includes(item.id) ? 'complete' : ''}`} onClick={() => selectLesson(item.id)} aria-current={item.id === lesson.id ? 'step' : undefined}>
          <span className="guide-step-number">{completed.includes(item.id) ? '✓' : item.number}</span>
          <span><small>{item.eyebrow}</small><strong>{item.title}</strong></span>
          <em>{item.duration}</em>
        </button>)}
        <div className="guide-path-tip"><span>GOOD TO KNOW</span><p>You can jump between lessons. Your completed steps stay saved on this device.</p></div>
      </aside>

      <article className="guide-lesson" key={lesson.id}>
        <header className="guide-lesson-header"><div><span>LESSON {lesson.number} · {lesson.duration}</span><h2>{lesson.title}</h2><p>{lesson.summary}</p></div><div className="guide-lesson-mark">{lesson.number}</div></header>

        <div className="guide-principles">{lesson.principles.map((principle, index) => <section key={principle.title}><span>0{index + 1}</span><div><h3>{principle.title}</h3><p>{principle.body}</p></div></section>)}</div>

        <section className="guide-makeover">
          <div className="guide-makeover-heading"><span>BEFORE → AFTER</span><h3>See the difference</h3></div>
          <div className="guide-before"><span>BEFORE</span><p>{lesson.before}</p></div>
          <div className="guide-after"><span>AFTER</span><p>{lesson.after}</p></div>
        </section>

        {lesson.id === 'xyz' && <XyzLab />}

        <section className="guide-check">
          <div className="guide-check-heading"><span>QUICK CHECK</span><h3>{lesson.question}</h3></div>
          <div className="guide-choices">{lesson.choices.map((choice, index) => <button key={choice} type="button" className={answered ? index === lesson.answer ? 'correct' : index === selectedAnswer ? 'incorrect' : '' : ''} onClick={() => setAnswers(current => ({ ...current, [lesson.id]: index }))}><span>{String.fromCharCode(65 + index)}</span>{choice}</button>)}</div>
          {answered && <div className={`guide-feedback ${correct ? 'correct' : 'retry'}`} role="status"><strong>{correct ? 'Exactly right.' : 'Not quite—take another look.'}</strong><p>{lesson.explanation}</p></div>}
        </section>

        <footer className="guide-lesson-footer">
          <button className="btn btn-ghost" type="button" disabled={activeIndex === 0} onClick={() => selectLesson(LESSONS[activeIndex - 1].id)}>← Previous</button>
          <span>{completed.includes(lesson.id) ? 'Lesson completed' : 'Ready for the next step?'}</span>
          <button className="btn btn-primary" type="button" onClick={completeLesson}>{activeIndex === LESSONS.length - 1 ? 'Complete the guide' : 'Complete & continue →'}</button>
        </footer>
      </article>
    </div>

    <section className="guide-finish">
      <div><span className="section-kicker">PUT IT INTO PRACTICE</span><h2>Knowledge becomes useful when it reaches the page.</h2><p>Build your resume from scratch, or review an existing document against the standards you just learned.</p></div>
      <div><button className="btn btn-primary" type="button" onClick={onOpenBuilder}>Build your own</button><button className="btn btn-secondary" type="button" onClick={onOpenReview}>Review my resume</button></div>
    </section>

    {showIntro && <div className="guide-intro-backdrop" role="presentation">
      <section className="guide-intro" role="dialog" aria-modal="true" aria-labelledby="guide-intro-title" aria-describedby="guide-intro-description">
        <header className="guide-intro-top"><div><span>FIELD GUIDE TOUR</span><strong>{introStep + 1} / {INTRO_STEPS.length}</strong></div><button type="button" onClick={finishIntro} aria-label="Skip introduction">Skip</button></header>
        <div className="guide-intro-body" key={introStep}>
          <div className={`guide-intro-visual ${INTRO_STEPS[introStep].visual}`} aria-hidden="true">
            {INTRO_STEPS[introStep].visual === 'map' && <><i>01</i><i>02</i><i>03</i><i>04</i><i>05</i><i>06</i></>}
            {INTRO_STEPS[introStep].visual === 'path' && <><i><small>01</small><span>LEARN</span></i><b>↓</b><i><small>02</small><span>SEE AN EXAMPLE</span></i><b>↓</b><i><small>03</small><span>TAKE THE QUIZ</span></i></>}
            {INTRO_STEPS[introStep].visual === 'compare' && <><i><small>BEFORE</small>Helped with APIs</i><b>→</b><i><small>AFTER</small>Cut API latency by 42%</i></>}
            {INTRO_STEPS[introStep].visual === 'quiz' && <><i>A</i><i className="selected">B</i><i>C</i><b>✓</b></>}
          </div>
          <div className="guide-intro-copy"><span>{INTRO_STEPS[introStep].kicker}</span><h2 id="guide-intro-title">{INTRO_STEPS[introStep].title}</h2><p id="guide-intro-description">{INTRO_STEPS[introStep].body}</p><div><i>✓</i><p><strong>{INTRO_STEPS[introStep].accent}</strong><small>{INTRO_STEPS[introStep].detail}</small></p></div></div>
        </div>
        <footer className="guide-intro-footer">
          <button className="guide-intro-arrow" type="button" disabled={introStep === 0} onClick={() => setIntroStep(current => Math.max(0, current - 1))} aria-label="Previous introduction step">←</button>
          <div className="guide-intro-dots" aria-label="Introduction progress">{INTRO_STEPS.map((step, index) => <button key={step.number} type="button" className={index === introStep ? 'active' : ''} onClick={() => setIntroStep(index)} aria-label={`Go to introduction step ${index + 1}`} aria-current={index === introStep ? 'step' : undefined} />)}</div>
          <button className={introStep === INTRO_STEPS.length - 1 ? 'btn btn-primary' : 'guide-intro-arrow'} type="button" onClick={() => introStep === INTRO_STEPS.length - 1 ? finishIntro() : setIntroStep(current => Math.min(INTRO_STEPS.length - 1, current + 1))} aria-label={introStep === INTRO_STEPS.length - 1 ? undefined : 'Next introduction step'}>{introStep === INTRO_STEPS.length - 1 ? 'Start lesson 1 →' : '→'}</button>
        </footer>
        <span className="guide-intro-keyhint">Tip: use ← → arrow keys</span>
      </section>
    </div>}
  </div>;
}
