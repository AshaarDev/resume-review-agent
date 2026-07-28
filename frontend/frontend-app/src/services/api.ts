import type {
  ResumeCreationBrief,
  WorkflowRequest,
  WorkflowResponse,
} from '../types';

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  (import.meta.env.DEV ? 'http://127.0.0.1:8001' : '');

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
    throw new Error(
      responseErrorMessage(
        payload,
        'Failed to run the resume review workflow',
      ),
    );
  }
  return response.json();
};

export const createResume = async (
  creationBrief: ResumeCreationBrief,
  jobDescription = '',
  userInstructions = '',
): Promise<WorkflowResponse> => {
  const request: WorkflowRequest = {
    intent: 'create',
    creation_brief: creationBrief,
    job_description: jobDescription,
    user_instructions: userInstructions,
  };
  return runWorkflow(request);
};

export const artifactUrl = (path: string): string =>
  path.startsWith('http') ? path : `${API_BASE_URL}${path}`;

const runWorkflow = async (
  request: WorkflowRequest,
): Promise<WorkflowResponse> => {
  const response = await fetch(`${API_BASE_URL}/api/resume-workflows`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(
      responseErrorMessage(payload, 'Failed to run the resume workflow'),
    );
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

interface ValidationIssue {
  loc?: Array<string | number>;
  msg?: string;
}

const responseErrorMessage = (
  payload: unknown,
  fallback: string,
): string => {
  if (!payload || typeof payload !== 'object') return fallback;
  const detail = (payload as { detail?: unknown }).detail;
  if (typeof detail === 'string') return detail;
  if (
    detail &&
    typeof detail === 'object' &&
    'message' in detail &&
    typeof (detail as { message?: unknown }).message === 'string'
  ) {
    return (detail as { message: string }).message;
  }
  if (Array.isArray(detail)) {
    const messages = detail
      .slice(0, 3)
      .map((issue: ValidationIssue) => {
        const path = (issue.loc || [])
          .filter((part) => part !== 'body')
          .map((part) => String(part).replaceAll('_', ' '))
          .join(' → ');
        return `${path ? `${path}: ` : ''}${issue.msg || 'Invalid value'}`;
      });
    if (messages.length) return messages.join(' ');
  }
  return fallback;
};
