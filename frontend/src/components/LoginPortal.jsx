import React, { useState } from 'react';
import { useAuth, ROLE_OPTIONS } from '../context/AuthContext';
import { 
  ShieldCheck, 
  Lock, 
  Mail, 
  ArrowRight, 
  Eye, 
  EyeOff, 
  KeyRound, 
  CheckCircle2, 
  AlertCircle, 
  Loader2, 
  ArrowLeft, 
  User, 
  Briefcase, 
  ShieldAlert, 
  Sparkles 
} from 'lucide-react';

export default function LoginPortal({ 
  onLoginSuccess, 
  onLaunchCandidateWithToken 
}) {
  const { login, register, requestPasswordReset, confirmPasswordReset } = useAuth();
  
  // Tab: 'login' | 'register' | 'candidate_token' | 'forgot_password'
  const [authTab, setAuthTab] = useState('login');
  
  // Email / Password Sign In Form
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);

  // Registration Form
  const [regFullName, setRegFullName] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [regRole, setRegRole] = useState('RECRUITER');

  // Candidate Token
  const [candidateToken, setCandidateToken] = useState('');

  // Password Reset State
  const [resetEmail, setResetEmail] = useState('');
  const [resetToken, setResetToken] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [resetStep, setResetStep] = useState(1);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  const validateEmail = (val) => {
    return /\S+@\S+\.\S+/.test(val);
  };

  // Handle standard email + password sign in
  const handleLoginSubmit = async (e) => {
    if (e) e.preventDefault();
    if (!email.trim() || !validateEmail(email)) {
      setError('Please provide a valid email address.');
      return;
    }
    if (!password) {
      setError('Password is required.');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const profile = await login(email.trim(), password);
      setSuccessMsg(`Welcome, ${profile.full_name || profile.email}! Redirecting...`);
      setTimeout(() => {
        if (onLoginSuccess) {
          onLoginSuccess(profile.role);
        }
      }, 300);
    } catch (err) {
      setError(err.message || 'Invalid email or password.');
    } finally {
      setLoading(false);
    }
  };

  // Handle new user self-service registration
  const handleRegisterSubmit = async (e) => {
    if (e) e.preventDefault();
    if (!regFullName.trim()) {
      setError('Full name is required.');
      return;
    }
    if (!regEmail.trim() || !validateEmail(regEmail)) {
      setError('Please provide a valid email address.');
      return;
    }
    if (!regPassword || regPassword.length < 6) {
      setError('Password must be at least 6 characters long.');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const profile = await register({
        full_name: regFullName.trim(),
        email: regEmail.trim().toLowerCase(),
        password: regPassword,
        role: regRole
      });
      setSuccessMsg(`Account created successfully! Welcome, ${profile.full_name || profile.email}!`);
      setTimeout(() => {
        if (onLoginSuccess) {
          onLoginSuccess(profile.role);
        }
      }, 300);
    } catch (err) {
      setError(err.message || 'Registration failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Handle Candidate Token Verification & Direct Exam Launch
  const handleTokenSubmit = (e) => {
    if (e) e.preventDefault();
    if (!candidateToken.trim()) {
      setError('Please enter your assessment invitation token.');
      return;
    }
    setError(null);
    if (onLaunchCandidateWithToken) {
      onLaunchCandidateWithToken(candidateToken.trim().toUpperCase());
    }
  };

  // Handle Forgot Password Request
  const handleRequestReset = async (e) => {
    if (e) e.preventDefault();
    if (!resetEmail.trim() || !validateEmail(resetEmail)) {
      setError('Please enter your registered email address.');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const res = await requestPasswordReset(resetEmail.trim());
      setSuccessMsg(res.message || 'Reset code sent to your email.');
      if (res.debug_reset_token) {
        setResetToken(res.debug_reset_token);
      }
      setResetStep(2);
    } catch (err) {
      setError(err.message || 'Failed to request password reset.');
    } finally {
      setLoading(false);
    }
  };

  // Handle Confirm Password Reset
  const handleConfirmReset = async (e) => {
    if (e) e.preventDefault();
    if (!resetToken.trim()) {
      setError('Reset token is required.');
      return;
    }
    if (!newPassword || newPassword.length < 8) {
      setError('New password must be at least 8 characters.');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      await confirmPasswordReset(resetToken.trim(), newPassword);
      setSuccessMsg('Password has been successfully updated! Please sign in.');
      setTimeout(() => {
        setAuthTab('login');
        setResetStep(1);
        setEmail(resetEmail);
        setPassword('');
        setError(null);
      }, 1000);
    } catch (err) {
      setError(err.message || 'Failed to update password.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#070b19] flex flex-col lg:flex-row font-['Plus_Jakarta_Sans',sans-serif]">
      
      {/* LEFT COLUMN: BRAND HERO & SECURITY VALUE PROPOSITION */}
      <div className="lg:w-1/2 p-8 sm:p-12 lg:p-16 flex flex-col justify-between relative overflow-hidden bg-gradient-to-br from-[#0c152e] via-[#091024] to-[#060a17] border-b lg:border-b-0 lg:border-r border-slate-800">
        
        {/* Subtle Ambient Background Gradients */}
        <div className="absolute -top-32 -left-32 w-96 h-96 bg-blue-600/15 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-32 -right-32 w-96 h-96 bg-indigo-600/15 rounded-full blur-3xl pointer-events-none" />

        {/* Top Logo */}
        <div className="relative z-10 flex items-center space-x-3">
          <div className="h-11 w-11 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center text-white shadow-lg shadow-blue-500/30">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <span className="text-2xl font-black tracking-tight text-white">
              Proctor<span className="text-blue-400">AI</span>
            </span>
            <span className="text-[10px] font-bold text-slate-400 block -mt-1 tracking-wider uppercase">
              Autonomous Talent Integrity Cloud
            </span>
          </div>
        </div>

        {/* Hero Value Proposition */}
        <div className="relative z-10 my-10 space-y-5 max-w-lg">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-400/20 text-blue-300 text-xs font-semibold">
            <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
            <span>High-Integrity Online Assessment Engine</span>
          </div>
          
          <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight leading-tight text-white">
            Secure Talent Evaluation at Global Scale.
          </h1>

          <p className="text-sm sm:text-base text-slate-300 font-normal leading-relaxed">
            AI-powered continuous gaze tracking, browser lockdown, multi-face computer vision surveillance, and isolated sandboxes.
          </p>

          <div className="grid grid-cols-2 gap-3 pt-2">
            <div className="p-3.5 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-sm">
              <div className="text-xl font-black text-white">99.8%</div>
              <div className="text-[11px] text-slate-400 font-medium">Anti-Cheat Verification</div>
            </div>
            <div className="p-3.5 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-sm">
              <div className="text-xl font-black text-white">&lt; 3.0s</div>
              <div className="text-[11px] text-slate-400 font-medium">Sandbox Execution Bounds</div>
            </div>
          </div>
        </div>

        {/* Security Compliance Footnote */}
        <div className="relative z-10 pt-4 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
          <span>OWASP & RBAC Compliant</span>
          <span>Argon2id Encrypted</span>
        </div>
      </div>

      {/* RIGHT COLUMN: INTERACTIVE AUTH & WORKSPACE GATEWAY */}
      <div className="lg:w-1/2 flex items-center justify-center p-6 sm:p-10 lg:p-14 bg-white min-h-screen">
        <div className="w-full max-w-md">
          
          {/* Header Title */}
          <div className="mb-6">
            <h2 className="text-2xl font-bold text-slate-900 tracking-tight">
              {authTab === 'forgot_password' && 'Reset Password'}
              {authTab === 'login' && 'Sign In to ProctorAI'}
              {authTab === 'register' && 'Create Your Account'}
              {authTab === 'candidate_token' && 'Candidate Exam Access'}
            </h2>
            <p className="text-xs text-slate-500 mt-1">
              {authTab === 'forgot_password' && 'Enter your email to receive a password reset token.'}
              {authTab === 'login' && 'Enter your credentials to access your organization workspace.'}
              {authTab === 'register' && 'Set up your account and select your role to get started.'}
              {authTab === 'candidate_token' && 'Enter your single-use invitation token to start your exam.'}
            </p>
          </div>

          {/* TAB SELECTOR */}
          {authTab !== 'forgot_password' && (
            <div className="flex p-1 bg-slate-100 rounded-2xl mb-6">
              <button
                type="button"
                onClick={() => {
                  setAuthTab('login');
                  setError(null);
                  setSuccessMsg(null);
                }}
                className={`flex-1 py-2 rounded-xl text-xs font-bold transition ${
                  authTab === 'login'
                    ? 'bg-white text-slate-900 shadow-sm'
                    : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                Sign In
              </button>

              <button
                type="button"
                onClick={() => {
                  setAuthTab('register');
                  setError(null);
                  setSuccessMsg(null);
                }}
                className={`flex-1 py-2 rounded-xl text-xs font-bold transition ${
                  authTab === 'register'
                    ? 'bg-white text-slate-900 shadow-sm'
                    : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                Register
              </button>

              <button
                type="button"
                onClick={() => {
                  setAuthTab('candidate_token');
                  setError(null);
                  setSuccessMsg(null);
                }}
                className={`flex-1 py-2 rounded-xl text-xs font-bold transition ${
                  authTab === 'candidate_token'
                    ? 'bg-white text-slate-900 shadow-sm'
                    : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                Exam Code
              </button>
            </div>
          )}

          {/* ERROR ALERT BANNER */}
          {error && (
            <div className="mb-4 p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs font-semibold flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* SUCCESS ALERT BANNER */}
          {successMsg && (
            <div className="mb-4 p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs font-semibold flex items-center space-x-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
              <span>{successMsg}</span>
            </div>
          )}

          {/* TAB 1: CANDIDATE EXAM CODE */}
          {authTab === 'candidate_token' && (
            <form onSubmit={handleTokenSubmit} className="space-y-4">
              <div className="p-3.5 bg-blue-50 border border-blue-200 rounded-2xl text-xs text-blue-900 space-y-1">
                <div className="font-bold flex items-center space-x-1.5">
                  <KeyRound className="w-4 h-4 text-blue-600" />
                  <span>Examinee Single-Use Invitation Code</span>
                </div>
                <p className="text-[11px] text-blue-700 leading-relaxed">
                  Enter your invitation token to start live camera verification, hardware diagnostics, and assessment instructions.
                </p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Assessment Token
                </label>
                <input
                  type="text"
                  required
                  value={candidateToken}
                  onChange={(e) => setCandidateToken(e.target.value)}
                  placeholder="Enter assessment invitation token"
                  className="w-full bg-slate-50 border border-slate-300 focus:border-blue-600 focus:bg-white rounded-xl px-4 py-2.5 text-sm text-slate-900 font-mono outline-none transition"
                />
              </div>

              <button
                type="submit"
                className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 rounded-xl shadow-lg shadow-blue-600/20 text-xs flex items-center justify-center space-x-2 transition"
              >
                <span>Verify Token & Launch Assessment</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </form>
          )}

          {/* TAB 2: REGISTER ACCOUNT */}
          {authTab === 'register' && (
            <form onSubmit={handleRegisterSubmit} className="space-y-3.5">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Full Name
                </label>
                <div className="relative">
                  <input
                    type="text"
                    required
                    value={regFullName}
                    onChange={(e) => setRegFullName(e.target.value)}
                    placeholder="e.g. John Doe"
                    className="w-full bg-slate-50 border border-slate-300 focus:border-blue-600 focus:bg-white rounded-xl pl-9 pr-3.5 py-2.5 text-sm text-slate-900 placeholder-slate-400 outline-none transition"
                  />
                  <User className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Email Address
                </label>
                <div className="relative">
                  <input
                    type="email"
                    required
                    value={regEmail}
                    onChange={(e) => setRegEmail(e.target.value)}
                    placeholder="name@company.com"
                    className="w-full bg-slate-50 border border-slate-300 focus:border-blue-600 focus:bg-white rounded-xl pl-9 pr-3.5 py-2.5 text-sm text-slate-900 placeholder-slate-400 outline-none transition"
                  />
                  <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Password
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    value={regPassword}
                    onChange={(e) => setRegPassword(e.target.value)}
                    placeholder="Create a strong password (6+ chars)"
                    className="w-full bg-slate-50 border border-slate-300 focus:border-blue-600 focus:bg-white rounded-xl pl-9 pr-10 py-2.5 text-sm text-slate-900 placeholder-slate-400 outline-none transition"
                  />
                  <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-3 text-slate-400 hover:text-slate-600"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Account Role
                </label>
                <select
                  value={regRole}
                  onChange={(e) => setRegRole(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-300 focus:border-blue-600 focus:bg-white rounded-xl px-3.5 py-2.5 text-sm text-slate-900 outline-none transition"
                >
                  {ROLE_OPTIONS.map((opt) => (
                    <option key={opt.role} value={opt.role}>
                      {opt.label} ({opt.role})
                    </option>
                  ))}
                </select>
                <p className="text-[11px] text-slate-500 mt-1">
                  {ROLE_OPTIONS.find((r) => r.role === regRole)?.desc}
                </p>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-bold py-3 rounded-xl shadow-lg shadow-blue-600/20 text-xs flex items-center justify-center space-x-2 transition mt-2"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Creating Account...</span>
                  </>
                ) : (
                  <>
                    <span>Create Account & Sign In</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>

              <div className="text-center text-xs text-slate-500 pt-2">
                Already have an account?{' '}
                <button
                  type="button"
                  onClick={() => setAuthTab('login')}
                  className="text-blue-600 font-bold hover:underline"
                >
                  Sign In
                </button>
              </div>
            </form>
          )}

          {/* TAB 3: SIGN IN (EMAIL + PASSWORD) */}
          {authTab === 'login' && (
            <form onSubmit={handleLoginSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Email Address
                </label>
                <div className="relative">
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="Enter your registered email"
                    className="w-full bg-slate-50 border border-slate-300 focus:border-blue-600 focus:bg-white rounded-xl pl-9 pr-3.5 py-2.5 text-sm text-slate-900 placeholder-slate-400 outline-none transition"
                  />
                  <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                </div>
              </div>

              <div>
                <div className="flex justify-between items-center mb-1.5">
                  <label className="text-xs font-semibold text-slate-700">
                    Password
                  </label>
                  <button
                    type="button"
                    onClick={() => {
                      setAuthTab('forgot_password');
                      setError(null);
                      setSuccessMsg(null);
                    }}
                    className="text-xs font-semibold text-blue-600 hover:text-blue-800"
                  >
                    Forgot password?
                  </button>
                </div>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full bg-slate-50 border border-slate-300 focus:border-blue-600 focus:bg-white rounded-xl pl-9 pr-10 py-2.5 text-sm text-slate-900 placeholder-slate-400 outline-none transition"
                  />
                  <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-3 text-slate-400 hover:text-slate-600"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div className="flex items-center justify-between text-xs">
                <label className="flex items-center space-x-2 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className="w-4 h-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="text-slate-600 font-medium">Remember this browser</span>
                </label>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-bold py-3 rounded-xl shadow-lg shadow-blue-600/20 text-xs flex items-center justify-center space-x-2 transition"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Signing in...</span>
                  </>
                ) : (
                  <>
                    <span>Sign In to Workspace</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>

              <div className="text-center text-xs text-slate-500 pt-2">
                Don't have an account yet?{' '}
                <button
                  type="button"
                  onClick={() => setAuthTab('register')}
                  className="text-blue-600 font-bold hover:underline"
                >
                  Create Account
                </button>
              </div>
            </form>
          )}

          {/* TAB 4: PASSWORD RESET FLOW */}
          {authTab === 'forgot_password' && (
            <div className="space-y-4">
              <button
                type="button"
                onClick={() => {
                  setAuthTab('login');
                  setError(null);
                  setSuccessMsg(null);
                }}
                className="inline-flex items-center space-x-1.5 text-xs text-blue-600 hover:text-blue-800 font-semibold"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                <span>Back to Sign In</span>
              </button>

              {resetStep === 1 ? (
                <form onSubmit={handleRequestReset} className="space-y-4">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                      Account Email Address
                    </label>
                    <input
                      type="email"
                      required
                      value={resetEmail}
                      onChange={(e) => setResetEmail(e.target.value)}
                      placeholder="Enter your registered email"
                      className="w-full bg-slate-50 border border-slate-300 focus:border-blue-600 focus:bg-white rounded-xl px-3.5 py-2.5 text-sm text-slate-900 placeholder-slate-400 outline-none transition"
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-bold py-3 rounded-xl shadow-lg shadow-blue-600/20 text-xs flex items-center justify-center space-x-2 transition"
                  >
                    {loading ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        <span>Sending Request...</span>
                      </>
                    ) : (
                      <>
                        <span>Request Password Reset Token</span>
                        <ArrowRight className="w-4 h-4" />
                      </>
                    )}
                  </button>
                </form>
              ) : (
                <form onSubmit={handleConfirmReset} className="space-y-4">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                      Reset Token
                    </label>
                    <input
                      type="text"
                      required
                      value={resetToken}
                      onChange={(e) => setResetToken(e.target.value)}
                      placeholder="Paste reset token from email"
                      className="w-full bg-slate-50 border border-slate-300 focus:border-blue-600 focus:bg-white rounded-xl px-3.5 py-2.5 text-sm font-mono text-slate-900 outline-none transition"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                      New Password (8+ characters)
                    </label>
                    <input
                      type="password"
                      required
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      placeholder="Enter your new secure password"
                      className="w-full bg-slate-50 border border-slate-300 focus:border-blue-600 focus:bg-white rounded-xl px-3.5 py-2.5 text-sm text-slate-900 outline-none transition"
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white font-bold py-3 rounded-xl shadow-lg shadow-emerald-600/20 text-xs flex items-center justify-center space-x-2 transition"
                  >
                    {loading ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        <span>Updating Password...</span>
                      </>
                    ) : (
                      <>
                        <span>Confirm & Reset Password</span>
                        <CheckCircle2 className="w-4 h-4" />
                      </>
                    )}
                  </button>
                </form>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
