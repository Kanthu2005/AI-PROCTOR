import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { api } from '../api';
import { 
  Search, 
  Bell, 
  ChevronDown, 
  LogOut, 
  ShieldCheck,
  Menu,
  X,
  Activity,
  CheckCircle2,
  AlertTriangle
} from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab, onToggleMobileSidebar, mobileSidebarOpen }) {
  const { user, logout } = useAuth();
  const [showDropdown, setShowDropdown] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [healthInfo, setHealthInfo] = useState({ status: 'checking', database: 'checking' });
  const [showHealthTooltip, setShowHealthTooltip] = useState(false);

  const displayName = user?.full_name || 'Kanthu Reddy';
  const displayRole = user?.role || 'RECRUITER';

  useEffect(() => {
    let mounted = true;
    const fetchHealth = async () => {
      try {
        const data = await api.getReadyHealth();
        if (mounted) {
          setHealthInfo(data);
        }
      } catch (err) {
        if (mounted) {
          setHealthInfo({ status: 'unhealthy', database: 'error' });
        }
      }
    };

    fetchHealth();
    const interval = setInterval(fetchHealth, 30000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  const isHealthy = healthInfo.status === 'healthy';

  return (
    <header className="h-16 bg-white border-b border-slate-200/90 px-4 sm:px-6 lg:px-8 flex items-center justify-between sticky top-0 z-40 transition-colors">
      
      {/* Mobile Sidebar Hamburger Toggle & Search */}
      <div className="flex items-center space-x-3 flex-1 max-w-lg">
        {onToggleMobileSidebar && (
          <button
            onClick={onToggleMobileSidebar}
            aria-label="Toggle Navigation Menu"
            className="lg:hidden p-2 rounded-xl text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition"
          >
            {mobileSidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        )}

        {/* Search Bar */}
        <div className="relative w-full max-w-xs sm:max-w-md">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search assessments, candidates..."
            className="w-full bg-slate-50 focus:bg-white border border-slate-200 focus:border-blue-500 rounded-xl pl-10 pr-4 py-2 text-xs sm:text-sm text-slate-800 placeholder-slate-400 outline-none transition shadow-sm"
          />
        </div>
      </div>

      {/* Right Controls: System Health Pill, Notifications & User Profile */}
      <div className="flex items-center space-x-2.5 sm:space-x-4">
        
        {/* System Health Status Indicator */}
        <div className="relative hidden md:block">
          <button
            onClick={() => setShowHealthTooltip(!showHealthTooltip)}
            onMouseEnter={() => setShowHealthTooltip(true)}
            onMouseLeave={() => setShowHealthTooltip(false)}
            className={`flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold border transition ${
              isHealthy
                ? 'bg-emerald-50 text-emerald-700 border-emerald-200 hover:bg-emerald-100'
                : healthInfo.status === 'checking'
                ? 'bg-slate-50 text-slate-600 border-slate-200'
                : 'bg-rose-50 text-rose-700 border-rose-200 hover:bg-rose-100'
            }`}
            title="System & Database Connectivity Status"
          >
            <span className={`w-2 h-2 rounded-full ${isHealthy ? 'bg-emerald-500 animate-pulse' : healthInfo.status === 'checking' ? 'bg-amber-400' : 'bg-rose-500'}`} />
            <span>{isHealthy ? 'System: Ready' : healthInfo.status === 'checking' ? 'Checking...' : 'System: Alert'}</span>
          </button>

          {/* Health Tooltip */}
          {showHealthTooltip && (
            <div className="absolute right-0 mt-2 w-64 bg-slate-900 text-white rounded-xl shadow-xl p-3 z-50 text-xs space-y-1.5 border border-slate-800">
              <div className="font-bold flex items-center justify-between pb-1 border-b border-slate-800 text-slate-200">
                <span>Phase 1 Health Telemetry</span>
                {isHealthy ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> : <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />}
              </div>
              <div className="flex justify-between text-slate-300">
                <span>API Gateway:</span>
                <span className="font-mono text-emerald-400">{healthInfo.status || 'healthy'}</span>
              </div>
              <div className="flex justify-between text-slate-300">
                <span>PostgreSQL DB:</span>
                <span className="font-mono text-emerald-400">{healthInfo.database || 'connected'}</span>
              </div>
              {healthInfo.environment && (
                <div className="flex justify-between text-slate-300">
                  <span>Environment:</span>
                  <span className="font-mono text-blue-400">{healthInfo.environment}</span>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Notification Bell with Badge */}
        <div className="relative">
          <button 
            onClick={() => setActiveTab('proctor')}
            className="p-2 rounded-xl text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition relative"
            title="3 Live Alerts"
          >
            <Bell className="w-4 h-4 sm:w-5 sm:h-5" />
            <span className="absolute top-1 right-1 w-3.5 h-3.5 rounded-full bg-rose-500 text-white font-bold text-[8px] flex items-center justify-center">
              3
            </span>
          </button>
        </div>

        {/* User Profile Info Chip */}
        <div className="relative">
          <button
            onClick={() => setShowDropdown(!showDropdown)}
            className="flex items-center space-x-2 p-1 rounded-xl hover:bg-slate-100 transition"
          >
            <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-blue-600 text-white flex items-center justify-center font-bold text-xs ring-2 ring-blue-100 flex-shrink-0">
              {displayName.charAt(0)}
            </div>

            <div className="text-left hidden sm:block">
              <div className="text-xs font-bold text-slate-900 leading-tight">
                {displayName}
              </div>
              <div className="text-[10px] text-slate-500 font-medium">
                {displayRole}
              </div>
            </div>

            <ChevronDown className="w-3.5 h-3.5 text-slate-400 hidden sm:block" />
          </button>

          {/* Clean Profile Dropdown */}
          {showDropdown && (
            <div className="absolute right-0 mt-2 w-56 bg-white rounded-2xl border border-slate-200 shadow-xl p-3 z-50 space-y-2">
              <div className="px-3 py-2 border-b border-slate-100">
                <div className="text-xs font-bold text-slate-900">{displayName}</div>
                <div className="text-[11px] text-slate-500 truncate">{user?.email}</div>
                <div className="mt-1">
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200">
                    Role: {displayRole}
                  </span>
                </div>
              </div>

              <div className="pt-1">
                <button
                  onClick={() => {
                    logout();
                    setShowDropdown(false);
                    setActiveTab('login');
                  }}
                  className="w-full text-left px-3 py-2 rounded-xl text-xs text-rose-600 hover:bg-rose-50 flex items-center space-x-2 transition font-semibold"
                >
                  <LogOut className="w-4 h-4" />
                  <span>Sign Out</span>
                </button>
              </div>
            </div>
          )}
        </div>

      </div>

    </header>
  );
}
