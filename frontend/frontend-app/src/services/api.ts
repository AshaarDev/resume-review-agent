import type {
  ResumeCreationBrief,
  WorkflowProgressEvent,
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
  onProgress?: (event: WorkflowProgressEvent) => void,
): Promise<WorkflowResponse> => {
  const request: WorkflowRequest = {
    intent: 'review',
    file_base64: await fileToBase64(file),
    file_type: file.name.split('.').pop() || 'pdf',
    job_description: jobDescription,
    user_instructions: userInstructions,
  };

  return runWorkflowStream(request, onProgress);
};

export const createResume = async (
  creationBrief: ResumeCreationBrief,
  jobDescription = '',
  userInstructions = '',
  onProgress?: (event: WorkflowProgressEvent) => void,
): Promise<WorkflowResponse> => {
  const request: WorkflowRequest = {
    intent: 'create',
    creation_brief: creationBrief,
    job_description: jobDescription,
    user_instructions: userInstructions,
  };
  return runWorkflowStream(request, onProgress);
};

export const artifactUrl = (path: string): string =>
  path.startsWith('http') ? path : `${API_BASE_URL}${path}`;

const runWorkflowStream = async (
  request: WorkflowRequest,
  onProgress?: (event: WorkflowProgressEvent) => void,
): Promise<WorkflowResponse> => {
  const response = await fetch(`${API_BASE_URL}/api/resume-workflows/stream`, {
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
  if (!response.body) {
    throw new Error('This browser could not open the workflow event stream.');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let result: WorkflowResponse | null = null;

  const processBlock = (block: string) => {
    if (!block.trim() || block.trimStart().startsWith(':')) return;
    let eventName = 'message';
    const dataLines: string[] = [];
    for (const line of block.split(/\r?\n/)) {
      if (line.startsWith('event:')) eventName = line.slice(6).trim();
      if (line.startsWith('data:')) dataLines.push(line.slice(5).trimStart());
    }
    if (!dataLines.length) return;
    const payload = JSON.parse(dataLines.join('\n')) as unknown;
    if (eventName === 'progress') {
      onProgress?.(payload as WorkflowProgressEvent);
    } else if (eventName === 'result') {
      result = payload as WorkflowResponse;
    } else if (eventName === 'error') {
      const streamError = payload as { message?: string };
      throw new Error(streamError.message || 'The workflow stream failed.');
    }
  };

  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });
    const blocks = buffer.split(/\r?\n\r?\n/);
    buffer = blocks.pop() || '';
    blocks.forEach(processBlock);
    if (done) break;
  }
  if (buffer.trim()) processBlock(buffer);
  if (!result) throw new Error('The workflow ended without returning a result.');
  return result;
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
