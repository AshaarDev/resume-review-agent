import { useState } from 'react';
import { FileUpload } from './components/FileUpload';
import { analyzeResume } from './services/api';
import './App.css';

function App() {
  const [file, setFile] = useState<File | null>(null);
  const [jobDescription, setJobDescription] = useState('');
  const [analysis, setAnalysis] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleFileSelect = (selectedFile: File) => {
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
    setAnalysis('');

    try {
      const result = await analyzeResume(file, jobDescription);
      setAnalysis(result.response);
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
              {analysis.split('\n').map((line, index) => (
                <p key={index}>{line}</p>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
