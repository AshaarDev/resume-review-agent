import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { FileUpload } from './components/FileUpload';
import { analyzeResume } from './services/api';
import type { AnalysisResponse } from './types';
import './App.css';

function App() {
  const [file, setFile] = useState<File | null>(null);
  const [jobDescription, setJobDescription] = useState('');
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleFileSelect = (selectedFile: File | null) => {
    setFile(selectedFile);
    setError('');
  };

  const handleAnalyze = async () => {
    if (!file) {
      setError('Please upload a resume first');
      return;
    }

    setLoading(true);
    setError('');
    setAnalysis(null);

    try {
      const result = await analyzeResume(file, jobDescription);
      setAnalysis(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to analyze resume');
    } finally {
      setLoading(false);
    }
  };

  const handleMockTest = () => {
    setError('');
    setAnalysis({
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
        error_message: null,
      },
      visual_review: {
        status: 'available',
        result: {
          visual_score: 85,
          pass_status: true,
          strengths: [
            'Consistent font hierarchy throughout',
            'Good use of whitespace for readability',
            'Professional color scheme',
          ],
          issues: [
            {
              code: 'INCONSISTENT_ALIGNMENT',
              description: 'Date alignment varies between sections',
              severity: 'minor',
              affected_area: 'Work Experience section',
              recommendation: 'Align all dates to the right margin',
            },
            {
              code: 'INCONSISTENT_SPACING',
              description: 'Spacing between sections is not uniform',
              severity: 'minor',
              affected_area: 'Multiple sections',
              recommendation: 'Use consistent 12pt spacing between sections',
            },
          ],
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
            width_points: 612.0,
            height_points: 792.0,
            text_density: 0.45,
            font_sizes: [10.0, 11.0, 12.0, 14.0, 16.0],
            min_font_size: 10.0,
            max_font_size: 16.0,
            median_font_size: 11.0,
            dominant_font_size: 11.0,
          },
        ],
        error_code: null,
        error_message: null,
      },
      metadata: {
        file_type: 'pdf',
        file_size_bytes: 45678,
        page_count: 1,
        processing_time_ms: 1234.56,
      },
    });
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>📄 Resume Review Agent</h1>
        <p>Upload your resume and get AI-powered feedback</p>
      </header>

      <main className="app-main">
        <div className="upload-section">
          <h2>Upload Resume</h2>
          <FileUpload onFileSelect={handleFileSelect} disabled={loading} />
        </div>

        <div className="job-description-section">
          <h2>Job Description (Optional)</h2>
          <textarea
            className="job-description-input"
            placeholder="Paste the job description here to get tailored feedback..."
            value={jobDescription}
            onChange={(e) => setJobDescription(e.target.value)}
            disabled={loading}
            rows={6}
          />
        </div>

        <button
          className="analyze-btn"
          onClick={handleAnalyze}
          disabled={!file || loading}
        >
          {loading ? '🔄 Analyzing...' : '✨ Analyze Resume'}
        </button>

        <button
          className="mock-test-btn"
          onClick={handleMockTest}
          disabled={loading}
        >
          🧪 Test with Mock Response
        </button>

        {error && (
          <div className="error-message">
            <span>⚠️</span>
            <p>{error}</p>
          </div>
        )}

        {analysis && (
          <div className="analysis-results">
            <h2>Analysis Results</h2>
            <div className="analysis-content">
              <h3>Content review</h3>
              {analysis.content_review.status === 'available' ? (
                <div className="markdown-content">
                  <ReactMarkdown>{analysis.content_review.response || ''}</ReactMarkdown>
                </div>
              ) : (
                <p>{analysis.content_review.error_message}</p>
              )}

              <h3>Visual review</h3>
              {analysis.visual_review.status === 'available' &&
              analysis.visual_review.result ? (
                <>
                  <p>
                    Score: {analysis.visual_review.result.visual_score}/100
                  </p>
                  {analysis.visual_review.result.strengths.length > 0 && (
                    <>
                      <h4>Strengths</h4>
                      <ul>
                        {analysis.visual_review.result.strengths.map((strength) => (
                          <li key={strength}>{strength}</li>
                        ))}
                      </ul>
                    </>
                  )}
                  {analysis.visual_review.result.issues.length > 0 && (
                    <>
                      <h4>Issues</h4>
                      <ul>
                        {analysis.visual_review.result.issues.map((issue, index) => (
                          <li key={`${issue.code}-${index}`}>
                            <strong>{issue.code}</strong> ({issue.severity}):{' '}
                            {issue.description} Recommendation: {issue.recommendation}
                          </li>
                        ))}
                      </ul>
                    </>
                  )}
                </>
              ) : (
                <p>{analysis.visual_review.error_message}</p>
              )}

              <h3>Layout analysis</h3>
              {analysis.layout_analysis.status === 'available' ? (
                <>
                  <p>{analysis.layout_analysis.page_count} page(s)</p>
                  <ul>
                    {analysis.layout_analysis.pages.map((page) => (
                      <li key={page.page_number}>
                        Page {page.page_number}: {page.width_points.toFixed(1)} ×{' '}
                        {page.height_points.toFixed(1)} pt, text density{' '}
                        {(page.text_density * 100).toFixed(1)}%, median font{' '}
                        {page.median_font_size ?? 'not detected'} pt
                      </li>
                    ))}
                  </ul>
                </>
              ) : (
                <p>{analysis.layout_analysis.error_message}</p>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
