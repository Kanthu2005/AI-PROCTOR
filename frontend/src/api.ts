import { HealthResponse, ReadyHealthResponse } from './types';

const ENV_API_BASE = (import.meta as any).env?.VITE_API_BASE_URL;
const API_BASE = ENV_API_BASE ? ENV_API_BASE.replace(/\/$/, '') : '/api/v1';

export interface RequestOptions extends RequestInit {
  headers?: Record<string, string>;
}

export async function apiRequest<T = any>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const token = localStorage.getItem('intellitest_token');
  const csrfToken = localStorage.getItem('proctorai_csrf_token') || 
    document.cookie.split('; ').find(row => row.startsWith('proctorai_csrf_token='))?.split('=')[1];

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    ...(csrfToken ? { 'X-CSRF-Token': csrfToken } : {}),
    ...(options.headers || {})
  };

  // Support absolute root endpoints like /health as well as /api/v1 paths
  const backendOrigin = ENV_API_BASE ? ENV_API_BASE.replace(/\/api\/v1\/?$/, '') : '';
  const url = endpoint.startsWith('/health') 
    ? (backendOrigin ? `${backendOrigin}${endpoint}` : endpoint) 
    : `${API_BASE}${endpoint}`;

  const response = await fetch(url, {
    credentials: 'include',
    ...options,
    headers
  });

  if (!response.ok) {
    let errorDetail = 'API request failed';
    let statusCode = response.status;
    try {
      const err = await response.json();
      errorDetail = err.detail || JSON.stringify(err);
    } catch {
      errorDetail = response.statusText || `HTTP Error ${response.status}`;
    }
    const error: Error & { statusCode?: number } = new Error(
      typeof errorDetail === 'string' ? errorDetail : JSON.stringify(errorDetail)
    );
    error.statusCode = statusCode;
    throw error;
  }

  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('text/csv') || contentType.includes('text/plain')) {
    return response.text();
  }
  if (contentType.includes('application/pdf') || contentType.includes('application/octet-stream')) {
    return response.blob();
  }

  return response.json();
}

export const api = {
  // System Health & Diagnostics (Phase 1)
  getHealth: (): Promise<HealthResponse> => apiRequest('/health'),
  getReadyHealth: (): Promise<ReadyHealthResponse> => apiRequest('/health/ready'),
  getLiveness: (): Promise<HealthResponse> => apiRequest('/health/live'),

  // Auth & RBAC
  login: (email: string, password: string) => apiRequest('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password })
  }),
  register: (data: Record<string, any>) => apiRequest('/auth/register', {
    method: 'POST',
    body: JSON.stringify(data)
  }),
  logout: () => apiRequest('/auth/logout', {
    method: 'POST'
  }),
  refreshToken: (refreshToken?: string) => apiRequest('/auth/refresh', {
    method: 'POST',
    body: JSON.stringify({ refresh_token: refreshToken })
  }),
  requestPasswordReset: (email: string) => apiRequest('/auth/password-reset/request', {
    method: 'POST',
    body: JSON.stringify({ email })
  }),
  confirmPasswordReset: (resetToken: string, newPassword: string) => apiRequest('/auth/password-reset/confirm', {
    method: 'POST',
    body: JSON.stringify({ reset_token: resetToken, new_password: newPassword })
  }),
  getMe: () => apiRequest('/auth/me'),
  getAuditLogs: (limit = 50) => apiRequest(`/auth/audit-logs?limit=${limit}`),

  // Organizations
  listOrgs: () => apiRequest('/organizations'),
  createOrg: (data: Record<string, any>) => apiRequest('/organizations', {
    method: 'POST',
    body: JSON.stringify(data)
  }),

  // Questions
  listQuestions: (orgId: string, params: Record<string, any> = {}) => {
    let url = `/questions?org_id=${encodeURIComponent(orgId)}`;
    if (params.search) url += `&search=${encodeURIComponent(params.search)}`;
    if (params.type && params.type !== 'ALL') url += `&question_type=${encodeURIComponent(params.type)}`;
    if (params.question_type && params.question_type !== 'ALL') url += `&question_type=${encodeURIComponent(params.question_type)}`;
    if (params.difficulty && params.difficulty !== 'ALL') url += `&difficulty=${encodeURIComponent(params.difficulty)}`;
    if (params.tag) url += `&tag=${encodeURIComponent(params.tag)}`;
    if (params.topic && params.topic !== 'ALL') url += `&topic=${encodeURIComponent(params.topic)}`;
    if (params.review_status && params.review_status !== 'ALL') url += `&review_status=${encodeURIComponent(params.review_status)}`;
    if (params.page) url += `&page=${params.page}`;
    if (params.page_size) url += `&page_size=${params.page_size}`;
    if (params.paginated) url += `&paginated=true`;
    return apiRequest(url);
  },
  createQuestion: (data: Record<string, any>) => apiRequest('/questions', {
    method: 'POST',
    body: JSON.stringify(data)
  }),
  updateQuestion: (id: string, data: Record<string, any>) => apiRequest(`/questions/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data)
  }),
  getQuestion: (id: string) => apiRequest(`/questions/${id}`),
  reviewQuestion: (id: string, reviewStatus: string) => apiRequest(`/questions/${id}/review`, {
    method: 'POST',
    body: JSON.stringify({ review_status: reviewStatus })
  }),
  duplicateQuestion: (id: string) => apiRequest(`/questions/${id}/duplicate`, {
    method: 'POST'
  }),
  deleteQuestion: (id: string) => apiRequest(`/questions/${id}`, {
    method: 'DELETE'
  }),

  // Assessments
  listAssessments: (orgId: string, status?: string) => {
    let url = `/assessments?org_id=${encodeURIComponent(orgId)}`;
    if (status && status !== 'ALL') url += `&status=${encodeURIComponent(status)}`;
    return apiRequest(url);
  },
  createAssessment: (data: Record<string, any>) => apiRequest('/assessments', {
    method: 'POST',
    body: JSON.stringify(data)
  }),
  getAssessment: (id: string) => apiRequest(`/assessments/${id}`),
  updateAssessment: (id: string, data: Record<string, any>) => apiRequest(`/assessments/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data)
  }),
  publishAssessment: (id: string) => apiRequest(`/assessments/${id}/publish`, {
    method: 'POST'
  }),
  scheduleAssessment: (id: string, startTime: string, endTime: string) => apiRequest(`/assessments/${id}/schedule`, {
    method: 'POST',
    body: JSON.stringify({ start_time: startTime, end_time: endTime })
  }),
  goLiveAssessment: (id: string) => apiRequest(`/assessments/${id}/live`, {
    method: 'POST'
  }),
  closeAssessment: (id: string) => apiRequest(`/assessments/${id}/close`, {
    method: 'POST'
  }),
  duplicateAssessment: (id: string) => apiRequest(`/assessments/${id}/duplicate`, {
    method: 'POST'
  }),
  previewAssessment: (id: string) => apiRequest(`/assessments/${id}/preview`),

  // Candidates & Invitations
  bulkInvite: (assessmentId: string, candidates: any[], expiresInHours = 72) => apiRequest('/candidates/bulk-invite', {
    method: 'POST',
    body: JSON.stringify({ assessment_id: assessmentId, candidates, expires_in_hours: expiresInHours })
  }),
  inviteSingleCandidate: (data: Record<string, any>) => apiRequest('/candidates/invite', {
    method: 'POST',
    body: JSON.stringify(data)
  }),
  // Real Exam Invitation Email System
  sendExamInvitations: (assessmentId: string, candidates: Array<{ email: string; full_name: string }>, expiresInHours = 72) => apiRequest(`/assessments/${assessmentId}/invitations`, {
    method: 'POST',
    body: JSON.stringify({ candidates, expires_in_hours: expiresInHours })
  }),
  previewExamInvitation: (assessmentId: string, sampleName?: string, sampleEmail?: string) => apiRequest(`/assessments/${assessmentId}/invitations/preview`, {
    method: 'POST',
    body: JSON.stringify({ sample_name: sampleName, sample_email: sampleEmail })
  }),
  listExamInvitations: (assessmentId: string, status?: string) => {
    let url = `/assessments/${assessmentId}/invitations`;
    if (status && status !== 'ALL') url += `?status=${encodeURIComponent(status)}`;
    return apiRequest(url);
  },
  resendExamInvitation: (invitationId: string, expiresInHours = 72) => apiRequest(`/invitations/${invitationId}/resend?expires_in_hours=${expiresInHours}`, {
    method: 'POST'
  }),
  remindExamInvitation: (invitationId: string) => apiRequest(`/invitations/${invitationId}/remind`, {
    method: 'POST'
  }),
  validateExamInvitation: (token: string) => apiRequest(`/invitations/validate/${encodeURIComponent(token)}`),
  getCandidateExamInvitations: () => apiRequest('/candidate/invitations'),

  revokeInvitation: (id: string) => apiRequest(`/candidates/invitations/${id}`, {
    method: 'DELETE'
  }),
  resendInvitation: (id: string) => apiRequest(`/candidates/invitations/${id}/resend`, {
    method: 'POST'
  }),
  listAllCandidates: (orgId?: string, assessmentId?: string) => {
    let url = '/candidates?';
    if (orgId) url += `org_id=${orgId}&`;
    if (assessmentId) url += `assessment_id=${assessmentId}`;
    return apiRequest(url);
  },
  listInvitations: (assessmentId: string) => apiRequest(`/candidates/assessments/${assessmentId}/invitations`),
  getMyInvitations: () => apiRequest('/candidates/me/invitations'),
  verifyToken: (token: string) => apiRequest(`/candidates/invitations/${token}/verify`),
  getInstructions: (token: string) => apiRequest(`/candidates/invitations/${token}/instructions`),
  systemCheck: (token: string, data: Record<string, any>) => apiRequest(`/candidates/invitations/${token}/system-check`, {
    method: 'POST',
    body: JSON.stringify(data)
  }),

  // Attempt & Test Engine
  startAttempt: (token: string) => apiRequest(`/attempts/start?invitation_token=${token}`, {
    method: 'POST'
  }),
  getAttemptState: (attemptId: string) => apiRequest(`/attempts/${attemptId}/state`),
  autosaveAnswers: (attemptId: string, answers: any, currentQuestionId?: string) => apiRequest(`/attempts/${attemptId}/answers/autosave`, {
    method: 'POST',
    body: JSON.stringify({ answers, current_question_id: currentQuestionId })
  }),
  submitAttempt: (attemptId: string, finalAnswers?: any) => apiRequest(`/attempts/${attemptId}/submit`, {
    method: 'POST',
    body: JSON.stringify({ final_answers: finalAnswers || [] })
  }),
  getAttemptResult: (attemptId: string) => apiRequest(`/attempts/${attemptId}/result`),
  sendCandidateResult: (attemptId: string, decision: string, recruiterFeedback?: string) => apiRequest(`/attempts/${attemptId}/send-result`, {
    method: 'POST',
    body: JSON.stringify({ decision, recruiter_feedback: recruiterFeedback })
  }),

  // AI Proctoring
  sendProctorEvent: (attemptId: string, eventData: Record<string, any>) => apiRequest(`/proctoring/attempts/${attemptId}/events`, {
    method: 'POST',
    body: JSON.stringify(eventData)
  }),
  getLiveProctorFeed: (assessmentId: string) => apiRequest(`/proctoring/assessments/${assessmentId}/live-feed`),
  getAttemptIncidents: (attemptId: string) => apiRequest(`/proctoring/attempts/${attemptId}/incidents`),
  reviewIncident: (attemptId: string, status: string, notes?: string) => apiRequest(`/proctoring/attempts/${attemptId}/review`, {
    method: 'POST',
    body: JSON.stringify({ status, proctor_notes: notes })
  }),

  // Coding Sandbox Runner
  runSandboxCode: (code: string, testCases: any[], language = 'python') => apiRequest('/sandbox/run', {
    method: 'POST',
    body: JSON.stringify({ code, test_cases: testCases, language })
  }),


  // Evaluation & Descriptive Grading
  evaluateAttempt: (attemptId: string, recomputeAll = false) => apiRequest(`/attempts/${attemptId}/evaluate?recompute_all=${recomputeAll}`, {
    method: 'POST'
  }),
  manualEvaluateAnswer: (attemptId: string, questionId: string, marksAwarded: number, comments?: string) => apiRequest(`/attempts/${attemptId}/answers/${questionId}/evaluate`, {
    method: 'POST',
    body: JSON.stringify({ marks_awarded: marksAwarded, reviewer_comments: comments })
  }),
  suggestScore: (attemptId: string, questionId: string) => apiRequest(`/attempts/${attemptId}/answers/${questionId}/suggest-score`, {
    method: 'POST'
  }),

  // Analytics & Exports
  getAssessmentAnalytics: (assessmentId: string) => apiRequest(`/analytics/assessments/${assessmentId}`),
  exportAssessmentReport: (assessmentId: string, format = 'csv') => apiRequest(`/analytics/assessments/${assessmentId}/export?format=${format}`),
  getCodeSimilarity: (assessmentId: string, questionId?: string, threshold = 0.70) => {
    let url = `/analytics/assessments/${assessmentId}/code-similarity?threshold=${threshold}`;
    if (questionId) url += `&question_id=${encodeURIComponent(questionId)}`;
    return apiRequest(url);
  },
  getRecruiterDashboard: (orgId?: string) => {
    let url = '/analytics/recruiter/dashboard';
    if (orgId) url += `?org_id=${encodeURIComponent(orgId)}`;
    return apiRequest(url);
  }
};


export default api;
