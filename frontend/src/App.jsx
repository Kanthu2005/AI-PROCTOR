import React, { useState, useEffect, useCallback } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import Navbar from './components/Navbar';
import Sidebar from './components/Sidebar';
import LoginPortal from './components/LoginPortal';
import RecruiterDashboard from './components/RecruiterDashboard';
import AssessmentBuilder from './components/AssessmentBuilder';
import QuestionBankManager from './components/QuestionBankManager';
import CandidateManagement from './components/CandidateManagement';
import CandidateInviteModal from './components/CandidateInviteModal';
import CandidateExamEngine from './components/CandidateExamEngine';
import CandidatePortal from './components/CandidatePortal';
import LiveProctorDashboard from './components/LiveProctorDashboard';
import ResultsAnalyticsView from './components/ResultsAnalyticsView';
import { ShieldCheck } from 'lucide-react';

function parseHashRoute() {
  const hash = window.location.hash.replace(/^#\/?/, '');
  if (!hash) return { tab: 'dashboard', params: {} };
  const [routePart, queryPart] = hash.split('?');
  const params = {};
  if (queryPart) {
    const searchParams = new URLSearchParams(queryPart);
    for (const [key, val] of searchParams.entries()) {
      params[key] = val;
    }
  }
  return { tab: routePart || 'dashboard', params };
}

function MainApp() {
  const { user, loading } = useAuth();
  
  // Default candidate exam token
  const initialRoute = parseHashRoute();
  const [candidateExamToken, setCandidateExamToken] = useState(initialRoute.params.token || '');
  const [activeTab, setActiveTabState] = useState(initialRoute.tab || 'dashboard');
  const [invitingAssessment, setInvitingAssessment] = useState(null);
  const [openWizardDirectly, setOpenWizardDirectly] = useState(false);
  const [isCandidateExamMode, setIsCandidateExamMode] = useState(initialRoute.tab === 'candidate_exam');
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  // Tab change with browser URL routing sync
  const setActiveTab = useCallback((tab, extraParams = {}) => {
    setActiveTabState(tab);
    let hash = `#/${tab}`;
    if (Object.keys(extraParams).length > 0) {
      const q = new URLSearchParams(extraParams).toString();
      hash += `?${q}`;
    }
    if (window.location.hash !== hash) {
      window.history.pushState(null, '', hash);
    }
  }, []);

  // Listen to browser Back/Forward buttons
  useEffect(() => {
    const handleHashChange = () => {
      const { tab, params } = parseHashRoute();
      if (tab === 'candidate_exam') {
        setIsCandidateExamMode(true);
        if (params.token) setCandidateExamToken(params.token);
      } else {
        setIsCandidateExamMode(false);
      }
      setActiveTabState(tab);
    };

    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  // Set appropriate starting tab based on role
  useEffect(() => {
    if (user) {
      const { tab } = parseHashRoute();
      if (!window.location.hash || tab === 'login') {
        if (user.role === 'CANDIDATE') {
          setActiveTab('candidate_portal');
        } else if (user.role === 'PROCTOR') {
          setActiveTab('proctor');
        } else if (user.role === 'QUESTION_AUTHOR') {
          setActiveTab('questions');
        } else {
          setActiveTab('dashboard');
        }
      }
    }
  }, [user?.role, setActiveTab]);

  // Launch Candidate Exam directly via token
  const handleLaunchCandidateWithToken = (token) => {
    const resolvedToken = token || '';
    setCandidateExamToken(resolvedToken);
    setIsCandidateExamMode(true);
    setActiveTab('candidate_exam', resolvedToken ? { token: resolvedToken } : {});
  };

  // Loading Screen
  if (loading) {
    return (
      <div className="min-h-screen bg-[#0b1329] flex flex-col items-center justify-center space-y-4 font-['Plus_Jakarta_Sans',sans-serif]">
        <div className="relative">
          <div className="w-14 h-14 rounded-2xl bg-blue-600 animate-spin blur-md opacity-50" />
          <div className="w-14 h-14 rounded-2xl bg-[#0b1329] border border-blue-500/40 flex items-center justify-center absolute inset-0 shadow-2xl">
            <ShieldCheck className="w-7 h-7 text-blue-400 animate-pulse" />
          </div>
        </div>
        <div className="text-xs font-mono font-bold text-slate-400 uppercase tracking-widest animate-pulse">
          Initializing ProctorAI Security System...
        </div>
      </div>
    );
  }

  // 1. If Candidate Mode is active (taking an active exam), show strictly the Exam Engine
  if (isCandidateExamMode || activeTab === 'candidate_exam') {
    return (
      <CandidateExamEngine 
        defaultToken={candidateExamToken}
        onBackToHome={() => {
          setIsCandidateExamMode(false);
          setActiveTab(user?.role === 'CANDIDATE' ? 'candidate_portal' : (user ? (user.role === 'PROCTOR' ? 'proctor' : 'dashboard') : 'login'));
        }}
      />
    );
  }

  // 2. If user is NOT logged in, show the Universal Login Page
  if (!user || activeTab === 'login') {
    return (
      <LoginPortal
        onLoginSuccess={(role) => {
          setIsCandidateExamMode(false);
          if (role === 'CANDIDATE') {
            setActiveTab('candidate_portal');
          } else if (role === 'PROCTOR') {
            setActiveTab('proctor');
          } else if (role === 'QUESTION_AUTHOR') {
            setActiveTab('questions');
          } else {
            setActiveTab('dashboard');
          }
        }}
        onLaunchCandidateWithToken={(token) => {
          handleLaunchCandidateWithToken(token);
        }}
      />
    );
  }

  // 3. CANDIDATE ACCESS ONLY: Strictly Candidate Workspace & Portal
  // NEVER show recruiter dashboard, question bank, or proctor console to candidates
  if (user.role === 'CANDIDATE' || activeTab === 'candidate_portal') {
    return (
      <CandidatePortal
        onLaunchCandidateExam={(token) => handleLaunchCandidateWithToken(token)}
      />
    );
  }

  // 4. Authenticated Staff Workspace (Recruiter / Proctor / Author / Admin)
  // Responsive Application Shell: Left Sidebar (Desktop + Mobile Drawer) + Header + Content
  return (
    <div className="min-h-screen bg-[#f8fafc] flex font-['Plus_Jakarta_Sans',sans-serif] overflow-x-hidden">
      
      {/* Responsive Sidebar (Desktop docked + Mobile drawer) */}
      <Sidebar 
        activeTab={activeTab} 
        setActiveTab={setActiveTab} 
        mobileOpen={mobileSidebarOpen}
        onCloseMobile={() => setMobileSidebarOpen(false)}
      />

      {/* Right Content Area: Header Bar + Workspace Body */}
      <div className="flex-1 flex flex-col min-w-0">
        
        {/* Top Header Bar with Mobile Drawer Button and System Health Pill */}
        <Navbar 
          activeTab={activeTab} 
          setActiveTab={setActiveTab} 
          onToggleMobileSidebar={() => setMobileSidebarOpen(!mobileSidebarOpen)}
          mobileSidebarOpen={mobileSidebarOpen}
        />

        {/* Scrollable Main Viewport */}
        <main className="flex-1 p-4 sm:p-6 lg:p-8 overflow-y-auto">
          
          {/* Recruiter Dashboard */}
          {activeTab === 'dashboard' && (
            <RecruiterDashboard
              onNavigateTab={(tab) => setActiveTab(tab)}
              onOpenCreateWizard={() => {
                setOpenWizardDirectly(true);
                setActiveTab('assessments');
              }}
              onOpenCandidateInvite={(assessment) => setInvitingAssessment(assessment)}
              onLaunchCandidateExam={(token) => handleLaunchCandidateWithToken(token)}
            />
          )}

          {/* Assessment Management & Wizard */}
          {activeTab === 'assessments' && (
            <AssessmentBuilder
              initialCreate={openWizardDirectly}
              onOpenCandidateInvite={(assessment) => setInvitingAssessment(assessment)}
              onLaunchCandidateExam={(token) => handleLaunchCandidateWithToken(token)}
            />
          )}

          {/* Question Bank Manager */}
          {activeTab === 'questions' && <QuestionBankManager />}

          {/* Candidate Management */}
          {activeTab === 'candidates' && (
            <CandidateManagement 
              onOpenCandidateInvite={(assessment) => setInvitingAssessment(assessment)}
              onLaunchCandidateExam={(token) => handleLaunchCandidateWithToken(token)} 
            />
          )}

          {/* Live Proctor Surveillance Console */}
          {activeTab === 'proctor' && <LiveProctorDashboard />}

          {/* Results & Analytics View */}
          {activeTab === 'analytics' && <ResultsAnalyticsView />}

        </main>
      </div>

      {/* Candidate Bulk Invite Modal */}
      {invitingAssessment && (
        <CandidateInviteModal
          assessment={invitingAssessment}
          onClose={() => setInvitingAssessment(null)}
          onLaunchCandidateExam={(token) => handleLaunchCandidateWithToken(token)}
        />
      )}

    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <MainApp />
    </AuthProvider>
  );
}
