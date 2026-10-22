import React, { createContext, useContext, useState, useEffect } from 'react';
import { api } from '../api';

const AuthContext = createContext();

export const ROLE_OPTIONS = [
  {
    role: 'RECRUITER',
    label: 'Enterprise Recruiter',
    roleTitle: 'Hiring Lead & Talent Architect',
    desc: 'Build assessments, manage question banks, configure proctoring policies, invite candidates, review telemetry & release results.',
    badgeColor: 'indigo',
    targetTab: 'dashboard',
    accentGradient: 'from-indigo-500 via-indigo-600 to-purple-600',
    iconName: 'Briefcase'
  },
  {
    role: 'CANDIDATE',
    label: 'Candidate / Examinee',
    roleTitle: 'Assessed Technical Talent',
    desc: 'Hardware diagnostic validation, full-screen lockdown exam engine, in-browser multi-language code editor & instant autosave.',
    badgeColor: 'cyan',
    targetTab: 'candidate_portal',
    accentGradient: 'from-cyan-500 via-teal-500 to-blue-600',
    iconName: 'GraduationCap'
  },
  {
    role: 'PLATFORM_ADMIN',
    label: 'Platform Administrator',
    roleTitle: 'Platform & Organization Controller',
    desc: 'Manage organizations and recruiter accounts, monitor cluster health, audit logs, and operational configuration.',
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
