export type UserRole =
  | 'PLATFORM_ADMIN'
  | 'ORG_ADMIN'
  | 'RECRUITER'
  | 'QUESTION_AUTHOR'
  | 'PROCTOR'
  | 'CANDIDATE';

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  org_id?: string | null;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  domain?: string | null;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface HealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  service: string;
  version: string;
  environment?: string;
  timestamp?: string;
}

export interface ReadyHealthResponse extends HealthResponse {
  database: 'connected' | 'disconnected' | 'error';
  database_type?: string;
  details?: Record<string, unknown>;
}

export interface ApiError {
  detail: string;
  status_code?: number;
  error_code?: string;
}

export type QuestionType =
  | 'MCQ_SINGLE'
  | 'MCQ_MULTIPLE'
  | 'CODING'
  | 'SQL'
  | 'DESCRIPTIVE';

export type DifficultyLevel = 'EASY' | 'MEDIUM' | 'HARD';

export interface QuestionVersion {
  id: string;
  version_number: number;
  title: string;
  description: string;
  question_type: QuestionType;
  difficulty: DifficultyLevel;
  max_score: number;
  content_payload: Record<string, any>;
  rubric_payload?: Record<string, any>;
  created_at?: string;
}

export interface Question {
  id: string;
  org_id: string;
  question_type: QuestionType;
  current_version_id?: string;
  active_version?: QuestionVersion;
  versions?: QuestionVersion[];
}

export interface Assessment {
  id: string;
  title: string;
  slug: string;
  description?: string;
  org_id: string;
  status: 'DRAFT' | 'PUBLISHED' | 'ARCHIVED';
  duration_minutes: number;
  rules_payload?: Record<string, any>;
  created_at?: string;
  updated_at?: string;
}

export interface Candidate {
  id: string;
  email: string;
  full_name: string;
  assessment_id: string;
  status: 'INVITED' | 'REGISTERED' | 'VERIFIED' | 'STARTED' | 'IN_PROGRESS' | 'SUBMITTED' | 'DISQUALIFIED';
  invitation_token?: string;
  invited_at?: string;
}
