export type ReviewStatus = 'available' | 'unavailable';
export type WorkflowStatus =
  | 'pending'
  | 'running'
  | 'completed'
  | 'partial'
  | 'failed'
  | 'not_implemented';
export type AgentStatus =
  | 'pending'
  | 'running'
  | 'completed'
  | 'partial'
  | 'failed'
  | 'not_invoked';

export interface WorkflowRequest {
  intent: 'review';
  file_base64: string;
  file_type: string;
  job_description?: string;
  user_instructions?: string;
}

export interface WorkflowMessage {
  code: string;
  message: string;
  source: string | null;
}

export interface PriorityAction {
  priority: number;
  source: string;
  issue_code: string | null;
  title: string;
  recommendation: string;
}

export interface ContentReview {
  status: ReviewStatus;
  response: string | null;
  analysis: ContentPolicyAnalysis | null;
  error_code: string | null;
  error_message: string | null;
}

export interface BulletPolicyAnalysis {
  bullet_text: string;
  has_accomplishment: boolean;
  has_measurement: boolean;
  has_method: boolean;
  has_meaningful_metric: boolean;
  suggested_rewrite: string | null;
}

export interface ContentPolicyAnalysis {
  overall_feedback: string;
  strengths: string[];
  recommendations: string[];
  estimated_relevant_experience_years: number | null;
  experience_estimate_confidence: number;
  bullets: BulletPolicyAnalysis[];
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
  metric_emphasis: {
    eligible_metric_count: number;
    emphasized_metric_count: number;
    coverage: number | null;
    confidence: number;
    unbolded_metrics: string[];
  } | null;
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

export interface ReviewAgentResult {
  status: AgentStatus;
  content_review: ContentReview;
  visual_review: VisualReview;
  layout_analysis: LayoutAnalysis;
  policy_id: string;
  policy_version: string;
  policy_findings: PolicyFinding[];
  proposed_actions: PriorityAction[];
  warnings: WorkflowMessage[];
  errors: WorkflowMessage[];
}

export interface PolicyFinding {
  code: string;
  status: 'passed' | 'minor_issue' | 'major_issue' | 'unavailable';
  source: string;
  description: string;
  measured_value: number | null;
  target_value: number | null;
  evidence: string[];
  recommendation: string;
}

export interface OrchestratorSummary {
  overall_assessment: string;
  top_strengths: string[];
  priority_actions: PriorityAction[];
  next_step: string;
}

export interface WorkflowResponse {
  workflow_id: string;
  policy_id: string | null;
  policy_version: string | null;
  intent: 'review' | 'create' | 'revise';
  status: WorkflowStatus;
  final_message: string;
  summary: OrchestratorSummary | null;
  review: ReviewAgentResult | null;
  agent_statuses: Record<string, AgentStatus>;
  warnings: WorkflowMessage[];
  errors: WorkflowMessage[];
}
