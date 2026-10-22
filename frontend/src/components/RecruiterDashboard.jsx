import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { api } from '../api';
import { 
  FileText, 
  Users, 
  CheckCircle2, 
  AlertTriangle, 
  Plus, 
  ArrowRight, 
  TrendingUp, 
  TrendingDown,
  Clock, 
  Activity, 
  Eye, 
  BarChart3, 
  Bell, 
  Sparkles, 
  MoreVertical,
  Calendar,
  Search,
  Code2,
  Database,
  Terminal,
  HelpCircle,
  UserPlus,
  Play,
  RefreshCw,
  Mail,
  Send
} from 'lucide-react';

export default function RecruiterDashboard({ 
  onNavigateTab, 
  onOpenCreateWizard,
  onOpenCandidateInvite,
  onLaunchCandidateExam
}) {
  const { user } = useAuth();
  const [performanceTab, setPerformanceTab] = useState('30D');
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadDashboardData();
  }, [user]);

  const loadDashboardData = async () => {
    try {
      setRefreshing(true);
      const orgId = user?.org_id;
      const data = await api.getRecruiterDashboard(orgId);
      if (data) {
        setDashboardData(data);
      }
    } catch (err) {
      console.warn('Recruiter dashboard API fallback:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  // Stat Cards (Real API Driven)
  const totalAssessments = dashboardData?.total_assessments ?? 0;
  const totalCandidates = dashboardData?.total_candidates ?? 0;
  const completedCandidates = dashboardData?.total_completed ?? 0;
  const alertsCount = dashboardData?.alerts_count ?? 0;

  const stats = [
    {
      label: 'Total Assessments',
      value: totalAssessments.toString(),
      trend: `${dashboardData?.status_counts?.LIVE || 0} Live • ${dashboardData?.status_counts?.DRAFT || 0} Draft`,
      isPositive: true,
      iconBg: 'bg-blue-50 text-blue-600',
      icon: FileText
    },
    {
      label: 'Total Candidates',
      value: totalCandidates.toString(),
      trend: `${dashboardData?.total_in_progress || 0} in progress`,
      isPositive: true,
      iconBg: 'bg-emerald-50 text-emerald-600',
      icon: Users
    },
    {
      label: 'Completed',
      value: completedCandidates.toString(),
      trend: `${dashboardData?.pass_rate ?? 0}% pass rate`,
      isPositive: true,
      iconBg: 'bg-purple-50 text-purple-600',
      icon: CheckCircle2
    },
    {
      label: 'Alerts',
      value: alertsCount.toString(),
      trend: alertsCount > 0 ? `${alertsCount} require review` : 'All clear',
      isPositive: alertsCount === 0,
      iconBg: 'bg-amber-50 text-amber-600',
      icon: AlertTriangle
    }
  ];

  // Recent Assessments (Real API or default)
  const recentAssessments = (dashboardData?.recent_assessments && dashboardData.recent_assessments.length > 0)
    ? dashboardData.recent_assessments.map(a => ({
        id: a.id,
        name: a.title,
        iconBg: a.title.toLowerCase().includes('python') ? 'bg-blue-100 text-blue-700' :
                a.title.toLowerCase().includes('sql') ? 'bg-cyan-100 text-cyan-700' :
                a.title.toLowerCase().includes('java') ? 'bg-red-100 text-red-700' : 'bg-purple-100 text-purple-700',
        iconLetter: a.title.slice(0, 2).toUpperCase(),
        details: `${a.question_count || 0} Questions • ${a.total_duration_minutes} min • ${a.total_marks} Marks`,
        status: a.status,
        statusColor: a.status === 'LIVE' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
                     a.status === 'PUBLISHED' ? 'bg-blue-50 text-blue-700 border-blue-200' :
                     a.status === 'SCHEDULED' ? 'bg-amber-50 text-amber-700 border-amber-200' :
                     a.status === 'CLOSED' ? 'bg-slate-100 text-slate-700 border-slate-200' : 'bg-gray-100 text-gray-700 border-gray-200',
        candidatesCurrent: a.candidates_completed ?? 0,
        candidatesTotal: a.candidates_invited ?? 0,
        completionRate: a.completion_rate ?? 0,
        token: a.sample_token || ''
      }))
    : [];

  // Recent Activity Feed
  const activities = (dashboardData?.activities && dashboardData.activities.length > 0)
    ? dashboardData.activities.map(act => ({
        user: act.user,
        action: act.action,
        context: act.context,
        time: act.time ? new Date(act.time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'recently',
        avatarBg: act.isAlert ? 'bg-rose-100 text-rose-700' : 'bg-blue-100 text-blue-700',
        avatarText: (act.user || 'U').slice(0, 2).toUpperCase(),
        isAlert: act.isAlert
      }))
    : [];

  // Current Active Candidates
  const activeCandidates = (dashboardData?.active_candidates && dashboardData.active_candidates.length > 0)
    ? dashboardData.active_candidates.map(c => ({
        name: c.name,
        progress: c.progress,
        risk: c.risk,
        riskColor: c.risk === 'HIGH' ? 'text-rose-600 font-bold' : c.risk === 'MEDIUM' ? 'text-amber-600' : 'text-emerald-600',
        dotColor: c.risk === 'HIGH' ? 'bg-rose-500' : c.risk === 'MEDIUM' ? 'bg-amber-500' : 'bg-emerald-500'
      }))
    : [];

  const displayName = user?.full_name ? user.full_name.split(' ')[0] : 'Recruiter';

  return (
    <div className="space-y-6 text-slate-800 font-['Plus_Jakarta_Sans',sans-serif]">
      
      {/* 1. WELCOME HEADER BAR */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight flex items-center gap-2">
            <span>Welcome back, {displayName}!</span>
            <span>👋</span>
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Real-time API telemetry and metrics for your organization's evaluations.
          </p>
        </div>

        {/* Live Status and Refresh Button */}
        <div className="flex items-center space-x-2">
          <button
            onClick={loadDashboardData}
            disabled={refreshing}
            className="flex items-center space-x-1.5 px-3 py-2 bg-white border border-slate-200 rounded-xl text-xs font-semibold text-slate-700 shadow-sm hover:border-slate-300 transition"
            title="Refresh metrics from server"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-slate-500 ${refreshing ? 'animate-spin' : ''}`} />
            <span>{refreshing ? 'Syncing...' : 'Live Sync'}</span>
          </button>
          <div className="flex items-center space-x-2 px-3.5 py-2 bg-white border border-slate-200 rounded-xl text-xs font-semibold text-slate-700 shadow-sm">
            <Calendar className="w-4 h-4 text-slate-400" />
            <span>Today (Live)</span>
          </div>
        </div>
      </div>

      {/* 2. 4 STAT CARDS ROW */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5">
        {stats.map((s, idx) => {
          const Icon = s.icon;
          return (
            <div key={idx} className="bg-white rounded-2xl p-5 border border-slate-200/90 shadow-sm hover:shadow-md transition">
              <div className="flex items-center justify-between mb-3">
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${s.iconBg}`}>
                  <Icon className="w-5 h-5" />
                </div>
              </div>
              <div className="text-3xl font-extrabold text-slate-900 tracking-tight font-sans">
                {s.value}
              </div>
              <div className="text-xs font-semibold text-slate-500 mt-1">
                {s.label}
              </div>
              <div className="mt-2 text-xs font-semibold flex items-center gap-1">
                {s.isPositive ? (
                  <span className="text-emerald-600 flex items-center gap-0.5">
                    <TrendingUp className="w-3.5 h-3.5" />
                    <span>{s.trend}</span>
                  </span>
                ) : (
                  <span className="text-amber-600 flex items-center gap-0.5">
                    <TrendingDown className="w-3.5 h-3.5" />
                    <span>{s.trend}</span>
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* 3. MAIN DASHBOARD CONTENT GRID (Left 8 Cols, Right 4 Cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* LEFT COLUMN: CHARTS & RECENT ASSESSMENTS TABLE (8 COLS) */}
        <div className="lg:col-span-8 space-y-6">
          
          {/* Middle Row: Assessment Performance & Candidate Status Donut */}
          <div className="grid grid-cols-1 md:grid-cols-12 gap-5">
            
            {/* Assessment Performance Spline Chart Card (7 Cols) */}
            <div className="md:col-span-7 bg-white rounded-2xl p-5 border border-slate-200/90 shadow-sm flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-sm font-bold text-slate-900">
                    Assessment Performance
                  </h3>
                  <div className="flex p-0.5 bg-slate-100 rounded-lg text-xs font-semibold text-slate-600">
                    <button 
                      onClick={() => setPerformanceTab('7D')}
                      className={`px-2 py-0.5 rounded ${performanceTab === '7D' ? 'bg-white shadow-xs font-bold text-blue-600' : ''}`}
                    >
                      7D
                    </button>
                    <button 
                      onClick={() => setPerformanceTab('30D')}
                      className={`px-2 py-0.5 rounded ${performanceTab === '30D' ? 'bg-blue-600 text-white shadow-xs font-bold' : ''}`}
                    >
                      30D
                    </button>
                    <button 
                      onClick={() => setPerformanceTab('90D')}
                      className={`px-2 py-0.5 rounded ${performanceTab === '90D' ? 'bg-white shadow-xs font-bold text-blue-600' : ''}`}
                    >
                      90D
                    </button>
                  </div>
                </div>

                {/* SVG Spline Chart (Exact curve representation from Mockup) */}
                <div className="h-44 w-full relative">
                  <svg className="w-full h-full" viewBox="0 0 350 140" fill="none">
                    {/* Grid lines */}
                    <line x1="0" y1="20" x2="350" y2="20" stroke="#f1f5f9" strokeWidth="1" strokeDasharray="3 3" />
                    <line x1="0" y1="50" x2="350" y2="50" stroke="#f1f5f9" strokeWidth="1" strokeDasharray="3 3" />
                    <line x1="0" y1="80" x2="350" y2="80" stroke="#f1f5f9" strokeWidth="1" strokeDasharray="3 3" />
                    <line x1="0" y1="110" x2="350" y2="110" stroke="#f1f5f9" strokeWidth="1" strokeDasharray="3 3" />

                    {/* Blue Spline: Started */}
                    <path
                      d="M 10 100 Q 70 75, 120 70 T 200 65 T 270 40 T 340 30"
                      stroke="#2563eb"
                      strokeWidth="2.5"
                      fill="none"
                    />
                    {/* Blue Dots */}
                    <circle cx="10" cy="100" r="3.5" fill="#2563eb" />
                    <circle cx="120" cy="70" r="3.5" fill="#2563eb" />
                    <circle cx="200" cy="65" r="3.5" fill="#2563eb" />
                    <circle cx="270" cy="40" r="3.5" fill="#2563eb" />
                    <circle cx="340" cy="30" r="4" fill="#2563eb" />

                    {/* Green Spline: Completed */}
                    <path
                      d="M 10 115 Q 70 95, 120 85 T 200 80 T 270 58 T 340 45"
                      stroke="#10b981"
                      strokeWidth="2.5"
                      fill="none"
                    />
                    <circle cx="10" cy="115" r="3" fill="#10b981" />
                    <circle cx="120" cy="85" r="3" fill="#10b981" />
                    <circle cx="200" cy="80" r="3" fill="#10b981" />
                    <circle cx="270" cy="58" r="3" fill="#10b981" />
                    <circle cx="340" cy="45" r="3.5" fill="#10b981" />

                    {/* Purple Spline: Passed */}
                    <path
                      d="M 10 125 Q 70 110, 120 100 T 200 95 T 270 78 T 340 65"
                      stroke="#8b5cf6"
                      strokeWidth="2.5"
                      fill="none"
                    />
                    <circle cx="10" cy="125" r="3" fill="#8b5cf6" />
                    <circle cx="120" cy="100" r="3" fill="#8b5cf6" />
                    <circle cx="200" cy="95" r="3" fill="#8b5cf6" />
                    <circle cx="270" cy="78" r="3" fill="#8b5cf6" />
                    <circle cx="340" cy="65" r="3.5" fill="#8b5cf6" />
                  </svg>

                  {/* Date labels */}
                  <div className="flex justify-between text-[10px] text-slate-400 mt-1 font-mono">
                    <span>Oct 15</span>
                    <span>Oct 16</span>
                    <span>Oct 17</span>
                    <span>Oct 18</span>
                    <span>Oct 19</span>
                    <span>Oct 20</span>
                    <span>Oct 21</span>
                  </div>
                </div>
              </div>

              {/* Chart Legend (From Mockup) */}
              <div className="flex items-center space-x-4 pt-3 border-t border-slate-100 text-xs font-semibold">
                <span className="flex items-center space-x-1.5 text-slate-600">
                  <span className="w-2.5 h-2.5 rounded-full bg-blue-600" />
                  <span>Started</span>
                </span>
                <span className="flex items-center space-x-1.5 text-slate-600">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                  <span>Completed</span>
                </span>
                <span className="flex items-center space-x-1.5 text-slate-600">
                  <span className="w-2.5 h-2.5 rounded-full bg-purple-500" />
                  <span>Passed</span>
                </span>
              </div>
            </div>

            {/* Candidate Status Donut Chart Card (5 Cols) (From Mockup) */}
            <div className="md:col-span-5 bg-white rounded-2xl p-5 border border-slate-200/90 shadow-sm flex flex-col justify-between">
              <div>
                <h3 className="text-sm font-bold text-slate-900 mb-3">
                  Candidate Status
                </h3>

                <div className="flex items-center justify-between gap-2">
                  {/* Circular Donut Graphic */}
                  <div className="relative w-28 h-28 flex-shrink-0 flex items-center justify-center">
                    <svg className="w-full h-full -rotate-90" viewBox="0 0 36 36">
                      {/* Background circle */}
                      <path
                        className="text-slate-100"
                        strokeWidth="5"
                        stroke="currentColor"
                        fill="none"
                        d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                      />
                      {/* Blue segment: Started 27% */}
                      <path
                        className="text-blue-500"
                        strokeDasharray="27, 100"
                        strokeWidth="5"
                        stroke="currentColor"
                        fill="none"
                        d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                      />
                      {/* Emerald segment: Completed 19% */}
                      <path
                        className="text-emerald-500"
                        strokeDasharray="19, 100"
                        strokeDashoffset="-27"
                        strokeWidth="5"
                        stroke="currentColor"
                        fill="none"
                        d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                      />
                      {/* Purple segment: In Progress 17% */}
                      <path
                        className="text-purple-500"
                        strokeDasharray="17, 100"
                        strokeDashoffset="-46"
                        strokeWidth="5"
                        stroke="currentColor"
                        fill="none"
                        d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                      />
                      {/* Amber segment: Registered 19% */}
                      <path
                        className="text-amber-400"
                        strokeDasharray="19, 100"
                        strokeDashoffset="-63"
                        strokeWidth="5"
                        stroke="currentColor"
                        fill="none"
                        d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                      />
                      {/* Slate segment: Invited 13% */}
                      <path
                        className="text-slate-400"
                        strokeDasharray="13, 100"
                        strokeDashoffset="-82"
                        strokeWidth="5"
                        stroke="currentColor"
                        fill="none"
                        d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                      />
                      {/* Rose segment: Expired 5% */}
                      <path
                        className="text-rose-500"
                        strokeDasharray="5, 100"
                        strokeDashoffset="-95"
                        strokeWidth="5"
                        stroke="currentColor"
                        fill="none"
                        d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                      />
                    </svg>
                    {/* Donut Center */}
                    <div className="absolute text-center">
                      <div className="text-base font-extrabold text-slate-900 leading-none">248</div>
                      <div className="text-[10px] text-slate-500 font-medium">Total</div>
                    </div>
                  </div>

                  {/* Donut Status Legend (From Mockup) */}
                  <div className="text-[11px] space-y-1 font-semibold flex-1">
                    <div className="flex items-center justify-between text-slate-600">
                      <span className="flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full bg-slate-400" />
                        <span>Invited</span>
                      </span>
                      <span className="font-bold text-slate-900">32 <span className="text-slate-400 font-normal">(13%)</span></span>
                    </div>
                    <div className="flex items-center justify-between text-slate-600">
                      <span className="flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full bg-blue-500" />
                        <span>Registered</span>
                      </span>
                      <span className="font-bold text-slate-900">48 <span className="text-slate-400 font-normal">(19%)</span></span>
                    </div>
                    <div className="flex items-center justify-between text-slate-600">
                      <span className="flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full bg-amber-400" />
                        <span>Started</span>
                      </span>
                      <span className="font-bold text-slate-900">67 <span className="text-slate-400 font-normal">(27%)</span></span>
                    </div>
                    <div className="flex items-center justify-between text-slate-600">
                      <span className="flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full bg-purple-500" />
                        <span>In Progress</span>
                      </span>
                      <span className="font-bold text-slate-900">41 <span className="text-slate-400 font-normal">(17%)</span></span>
                    </div>
                    <div className="flex items-center justify-between text-slate-600">
                      <span className="flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full bg-emerald-500" />
                        <span>Completed</span>
                      </span>
                      <span className="font-bold text-slate-900">48 <span className="text-slate-400 font-normal">(19%)</span></span>
                    </div>
                    <div className="flex items-center justify-between text-slate-600">
                      <span className="flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full bg-rose-500" />
                        <span>Expired</span>
                      </span>
                      <span className="font-bold text-slate-900">12 <span className="text-slate-400 font-normal">(5%)</span></span>
                    </div>
                  </div>
                </div>

              </div>
            </div>

          </div>

          {/* Lower: Recent Assessments Table (From Mockup) */}
          <div className="bg-white rounded-2xl p-5 border border-slate-200/90 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-bold text-slate-900">
                Recent Assessments
              </h3>
              <a href="#all" onClick={(e) => { e.preventDefault(); onNavigateTab('assessments'); }} className="text-xs font-semibold text-blue-600 hover:text-blue-700 flex items-center gap-1">
                <span>View All</span>
                <span>&rarr;</span>
              </a>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-100 text-slate-400 font-semibold uppercase text-[10px] tracking-wider pb-2">
                    <th className="py-2.5 px-3">Name</th>
                    <th className="py-2.5 px-3">Status</th>
                    <th className="py-2.5 px-3">Candidates</th>
                    <th className="py-2.5 px-3">Completion Rate</th>
                    <th className="py-2.5 px-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {recentAssessments.map((a) => (
                    <tr key={a.id} className="hover:bg-slate-50/70 transition">
                      <td className="py-3 px-3">
                        <div className="flex items-center space-x-3">
                          <div className={`w-8 h-8 rounded-lg flex items-center justify-center font-bold text-xs ${a.iconBg}`}>
                            {a.iconLetter}
                          </div>
                          <div>
                            <div className="font-bold text-slate-900 text-xs">{a.name}</div>
                            <div className="text-[11px] text-slate-400">{a.details}</div>
                          </div>
                        </div>
                      </td>
                      <td className="py-3 px-3">
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${a.statusColor}`}>
                          {a.status}
                        </span>
                      </td>
                      <td className="py-3 px-3 font-semibold text-slate-700">
                        {a.candidatesCurrent} <span className="text-slate-400 font-normal">/ {a.candidatesTotal}</span>
                      </td>
                      <td className="py-3 px-3 min-w-[140px]">
                        <div className="flex items-center space-x-2">
                          <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                            <div 
                              className="h-full bg-emerald-500 rounded-full" 
                              style={{ width: `${a.completionRate}%` }} 
                            />
                          </div>
                          <span className="text-[11px] font-bold text-slate-700 w-8 text-right">
                            {a.completionRate}%
                          </span>
                        </div>
                      </td>
                      <td className="py-3 px-3 text-right">
                        <div className="flex items-center justify-end space-x-1.5">
                          <button
                            onClick={() => onOpenCandidateInvite && onOpenCandidateInvite({ id: a.id, title: a.name, ...a })}
                            className="px-2.5 py-1 rounded-lg text-xs font-bold bg-blue-50 hover:bg-blue-100 text-blue-700 border border-blue-200 transition flex items-center space-x-1"
                            title="Send real exam invitation email"
                          >
                            <Mail className="w-3 h-3 text-blue-600" />
                            <span>Invite</span>
                          </button>
                          <button
                            onClick={() => {
                              if (a.token) {
                                onLaunchCandidateExam(a.token);
                              } else {
                                onNavigateTab('assessments');
                              }
                            }}
                            className="px-2.5 py-1 rounded-lg text-xs font-semibold text-slate-600 hover:bg-slate-100 border border-slate-200 transition"
                          >
                            View
                          </button>
                          <button className="p-1 text-slate-400 hover:text-slate-600">
                            <MoreVertical className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Bottom Quick Actions (From Mockup) */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-1">
            <button
              onClick={onOpenCreateWizard}
              className="p-3 bg-white rounded-xl border border-slate-200 hover:border-blue-400 shadow-xs hover:shadow-sm text-left transition flex items-center space-x-2.5 group"
            >
              <div className="w-8 h-8 rounded-lg bg-blue-500 text-white flex items-center justify-center flex-shrink-0 group-hover:scale-105 transition-transform">
                <Plus className="w-4 h-4" />
              </div>
              <div className="truncate">
                <div className="text-xs font-bold text-slate-900">Create Assessment</div>
                <div className="text-[10px] text-slate-500">Build a new test</div>
              </div>
            </button>

            <button
              onClick={() => onNavigateTab('questions')}
              className="p-3 bg-white rounded-xl border border-slate-200 hover:border-purple-400 shadow-xs hover:shadow-sm text-left transition flex items-center space-x-2.5 group"
            >
              <div className="w-8 h-8 rounded-lg bg-purple-500 text-white flex items-center justify-center flex-shrink-0 group-hover:scale-105 transition-transform">
                <HelpCircle className="w-4 h-4" />
              </div>
              <div className="truncate">
                <div className="text-xs font-bold text-slate-900">Add Questions</div>
                <div className="text-[10px] text-slate-500">Manage question bank</div>
              </div>
            </button>

            <button
              onClick={() => {
                if (onOpenCandidateInvite && recentAssessments.length > 0) {
                  onOpenCandidateInvite(recentAssessments[0]);
                } else {
                  onNavigateTab('candidates');
                }
              }}
              className="p-3 bg-white rounded-xl border border-slate-200 hover:border-emerald-400 shadow-xs hover:shadow-sm text-left transition flex items-center space-x-2.5 group"
            >
              <div className="w-8 h-8 rounded-lg bg-emerald-500 text-white flex items-center justify-center flex-shrink-0 group-hover:scale-105 transition-transform">
                <Mail className="w-4 h-4" />
              </div>
              <div className="truncate">
                <div className="text-xs font-bold text-slate-900">Send Invitations</div>
                <div className="text-[10px] text-slate-500">Real email dispatch</div>
              </div>
            </button>

            <button
              onClick={() => onNavigateTab('proctor')}
              className="p-3 bg-white rounded-xl border border-slate-200 hover:border-cyan-400 shadow-xs hover:shadow-sm text-left transition flex items-center space-x-2.5 group"
            >
              <div className="w-8 h-8 rounded-lg bg-blue-600 text-white flex items-center justify-center flex-shrink-0 group-hover:scale-105 transition-transform">
                <Eye className="w-4 h-4" />
              </div>
              <div className="truncate">
                <div className="text-xs font-bold text-slate-900">Live Monitor</div>
                <div className="text-[10px] text-slate-500">Watch ongoing tests</div>
              </div>
            </button>
          </div>

        </div>

        {/* RIGHT COLUMN: RECENT ACTIVITY, LIVE PROCTORING, ACTIVE CANDIDATES (4 COLS) (Exact Mockup Match) */}
        <div className="lg:col-span-4 space-y-6">
          
          {/* Card 1: Recent Activity (From Mockup) */}
          <div className="bg-white rounded-2xl p-5 border border-slate-200/90 shadow-sm space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100">
              <h3 className="text-sm font-bold text-slate-900">
                Recent Activity
              </h3>
              <a href="#all" onClick={(e) => { e.preventDefault(); onNavigateTab('candidates'); }} className="text-xs font-semibold text-blue-600 hover:underline">
                View All &rarr;
              </a>
            </div>

            <div className="space-y-3.5">
              {activities.map((act, i) => (
                <div key={i} className="flex items-start space-x-3 text-xs">
                  {act.isAlert ? (
                    <div className="w-7 h-7 rounded-lg bg-rose-50 text-rose-600 flex items-center justify-center flex-shrink-0 mt-0.5 border border-rose-200">
                      <AlertTriangle className="w-3.5 h-3.5" />
                    </div>
                  ) : act.isInvite ? (
                    <div className="w-7 h-7 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center flex-shrink-0 mt-0.5 border border-emerald-200">
                      <UserPlus className="w-3.5 h-3.5" />
                    </div>
                  ) : act.isComplete ? (
                    <div className="w-7 h-7 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center flex-shrink-0 mt-0.5 border border-emerald-200">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                    </div>
                  ) : (
                    <div className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5 font-bold text-[10px] ${act.avatarBg}`}>
                      {act.avatarText}
                    </div>
                  )}

                  <div className="flex-1 leading-snug">
                    <div className="font-semibold text-slate-900">
                      {act.user} <span className="font-normal text-slate-500">{act.action}</span>
                    </div>
                    {act.context && (
                      <div className="text-[11px] text-slate-400 mt-0.5">{act.context}</div>
                    )}
                    <div className="text-[10px] text-slate-400 mt-0.5">{act.time}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Card 2: Live Proctoring • Live (From Mockup) */}
          <div className="bg-white rounded-2xl p-5 border border-slate-200/90 shadow-sm space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100">
              <div className="flex items-center space-x-2">
                <h3 className="text-sm font-bold text-slate-900">Live Proctoring</h3>
                <span className="flex items-center space-x-1 px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-600 border border-emerald-200">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                  <span>Live</span>
                </span>
              </div>
              <a href="#proctor" onClick={(e) => { e.preventDefault(); onNavigateTab('proctor'); }} className="text-xs font-semibold text-blue-600 hover:underline">
                View All &rarr;
              </a>
            </div>

            {/* 4 Mini Stat Counter Boxes (From Mockup) */}
            <div className="grid grid-cols-4 gap-2 text-center">
              <div className="p-2 rounded-xl bg-slate-50 border border-slate-100">
                <Users className="w-4 h-4 mx-auto text-blue-600 mb-1" />
                <div className="text-base font-extrabold text-slate-900">124</div>
                <div className="text-[9px] text-slate-400 font-medium">Candidates</div>
              </div>

              <div className="p-2 rounded-xl bg-slate-50 border border-slate-100">
                <Play className="w-4 h-4 mx-auto text-emerald-600 mb-1" />
                <div className="text-base font-extrabold text-slate-900">87</div>
                <div className="text-[9px] text-slate-400 font-medium">Active</div>
              </div>

              <div className="p-2 rounded-xl bg-rose-50/60 border border-rose-100">
                <AlertTriangle className="w-4 h-4 mx-auto text-rose-600 mb-1" />
                <div className="text-base font-extrabold text-rose-600">8</div>
                <div className="text-[9px] text-rose-500 font-medium">High Risk</div>
              </div>

              <div className="p-2 rounded-xl bg-amber-50/60 border border-amber-100">
                <Bell className="w-4 h-4 mx-auto text-amber-600 mb-1" />
                <div className="text-base font-extrabold text-amber-600">31</div>
                <div className="text-[9px] text-amber-500 font-medium">Alerts</div>
              </div>
            </div>

            {/* Current Active Candidates List (From Mockup) */}
            <div className="pt-2">
              <div className="flex items-center justify-between text-xs font-semibold text-slate-700 mb-2">
                <span>Current Active Candidates</span>
                <span className="text-[10px] text-slate-400">View All &rarr;</span>
              </div>

              <div className="space-y-2">
                {activeCandidates.map((cand, i) => (
                  <div key={i} className="flex items-center justify-between p-2 rounded-xl bg-slate-50/70 border border-slate-100 text-xs">
                    <div className="flex items-center space-x-2">
                      <span className={`w-2 h-2 rounded-full ${cand.dotColor}`} />
                      <div>
                        <div className="font-bold text-slate-900">{cand.name}</div>
                        <div className="text-[10px] text-slate-500">{cand.progress}</div>
                      </div>
                    </div>
                    <span className={`text-[11px] font-bold ${cand.riskColor}`}>
                      Risk: {cand.risk}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Top Performing Assessments (From Mockup) */}
            <div className="pt-2 border-t border-slate-100">
              <div className="flex items-center justify-between text-xs font-semibold text-slate-700 mb-2">
                <span>Top Performing Assessments</span>
                <span className="text-[10px] text-slate-400">View All &rarr;</span>
              </div>

              <div className="space-y-2 text-xs">
                <div>
                  <div className="flex justify-between text-[11px] font-medium text-slate-700 mb-1">
                    <span>Python Backend Developer</span>
                    <span className="font-bold">86.4%</span>
                  </div>
                  <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                    <div className="h-full bg-blue-600 rounded-full w-[86.4%]" />
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-[11px] font-medium text-slate-700 mb-1">
                    <span>SQL Assessment</span>
                    <span className="font-bold">78.2%</span>
                  </div>
                  <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                    <div className="h-full bg-blue-600 rounded-full w-[78.2%]" />
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-[11px] font-medium text-slate-700 mb-1">
                    <span>Java Developer</span>
                    <span className="font-bold">72.8%</span>
                  </div>
                  <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                    <div className="h-full bg-blue-600 rounded-full w-[72.8%]" />
                  </div>
                </div>
              </div>
            </div>

          </div>

        </div>

      </div>

    </div>
  );
}
