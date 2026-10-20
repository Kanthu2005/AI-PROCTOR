import React, { useState, useEffect } from 'react';
import { api } from '../api';
import { 
  UserPlus, 
  Copy, 
  Check, 
  Clock, 
  Play,
  X,
  RotateCw,
  Trash2,
  Users,
  User,
  AlertCircle,
  Mail,
  Send,
  Eye,
  CheckCircle2,
  Calendar,
  Sparkles,
  Search,
  Filter,
  ExternalLink,
  BellRing,
  Info,
  ShieldCheck,
  AlertTriangle
} from 'lucide-react';

export default function CandidateInviteModal({ assessment, onClose, onLaunchCandidateExam }) {
  const [activeTab, setActiveTab] = useState('dispatch'); // 'dispatch' | 'preview' | 'history'
  const [inviteMode, setInviteMode] = useState('bulk'); // 'bulk' | 'single'
  
  // Bulk input
  const [candidatesText, setCandidatesText] = useState(
    'alex.johnson@example.com, Alex Johnson\nsamira.patel@example.com, Samira Patel'
  );
  
  // Single input
  const [singleEmail, setSingleEmail] = useState('');
  const [singleName, setSingleName] = useState('');

  const [expiresInHours, setExpiresInHours] = useState(72);
  const [inviting, setInviting] = useState(false);
  const [actionLoadingId, setActionLoadingId] = useState(null);
  const [statusMessage, setStatusMessage] = useState(null);
  const [copiedToken, setCopiedToken] = useState(null);

  // Email Preview State
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewData, setPreviewData] = useState(null);
  const [previewFormat, setPreviewFormat] = useState('html'); // 'html' | 'text'

  // Invitation History State
  const [invitations, setInvitations] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [historySearch, setHistorySearch] = useState('');
  const [historyStatusFilter, setHistoryStatusFilter] = useState('ALL');
  const [selectedInvitationAttempts, setSelectedInvitationAttempts] = useState(null);

  // Load Invitations on Mount or Refresh
  const loadInvitations = async () => {
    if (!assessment?.id) return;
    try {
      setLoadingHistory(true);
      const data = await api.listExamInvitations(assessment.id);
      setInvitations(data || []);
    } catch (e) {
      console.warn('Falling back to legacy candidate invitations:', e);
      try {
        const fallbackData = await api.listInvitations(assessment.id);
        const mapped = (fallbackData || []).map(inv => ({
          id: inv.id,
          assessment_id: inv.assessment_id,
          recipient_email: inv.email,
          recipient_name: inv.full_name,
          status: inv.status,
          sent_at: inv.created_at,
          expires_at: inv.expires_at,
          candidate_invitation_token: inv.invitation_token,
          provider_message_id: null,
          delivery_attempts: []
        }));
        setInvitations(mapped);
      } catch {
        setInvitations([]);
      }
    } finally {
      setLoadingHistory(false);
    }
  };

  useEffect(() => {
    if (assessment) {
      loadInvitations();
      loadEmailPreview();
    }
  }, [assessment]);

  const loadEmailPreview = async () => {
    if (!assessment?.id) return;
    try {
      setPreviewLoading(true);
      const data = await api.previewExamInvitation(
        assessment.id,
        singleName || 'Alex Johnson',
        singleEmail || 'alex.johnson@example.com'
      );
      setPreviewData(data);
    } catch (err) {
      console.warn('Failed to load email preview:', err);
    } finally {
      setPreviewLoading(false);
    }
  };

  // Trigger Real Email Delivery
  const handleSendInvitations = async (e) => {
    e.preventDefault();
    try {
      setInviting(true);
      let payloadCandidates = [];

      if (inviteMode === 'bulk') {
        const lines = candidatesText.split('\n').map(l => l.trim()).filter(Boolean);
        payloadCandidates = lines.map(line => {
          const parts = line.split(',');
          return {
            email: parts[0]?.trim(),
            full_name: parts[1]?.trim() || parts[0]?.trim().split('@')[0] || 'Candidate'
          };
        }).filter(c => c.email && c.email.includes('@'));
      } else {
        if (!singleEmail) return;
        payloadCandidates = [{
          email: singleEmail.trim(),
          full_name: singleName.trim() || singleEmail.trim().split('@')[0] || 'Candidate'
        }];
      }

      if (payloadCandidates.length === 0) {
        setStatusMessage({ type: 'error', text: 'Please enter at least one valid candidate email address.' });
        return;
      }

      const res = await api.sendExamInvitations(
        assessment.id,
        payloadCandidates,
        parseInt(expiresInHours)
      );

      setStatusMessage({
        type: 'success',
        text: `Delivered ${res.total_sent} of ${res.total_processed} invitation email(s) successfully!`
      });

      if (inviteMode === 'single') {
        setSingleEmail('');
        setSingleName('');
      } else {
        setCandidatesText('');
      }

      // Refresh sent history and switch to history tab to show real delivery results
      await loadInvitations();
      setActiveTab('history');
    } catch (err) {
      setStatusMessage({ type: 'error', text: `Failed to deliver invitation emails: ${err.message}` });
    } finally {
      setInviting(false);
    }
  };

  const handleResend = async (invId) => {
    try {
      setActionLoadingId(invId);
      const res = await api.resendExamInvitation(invId, parseInt(expiresInHours));
      setStatusMessage({
        type: 'success',
        text: `Invitation refreshed and email delivered to ${res.recipient_email}!`
      });
      await loadInvitations();
    } catch (err) {
      setStatusMessage({ type: 'error', text: `Resend failed: ${err.message}` });
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleSendReminder = async (invId) => {
    try {
      setActionLoadingId(invId);
      const res = await api.remindExamInvitation(invId);
      setStatusMessage({
        type: 'success',
        text: `Exam reminder email delivered to ${res.recipient_email}!`
      });
      await loadInvitations();
    } catch (err) {
      setStatusMessage({ type: 'error', text: `Reminder delivery failed: ${err.message}` });
    } finally {
      setActionLoadingId(null);
    }
  };

  const copyToClipboard = (token) => {
    if (!token) return;
    const url = `${window.location.origin}/#/candidate_exam?token=${token}`;
    navigator.clipboard.writeText(url);
    setCopiedToken(token);
    setTimeout(() => setCopiedToken(null), 2000);
  };

  const getStatusBadge = (status) => {
    const norm = (status || '').toUpperCase();
    switch (norm) {
      case 'DELIVERED':
        return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'OPENED':
        return 'bg-purple-50 text-purple-700 border-purple-200';
      case 'SENT':
        return 'bg-blue-50 text-blue-700 border-blue-200';
      case 'PENDING':
        return 'bg-amber-50 text-amber-700 border-amber-200 animate-pulse';
      case 'FAILED':
        return 'bg-rose-50 text-rose-700 border-rose-200';
      case 'REVOKED':
      case 'EXPIRED':
        return 'bg-slate-100 text-slate-600 border-slate-300';
      default:
        return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  };

  // Filtered invitations list
  const filteredInvitations = invitations.filter(inv => {
    const matchesSearch = 
      (inv.recipient_name || '').toLowerCase().includes(historySearch.toLowerCase()) ||
      (inv.recipient_email || '').toLowerCase().includes(historySearch.toLowerCase()) ||
      (inv.provider_message_id || '').toLowerCase().includes(historySearch.toLowerCase());
    
    const matchesStatus = 
      historyStatusFilter === 'ALL' || 
      (inv.status || '').toUpperCase() === historyStatusFilter;

    return matchesSearch && matchesStatus;
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-slate-900/65 backdrop-blur-sm overflow-y-auto font-['Plus_Jakarta_Sans',sans-serif]">
      <div className="bg-white border border-slate-200 w-full max-w-4xl rounded-2xl p-5 sm:p-7 my-6 max-h-[92vh] overflow-y-auto shadow-2xl space-y-5 text-slate-800 flex flex-col">
        
        {/* Top Header */}
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 text-white flex items-center justify-center font-bold shadow-md shadow-blue-500/20">
              <Mail className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h2 className="text-lg font-extrabold text-slate-900">
                  Exam Invitation Dispatcher
                </h2>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200">
                  Transactional Email Delivery
                </span>
              </div>
              <p className="text-xs text-slate-500">
                Assessment: <strong className="text-slate-800">{assessment?.title || 'Technical Assessment'}</strong> • {assessment?.total_duration_minutes || 60} mins • {assessment?.total_marks || 100} Marks
              </p>
            </div>
          </div>
          <button 
            onClick={onClose} 
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Global Status Notification Banner */}
        {statusMessage && (
          <div className={`p-3.5 rounded-xl text-xs flex items-center justify-between border ${
            statusMessage.type === 'success' 
              ? 'bg-emerald-50 text-emerald-900 border-emerald-200' 
              : 'bg-rose-50 text-rose-900 border-rose-200'
          }`}>
            <div className="flex items-center space-x-2">
              {statusMessage.type === 'success' ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
              ) : (
                <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0" />
              )}
              <span className="font-medium">{statusMessage.text}</span>
            </div>
            <button onClick={() => setStatusMessage(null)} className="text-slate-400 hover:text-slate-700 text-xs">
              &times;
            </button>
          </div>
        )}

        {/* Navigation Tabs */}
        <div className="flex items-center space-x-2 border-b border-slate-200 pb-1">
          <button
            onClick={() => setActiveTab('dispatch')}
            className={`px-4 py-2 rounded-t-lg font-bold text-xs flex items-center space-x-2 transition border-b-2 ${
              activeTab === 'dispatch'
                ? 'border-blue-600 text-blue-600 bg-blue-50/50'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <Send className="w-3.5 h-3.5" />
            <span>Send Invitations</span>
          </button>

          <button
            onClick={() => {
              setActiveTab('preview');
              loadEmailPreview();
            }}
            className={`px-4 py-2 rounded-t-lg font-bold text-xs flex items-center space-x-2 transition border-b-2 ${
              activeTab === 'preview'
                ? 'border-blue-600 text-blue-600 bg-blue-50/50'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <Eye className="w-3.5 h-3.5" />
            <span>Email Preview</span>
          </button>

          <button
            onClick={() => {
              setActiveTab('history');
              loadInvitations();
            }}
            className={`px-4 py-2 rounded-t-lg font-bold text-xs flex items-center space-x-2 transition border-b-2 ${
              activeTab === 'history'
                ? 'border-blue-600 text-blue-600 bg-blue-50/50'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <Clock className="w-3.5 h-3.5" />
            <span>Sent History ({invitations.length})</span>
          </button>
        </div>

        {/* TAB 1: SEND INVITATIONS */}
        {activeTab === 'dispatch' && (
          <div className="space-y-4">
            
            {/* Assessment Details Summary Card */}
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5 text-xs text-slate-700 grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div>
                <span className="text-slate-400 block font-medium">Duration</span>
                <strong className="text-slate-900">{assessment?.total_duration_minutes || 60} Minutes</strong>
              </div>
              <div>
                <span className="text-slate-400 block font-medium">Marks</span>
                <strong className="text-slate-900">{assessment?.total_marks || 100} (Pass: {assessment?.passing_percentage || 50}%)</strong>
              </div>
              <div>
                <span className="text-slate-400 block font-medium">Window Start</span>
                <strong className="text-slate-900">
                  {assessment?.start_time ? new Date(assessment.start_time).toLocaleDateString() : 'Immediate'}
                </strong>
              </div>
              <div>
                <span className="text-slate-400 block font-medium">Window End</span>
                <strong className="text-slate-900">
                  {assessment?.end_time ? new Date(assessment.end_time).toLocaleDateString() : 'Open'}
                </strong>
              </div>
            </div>

            {/* Input Mode Selector */}
            <div className="flex space-x-2 bg-slate-100 p-1 rounded-xl text-xs font-bold w-fit">
              <button
                type="button"
                onClick={() => setInviteMode('bulk')}
                className={`px-3.5 py-1.5 rounded-lg flex items-center space-x-1.5 transition ${
                  inviteMode === 'bulk' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <Users className="w-3.5 h-3.5" />
                <span>Bulk Email Entry</span>
              </button>
              <button
                type="button"
                onClick={() => setInviteMode('single')}
                className={`px-3.5 py-1.5 rounded-lg flex items-center space-x-1.5 transition ${
                  inviteMode === 'single' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <User className="w-3.5 h-3.5" />
                <span>Single Candidate</span>
              </button>
            </div>

            {/* Form */}
            <form onSubmit={handleSendInvitations} className="space-y-4">
              {inviteMode === 'bulk' ? (
                <div>
                  <label className="block text-xs font-bold text-slate-800 mb-1.5">
                    Candidate Email List (One per line: <code className="text-blue-600 font-mono">email, full name</code>)
                  </label>
                  <textarea
                    rows={4}
                    required
                    value={candidatesText}
                    onChange={(e) => setCandidatesText(e.target.value)}
                    placeholder="candidate1@example.com, Alex Johnson&#10;candidate2@example.com, Samira Patel"
                    className="w-full bg-white border border-slate-300 rounded-xl p-3 text-xs text-slate-900 font-mono outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                  />
                  <span className="text-[11px] text-slate-400 mt-1 block">
                    Tip: Comma-separate email and full name. Real invitation emails will be dispatched to each address.
                  </span>
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                  <div>
                    <label className="block text-xs font-bold text-slate-800 mb-1.5">
                      Candidate Email Address *
                    </label>
                    <input
                      type="email"
                      required
                      value={singleEmail}
                      onChange={(e) => setSingleEmail(e.target.value)}
                      placeholder="candidate@example.com"
                      className="w-full bg-white border border-slate-300 rounded-xl px-3.5 py-2.5 text-xs text-slate-900 outline-none focus:border-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-slate-800 mb-1.5">
                      Full Name
                    </label>
                    <input
                      type="text"
                      value={singleName}
                      onChange={(e) => setSingleName(e.target.value)}
                      placeholder="Jane Doe"
                      className="w-full bg-white border border-slate-300 rounded-xl px-3.5 py-2.5 text-xs text-slate-900 outline-none focus:border-blue-500"
                    />
                  </div>
                </div>
              )}

              {/* Expiration and Actions */}
              <div className="flex items-center justify-between flex-wrap gap-3 pt-2">
                <div className="flex items-center space-x-2 text-xs text-slate-600">
                  <Clock className="w-4 h-4 text-blue-600" />
                  <span className="font-medium">Invitation Expiration:</span>
                  <select
                    value={expiresInHours}
                    onChange={(e) => setExpiresInHours(e.target.value)}
                    className="bg-white border border-slate-300 rounded-lg px-2.5 py-1 text-slate-800 outline-none text-xs font-semibold"
                  >
                    <option value={24}>24 Hours</option>
                    <option value={48}>48 Hours (2 Days)</option>
                    <option value={72}>72 Hours (3 Days)</option>
                    <option value={168}>7 Days</option>
                    <option value={336}>14 Days</option>
                  </select>
                </div>

                <div className="flex items-center space-x-2.5">
                  <button
                    type="button"
                    onClick={() => {
                      setActiveTab('preview');
                      loadEmailPreview();
                    }}
                    className="px-4 py-2.5 rounded-xl border border-slate-300 hover:bg-slate-50 text-slate-700 font-bold text-xs transition flex items-center space-x-1.5"
                  >
                    <Eye className="w-3.5 h-3.5 text-slate-500" />
                    <span>Preview Email</span>
                  </button>

                  <button
                    type="submit"
                    disabled={inviting}
                    className="px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs transition shadow-md shadow-blue-500/20 disabled:opacity-50 flex items-center space-x-2"
                  >
                    {inviting ? (
                      <>
                        <RotateCw className="w-4 h-4 animate-spin" />
                        <span>Dispatching Emails...</span>
                      </>
                    ) : (
                      <>
                        <Send className="w-4 h-4" />
                        <span>Send Exam Invitation(s)</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            </form>
          </div>
        )}

        {/* TAB 2: EMAIL PREVIEW */}
        {activeTab === 'preview' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between bg-slate-50 border border-slate-200 rounded-xl p-3">
              <div>
                <span className="text-[11px] font-semibold text-slate-400 block uppercase tracking-wider">Subject Line:</span>
                <strong className="text-xs text-slate-900 font-mono">
                  {previewData?.subject || `Exam Invitation: ${assessment?.title} — ProctorAI`}
                </strong>
              </div>
              <div className="flex items-center space-x-1 bg-white border border-slate-200 p-0.5 rounded-lg text-xs font-bold">
                <button
                  onClick={() => setPreviewFormat('html')}
                  className={`px-3 py-1 rounded-md transition ${previewFormat === 'html' ? 'bg-blue-600 text-white' : 'text-slate-600'}`}
                >
                  HTML Preview
                </button>
                <button
                  onClick={() => setPreviewFormat('text')}
                  className={`px-3 py-1 rounded-md transition ${previewFormat === 'text' ? 'bg-blue-600 text-white' : 'text-slate-600'}`}
                >
                  Plain Text
                </button>
              </div>
            </div>

            {previewLoading ? (
              <div className="p-12 text-center text-xs text-slate-400 flex items-center justify-center space-x-2">
                <RotateCw className="w-4 h-4 animate-spin text-blue-600" />
                <span>Rendering template preview...</span>
              </div>
            ) : previewFormat === 'html' ? (
              <div className="border border-slate-200 rounded-xl overflow-hidden shadow-inner max-h-[500px] overflow-y-auto bg-slate-100 p-4">
                <div 
                  className="bg-white rounded-xl shadow-sm overflow-hidden max-w-2xl mx-auto"
                  dangerouslySetInnerHTML={{ __html: previewData?.html || '<p>Loading preview...</p>' }} 
                />
              </div>
            ) : (
              <pre className="p-4 bg-slate-900 text-slate-100 rounded-xl text-xs font-mono whitespace-pre-wrap max-h-[450px] overflow-y-auto border border-slate-800">
                {previewData?.text || 'Loading preview...'}
              </pre>
            )}

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setActiveTab('dispatch')}
                className="px-4 py-2 rounded-xl bg-blue-600 text-white font-bold text-xs hover:bg-blue-700 transition"
              >
                Back to Send Form
              </button>
            </div>
          </div>
        )}

        {/* TAB 3: SENT HISTORY & STATUS TABLE */}
        {activeTab === 'history' && (
          <div className="space-y-3.5">
            {/* Filter Bar */}
            <div className="flex flex-col sm:flex-row items-center justify-between gap-2.5">
              <div className="relative w-full sm:w-64">
                <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Search recipient or ID..."
                  value={historySearch}
                  onChange={(e) => setHistorySearch(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl pl-8 pr-3 py-1.5 text-xs text-slate-900 outline-none focus:border-blue-500"
                />
              </div>

              <div className="flex items-center space-x-1.5 overflow-x-auto w-full sm:w-auto pb-1 sm:pb-0">
                {['ALL', 'SENT', 'DELIVERED', 'OPENED', 'PENDING', 'FAILED'].map(st => (
                  <button
                    key={st}
                    onClick={() => setHistoryStatusFilter(st)}
                    className={`px-2.5 py-1 rounded-lg text-[10px] font-bold uppercase transition ${
                      historyStatusFilter === st
                        ? 'bg-blue-600 text-white shadow-xs'
                        : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                    }`}
                  >
                    {st}
                  </button>
                ))}
                <button
                  onClick={loadInvitations}
                  title="Refresh status list"
                  className="p-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-600 transition"
                >
                  <RotateCw className={`w-3.5 h-3.5 ${loadingHistory ? 'animate-spin' : ''}`} />
                </button>
              </div>
            </div>

            {/* Table of Invitations */}
            <div className="border border-slate-200 rounded-xl overflow-hidden">
              <div className="overflow-x-auto max-h-72 overflow-y-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead className="bg-slate-50 border-b border-slate-200 sticky top-0 z-10 text-[11px] font-bold text-slate-600 uppercase tracking-wider">
                    <tr>
                      <th className="p-3">Candidate</th>
                      <th className="p-3">Delivery Status</th>
                      <th className="p-3">Provider Msg ID</th>
                      <th className="p-3">Sent At</th>
                      <th className="p-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {loadingHistory ? (
                      <tr>
                        <td colSpan={5} className="p-8 text-center text-slate-400">
                          <RotateCw className="w-4 h-4 animate-spin mx-auto mb-2 text-blue-600" />
                          Loading sent invitations...
                        </td>
                      </tr>
                    ) : filteredInvitations.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="p-8 text-center text-slate-400">
                          No matching exam invitations found.
                        </td>
                      </tr>
                    ) : (
                      filteredInvitations.map(inv => (
                        <tr key={inv.id} className="hover:bg-slate-50 transition">
                          <td className="p-3">
                            <div className="font-bold text-slate-900">{inv.recipient_name}</div>
                            <div className="text-[11px] text-slate-400 font-mono">{inv.recipient_email}</div>
                          </td>

                          <td className="p-3">
                            <span className={`px-2.5 py-0.5 rounded-full font-bold text-[10px] border ${getStatusBadge(inv.status)}`}>
                              {inv.status}
                            </span>
                            {inv.last_error && (
                              <div className="text-[10px] text-rose-600 font-medium mt-1 truncate max-w-[180px]" title={inv.last_error}>
                                Error: {inv.last_error}
                              </div>
                            )}
                          </td>

                          <td className="p-3">
                            {inv.provider_message_id ? (
                              <code className="text-[11px] text-slate-600 bg-slate-100 px-1.5 py-0.5 rounded font-mono">
                                {inv.provider_message_id.slice(0, 14)}...
                              </code>
                            ) : (
                              <span className="text-slate-400 text-[11px]">—</span>
                            )}
                          </td>

                          <td className="p-3 text-slate-500 text-[11px]">
                            {inv.sent_at ? new Date(inv.sent_at).toLocaleDateString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : 'Pending'}
                          </td>

                          <td className="p-3 text-right">
                            <div className="flex items-center justify-end space-x-1.5">
                              {/* Copy Link */}
                              {inv.candidate_invitation_token && (
                                <button
                                  onClick={() => copyToClipboard(inv.candidate_invitation_token)}
                                  className="p-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-600 transition"
                                  title="Copy secure candidate invitation URL"
                                >
                                  {copiedToken === inv.candidate_invitation_token ? (
                                    <Check className="w-3.5 h-3.5 text-emerald-600" />
                                  ) : (
                                    <Copy className="w-3.5 h-3.5" />
                                  )}
                                </button>
                              )}

                              {/* Resend Email */}
                              <button
                                onClick={() => handleResend(inv.id)}
                                disabled={actionLoadingId === inv.id}
                                className="px-2 py-1 rounded-lg bg-slate-100 hover:bg-blue-50 text-slate-600 hover:text-blue-600 border border-slate-200 text-[11px] font-bold transition flex items-center space-x-1"
                                title="Resend invitation email with refreshed token"
                              >
                                <RotateCw className={`w-3 h-3 ${actionLoadingId === inv.id ? 'animate-spin' : ''}`} />
                                <span className="hidden sm:inline">Resend</span>
                              </button>

                              {/* Send Reminder */}
                              <button
                                onClick={() => handleSendReminder(inv.id)}
                                disabled={actionLoadingId === inv.id}
                                className="px-2 py-1 rounded-lg bg-slate-100 hover:bg-amber-50 text-slate-600 hover:text-amber-700 border border-slate-200 text-[11px] font-bold transition flex items-center space-x-1"
                                title="Send reminder email"
                              >
                                <BellRing className="w-3 h-3 text-amber-600" />
                                <span className="hidden sm:inline">Remind</span>
                              </button>

                              {/* Direct Launch Preview */}
                              {inv.candidate_invitation_token && onLaunchCandidateExam && (
                                <button
                                  onClick={() => {
                                    onClose();
                                    onLaunchCandidateExam(inv.candidate_invitation_token);
                                  }}
                                  className="p-1.5 rounded-lg bg-blue-50 hover:bg-blue-100 text-blue-700 transition"
                                  title="Open exam landing with this token"
                                >
                                  <ExternalLink className="w-3.5 h-3.5" />
                                </button>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
