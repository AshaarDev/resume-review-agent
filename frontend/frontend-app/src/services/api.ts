import type { WorkflowRequest, WorkflowResponse } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001';

export const analyzeResume = async (
  file: File,
  jobDescription = '',
  userInstructions = '',
): Promise<WorkflowResponse> => {
  const request: WorkflowRequest = {
    intent: 'review',
    file_base64: await fileToBase64(file),
    file_type: file.name.split('.').pop() || 'pdf',
    job_description: jobDescription,
    user_instructions: userInstructions,
  };

  const response = await fetch(`${API_BASE_URL}/api/resume-workflows`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    const detail = payload?.detail;
    const message =
      typeof detail === 'string'
        ? detail
        : detail?.message || 'Failed to run the resume review workflow';
    throw new Error(message);
  }
  return response.json();
};

const fileToBase64 = (file: File): Promise<string> =>
  new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = () => {
      const result = reader.result as string;
      resolve(result.split(',')[1]);
    };
    reader.onerror = reject;
  });
