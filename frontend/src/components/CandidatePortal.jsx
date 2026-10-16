import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { api } from '../api';
import { 
  ShieldCheck, 
  LogOut, 
  Play, 
  Clock, 
  Award, 
  CheckCircle2, 
  AlertCircle, 
  FileText, 
  Laptop, 
  KeyRound, 
  ArrowRight,
  User,
  Shield,
  Eye,
  Check,
  Calendar,
  Sparkles
} from 'lucide-react';

export default function CandidatePortal({ onLaunchCandidateExam }) {
  const { user, logout } = useAuth();
  const [tokenInput, setTokenInput] = useState('');
  const [invitations, setInvitations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadMyInvitations();
  }, [user]);

  const loadMyInvitations = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getMyInvitations();
      setInvitations(data || []);
    } catch (err) {
      console.warn('Failed to load candidate invitations:', err);
      setInvitations([]);
    } finally {
      setLoading(false);
    }
  };

  const handleLaunchWithCustomToken = (e) => {
    e.preventDefault();
    if (!tokenInput.trim()) {
      setError('Please enter a valid invitation token.');
      return;
    }
    if (onLaunchCandidateExam) {
      onLaunchCandidateExam(tokenInput.trim().toUpperCase());
    }
  };

  const candidateName = user?.full_name || 'Candidate';
  const candidateEmail = user?.email || '';

  return (
    <div className="min-h-screen bg-[#f8fafc] text-slate-800 font-['Plus_Jakarta_Sans',sans-serif] flex flex-col">
      
      {/* Top Header Bar */}
      <header className="h-16 bg-white border-b border-slate-200 px-6 sm:px-10 flex items-center justify-between sticky top-0 z-40 shadow-xs">
        <div className="flex items-center space-x-3">
          <div className="h-9 w-9 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-md shadow-blue-500/25">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <span className="text-lg font-extrabold tracking-tight text-slate-900">
              Proctor<span className="text-blue-600">AI</span>
            </span>
            <span className="text-[10px] font-semibold text-slate-400 block -mt-1 tracking-wider uppercase">
              Candidate Examination Portal
            </span>
          </div>
        </div>

        {/* User Badge & Sign Out */}
        <div className="flex items-center space-x-3 sm:space-x-4">
          <div className="flex items-center space-x-2.5 p-1.5 rounded-xl bg-slate-50 border border-slate-200">
            <div className="w-7 h-7 rounded-lg bg-blue-600 text-white flex items-center justify-center font-bold text-xs uppercase">
              {candidateName.charAt(0) || 'C'}
            </div>
            <div className="text-left hidden sm:block">
              <div className="text-xs font-bold text-slate-900 leading-tight">
                {candidateName}
              </div>
              <div className="text-[10px] text-blue-600 font-semibold font-mono">
                {candidateEmail}
              </div>
            </div>
            <span className="px-2 py-0.5 rounded text-[9px] font-bold bg-cyan-50 text-cyan-700 border border-cyan-200 hidden md:inline-block">
              Candidate
            </span>
          </div>

          <button
            onClick={logout}
            className="px-3.5 py-2 rounded-xl text-xs font-bold text-rose-600 bg-rose-50 hover:bg-rose-100 border border-rose-200 transition flex items-center space-x-1.5 shadow-2xs"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Sign Out</span>
          </button>
        </div>
      </header>

      {/* Main Workspace Body */}
      <main className="flex-1 max-w-6xl w-full mx-auto p-5 sm:p-8 space-y-8">
        
        {/* Welcome Banner */}
        <div className="rounded-3xl p-6 sm:p-8 bg-gradient-to-r from-[#0c1838] via-[#10204d] to-[#1e3a8a] text-white shadow-xl relative overflow-hidden flex flex-col md:flex-row md:items-center md:justify-between gap-6">
          <div className="absolute inset-0 opacity-15 pointer-events-none bg-[radial-gradient(#60a5fa_1px,transparent_1px)] [background-size:20px_20px]" />
          
          <div className="relative z-10 space-y-2 max-w-xl">
            <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-blue-500/20 border border-blue-400/30 text-[11px] font-bold text-blue-300">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Zero-Tolerance AI Proctoring Enforced</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
              Welcome, {candidateName}
            </h1>
            <p className="text-xs sm:text-sm text-slate-300 leading-relaxed font-normal">
              You are logged in to your Candidate Workspace. Here you can start your assigned technical screening tests, verify your hardware, or enter single-use test invitation tokens.
            </p>
          </div>
        </div>

        {/* 2-Column Section: Active Assessments (Left 7 Cols) + Quick Token Entry & Guidelines (Right 5 Cols) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          
          {/* LEFT: Assigned Assessments List */}
          <div className="lg:col-span-7 space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-200">
              <div>
                <h2 className="text-lg font-bold text-slate-900 flex items-center space-x-2">
                  <FileText className="w-5 h-5 text-blue-600" />
                  <span>My Assigned Assessments</span>
                </h2>
                <p className="text-xs text-slate-500">
                  Tests provisioned for your candidate profile
                </p>
              </div>
              <span className="text-xs font-mono font-bold text-slate-500">
                {invitations.length} Total
              </span>
            </div>

            {loading ? (
              <div className="p-8 text-center text-xs text-slate-400 bg-white rounded-2xl border border-slate-200">
                Loading assigned assessments...
              </div>
            ) : invitations.length === 0 ? (
              <div className="p-8 text-center bg-white rounded-2xl border border-slate-200 space-y-3">
                <Laptop className="w-10 h-10 mx-auto text-slate-300" />
                <div className="text-sm font-bold text-slate-800">No Scheduled Assessments Yet</div>
                <p className="text-xs text-slate-500 max-w-sm mx-auto leading-relaxed">
                  You currently have no tests assigned to this account. When a recruiter invites you to an assessment, it will appear here automatically. You can also enter an invitation token on the right.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {invitations.map((inv) => {
                  const isCompleted = inv.status === 'SUBMITTED';
                  const isInProgress = inv.status === 'IN_PROGRESS' || inv.status === 'STARTED';

                  return (
                    <div 
                      key={inv.id || inv.invitation_token}
                      className="bg-white rounded-2xl p-5 border border-slate-200/90 shadow-sm hover:border-blue-300 transition space-y-4"
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="space-y-1">
                          <h3 className="text-base font-extrabold text-slate-900">
                            {inv.assessment_title || 'Technical Assessment'}
                          </h3>
                          <div className="flex items-center space-x-3 text-xs text-slate-500 font-mono">
                            <span className="flex items-center space-x-1">
                              <Clock className="w-3.5 h-3.5 text-blue-600" />
                              <span>{inv.duration_minutes || 90} Minutes</span>
                            </span>
                            <span>•</span>
                            <span className="flex items-center space-x-1">
                              <KeyRound className="w-3.5 h-3.5 text-slate-400" />
                              <span>Code: <strong>{inv.invitation_token}</strong></span>
                            </span>
                          </div>
                        </div>

                        <div>
                          <span className={`px-2.5 py-1 rounded-full text-[10px] font-bold font-mono border ${
                            isCompleted 
                              ? 'bg-emerald-50 text-emerald-700 border-emerald-200' 
                              : isInProgress
                              ? 'bg-amber-50 text-amber-700 border-amber-200 animate-pulse'
                              : 'bg-blue-50 text-blue-700 border-blue-200'
                          }`}>
                            {inv.status}
                          </span>
                        </div>
                      </div>

                      {/* Performance or Start Banner */}
                      <div className="pt-2 border-t border-slate-100 flex items-center justify-between">
                        {isCompleted ? (
                          <div className="flex items-center space-x-3 text-xs">
                            <span className="font-bold text-slate-700">
                              Result: {inv.total_score !== null ? `${inv.total_score} / 100` : 'Evaluated'}
                            </span>
                            <span className="text-emerald-600 font-bold">
                              {inv.is_passed ? '✓ PASSED' : 'COMPLETED'}
                            </span>
                          </div>
                        ) : (
                          <div className="text-[11px] text-slate-500 font-normal">
                            Full webcam, microphone & full-screen check required
                          </div>
                        )}

                        <button
                          onClick={() => onLaunchCandidateExam && onLaunchCandidateExam(inv.invitation_token)}
                          className={`px-4 py-2 rounded-xl text-xs font-bold transition flex items-center space-x-1.5 shadow-xs ${
                            isCompleted 
                              ? 'bg-slate-100 hover:bg-slate-200 text-slate-700' 
                              : 'bg-blue-600 hover:bg-blue-700 text-white'
                          }`}
                        >
                          <Play className="w-3.5 h-3.5 fill-current" />
                          <span>{isCompleted ? 'Review Result' : isInProgress ? 'Resume Test' : 'Start Assessment'}</span>
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* RIGHT: Quick Token Launcher & Hardware Guidelines */}
          <div className="lg:col-span-5 space-y-6">
            
            {/* Quick Token Launcher Card */}
            <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4">
              <div className="space-y-1">
                <h3 className="text-sm font-bold text-slate-900 flex items-center space-x-2">
                  <KeyRound className="w-4 h-4 text-blue-600" />
                  <span>Enter Assessment Code</span>
                </h3>
                <p className="text-xs text-slate-500">
                  Received an invitation token via email? Enter it below to begin testing.
                </p>
              </div>

              {error && (
                <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs font-semibold">
                  {error}
                </div>
              )}

              <form onSubmit={handleLaunchWithCustomToken} className="space-y-3">
                <div>
                  <input
                    type="text"
                    required
                    value={tokenInput}
                    onChange={(e) => setTokenInput(e.target.value)}
                    placeholder="Enter your invitation token"
                    className="w-full bg-slate-50 border border-slate-300 focus:border-blue-600 focus:bg-white rounded-xl px-3.5 py-2.5 text-xs sm:text-sm font-mono text-slate-900 outline-none transition"
                  />
                </div>

                <button
                  type="submit"
                  className="w-full py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow-md shadow-blue-500/20 transition flex items-center justify-center space-x-1.5"
                >
                  <span>Launch Assessment Diagnostic</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </form>
            </div>

            {/* Diagnostic Guidelines Card */}
            <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-3 text-xs">
              <div className="font-bold text-slate-900 flex items-center space-x-2">
                <Shield className="w-4 h-4 text-blue-600" />
                <span>Candidate Exam Environment Rules</span>
              </div>

              <div className="space-y-2 text-slate-600 text-[11px] leading-relaxed">
                <div className="flex items-start space-x-2">
                  <Check className="w-3.5 h-3.5 text-emerald-600 mt-0.5 flex-shrink-0" />
                  <span>Working webcam and microphone must be allowed for AI proctoring.</span>
                </div>
                <div className="flex items-start space-x-2">
                  <Check className="w-3.5 h-3.5 text-emerald-600 mt-0.5 flex-shrink-0" />
                  <span>Browser must stay in full-screen lockdown. Tab switching is logged.</span>
                </div>
                <div className="flex items-start space-x-2">
                  <Check className="w-3.5 h-3.5 text-emerald-600 mt-0.5 flex-shrink-0" />
                  <span>Copy/paste and developer tools are blocked during active assessment.</span>
                </div>
                <div className="flex items-start space-x-2">
                  <Check className="w-3.5 h-3.5 text-emerald-600 mt-0.5 flex-shrink-0" />
                  <span>Answers are automatically autosaved to the server every 30 seconds.</span>
                </div>
              </div>
            </div>

          </div>

        </div>

      </main>

    </div>
  );
}
