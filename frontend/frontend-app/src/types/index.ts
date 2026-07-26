export interface AnalysisRequest {
  file_base64: string;
  file_type: string;
  job_description?: string;
}

export interface AnalysisResponse {
  content_review: ContentReview;
  visual_review: VisualReview;
  layout_analysis: LayoutAnalysis;
  metadata: {
    file_type: string;
    file_size_bytes: number;
    page_count: number | null;
    processing_time_ms: number;
  };
}

export type ReviewStatus = 'available' | 'unavailable';

export interface ContentReview {
  status: ReviewStatus;
  response: string | null;
  error_code: string | null;
  error_message: string | null;
}

export interface VisualIssue {
  code: string;
  description: string;
  severity: 'critical' | 'major' | 'minor';
  affected_area: string | null;
  recommendation: string;
}

export interface VisualReviewResult {
  visual_score: number;
  pass_status: boolean;
  strengths: string[];
  issues: VisualIssue[];
}

export interface VisualReview {
  status: ReviewStatus;
  result: VisualReviewResult | null;
  error_code: string | null;
  error_message: string | null;
  page_count: number | null;
}

export interface LayoutPageMetrics {
  page_number: number;
  width_points: number;
  height_points: number;
  text_density: number;
  font_sizes: number[];
  min_font_size: number | null;
  max_font_size: number | null;
  median_font_size: number | null;
  dominant_font_size: number | null;
}

export interface LayoutAnalysis {
  status: ReviewStatus;
  page_count: number | null;
  pages: LayoutPageMetrics[];
  error_code: string | null;
  error_message: string | null;
}

export interface ApiError {
  detail: string;
}
