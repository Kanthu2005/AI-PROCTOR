import React, { useState, useEffect } from 'react';
import { 
  ShieldCheck, 
  ArrowRight, 
  CheckCircle2, 
  Eye, 
  Code2, 
  BarChart3, 
  Cpu, 
  Play, 
  Sparkles, 
  AlertTriangle, 
  Lock, 
  Users, 
  Activity,
  Layers,
  ChevronRight,
  ExternalLink,
  Briefcase,
  GraduationCap,
  FileCode2,
  Building2,
  ShieldAlert,
  Terminal,
  ScanFace,
  Radio,
  Zap,
  LogIn
} from 'lucide-react';
import { DEFAULT_USERS } from '../context/AuthContext';

export default function LandingPage({ 
  onEnterRecruiter, 
  onEnterCandidate, 
  onEnterProctor,
  onOpenAssessmentBuilder,
  onOpenLoginPortal
}) {
  const [pulseRisk, setPulseRisk] = useState(24);
  const [simulatedSecond, setSimulatedSecond] = useState(42);

  // Live timer tick for simulated hero card
  useEffect(() => {
    const interval = setInterval(() => {
      setSimulatedSecond(prev => (prev > 0 ? prev - 1 : 59));
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-[#070b14] text-slate-100 font-['Plus_Jakarta_Sans',sans-serif] selection:bg-indigo-500 selection:text-white">
      
      {/* SaaS Top Header */}
      <header className="sticky top-0 z-50 glass-panel border-b border-slate-800/80 backdrop-blur-2xl">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          
          {/* Logo & Tagline */}
          <div className="flex items-center space-x-3 cursor-pointer group">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-indigo-500 via-purple-600 to-emerald-400 p-[1px] shadow-lg shadow-indigo-500/20 group-hover:scale-105 transition-transform">
              <div className="w-full h-full bg-[#070b14] rounded-[11px] flex items-center justify-center">
                <ShieldCheck className="w-5 h-5 text-emerald-400" />
              </div>
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="text-xl font-black tracking-tight text-white flex items-center">
                  PROCTOR<span className="bg-gradient-to-r from-emerald-400 to-teal-300 bg-clip-text text-transparent">AI</span>
                </span>
                <span className="hidden sm:inline-block px-1.5 py-0.2 rounded text-[8.5px] font-mono font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                  ENTERPRISE
                </span>
              </div>
              <span className="block text-[8.5px] font-bold text-slate-400 uppercase tracking-widest -mt-0.5 font-mono">
                Assess • Monitor • Evaluate • Hire
              </span>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="hidden md:flex items-center space-x-6 text-xs font-semibold text-slate-300">
            <a href="#roles" className="hover:text-white transition">Role Portals</a>
            <a href="#features" className="hover:text-white transition">AI Proctoring</a>
            <a href="#sandbox" className="hover:text-white transition">Code Sandbox</a>
            <a href="#architecture" className="hover:text-white transition">Security</a>
          </nav>

          {/* Quick Access Portal Buttons */}
          <div className="flex items-center space-x-2.5">
            <button
              onClick={() => onOpenLoginPortal('CANDIDATE')}
              className="px-3.5 py-1.5 rounded-xl text-xs font-bold text-slate-300 hover:text-white hover:bg-slate-800/80 border border-slate-800 transition flex items-center space-x-1.5"
            >
              <GraduationCap className="w-3.5 h-3.5 text-cyan-400" />
              <span>Candidate Login</span>
            </button>
            <button
              onClick={() => onOpenLoginPortal('RECRUITER')}
              className="px-4 py-1.5 rounded-xl text-xs font-bold bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white shadow-lg shadow-indigo-600/30 transition flex items-center space-x-1.5"
            >
              <LogIn className="w-3.5 h-3.5" />
              <span>Sign In / All Roles</span>
            </button>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative pt-16 pb-20 overflow-hidden">
        {/* Ambient Glow Orbs */}
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[500px] bg-gradient-to-tr from-indigo-600/15 via-purple-600/15 to-emerald-500/10 blur-[140px] pointer-events-none rounded-full" />
        <div className="absolute -top-10 left-10 w-80 h-80 bg-indigo-500/10 rounded-full blur-[110px] pointer-events-none" />
        
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
            
            {/* Left Column: Value Proposition */}
            <div className="lg:col-span-7 space-y-6 text-center lg:text-left">
              <div className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-slate-900/90 border border-indigo-500/30 text-indigo-400 text-xs font-mono font-semibold shadow-inner">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
                <span>AI-POWERED TECHNICAL ASSESSMENTS & LIVE PROCTORING</span>
              </div>

              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-white leading-tight">
                Assess technical talent with <span className="bg-gradient-to-r from-indigo-400 via-purple-300 to-emerald-400 bg-clip-text text-transparent">uncompromising confidence</span>.
              </h1>

              <p className="text-base sm:text-lg text-slate-300 max-w-2xl mx-auto lg:mx-0 leading-relaxed font-normal">
                Enterprise candidate evaluations with real-time biometric proctoring, isolated sandbox runtimes, automated scoring rubrics, and role-tailored workspaces.
              </p>

              {/* Action Buttons */}
              <div className="flex flex-wrap items-center justify-center lg:justify-start gap-3.5 pt-2">
                <button
                  onClick={() => onOpenLoginPortal('RECRUITER')}
                  className="px-6 py-3.5 rounded-2xl bg-gradient-to-r from-indigo-600 via-purple-600 to-indigo-600 hover:opacity-95 text-white font-bold text-sm shadow-xl shadow-indigo-600/30 flex items-center space-x-2 transition transform hover:-translate-y-0.5"
                >
                  <Sparkles className="w-4 h-4 text-emerald-300" />
                  <span>Open Role Login Portal</span>
                  <ArrowRight className="w-4 h-4" />
                </button>

                <button
                  onClick={() => onOpenLoginPortal('CANDIDATE')}
                  className="px-6 py-3.5 rounded-2xl bg-slate-900/90 hover:bg-slate-800 text-slate-200 border border-slate-700/80 font-bold text-sm transition flex items-center space-x-2"
                >
                  <Play className="w-4 h-4 text-emerald-400" />
                  <span>Candidate Exam Access</span>
                </button>

                <button
                  onClick={onEnterProctor}
                  className="px-5 py-3.5 rounded-2xl bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-bold text-sm transition flex items-center space-x-2"
                >
                  <Eye className="w-4 h-4 text-emerald-400 animate-pulse" />
                  <span>Live Proctor Console</span>
                </button>
              </div>

              {/* Key Trust Signals */}
              <div className="pt-4 flex flex-wrap items-center justify-center lg:justify-start gap-6 text-xs text-slate-400 font-medium">
                <div className="flex items-center space-x-1.5">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span>Server-Authoritative Clock</span>
                </div>
                <div className="flex items-center space-x-1.5">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span>CV Biometrics & Gaze Detection</span>
                </div>
                <div className="flex items-center space-x-1.5">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span>Zero-Trust Sandbox Isolation</span>
                </div>
              </div>
            </div>

            {/* Right Column: Hero Visual - Live Monitor Interactive Card */}
            <div className="lg:col-span-5 relative">
              <div className="relative mx-auto max-w-sm sm:max-w-md">
                
                {/* Glowing border card */}
                <div className="rounded-3xl glass-panel-elevated border border-slate-700/80 overflow-hidden shadow-2xl relative">
                  
                  {/* Card Header with Live Indicator */}
                  <div className="p-4 border-b border-slate-800/80 bg-slate-900/80 flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <span className="w-2.5 h-2.5 rounded-full bg-rose-500 animate-ping" />
                      <span className="text-xs font-mono font-bold text-white uppercase tracking-wider">
                        Live AI Proctor Surveillance
                      </span>
                    </div>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                      WebSocket Active
                    </span>
                  </div>

                  {/* Simulated Camera Feed Viewport */}
                  <div className="relative h-60 bg-slate-950 flex items-center justify-center overflow-hidden">
                    {/* Grid Overlay */}
                    <div className="absolute inset-0 bg-grid-cyber opacity-40 pointer-events-none" />

                    {/* Facial Bounding Box HUD */}
                    <div className="relative w-36 h-48 rounded-2xl border-2 border-emerald-400/80 flex flex-col justify-between p-2 shadow-lg shadow-emerald-500/20">
                      <div className="flex items-center justify-between text-[9px] font-mono text-emerald-400 font-bold">
                        <span>CONF: 99.2%</span>
                        <ScanFace className="w-3.5 h-3.5 text-emerald-400" />
                      </div>
                      
                      {/* Center Silhouette Graphic */}
                      <div className="my-auto mx-auto text-slate-600">
                        <Users className="w-16 h-16 opacity-30" />
                      </div>

                      <div className="text-[9px] font-mono text-emerald-300 font-bold bg-slate-950/80 px-1.5 py-0.5 rounded text-center">
                        FACE_VERIFIED
                      </div>
                    </div>

                    {/* HUD Radar Sweep Line */}
                    <div className="absolute inset-0 bg-gradient-to-b from-transparent via-emerald-500/10 to-transparent h-10 w-full animate-pulse pointer-events-none" />

                    {/* Live Telemetry Floating Pills */}
                    <div className="absolute top-3 left-3 px-2 py-1 rounded-lg bg-slate-900/90 border border-slate-800 text-[10px] font-mono text-slate-300 flex items-center space-x-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                      <span>FPS: 30.0</span>
                    </div>

                    <div className="absolute top-3 right-3 px-2 py-1 rounded-lg bg-slate-900/90 border border-slate-800 text-[10px] font-mono text-emerald-400 flex items-center space-x-1.5">
                      <Radio className="w-3 h-3 text-emerald-400 animate-pulse" />
                      <span>Gaze: Centered</span>
                    </div>

                    <div className="absolute bottom-3 left-3 right-3 p-2.5 rounded-xl bg-slate-900/90 border border-slate-800 flex items-center justify-between text-xs">
                      <div>
                        <div className="text-white font-bold text-xs">Rahul Sharma</div>
                        <div className="text-[10px] text-slate-400 font-mono">Python Backend Evaluation</div>
                      </div>
                      <div className="text-right">
                        <div className="text-[10px] font-mono text-slate-400">Risk Score</div>
                        <div className="text-xs font-bold font-mono text-emerald-400">12/100 (Nominal)</div>
                      </div>
                    </div>
                  </div>

                  {/* Card Bottom Controls */}
                  <div className="p-4 bg-slate-950/60 border-t border-slate-800/80 flex items-center justify-between text-xs">
                    <span className="text-slate-400 font-mono text-[11px]">Auto-Flag Threshold: 40+</span>
                    <button
                      onClick={onEnterProctor}
                      className="text-xs font-bold text-indigo-400 hover:text-indigo-300 flex items-center space-x-1 group"
                    >
                      <span>Open Live Monitor</span>
                      <ChevronRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
                    </button>
                  </div>
                </div>

              </div>
            </div>

          </div>
        </div>
      </section>

      {/* SECTION: ACCESS BY ROLE PORTAL (Dedicated Multi-Role Grid) */}
      <section id="roles" className="py-20 border-t border-slate-800/80 bg-slate-950/60 relative">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          
          <div className="text-center max-w-3xl mx-auto mb-14 space-y-3">
            <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/30 text-indigo-400 text-xs font-mono font-semibold">
              <Layers className="w-3.5 h-3.5" />
              <span>ROLE-BASED WORKSPACES & AUTHENTICATION</span>
            </div>
            <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
              A Dedicated Workspace for Every Stakeholder
            </h2>
            <p className="text-sm sm:text-base text-slate-400 leading-relaxed">
              Log in with role-tailored permissions, zero-trust telemetry, and instant access to specialized consoles.
            </p>
          </div>

          {/* 6 Role Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            
            {/* 1. Recruiter */}
            <div 
              onClick={() => onOpenLoginPortal('RECRUITER')}
              className="glass-card-interactive p-6 rounded-3xl border border-slate-800 hover:border-indigo-500/50 cursor-pointer group flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-4">
                  <div className="w-12 h-12 rounded-2xl bg-indigo-500/15 border border-indigo-500/30 flex items-center justify-center text-indigo-400 group-hover:scale-110 transition-transform">
                    <Briefcase className="w-6 h-6" />
                  </div>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-bold">
                    RECRUITER
                  </span>
                </div>
                <h3 className="text-xl font-bold text-white mb-2 group-hover:text-indigo-300 transition">
                  Enterprise Recruiter Hub
                </h3>
                <p className="text-xs text-slate-400 leading-relaxed mb-4">
                  5-step assessment wizard, automated negative marking formulas, bulk candidate batch invitations, and instant cohort rankings.
                </p>
              </div>

              <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs font-bold text-indigo-400 group-hover:text-indigo-300">
                <span>Sign In as Recruiter</span>
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </div>
            </div>

            {/* 2. Live AI Proctor */}
            <div 
              onClick={() => onOpenLoginPortal('PROCTOR')}
              className="glass-card-interactive p-6 rounded-3xl border border-slate-800 hover:border-emerald-500/50 cursor-pointer group flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-4">
                  <div className="w-12 h-12 rounded-2xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-400 group-hover:scale-110 transition-transform">
                    <Eye className="w-6 h-6" />
                  </div>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-bold">
                    LIVE PROCTOR
                  </span>
                </div>
                <h3 className="text-xl font-bold text-white mb-2 group-hover:text-emerald-300 transition">
                  Surveillance & Incident Console
                </h3>
                <p className="text-xs text-slate-400 leading-relaxed mb-4">
                  Multi-candidate live video grid, dynamic AI anomaly detection, gaze tracking, secondary face alarms, and 1-click disqualifications.
                </p>
              </div>

              <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs font-bold text-emerald-400 group-hover:text-emerald-300">
                <span>Sign In as Proctor</span>
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </div>
            </div>

            {/* 3. Candidate / Test Taker */}
            <div 
              onClick={() => onOpenLoginPortal('CANDIDATE')}
              className="glass-card-interactive p-6 rounded-3xl border border-slate-800 hover:border-cyan-500/50 cursor-pointer group flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-4">
                  <div className="w-12 h-12 rounded-2xl bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center text-cyan-400 group-hover:scale-110 transition-transform">
                    <GraduationCap className="w-6 h-6" />
                  </div>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 font-bold">
                    CANDIDATE
                  </span>
                </div>
                <h3 className="text-xl font-bold text-white mb-2 group-hover:text-cyan-300 transition">
                  Lockdown Candidate Exam Engine
                </h3>
                <p className="text-xs text-slate-400 leading-relaxed mb-4">
                  Hardware diagnostics, full-screen lockdown, Monaco-grade code editor, multi-language sandbox execution, and real-time autosave.
                </p>
              </div>

              <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs font-bold text-cyan-400 group-hover:text-cyan-300">
                <span>Enter with Token or Sign In</span>
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </div>
            </div>

            {/* 4. Question Author */}
            <div 
              onClick={() => onOpenLoginPortal('QUESTION_AUTHOR')}
              className="glass-card-interactive p-6 rounded-3xl border border-slate-800 hover:border-purple-500/50 cursor-pointer group flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-4">
                  <div className="w-12 h-12 rounded-2xl bg-purple-500/15 border border-purple-500/30 flex items-center justify-center text-purple-400 group-hover:scale-110 transition-transform">
                    <FileCode2 className="w-6 h-6" />
                  </div>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-purple-500/10 text-purple-400 border border-purple-500/20 font-bold">
                    QUESTION AUTHOR
                  </span>
                </div>
                <h3 className="text-xl font-bold text-white mb-2 group-hover:text-purple-300 transition">
                  Curriculum & Problem Bank
                </h3>
                <p className="text-xs text-slate-400 leading-relaxed mb-4">
                  Version-controlled question banking, hidden test cases, MCQ distractors, time complexity rubrics, and automated validation.
                </p>
              </div>

              <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs font-bold text-purple-400 group-hover:text-purple-300">
                <span>Sign In as Author</span>
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </div>
            </div>

            {/* 5. Organization Admin */}
            <div 
              onClick={() => onOpenLoginPortal('ORG_ADMIN')}
              className="glass-card-interactive p-6 rounded-3xl border border-slate-800 hover:border-amber-500/50 cursor-pointer group flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-4">
                  <div className="w-12 h-12 rounded-2xl bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-amber-400 group-hover:scale-110 transition-transform">
                    <Building2 className="w-6 h-6" />
                  </div>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 font-bold">
                    ORG ADMIN
                  </span>
                </div>
                <h3 className="text-xl font-bold text-white mb-2 group-hover:text-amber-300 transition">
                  Tenant Governance & Policies
                </h3>
                <p className="text-xs text-slate-400 leading-relaxed mb-4">
                  Organization-wide anti-cheat sensitivity settings, team user management, departmental assessment quotas, and security logs.
                </p>
              </div>

              <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs font-bold text-amber-400 group-hover:text-amber-300">
                <span>Sign In as Org Admin</span>
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </div>
            </div>

            {/* 6. Platform Superadmin */}
            <div 
              onClick={() => onOpenLoginPortal('PLATFORM_ADMIN')}
              className="glass-card-interactive p-6 rounded-3xl border border-slate-800 hover:border-rose-500/50 cursor-pointer group flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-4">
                  <div className="w-12 h-12 rounded-2xl bg-rose-500/15 border border-rose-500/30 flex items-center justify-center text-rose-400 group-hover:scale-110 transition-transform">
                    <ShieldAlert className="w-6 h-6" />
                  </div>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20 font-bold">
                    SUPERADMIN
                  </span>
                </div>
                <h3 className="text-xl font-bold text-white mb-2 group-hover:text-rose-300 transition">
                  Platform Oversight & Sandbox Telemetry
                </h3>
                <p className="text-xs text-slate-400 leading-relaxed mb-4">
                  Cross-tenant container health, global evaluation metrics, microservices uptime, and compliance audit trail inspection.
                </p>
              </div>

              <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs font-bold text-rose-400 group-hover:text-rose-300">
                <span>Sign In as Superadmin</span>
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </div>
            </div>

          </div>

        </div>
      </section>

      {/* Features Bento Grid */}
      <section id="features" className="py-20 border-t border-slate-800/80">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          
          <div className="text-center max-w-3xl mx-auto mb-14 space-y-3">
            <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
              Enterprise Evaluation Architecture
            </h2>
            <p className="text-sm sm:text-base text-slate-400 leading-relaxed">
              Four specialized layers engineered for high-stakes assessment accuracy.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="glass-panel p-6 rounded-2xl border border-slate-800/80 space-y-3">
              <div className="p-3 rounded-xl bg-indigo-500/10 border border-indigo-500/30 text-indigo-400 w-fit">
                <ScanFace className="w-5 h-5" />
              </div>
              <h4 className="text-base font-bold text-white">Biometric CV Telemetry</h4>
              <p className="text-xs text-slate-400 leading-relaxed">
                Continual facial presence verification, gaze angle tracking, secondary face detection, and mobile phone recognition.
              </p>
            </div>

            <div className="glass-panel p-6 rounded-2xl border border-slate-800/80 space-y-3">
              <div className="p-3 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 w-fit">
                <Terminal className="w-5 h-5" />
              </div>
              <h4 className="text-base font-bold text-white">Isolated Sandbox Runner</h4>
              <p className="text-xs text-slate-400 leading-relaxed">
                Sandboxed Docker runtime executing Python, Java, and C++ with strict CPU/memory limits, timeouts, and hidden unit tests.
              </p>
            </div>

            <div className="glass-panel p-6 rounded-2xl border border-slate-800/80 space-y-3">
              <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 w-fit">
                <Activity className="w-5 h-5" />
              </div>
              <h4 className="text-base font-bold text-white">Dynamic Threat Meter</h4>
              <p className="text-xs text-slate-400 leading-relaxed">
                Real-time risk scoring engine aggregating tab switches, audio anomalies, and gaze violations into a normalized 0-100 score.
              </p>
            </div>

            <div className="glass-panel p-6 rounded-2xl border border-slate-800/80 space-y-3">
              <div className="p-3 rounded-xl bg-purple-500/10 border border-purple-500/30 text-purple-400 w-fit">
                <BarChart3 className="w-5 h-5" />
              </div>
              <h4 className="text-base font-bold text-white">Psychometric Analytics</h4>
              <p className="text-xs text-slate-400 leading-relaxed">
                Gaussian distribution models, candidate percentile ranking, topic mastery heatmaps, and comprehensive anti-cheat audit logs.
              </p>
            </div>
          </div>

        </div>
      </section>

      {/* Modern SaaS Footer */}
      <footer className="border-t border-slate-800/80 glass-panel py-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row items-center justify-between gap-6 text-xs text-slate-500 font-mono">
          <div className="flex items-center space-x-3">
            <ShieldCheck className="w-5 h-5 text-emerald-400" />
            <span className="font-bold text-slate-300">ProctorAI Enterprise Assessment System</span>
            <span>•</span>
            <span>Multi-Role RBAC Architecture</span>
          </div>

          <div className="flex items-center space-x-6 text-[11px]">
            <span>FastAPI Core</span>
            <span>PostgreSQL & MongoDB</span>
            <span>Docker Sandbox</span>
            <span>OpenCV CV Biometrics</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
