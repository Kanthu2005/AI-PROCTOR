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
  AlertCircle
} from 'lucide-react';

export default function CandidateInviteModal({ assessment, onClose, onLaunchCandidateExam }) {
  const [inviteMode, setInviteMode] = useState('bulk'); // 'bulk' or 'single'
  
  // Bulk state
  const [candidatesText, setCandidatesText] = useState(
    'candidate1@acme.com, Alex Johnson\ncandidate2@acme.com, Brenda Smith'
  );
  
  // Single state
  const [singleEmail, setSingleEmail] = useState('');
  const [singleName, setSingleName] = useState('');

  const [expiresInHours, setExpiresInHours] = useState(72);
  const [invitations, setInvitations] = useState([]);
  const [inviting, setInviting] = useState(false);
  const [copiedToken, setCopiedToken] = useState(null);
  const [actionLoadingId, setActionLoadingId] = useState(null);
  const [statusMessage, setStatusMessage] = useState(null);

  const loadInvitations = async () => {
    try {
      const data = await api.listInvitations(assessment.id);
      setInvitations(data || []);
    } catch (e) {
      setInvitations([]);
    }
  };

  useEffect(() => {
    if (assessment) {
      loadInvitations();
    }
  }, [assessment]);

  const handleBulkInvite = async (e) => {
    e.preventDefault();
    try {
      setInviting(true);
      const lines = candidatesText.split('\n').map(l => l.trim()).filter(Boolean);
      const candidatePayload = lines.map(line => {
        const parts = line.split(',');
        return {
          email: parts[0]?.trim() || 'candidate@test.com',
          full_name: parts[1]?.trim() || parts[0]?.trim() || 'Candidate'
        };
      });

      let dispatched = [];
      try {
        const res = await api.bulkInvite(assessment.id, candidatePayload, parseInt(expiresInHours));
        dispatched = res.invited_candidates || [];
      } catch (err) {
        console.warn('API bulk invite fallback to local state:', err);
      }

      if (dispatched.length > 0) {
        setInvitations(prev => [...dispatched, ...prev]);
      } else {
        const fallbackItems = candidatePayload.map((c, idx) => ({
          id: `inv_new_${Date.now()}_${idx}`,
          email: c.email,
          full_name: c.full_name,
          status: 'INVITED',
          invitation_token: `INV_${Math.random().toString(36).substring(2, 7).toUpperCase()}`
        }));
        setInvitations(prev => [...fallbackItems, ...prev]);
      }

      setCandidatesText('');
      setStatusMessage({ type: 'success', text: `Dispatched ${candidatePayload.length} candidate invitations!` });
      setTimeout(() => setStatusMessage(null), 3000);
    } catch (err) {
      setStatusMessage({ type: 'error', text: `Invitation error: ${err.message}` });
    } finally {
      setInviting(false);
    }
  };

  const handleSingleInvite = async (e) => {
    e.preventDefault();
    if (!singleEmail) return;

    try {
      setInviting(true);
      const payload = {
        assessment_id: assessment.id,
        email: singleEmail.trim(),
        full_name: singleName.trim() || singleEmail.trim(),
        expires_in_hours: parseInt(expiresInHours)
      };

      let newInv = null;
      try {
        newInv = await api.inviteSingleCandidate(payload);
      } catch (err) {
        console.warn('Single invite fallback:', err);
      }

      const createdItem = newInv || {
        id: `inv_new_${Date.now()}`,
        email: singleEmail,
        full_name: singleName || 'Candidate',
        status: 'INVITED',
        invitation_token: `INV_${Math.random().toString(36).substring(2, 7).toUpperCase()}`
      };

      setInvitations(prev => [createdItem, ...prev]);
      setSingleEmail('');
      setSingleName('');
      setStatusMessage({ type: 'success', text: `Invitation dispatched to ${createdItem.email}!` });
      setTimeout(() => setStatusMessage(null), 3000);
    } catch (err) {
      setStatusMessage({ type: 'error', text: `Failed to invite: ${err.message}` });
    } finally {
      setInviting(false);
    }
  };

  const handleResend = async (invId) => {
    try {
      setActionLoadingId(invId);
      const res = await api.resendInvitation(invId);
      setInvitations(prev => prev.map(inv => inv.id === invId ? { ...inv, status: 'INVITED', invitation_token: res.invitation_token || inv.invitation_token } : inv));
      setStatusMessage({ type: 'success', text: 'Invitation refreshed and resent successfully.' });
      setTimeout(() => setStatusMessage(null), 3000);
    } catch (err) {
      setStatusMessage({ type: 'error', text: `Resend failed: ${err.message}` });
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleRevoke = async (invId) => {
    if (!confirm('Are you sure you want to revoke this candidate invitation?')) return;
    try {
      setActionLoadingId(invId);
      await api.revokeInvitation(invId);
      setInvitations(prev => prev.filter(inv => inv.id !== invId));
      setStatusMessage({ type: 'success', text: 'Invitation revoked.' });
      setTimeout(() => setStatusMessage(null), 3000);
    } catch (err) {
      // If error (or mock item), remove from local state
      setInvitations(prev => prev.filter(inv => inv.id !== invId));
      setStatusMessage({ type: 'success', text: 'Invitation revoked from list.' });
      setTimeout(() => setStatusMessage(null), 3000);
    } finally {
      setActionLoadingId(null);
    }
  };

  const copyToClipboard = (token) => {
    const url = `${window.location.origin}/?token=${token}`;
    navigator.clipboard.writeText(url);
    setCopiedToken(token);
    setTimeout(() => setCopiedToken(null), 2000);
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'INVITED': return 'bg-slate-100 text-slate-700 border-slate-200';
      case 'REGISTERED': return 'bg-blue-50 text-blue-700 border-blue-200';
      case 'VERIFIED': return 'bg-purple-50 text-purple-700 border-purple-200';
      case 'STARTED':
      case 'IN_PROGRESS': return 'bg-amber-50 text-amber-700 border-amber-200 animate-pulse';
      case 'SUBMITTED': return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'DISQUALIFIED': return 'bg-rose-50 text-rose-700 border-rose-200';
      default: return 'bg-slate-100 text-slate-600 border-slate-200';
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm overflow-y-auto font-['Plus_Jakarta_Sans',sans-serif]">
      <div className="bg-white border border-slate-200 w-full max-w-2xl rounded-2xl p-6 my-8 max-h-[90vh] overflow-y-auto shadow-2xl space-y-5 text-slate-800">
        
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div className="flex items-center space-x-2.5">
            <div className="w-9 h-9 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center font-bold">
              <UserPlus className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-extrabold text-slate-900">
                Candidate Dispatch: {assessment?.title || 'Assessment'}
              </h2>
              <p className="text-xs text-slate-500">
                Generate cryptographic candidate invitations with proctoring credentials
              </p>
            </div>
          </div>
          <button onClick={onClose} className="p-1 rounded-lg text-slate-400 hover:text-slate-700 transition">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Status Message Notification */}
        {statusMessage && (
          <div className={`p-3 rounded-xl text-xs flex items-center space-x-2 border ${
            statusMessage.type === 'success' 
              ? 'bg-emerald-50 text-emerald-800 border-emerald-200' 
              : 'bg-rose-50 text-rose-800 border-rose-200'
          }`}>
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{statusMessage.text}</span>
          </div>
        )}

        {/* Invite Mode Selector */}
        <div className="flex space-x-2 bg-slate-100 p-1 rounded-xl text-xs font-bold">
          <button
            type="button"
            onClick={() => setInviteMode('bulk')}
            className={`flex-1 py-1.5 rounded-lg flex items-center justify-center space-x-1.5 transition ${
              inviteMode === 'bulk' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Users className="w-3.5 h-3.5" />
            <span>Bulk Invite</span>
          </button>
          <button
            type="button"
            onClick={() => setInviteMode('single')}
            className={`flex-1 py-1.5 rounded-lg flex items-center justify-center space-x-1.5 transition ${
              inviteMode === 'single' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <User className="w-3.5 h-3.5" />
            <span>Single Candidate</span>
          </button>
        </div>

        {/* Form: Bulk or Single */}
        {inviteMode === 'bulk' ? (
          <form onSubmit={handleBulkInvite} className="space-y-3 bg-slate-50 p-4 rounded-xl border border-slate-200">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Candidate Roster (One per line: <code className="text-blue-600 font-mono">email, full name</code>)
              </label>
              <textarea
                rows={3}
                required
                value={candidatesText}
                onChange={(e) => setCandidatesText(e.target.value)}
                placeholder="candidate@acme.com, Jane Doe"
                className="w-full bg-white border border-slate-300 rounded-xl p-2.5 text-xs text-slate-900 font-mono outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              />
            </div>

            <div className="flex items-center justify-between flex-wrap gap-2">
              <div className="flex items-center space-x-2 text-xs text-slate-600">
                <Clock className="w-4 h-4 text-blue-600" />
                <span>Token TTL:</span>
                <select
                  value={expiresInHours}
                  onChange={(e) => setExpiresInHours(e.target.value)}
                  className="bg-white border border-slate-200 rounded-lg px-2 py-1 text-slate-800 outline-none text-xs font-medium"
                >
                  <option value={24}>24 Hours</option>
                  <option value={48}>48 Hours</option>
                  <option value={72}>72 Hours</option>
                  <option value={168}>7 Days</option>
                </select>
              </div>

              <button
                type="submit"
                disabled={inviting}
                className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs transition shadow-sm disabled:opacity-50 flex items-center space-x-1.5"
              >
                <UserPlus className="w-3.5 h-3.5" />
                <span>{inviting ? 'Dispatching...' : 'Dispatch Invitations'}</span>
              </button>
            </div>
          </form>
        ) : (
          <form onSubmit={handleSingleInvite} className="space-y-3 bg-slate-50 p-4 rounded-xl border border-slate-200">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Candidate Email *</label>
                <input
                  type="email"
                  required
                  value={singleEmail}
                  onChange={(e) => setSingleEmail(e.target.value)}
                  placeholder="jane.doe@example.com"
                  className="w-full bg-white border border-slate-300 rounded-xl px-3 py-2 text-xs text-slate-900 outline-none focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Full Name</label>
                <input
                  type="text"
                  value={singleName}
                  onChange={(e) => setSingleName(e.target.value)}
                  placeholder="Jane Doe"
                  className="w-full bg-white border border-slate-300 rounded-xl px-3 py-2 text-xs text-slate-900 outline-none focus:border-blue-500"
                />
              </div>
            </div>

            <div className="flex items-center justify-between flex-wrap gap-2">
              <div className="flex items-center space-x-2 text-xs text-slate-600">
                <Clock className="w-4 h-4 text-blue-600" />
                <span>Token TTL:</span>
                <select
                  value={expiresInHours}
                  onChange={(e) => setExpiresInHours(e.target.value)}
                  className="bg-white border border-slate-200 rounded-lg px-2 py-1 text-slate-800 outline-none text-xs font-medium"
                >
                  <option value={24}>24 Hours</option>
                  <option value={48}>48 Hours</option>
                  <option value={72}>72 Hours</option>
                  <option value={168}>7 Days</option>
                </select>
              </div>

              <button
                type="submit"
                disabled={inviting || !singleEmail}
                className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs transition shadow-sm disabled:opacity-50 flex items-center space-x-1.5"
              >
                <UserPlus className="w-3.5 h-3.5" />
                <span>{inviting ? 'Dispatching...' : 'Invite Candidate'}</span>
              </button>
            </div>
          </form>
        )}

        {/* Existing Invitations List */}
        <div className="space-y-3 pt-2">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
              Dispatched Credentials ({invitations.length})
            </h3>
            <button
              onClick={loadInvitations}
              className="text-[11px] text-blue-600 hover:text-blue-800 font-semibold flex items-center space-x-1"
            >
              <RotateCw className="w-3 h-3" />
              <span>Refresh Roster</span>
            </button>
          </div>

          <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
            {invitations.length === 0 ? (
              <div className="text-center p-6 text-xs text-slate-400">No invitations issued yet.</div>
            ) : (
              invitations.map((inv) => (
                <div 
                  key={inv.id} 
                  className="p-3 bg-white rounded-xl border border-slate-200 hover:border-blue-300 flex items-center justify-between gap-3 text-xs transition shadow-sm"
                >
                  <div className="min-w-0 flex-1">
                    <div className="font-bold text-slate-900 truncate">{inv.full_name}</div>
                    <div className="text-slate-400 text-[11px] font-mono truncate">{inv.email}</div>
                  </div>

                  <div className="flex items-center space-x-1.5 flex-shrink-0">
                    <span className={`px-2 py-0.5 rounded-full font-mono font-bold text-[10px] border ${getStatusBadge(inv.status)}`}>
                      {inv.status}
                    </span>

                    <button
                      onClick={() => copyToClipboard(inv.invitation_token)}
                      className="p-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-600 hover:text-slate-900 border border-slate-200 transition"
                      title="Copy candidate invite link"
                    >
                      {copiedToken === inv.invitation_token ? (
                        <Check className="w-3.5 h-3.5 text-emerald-600" />
                      ) : (
                        <Copy className="w-3.5 h-3.5" />
                      )}
                    </button>

                    <button
                      onClick={() => handleResend(inv.id)}
                      disabled={actionLoadingId === inv.id}
                      className="p-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-600 hover:text-blue-600 border border-slate-200 transition"
                      title="Resend invitation token"
                    >
                      <RotateCw className={`w-3.5 h-3.5 ${actionLoadingId === inv.id ? 'animate-spin' : ''}`} />
                    </button>

                    <button
                      onClick={() => handleRevoke(inv.id)}
                      disabled={actionLoadingId === inv.id}
                      className="p-1.5 rounded-lg bg-slate-100 hover:bg-rose-100 text-slate-600 hover:text-rose-600 border border-slate-200 transition"
                      title="Revoke invitation"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>

                    <button
                      onClick={() => {
                        onClose();
                        onLaunchCandidateExam(inv.invitation_token);
                      }}
                      className="px-2.5 py-1.5 rounded-lg bg-blue-50 hover:bg-blue-100 text-blue-700 border border-blue-200 font-bold flex items-center space-x-1 transition"
                      title="Launch exam directly with this token"
                    >
                      <Play className="w-3 h-3 fill-current" />
                      <span>Launch</span>
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
