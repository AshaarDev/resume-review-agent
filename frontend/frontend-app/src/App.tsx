import { useState } from 'react';
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
                analysis.content_review.response?.split('\n').map((line, index) => (
                  <p key={index}>{line}</p>
                ))
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
