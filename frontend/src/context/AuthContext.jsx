import React, { createContext, useContext, useState, useEffect } from 'react';
import { api } from '../api';

const AuthContext = createContext();

export const ROLE_OPTIONS = [
  {
    role: 'RECRUITER',
    label: 'Enterprise Recruiter',
    roleTitle: 'Hiring Lead & Talent Architect',
    desc: 'Build technical assessments, configure dynamic anti-cheat policies, invite candidates & evaluate scores.',
    badgeColor: 'indigo',
    targetTab: 'dashboard',
    accentGradient: 'from-indigo-500 via-indigo-600 to-purple-600',
    iconName: 'Briefcase'
  },
  {
    role: 'PROCTOR',
    label: 'Live AI Proctor',
    roleTitle: 'Surveillance & Integrity Auditor',
    desc: 'Real-time multi-candidate telemetry grid, computer vision anomaly alarms, gaze tracking & immediate flags.',
    badgeColor: 'emerald',
    targetTab: 'proctor',
    accentGradient: 'from-emerald-500 via-teal-600 to-emerald-600',
    iconName: 'Eye'
  },
  {
    role: 'QUESTION_AUTHOR',
    label: 'Question Author',
    roleTitle: 'Curriculum & Problem Bank Specialist',
    desc: 'Immutable question versioning, sandbox test case design, custom rubric definition & difficulty calibration.',
    badgeColor: 'purple',
    targetTab: 'questions',
    accentGradient: 'from-purple-500 via-fuchsia-600 to-indigo-600',
    iconName: 'FileCode2'
  },
  {
    role: 'CANDIDATE',
    label: 'Candidate / Examinee',
    roleTitle: 'Assessed Technical Talent',
    desc: 'Hardware diagnostic validation, full-screen lockdown exam engine, in-browser code runner & instant autosave.',
    badgeColor: 'cyan',
    targetTab: 'candidate_portal',
    accentGradient: 'from-cyan-500 via-teal-500 to-blue-600',
    iconName: 'GraduationCap'
  },
  {
    role: 'ORG_ADMIN',
    label: 'Organization Admin',
    roleTitle: 'Enterprise Governance Officer',
    desc: 'Tenant workspace policies, custom proctoring risk thresholds, department billing & API integrations.',
    badgeColor: 'amber',
    targetTab: 'dashboard',
    accentGradient: 'from-amber-500 via-orange-600 to-yellow-500',
    iconName: 'Building2'
  },
  {
    role: 'PLATFORM_ADMIN',
    label: 'Platform Superadmin',
    roleTitle: 'Infrastructure & Compliance Controller',
    desc: 'Global sandbox health monitoring, multi-tenant cluster isolation, security audit trails & system telemetry.',
    badgeColor: 'rose',
    targetTab: 'analytics',
    accentGradient: 'from-rose-500 via-pink-600 to-red-600',
    iconName: 'ShieldAlert'
  }
];

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const initAuth = async () => {
      const storedToken = localStorage.getItem('intellitest_token');
      const storedUser = localStorage.getItem('intellitest_user');

      if (storedToken && !storedToken.startsWith('demo_token_')) {
        try {
          const profile = await api.getMe();
          setUser(profile);
          localStorage.setItem('intellitest_user', JSON.stringify(profile));
        } catch (e) {
          console.warn('Session expired or invalid, clearing stored credentials');
          localStorage.removeItem('intellitest_token');
          localStorage.removeItem('intellitest_user');
          localStorage.removeItem('proctorai_csrf_token');
          setUser(null);
        }
      } else {
        localStorage.removeItem('intellitest_token');
        localStorage.removeItem('intellitest_user');
        localStorage.removeItem('proctorai_csrf_token');
        setUser(null);
      }
      setLoading(false);
    };

    initAuth();
  }, []);

  const login = async (email, password) => {
    const tokenRes = await api.login(email.trim(), password);
    localStorage.setItem('intellitest_token', tokenRes.access_token);
    if (tokenRes.csrf_token) {
      localStorage.setItem('proctorai_csrf_token', tokenRes.csrf_token);
    }
    const profile = {
      id: tokenRes.user_id,
      role: tokenRes.role,
      org_id: tokenRes.org_id,
      full_name: tokenRes.full_name,
      email: email.trim().toLowerCase()
    };
    setUser(profile);
    localStorage.setItem('intellitest_user', JSON.stringify(profile));
    return profile;
  };

  const register = async (userData) => {
    await api.register(userData);
    const tokenRes = await api.login(userData.email.trim(), userData.password);
    localStorage.setItem('intellitest_token', tokenRes.access_token);
    if (tokenRes.csrf_token) {
      localStorage.setItem('proctorai_csrf_token', tokenRes.csrf_token);
    }
    const profile = {
      id: tokenRes.user_id,
      role: tokenRes.role,
      org_id: tokenRes.org_id,
      full_name: tokenRes.full_name,
      email: userData.email.trim().toLowerCase()
    };
    setUser(profile);
    localStorage.setItem('intellitest_user', JSON.stringify(profile));
    return profile;
  };

  const logout = async () => {
    try {
      await api.logout();
    } catch (e) {
      // Ignore network errors on logout
    }
    localStorage.removeItem('intellitest_token');
    localStorage.removeItem('intellitest_user');
    localStorage.removeItem('proctorai_csrf_token');
    setUser(null);
  };

  const requestPasswordReset = async (email) => {
    return await api.requestPasswordReset(email);
  };

  const confirmPasswordReset = async (token, newPassword) => {
    return await api.confirmPasswordReset(token, newPassword);
  };

  return (
    <AuthContext.Provider value={{ 
      user, 
      loading, 
      login, 
      register, 
      logout, 
      requestPasswordReset,
      confirmPasswordReset
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
