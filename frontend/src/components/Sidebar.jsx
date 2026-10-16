import React from 'react';
import { 
  ShieldCheck, 
  LayoutDashboard, 
  FileText, 
  BookOpen, 
  Users, 
  Eye, 
  TrendingUp, 
  BrainCircuit, 
  LogOut,
  X
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function Sidebar({ activeTab, setActiveTab, mobileOpen, onCloseMobile }) {
  const { user, logout } = useAuth();

  const isProctor = user?.role === 'PROCTOR';
  const isAuthor = user?.role === 'QUESTION_AUTHOR';

  let menuItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'assessments', label: 'Assessments', icon: FileText },
    { id: 'questions', label: 'Question Bank', icon: BookOpen },
    { id: 'candidates', label: 'Candidates', icon: Users },
    { id: 'analytics', label: 'Analytics', icon: TrendingUp }
  ];

  if (isProctor) {
    menuItems = [
      { id: 'proctor', label: 'Live Surveillance', icon: Eye, hasAlert: true },
      { id: 'analytics', label: 'Integrity Analytics', icon: TrendingUp }
    ];
  } else if (isAuthor) {
    menuItems = [
      { id: 'questions', label: 'Question Bank', icon: BookOpen },
      { id: 'assessments', label: 'Assessments', icon: FileText }
    ];
  }

  const handleSelectTab = (tabId) => {
    setActiveTab(tabId);
    if (onCloseMobile) {
      onCloseMobile();
    }
  };

  const sidebarContent = (
    <div className="w-64 bg-[#0b1329] text-slate-400 flex flex-col justify-between border-r border-slate-800/80 h-full font-['Plus_Jakarta_Sans',sans-serif]">
      {/* Top Logo & Menu */}
      <div>
        {/* Brand Header */}
        <div className="p-6 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="h-10 w-10 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-lg shadow-blue-500/25 flex-shrink-0">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <span className="text-xl font-bold tracking-tight text-white flex items-center">
                Proctor<span className="text-blue-400">AI</span>
              </span>
              <span className="block text-[8.5px] font-medium text-slate-400 uppercase tracking-widest -mt-0.5">
                Enterprise Examination
              </span>
            </div>
          </div>
          {onCloseMobile && (
            <button
              onClick={onCloseMobile}
              className="lg:hidden p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
              aria-label="Close Navigation"
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>

        {/* Menu Items */}
        <nav className="px-3 space-y-1.5 mt-2">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => handleSelectTab(item.id)}
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-semibold transition-all ${
                  isActive
                    ? 'bg-blue-600 text-white shadow-md shadow-blue-600/30 font-bold'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                }`}
              >
                <div className="flex items-center space-x-3">
                  <Icon className={`w-4 h-4 ${isActive ? 'text-white' : 'text-slate-400'}`} />
                  <span>{item.label}</span>
                </div>
                {item.hasAlert && (
                  <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse" />
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Bottom AI Status & Sign Out */}
      <div className="p-3 space-y-3">
        <div className="p-4 rounded-2xl bg-[#121c38] border border-blue-900/40 text-left space-y-2 shadow-inner">
          <div className="w-8 h-8 rounded-xl bg-blue-500/20 text-blue-400 flex items-center justify-center">
            <BrainCircuit className="w-4 h-4" />
          </div>
          <div>
            <div className="text-xs font-bold text-white">AI-Powered Proctoring</div>
            <div className="text-[10px] text-slate-400 mt-0.5 leading-snug">
              Active CV facial surveillance & threat detection running.
            </div>
          </div>
        </div>

        <button
          onClick={() => {
            logout();
            setActiveTab('login');
            if (onCloseMobile) onCloseMobile();
          }}
          className="w-full py-2.5 px-3 rounded-xl border border-slate-800 text-xs text-rose-400 hover:bg-rose-500/10 hover:border-rose-500/30 font-semibold flex items-center justify-center space-x-2 transition"
        >
          <LogOut className="w-3.5 h-3.5" />
          <span>Sign Out</span>
        </button>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop Persistent Sidebar */}
      <aside className="hidden lg:flex flex-shrink-0 min-h-screen">
        {sidebarContent}
      </aside>

      {/* Mobile Drawer with Backdrop */}
      {mobileOpen && (
        <div className="lg:hidden fixed inset-0 z-50 flex">
          <div 
            className="fixed inset-0 bg-slate-950/70 backdrop-blur-sm transition-opacity"
            onClick={onCloseMobile}
          />
          <div className="relative z-50 flex-1 max-w-xs w-full bg-[#0b1329] shadow-2xl">
            {sidebarContent}
          </div>
        </div>
      )}
    </>
  );
}
