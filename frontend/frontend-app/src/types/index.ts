export interface AnalysisRequest {
  file_base64: string;
  file_type: string;
  job_description?: string;
}

export interface AnalysisResponse {
  response: string;
}

export interface ApiError {
  detail: string;
}
