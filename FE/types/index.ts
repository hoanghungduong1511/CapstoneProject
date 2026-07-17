// View states for navigation
export type ViewState = 'landing' | 'login' | 'register' | 'upload' | 'validating' | 'analyzing' | 'result' | 'chat' | 'profile' | 'admin-users';

// Chat message type
export interface Message {
  id: string;
  role: 'user' | 'ai';
  content: string;
  timestamp: Date;
}

// Skin Analysis response
export interface ValidationResult {
  is_skin: boolean;
  confidence: number;
  class_name: string;
  probability: number;
  threshold: number;
  processing_time_ms?: number;
}

export interface SegmentationDetail {
  mask_url: string;
  roi_url: string;
  lesion_ratio: number;
  bbox: number[];
  fallback: boolean;
}

export interface ClassificationCandidate {
  id: string;
  name: string;
  latinName: string;
  icd: string;
  description: string;
  urgency: string;
  recommendation: string;
  confidence: number;
}

export interface ClassificationResult {
  top_id: string;
  top_label: string;
  top_confidence: number;
  candidates: ClassificationCandidate[];
}

export interface SkinAnalysisResponse {
  accepted: boolean;
  message: string;
  original_image_url: string;
  validation: ValidationResult;
  segmentation?: SegmentationDetail;
  classification?: ClassificationResult;
  processing_time_ms: number;
  image_id?: string;
  ai_result_id?: string;
}

// Structured Medical Context for LLM (pipeline chuẩn)
export interface MedicalContext {
  disease: string;
  confidence: number;
  severity: 'low' | 'medium' | 'high';
  lesionAreaPercent: number;
  symptoms: string[];
  characteristics: string[];
  patient?: PatientInfo;
}

// Patient metadata (optional)
export interface PatientInfo {
  age?: number;
  gender?: 'male' | 'female' | 'other';
  skinType?: string;
  medicalHistory?: string[];
}

// User type (matches API response)
export interface User {
  id: string;
  email: string;
  name: string | null;
  avatar_url: string | null;
  provider: string;
  role: string;
  status: string;
  date_of_birth: string | null;
  gender: string | null;
  created_at: string;
}

// Auth tokens from API
export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

// Toast notification type
export interface Toast {
  message: string;
  type: 'error' | 'success';
}

// Severity configuration for UI
export interface SeverityConfig {
  color: string;
  text: string;
  border: string;
  bgSoft: string;
  textCol: string;
}

// Step indicator step type
export interface Step {
  id: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}

// Diagnosis history types
export interface DiagnosisHistoryItem {
  id: string;
  image_url: string | null;
  top1_label: string | null;
  top1_confidence: number | null;
  status: string;
  created_at: string;
}

export interface DiagnosisHistory {
  items: DiagnosisHistoryItem[];
  total: number;
}

export interface ChatMessageRecord {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  metadata: Record<string, unknown> | null;
  safety_level?: 'low' | 'medium' | 'high' | 'urgent' | null;
  model_name?: string | null;
  created_at: string;
}

export interface ChatTurnResponse {
  message_id: string;
  answer: string;
  safety_level: 'low' | 'medium' | 'high' | 'urgent';
  sources: string[];
  missing_questions: string[];
  medical_context_id: string;
  rag_query_id: string;
  rag_result_id: string;
  model_name: string;
  token_usage: Record<string, number> | null;
}

export interface ChatSessionSummary {
  id: string;
  ai_result_id: string | null;
  title: string;
  message_count: number;
  last_message: string | null;
  created_at: string;
  last_message_at: string;
}

export interface ChatSessionListResponse {
  items: ChatSessionSummary[];
  total: number;
}

export interface ChatSessionDetail {
  id: string;
  ai_result_id: string | null;
  created_at: string;
  messages: ChatMessageRecord[];
}

export interface AdminUserListItem {
  id: string;
  email: string;
  name: string | null;
  avatar_url: string | null;
  provider: string;
  status: string;
  date_of_birth: string | null;
  gender: string | null;
  analysis_count: number;
  last_analysis_at: string | null;
  created_at: string;
}

export interface AdminUserListResponse {
  items: AdminUserListItem[];
  total: number;
  active: number;
  inactive: number;
  total_analyses: number;
}

export interface AdminAnalysisHistoryItem {
  id: string;
  image_url: string | null;
  status: string;
  top1_label: string | null;
  top1_confidence: number | null;
  lesion_area_percent: number | null;
  processing_time_ms: number | null;
  created_at: string;
}

export interface AdminUserDetail {
  id: string;
  email: string;
  name: string | null;
  avatar_url: string | null;
  provider: string;
  role: string;
  status: string;
  date_of_birth: string | null;
  gender: string | null;
  created_at: string;
  updated_at: string;
  analysis_count: number;
  history: AdminAnalysisHistoryItem[];
}
