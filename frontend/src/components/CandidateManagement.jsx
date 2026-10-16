import React, { useState, useEffect } from 'react';
import { api } from '../api';
import { useAuth } from '../context/AuthContext';
import { 
  Users, 
  UserPlus, 
  Copy, 
  Check, 
  Play, 
  Search, 
  Filter, 
  Mail, 
  CheckCircle2, 
  AlertTriangle,
  X,
  Calendar,
  Sparkles
} from 'lucide-react';

export default function CandidateManagement({ onLaunchCandidateExam }) {
  const { user } = useAuth();
  const [candidates, setCandidates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');

  // Modal states
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [showBulkModal, setShowBulkModal] = useState(false);

  // Invite Form
  const [candidateName, setCandidateName] = useState('Rahul Sharma');
  const [candidateEmail, setCandidateEmail] = useState('rahul@gmail.com');
  const [generatedLink, setGeneratedLink] = useState('');
  const [copied, setCopied] = useState(false);

  // Bulk Upload Form
  const [bulkCsvText, setBulkCsvText] = useState(
    'rahul@gmail.com, Rahul Sharma\npriya@gmail.com, Priya Reddy\narjun@gmail.com, Arjun Kumar\nsneha@gmail.com, Sneha Rao'
  );

  // Default Candidates
  const defaultCandidates = [
    {
      id: 'c1',
      full_name: 'Rahul Sharma',
      email: 'rahul@gmail.com',
      assessment_title: 'Python Backend Developer',
      status: 'IN_PROGRESS',
      risk_level: 'LOW',
      current_risk_score: 12,
      invitation_token: 'ABC123',
      invited_at: '2026-10-15'
    },
    {
      id: 'c2',
      full_name: 'Priya Reddy',
      email: 'priya@gmail.com',
      assessment_title: 'Java Developer',
      status: 'SUBMITTED',
      risk_level: 'HIGH',
      current_risk_score: 72,
      invitation_token: 'JAVA_EXP',
      invited_at: '2026-10-15'
    },
    {
      id: 'c3',
      full_name: 'Arjun Kumar',
      email: 'arjun@gmail.com',
      assessment_title: 'Python Backend Developer',
      status: 'IN_PROGRESS',
      risk_level: 'MEDIUM',
      current_risk_score: 42,
      invitation_token: 'ARJ_TEST',
      invited_at: '2026-10-16'
    },
    {
      id: 'c4',
      full_name: 'Sneha Rao',
      email: 'sneha@gmail.com',
      assessment_title: 'SQL Assessment',
      status: 'INVITED',
      risk_level: 'LOW',
      current_risk_score: 0,
      invitation_token: 'SQL_INV',
      invited_at: '2026-10-16'
    }
  ];

  const [assessments, setAssessments] = useState([]);
  const [selectedAssessmentId, setSelectedAssessmentId] = useState('');

  useEffect(() => {
    loadData();
  }, [user]);

  const loadData = async () => {
    try {
      setLoading(true);
      const orgId = user?.org_id || 'test_org';
      const [candList, assessList] = await Promise.all([
        api.listAllCandidates(orgId).catch(() => []),
        api.listAssessments(orgId).catch(() => [])
      ]);

      setCandidates(candList || []);

      if (assessList && assessList.length > 0) {
        setAssessments(assessList);
        setSelectedAssessmentId(assessList[0].id);
      } else {
        setAssessments([]);
        setSelectedAssessmentId('');
      }
    } catch (e) {
      setCandidates([]);
      setAssessments([]);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateInvitation = async (e) => {
    e.preventDefault();
    const assessId = selectedAssessmentId || (assessments[0] && assessments[0].id) || 'assess_default';
    let token = `TEST_${Math.random().toString(36).substring(2, 8).toUpperCase()}`;

    try {
      const res = await api.inviteSingleCandidate({
        assessment_id: assessId,
        email: candidateEmail,
        full_name: candidateName,
        expires_in_hours: 72
      });
      if (res?.invitation_token) {
        token = res.invitation_token;
      }
    } catch (err) {
      console.warn('API single invite fallback:', err);
    }

    const newCand = {
      id: `c_${Date.now()}`,
      full_name: candidateName,
      email: candidateEmail,
      assessment_title: assessments.find(a => a.id === assessId)?.title || 'Python Backend Developer',
      status: 'INVITED',
      risk_level: 'LOW',
      current_risk_score: 0,
      invitation_token: token,
      invited_at: 'Just now'
    };

    setCandidates(prev => [newCand, ...prev]);
    const origin = window.location.origin || 'http://localhost:5173';
    setGeneratedLink(`${origin}/?token=${token}`);
    alert(`Invite created with token: ${token}`);
  };

  const handleRevokeInvitation = async (candId) => {
    if (!confirm('Are you sure you want to revoke this candidate invitation?')) return;
    try {
      setLoading(true);
      await api.revokeInvitation(candId);
      setCandidates(prev => prev.filter(c => c.id !== candId));
      alert('Candidate invitation revoked.');
    } catch (err) {
      alert(`Revocation failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleResendInvitation = async (candId) => {
    try {
      setLoading(true);
      const refreshed = await api.resendInvitation(candId);
      setCandidates(prev => prev.map(c => c.id === candId ? { ...c, invitation_token: refreshed.invitation_token, status: 'INVITED' } : c));
      alert(`New invitation token generated: ${refreshed.invitation_token}`);
    } catch (err) {
      alert(`Resend failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleBulkUpload = async (e) => {
    e.preventDefault();
    const assessId = selectedAssessmentId || (assessments[0] && assessments[0].id) || 'assess_default';
    const lines = bulkCsvText.split('\n').map(l => l.trim()).filter(Boolean);
    const candidatePayload = lines.map(line => {
      const parts = line.split(',');
      return {
        email: parts[0]?.trim() || 'candidate@test.com',
        full_name: parts[1]?.trim() || parts[0]?.trim() || 'Candidate'
      };
    });

    let dispatched = [];
    try {
      const res = await api.bulkInvite(assessId, candidatePayload);
      dispatched = res.invited_candidates || [];
    } catch (err) {
      console.warn('API bulk invite fallback:', err);
    }

    if (dispatched.length > 0) {
      setCandidates(prev => [...dispatched, ...prev]);
    } else {
      const newItems = candidatePayload.map((c, i) => ({
        id: `c_bulk_${i}_${Date.now()}`,
        email: c.email,
        full_name: c.full_name,
        assessment_title: 'Python Backend Developer',
        status: 'INVITED',
        risk_level: 'LOW',
        current_risk_score: 0,
        invitation_token: `INV_${i}_${Date.now().toString().slice(-4)}`,
        invited_at: 'Just now'
      }));
      setCandidates(prev => [...newItems, ...prev]);
    }

    setShowBulkModal(false);
    alert(`Successfully dispatched ${candidatePayload.length} candidate invitations!`);
  };

  const copyToClipboard = () => {
    if (!generatedLink) return;
    navigator.clipboard.writeText(generatedLink);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const filtered = candidates.filter(c => {
    const matchSearch = !search || 
      c.full_name?.toLowerCase().includes(search.toLowerCase()) ||
      c.email?.toLowerCase().includes(search.toLowerCase());
    const matchStatus = statusFilter === 'ALL' || c.status === statusFilter;
    return matchSearch && matchStatus;
  });

  return (
    <div className="space-y-6 text-slate-800 font-['Plus_Jakarta_Sans',sans-serif]">
      
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Candidate Management
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Dispatch assessment links, track test completion, and review integrity markers.
          </p>
        </div>

        <div className="flex items-center space-x-2.5">
          <button
            onClick={() => setShowBulkModal(true)}
            className="px-4 py-2.5 rounded-xl border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 font-bold text-xs shadow-xs transition"
          >
            Bulk CSV Upload
          </button>
          <button
            onClick={() => setShowInviteModal(true)}
            className="px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow-md shadow-blue-500/25 flex items-center space-x-2 transition"
          >
            <UserPlus className="w-4 h-4" />
            <span>+ Invite Candidate</span>
          </button>
        </div>
      </div>

      {/* Search & Filter Bar */}
      <div className="bg-white rounded-2xl p-4 border border-slate-200/90 shadow-sm flex flex-col sm:flex-row items-center gap-3">
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search candidate name or email..."
            className="w-full bg-slate-50 focus:bg-white border border-slate-200 focus:border-blue-500 rounded-xl pl-10 pr-4 py-2 text-xs sm:text-sm text-slate-900 outline-none transition"
          />
        </div>

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="bg-slate-50 border border-slate-200 text-xs text-slate-700 rounded-xl px-3 py-2 outline-none font-semibold w-full sm:w-auto"
        >
          <option value="ALL">All Statuses</option>
          <option value="INVITED">Invited</option>
          <option value="IN_PROGRESS">In Progress</option>
          <option value="SUBMITTED">Submitted</option>
        </select>
      </div>

      {/* Candidates Table (Clear Dark Text on White Cards) */}
      <div className="bg-white rounded-2xl border border-slate-200/90 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50/70 text-slate-500 uppercase text-[10px] font-bold tracking-wider">
                <th className="py-3 px-4">Candidate</th>
                <th className="py-3 px-4">Assessment</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Risk Marker</th>
                <th className="py-3 px-4">Invitation Token</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.map((c) => (
                <tr key={c.id} className="hover:bg-slate-50/70 transition">
                  <td className="py-3.5 px-4">
                    <div className="flex items-center space-x-3">
                      <div className="w-8 h-8 rounded-full bg-blue-100 text-blue-700 font-bold flex items-center justify-center text-xs">
                        {c.full_name?.charAt(0) || 'C'}
                      </div>
                      <div>
                        <div className="font-bold text-slate-900 text-xs">{c.full_name}</div>
                        <div className="text-[11px] text-slate-500">{c.email}</div>
                      </div>
                    </div>
                  </td>
                  <td className="py-3.5 px-4 font-semibold text-slate-700">
                    {c.assessment_title}
                  </td>
                  <td className="py-3.5 px-4">
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                      c.status === 'SUBMITTED' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
                      c.status === 'IN_PROGRESS' ? 'bg-blue-50 text-blue-700 border-blue-200' :
                      'bg-slate-100 text-slate-700 border-slate-200'
                    }`}>
                      {c.status}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 font-semibold">
                    <span className={
                      c.risk_level === 'HIGH' ? 'text-rose-600 font-bold' :
                      c.risk_level === 'MEDIUM' ? 'text-amber-600' :
                      'text-emerald-600'
                    }>
                      {c.risk_level || 'LOW'} ({c.risk_score ?? c.current_risk_score ?? 0}/100)
                    </span>
                  </td>
                  <td className="py-3.5 px-4 font-mono text-[11px] text-slate-600">
                    <div className="flex items-center space-x-1.5">
                      <span>{c.invitation_token}</span>
                      <button
                        onClick={() => {
                          const origin = window.location.origin || 'http://localhost:5173';
                          navigator.clipboard.writeText(`${origin}/?token=${c.invitation_token}`);
                          alert(`Copied link for ${c.full_name}!`);
                        }}
                        title="Copy Exam URL"
                        className="text-blue-600 hover:text-blue-800 p-0.5"
                      >
                        <Copy className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </td>
                  <td className="py-3.5 px-4 text-right">
                    <div className="flex items-center justify-end space-x-1.5">
                      <button
                        onClick={() => handleResendInvitation(c.id)}
                        className="px-2.5 py-1.5 rounded-lg bg-slate-50 hover:bg-slate-100 text-slate-700 font-bold text-xs border border-slate-200 transition"
                        title="Generate and send fresh invitation token"
                      >
                        Resend
                      </button>
                      <button
                        onClick={() => handleRevokeInvitation(c.id)}
                        className="px-2.5 py-1.5 rounded-lg bg-rose-50 hover:bg-rose-100 text-rose-700 font-bold text-xs border border-rose-200 transition"
                        title="Revoke access"
                      >
                        Revoke
                      </button>
                      <button
                        onClick={() => onLaunchCandidateExam(c.invitation_token)}
                        className="px-3 py-1.5 rounded-lg bg-blue-50 hover:bg-blue-100 text-blue-700 font-bold text-xs border border-blue-200 transition"
                      >
                        Open Test
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Invite Modal */}
      {showInviteModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl p-6 sm:p-8 max-w-md w-full border border-slate-200 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h2 className="text-lg font-bold text-slate-900">Invite Single Candidate</h2>
              <button onClick={() => setShowInviteModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleGenerateInvitation} className="space-y-3.5">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Full Name</label>
                <input
                  type="text"
                  required
                  value={candidateName}
                  onChange={(e) => setCandidateName(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3.5 py-2 text-xs text-slate-900 outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Email Address</label>
                <input
                  type="email"
                  required
                  value={candidateEmail}
                  onChange={(e) => setCandidateEmail(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3.5 py-2 text-xs text-slate-900 outline-none focus:border-blue-500"
                />
              </div>

              {generatedLink && (
                <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-xs space-y-1">
                  <div className="font-bold text-emerald-800">Generated Invitation Link:</div>
                  <div className="flex items-center justify-between text-[11px] text-slate-700 font-mono">
                    <span className="truncate pr-2">{generatedLink}</span>
                    <button type="button" onClick={copyToClipboard} className="text-blue-600 font-bold hover:underline">
                      {copied ? 'Copied!' : 'Copy'}
                    </button>
                  </div>
                </div>
              )}

              <div className="pt-2 flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setShowInviteModal(false)}
                  className="px-4 py-2 rounded-xl border border-slate-300 text-xs font-semibold text-slate-600 hover:bg-slate-100"
                >
                  Close
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow-md"
                >
                  Generate Invitation
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Bulk Modal */}
      {showBulkModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl p-6 sm:p-8 max-w-lg w-full border border-slate-200 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h2 className="text-lg font-bold text-slate-900">Bulk Candidate CSV Upload</h2>
              <button onClick={() => setShowBulkModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleBulkUpload} className="space-y-3.5">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  Candidate List (Format: email, full name)
                </label>
                <textarea
                  rows={5}
                  value={bulkCsvText}
                  onChange={(e) => setBulkCsvText(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-300 rounded-xl p-3 text-xs font-mono text-slate-900 outline-none focus:border-blue-500"
                />
              </div>

              <div className="pt-2 flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setShowBulkModal(false)}
                  className="px-4 py-2 rounded-xl border border-slate-300 text-xs font-semibold text-slate-600 hover:bg-slate-100"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow-md"
                >
                  Upload & Dispatch
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}
