import type { AnalysisRequest, AnalysisResponse } from '../types';

const API_BASE_URL = 'http://localhost:8001';

export const analyzeResume = async (
  file: File,
  jobDescription: string = ''
): Promise<AnalysisResponse> => {
  const base64 = await fileToBase64(file);
  const fileType = file.name.split('.').pop() || 'pdf';

  const request: AnalysisRequest = {
    file_base64: base64,
    file_type: fileType,
    job_description: jobDescription,
  };

  const response = await fetch(`${API_BASE_URL}/api/analyze-resume`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to analyze resume');
  }

  return response.json();
};

const fileToBase64 = (file: File): Promise<string> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = () => {
      const result = reader.result as string;
      const base64 = result.split(',')[1];
      resolve(base64);
    };
    reader.onerror = (error) => reject(error);
  });
};
