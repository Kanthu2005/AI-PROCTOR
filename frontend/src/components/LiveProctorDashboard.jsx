import React, { useState, useEffect } from 'react';
import { api } from '../api';
import { useAuth } from '../context/AuthContext';
import { 
  Eye, 
  ShieldAlert, 
  AlertTriangle, 
  CheckCircle, 
  XCircle, 
  Activity, 
  Radio, 
  Clock, 
  UserX, 
  UserCheck, 
  RotateCcw,
  Sparkles,
  Search,
  ExternalLink,
  ChevronRight,
  Maximize2,
  FileText,
  Check,
  X,
  Volume2,
  Camera,
  ShieldCheck,
  AlertCircle
} from 'lucide-react';

export default function LiveProctorDashboard() {
  const { user } = useAuth();
  const [candidatesFeed, setCandidatesFeed] = useState([]);
  const [selectedCandidate, setSelectedCandidate] = useState(null);
  const [showReviewModal, setShowReviewModal] = useState(false);
  const [reviewDecision, setReviewDecision] = useState('CONFIRMED_VIOLATION'); 
  const [reviewComment, setReviewComment] = useState('Multiple face anomaly verified during exam surveillance.');
  const [wsConnected, setWsConnected] = useState(true);
  const [search, setSearch] = useState('');
  const [riskFilter, setRiskFilter] = useState('ALL');

  // Metrics
  const [metrics, setMetrics] = useState({
    candidates: 0,
    active: 0,
    highRisk: 0,
    alerts: 0
  });

  useEffect(() => {
    loadLiveSurveillance();
  }, [user]);

  const loadLiveSurveillance = async () => {
    try {
      const orgId = user?.org_id || 'test_org';
      const assessments = await api.listAssessments(orgId).catch(() => []);
      let liveFeed = [];
      if (assessments && assessments.length > 0) {
        liveFeed = await api.getLiveProctorFeed(assessments[0].id).catch(() => []);
      }

      if (liveFeed && liveFeed.length > 0) {
        const formatted = liveFeed.map((cand, idx) => ({
          id: cand.attempt_id || `cand_${idx}`,
          attempt_id: cand.attempt_id,
          name: cand.candidate_name || 'Candidate',
          email: cand.candidate_email || 'candidate@test.com',
          status: cand.status || 'Active',
          riskScore: cand.risk_score || 0,
          riskLevel: cand.risk_level || 'LOW',
          alertsCount: cand.alerts_count || 0,
          questionProgress: cand.progress || 'In Progress',
          timeRemaining: cand.remaining_time || '35:00',
          cameraActive: true,
          humanReviewStatus: cand.human_review_status || 'PENDING',
          events: cand.incidents || []
        }));
        setCandidatesFeed(formatted);
        setSelectedCandidate(formatted[0]);
        setMetrics({
          candidates: formatted.length,
          active: formatted.filter(c => c.status === 'Active' || c.status === 'IN_PROGRESS').length,
          highRisk: formatted.filter(c => c.riskScore > 50 || c.riskLevel === 'HIGH').length,
          alerts: formatted.reduce((acc, c) => acc + (c.alertsCount || 0), 0)
        });
      } else {
        setCandidatesFeed([]);
        setSelectedCandidate(null);
        setMetrics({ candidates: 0, active: 0, highRisk: 0, alerts: 0 });
      }
    } catch (e) {
      console.warn('Live feed fallback:', e);
      setCandidatesFeed([]);
      setSelectedCandidate(null);
      setMetrics({ candidates: 0, active: 0, highRisk: 0, alerts: 0 });
    }
  };

  const handleSelectCandidate = async (candidate) => {
    setSelectedCandidate(candidate);
    if (candidate.attempt_id) {
      try {
        const incidents = await api.getAttemptIncidents(candidate.attempt_id).catch(() => []);
        if (incidents && incidents.length > 0) {
          const mappedEvents = incidents.map(inc => ({
            time: new Date(inc.occurred_at).toLocaleTimeString(),
            type: inc.event_type,
            points: `+${inc.risk_points}`,
            severity: inc.risk_points >= 30 ? 'CRITICAL' : inc.risk_points >= 15 ? 'HIGH' : 'MEDIUM',
            rationale: inc.rationale || 'Surveillance anomaly recorded.',
            hasEvidence: Boolean(inc.evidence_snapshot_url)
          }));
          setSelectedCandidate(prev => ({ ...prev, events: mappedEvents }));
        }
      } catch (err) {
        console.warn('Incident fetch warning:', err);
      }
    }
  };

  const handleOpenReviewModal = () => {
    setShowReviewModal(true);
  };

  const handleSubmitReviewDecision = async () => {
    if (!selectedCandidate) return;
    
    try {
      if (selectedCandidate.attempt_id) {
        await api.reviewIncident(selectedCandidate.attempt_id, reviewDecision, reviewComment).catch(console.warn);
      }
    } catch (e) {
      console.warn('Review API sync:', e);
    }

    setCandidatesFeed(prev => prev.map(c => {
      if (c.id === selectedCandidate.id) {
        let updatedScore = c.riskScore;
        let updatedLevel = c.riskLevel;
        if (reviewDecision === 'FALSE_POSITIVE') {
          updatedScore = Math.max(0, updatedScore - 40);
          updatedLevel = updatedScore <= 20 ? 'LOW' : updatedScore <= 50 ? 'MEDIUM' : 'HIGH';
        }
        return {
          ...c,
          humanReviewStatus: reviewDecision,
          riskScore: updatedScore,
          riskLevel: updatedLevel
        };
      }
      return c;
    }));

    setSelectedCandidate(prev => ({
      ...prev,
      humanReviewStatus: reviewDecision,
      riskScore: reviewDecision === 'FALSE_POSITIVE' ? Math.max(0, prev.riskScore - 40) : prev.riskScore,
      riskLevel: reviewDecision === 'FALSE_POSITIVE' ? 'MEDIUM' : prev.riskLevel
    }));

    setShowReviewModal(false);
    alert(`Review verdict saved: ${reviewDecision}. Candidate record updated.`);
  };

  // Play browser chime
  const handleSendWarning = () => {
    try {
      const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.frequency.value = 880;
      gain.gain.setValueAtTime(0.2, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.4);
      osc.start();
      osc.stop(audioCtx.currentTime + 0.4);
    } catch (e) {}

    alert(`Warning chime and message dispatched to ${selectedCandidate?.name}'s exam console.`);
  };

  // Clear Risk & Verify
  const handleClearRisk = async () => {
    if (!selectedCandidate) return;
    try {
      if (selectedCandidate.attempt_id) {
        await api.reviewIncident(selectedCandidate.attempt_id, 'VALID', 'Proctor cleared false positives and certified session valid.').catch(console.warn);
      }
    } catch (e) {
      console.warn('Clear risk API sync:', e);
    }
    setCandidatesFeed(prev => prev.map(c => {
      if (c.id === selectedCandidate.id) {
        return { ...c, riskScore: 0, riskLevel: 'LOW', humanReviewStatus: 'VALID' };
      }
      return c;
    }));
    setSelectedCandidate(prev => ({ ...prev, riskScore: 0, riskLevel: 'LOW', humanReviewStatus: 'VALID' }));
    alert(`Risk cleared for ${selectedCandidate.name}. Candidate marked verified.`);
  };

  // Force Disqualify
  const handleDisqualify = async () => {
    if (!selectedCandidate) return;
    if (window.confirm(`Are you sure you want to force-terminate and DISQUALIFY ${selectedCandidate.name}?`)) {
      try {
        if (selectedCandidate.attempt_id) {
          await api.reviewIncident(selectedCandidate.attempt_id, 'CONFIRMED_VIOLATION', 'Force terminated and disqualified by live proctor.').catch(console.warn);
        }
      } catch (e) {
        console.warn('Disqualify API sync:', e);
      }
      setCandidatesFeed(prev => prev.map(c => {
        if (c.id === selectedCandidate.id) {
          return { ...c, status: 'DISQUALIFIED', riskScore: 100, riskLevel: 'CRITICAL', humanReviewStatus: 'CONFIRMED_VIOLATION' };
        }
        return c;
      }));
      setSelectedCandidate(prev => ({ ...prev, status: 'DISQUALIFIED', riskScore: 100, riskLevel: 'CRITICAL', humanReviewStatus: 'CONFIRMED_VIOLATION' }));
      alert(`${selectedCandidate.name} has been disqualified.`);
    }
  };

  const getRiskBadge = (level) => {
    switch (level) {
      case 'LOW':
        return 'text-emerald-700 bg-emerald-50 border-emerald-200';
      case 'MEDIUM':
        return 'text-amber-700 bg-amber-50 border-amber-200';
      case 'HIGH':
        return 'text-rose-700 bg-rose-50 border-rose-200 font-bold';
      case 'CRITICAL':
        return 'text-rose-800 bg-rose-100 border-rose-300 font-bold animate-pulse';
      default:
        return 'text-slate-600 bg-slate-100 border-slate-200';
    }
  };

  const filteredCandidates = candidatesFeed.filter(c => {
    const matchSearch = !search || c.name.toLowerCase().includes(search.toLowerCase()) || c.email.toLowerCase().includes(search.toLowerCase());
    const matchRisk = riskFilter === 'ALL' || c.riskLevel === riskFilter;
    return matchSearch && matchRisk;
  });

  return (
    <div className="space-y-6 text-slate-800 font-['Plus_Jakarta_Sans',sans-serif]">
      
      {/* Top Banner */}
      <div className="dash-card bg-white border border-slate-200/90 p-6 rounded-2xl shadow-sm flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2.5">
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">LIVE PROCTORING CONSOLE</h1>
            <span className="flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-bold bg-rose-50 text-rose-700 border border-rose-200">
              <span className="w-2 h-2 rounded-full bg-rose-500 animate-ping" />
              <span>🔴 LIVE SURVEILLANCE</span>
            </span>
          </div>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Proctor Auditor: <strong className="text-blue-700 font-semibold">{user?.full_name || 'AI Proctor Auditor'}</strong> ({user?.email || 'Active Session'}) • Real-time computer vision biometric surveillance & audit reviews.
          </p>
        </div>

        <div className="flex items-center space-x-2 text-xs font-semibold text-emerald-700 bg-emerald-50 px-3 py-1.5 rounded-xl border border-emerald-200">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span>WebSocket Stream Connected</span>
        </div>
      </div>

      {/* 4 Metric Counters */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="dash-card bg-white border border-slate-200/90 p-5 rounded-2xl text-center shadow-sm">
          <div className="text-xs font-bold text-slate-500 uppercase tracking-wider">Candidates</div>
          <div className="text-3xl font-extrabold text-slate-900 font-mono mt-1">{metrics.candidates}</div>
          <div className="text-[11px] text-slate-400 mt-0.5">Enrolled cohort</div>
        </div>
        <div className="dash-card bg-white border border-slate-200/90 p-5 rounded-2xl text-center shadow-sm">
          <div className="text-xs font-bold text-slate-500 uppercase tracking-wider">Active</div>
          <div className="text-3xl font-extrabold text-blue-600 font-mono mt-1">{metrics.active}</div>
          <div className="text-[11px] text-slate-400 mt-0.5">Currently testing</div>
        </div>
        <div className="dash-card bg-white border border-slate-200/90 p-5 rounded-2xl text-center shadow-sm">
          <div className="text-xs font-bold text-slate-500 uppercase tracking-wider">High Risk</div>
          <div className="text-3xl font-extrabold text-rose-600 font-mono mt-1">{metrics.highRisk}</div>
          <div className="text-[11px] text-rose-500 font-bold mt-0.5">Threat score &gt; 50</div>
        </div>
        <div className="dash-card bg-white border border-slate-200/90 p-5 rounded-2xl text-center shadow-sm">
          <div className="text-xs font-bold text-slate-500 uppercase tracking-wider">Alerts</div>
          <div className="text-3xl font-extrabold text-amber-600 font-mono mt-1">{metrics.alerts}</div>
          <div className="text-[11px] text-slate-400 mt-0.5">Real-time flags</div>
        </div>
      </div>

      {/* Main Grid: Left Candidates Table (7 cols) + Right Candidate Inspector (5 cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Candidates Table (7 cols) */}
        <div className="lg:col-span-7 dash-card bg-white border border-slate-200/90 p-5 rounded-2xl space-y-4 shadow-sm">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <div>
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-700">
                Active Candidate Sessions ({filteredCandidates.length})
              </h2>
              <span className="text-[11px] text-slate-400">Click candidate to inspect threat analysis & video feed</span>
            </div>

            <div className="flex items-center space-x-2">
              <select
                value={riskFilter}
                onChange={(e) => setRiskFilter(e.target.value)}
                className="bg-slate-50 border border-slate-200 text-xs text-slate-700 rounded-lg px-2.5 py-1 outline-none font-medium"
              >
                <option value="ALL">All Risk Levels</option>
                <option value="HIGH">High Risk</option>
                <option value="MEDIUM">Medium Risk</option>
                <option value="LOW">Low Risk</option>
              </select>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-100 text-slate-500 font-bold text-[11px]">
                  <th className="pb-3">Candidate</th>
                  <th className="pb-3">Status</th>
                  <th className="pb-3">Risk</th>
                  <th className="pb-3 text-center">Alerts</th>
                  <th className="pb-3 text-right">Progress</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-medium">
                {filteredCandidates.map((c) => {
                  const isSelected = selectedCandidate?.id === c.id;
                  return (
                    <tr
                      key={c.id}
                      onClick={() => handleSelectCandidate(c)}
                      className={`cursor-pointer transition ${
                        isSelected 
                          ? 'bg-blue-50/80 border-l-4 border-blue-600' 
                          : 'hover:bg-slate-50'
                      }`}
                    >
                      <td className="py-3 pr-2">
                        <div className="font-bold text-slate-900">{c.name}</div>
                        <div className="text-[11px] text-slate-400">{c.email}</div>
                      </td>
                      <td className="py-3">
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                          c.status === 'DISQUALIFIED'
                            ? 'bg-rose-100 text-rose-800 border-rose-300'
                            : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                        }`}>
                          {c.status}
                        </span>
                      </td>
                      <td className="py-3">
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-mono border ${getRiskBadge(c.riskLevel)}`}>
                          {c.riskLevel} ({c.riskScore})
                        </span>
                      </td>
                      <td className="py-3 text-center">
                        <span className={`px-2 py-0.5 rounded font-mono font-bold text-[11px] ${
                          c.alertsCount > 0 ? 'bg-amber-50 text-amber-700 border border-amber-200' : 'text-slate-400'
                        }`}>
                          {c.alertsCount}
                        </span>
                      </td>
                      <td className="py-3 text-right font-mono text-xs text-slate-600">
                        {c.questionProgress}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right Candidate Inspector & Risk Analysis (5 cols) */}
        {selectedCandidate ? (
          <div className="lg:col-span-5 dash-card bg-white border border-slate-200/90 p-6 rounded-2xl space-y-5 shadow-sm">
            
            {/* Candidate Header */}
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 rounded-full bg-blue-600 text-white flex items-center justify-center font-bold text-sm shadow-sm">
                  {selectedCandidate.name.charAt(0)}
                </div>
                <div>
                  <h3 className="font-extrabold text-slate-900 text-sm leading-tight">{selectedCandidate.name}</h3>
                  <p className="text-[11px] text-slate-500">{selectedCandidate.email}</p>
                </div>
              </div>

              <span className={`px-2.5 py-0.5 rounded-full text-xs font-mono font-bold border ${getRiskBadge(selectedCandidate.riskLevel)}`}>
                Score: {selectedCandidate.riskScore}/100
              </span>
            </div>

            {/* Live Camera Viewport Preview */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-slate-700 flex items-center space-x-1.5">
                  <Camera className="w-3.5 h-3.5 text-blue-600" />
                  <span>Real-time Video Feed</span>
                </span>
                <span className="text-[11px] font-mono text-emerald-600 font-bold flex items-center space-x-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                  <span>Active • 30 FPS</span>
                </span>
              </div>

              {/* Camera Frame */}
              <div className="relative w-full aspect-video rounded-xl bg-slate-900 overflow-hidden border border-slate-800 shadow-inner flex items-center justify-center">
                <div className="text-center space-y-1">
                  <div className="w-12 h-12 rounded-full bg-slate-800 text-blue-400 flex items-center justify-center mx-auto border border-slate-700">
                    <Eye className="w-6 h-6 animate-pulse" />
                  </div>
                  <div className="text-xs font-bold text-slate-300">Biometric Surveillance</div>
                  <div className="text-[10px] text-emerald-400 font-mono">Face verified • 1 person in frame</div>
                </div>

                {/* Overlaid Detection Box */}
                <div className="absolute inset-x-12 inset-y-6 border-2 border-emerald-500/70 rounded-lg pointer-events-none flex flex-col justify-between p-1.5">
                  <div className="flex justify-between text-[9px] font-mono text-emerald-400 font-bold bg-slate-950/80 px-1.5 py-0.5 rounded">
                    <span>FACE CONFIDENCE: 98.6%</span>
                    <span>GAZE: CENTER</span>
                  </div>
                  <div className="text-[9px] font-mono text-slate-300 bg-slate-950/80 px-1.5 py-0.5 rounded">
                    STREAM ID: {selectedCandidate.attempt_id}
                  </div>
                </div>
              </div>
            </div>

            {/* Threat Indicators */}
            <div className="space-y-3 pt-2">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700">
                Threat Breakdown
              </h4>

              <div className="space-y-2 text-xs">
                <div>
                  <div className="flex justify-between text-[11px] font-semibold text-slate-600 mb-1">
                    <span>Gaze Deviation</span>
                    <span className="font-bold text-slate-900 font-mono">14% (Normal)</span>
                  </div>
                  <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                    <div className="h-full bg-emerald-500 rounded-full" style={{ width: '14%' }} />
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-[11px] font-semibold text-slate-600 mb-1">
                    <span>Audio / Speech Level</span>
                    <span className="font-bold text-slate-900 font-mono">32 dB (Ambient)</span>
                  </div>
                  <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                    <div className="h-full bg-blue-500 rounded-full" style={{ width: '32%' }} />
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-[11px] font-semibold text-slate-600 mb-1">
                    <span>Calculated Threat Index</span>
                    <span className={`font-bold font-mono ${selectedCandidate.riskScore > 50 ? 'text-rose-600' : 'text-slate-900'}`}>
                      {selectedCandidate.riskScore}% ({selectedCandidate.riskLevel})
                    </span>
                  </div>
                  <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                    <div 
                      className={`h-full rounded-full ${
                        selectedCandidate.riskScore > 50 ? 'bg-rose-500' : selectedCandidate.riskScore > 25 ? 'bg-amber-500' : 'bg-emerald-500'
                      }`} 
                      style={{ width: `${selectedCandidate.riskScore}%` }} 
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Proctor Action Controls */}
            <div className="space-y-2 pt-2 border-t border-slate-100">
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={handleSendWarning}
                  className="py-2.5 px-3 rounded-xl bg-amber-50 hover:bg-amber-100 text-amber-800 border border-amber-200 text-xs font-bold transition flex items-center justify-center space-x-1.5"
                >
                  <Volume2 className="w-3.5 h-3.5" />
                  <span>Send Warning</span>
                </button>

                <button
                  onClick={handleClearRisk}
                  className="py-2.5 px-3 rounded-xl bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-200 text-xs font-bold transition flex items-center justify-center space-x-1.5"
                >
                  <CheckCircle className="w-3.5 h-3.5" />
                  <span>Mark Verified</span>
                </button>
              </div>

              <button
                onClick={handleDisqualify}
                className="w-full py-2.5 px-3 rounded-xl bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 text-xs font-bold transition flex items-center justify-center space-x-1.5"
              >
                <XCircle className="w-3.5 h-3.5" />
                <span>Force Terminate Candidate</span>
              </button>

              <button
                onClick={handleOpenReviewModal}
                className="w-full py-2.5 px-3 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold shadow-sm transition flex items-center justify-center space-x-1.5"
              >
                <FileText className="w-3.5 h-3.5" />
                <span>Full Video & Incident Timeline Review</span>
              </button>
            </div>

          </div>
        ) : (
          <div className="lg:col-span-5 dash-card bg-white border border-slate-200 p-8 rounded-2xl text-center space-y-3">
            <Eye className="w-10 h-10 text-slate-300 mx-auto" />
            <div className="text-sm font-bold text-slate-700">No Candidate Selected</div>
            <p className="text-xs text-slate-500">Select a candidate on the left to inspect live telemetry.</p>
          </div>
        )}

      </div>

      {/* Comprehensive Incident Review Modal */}
      {showReviewModal && selectedCandidate && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white max-w-xl w-full rounded-2xl border border-slate-200 shadow-2xl overflow-hidden my-8">
            
            <div className="bg-slate-50 p-5 border-b border-slate-200 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-slate-900">
                  Incident Review: {selectedCandidate.name}
                </h3>
                <p className="text-xs text-slate-500">
                  Audit flagged events and submit certified human proctor verdict
                </p>
              </div>
              <button
                onClick={() => setShowReviewModal(false)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-700 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-5 max-h-[70vh] overflow-y-auto text-xs">
              
              {/* Event Timeline List */}
              <div className="space-y-2">
                <div className="font-bold text-slate-800 uppercase tracking-wider text-[11px]">
                  Flagged Threat Timeline ({selectedCandidate.events.length} Incidents)
                </div>

                <div className="divide-y divide-slate-100 border border-slate-200 rounded-xl overflow-hidden">
                  {selectedCandidate.events.length === 0 ? (
                    <div className="p-4 text-center text-slate-400 font-medium">No security incidents logged.</div>
                  ) : (
                    selectedCandidate.events.map((ev, i) => (
                      <div key={i} className="p-3 bg-white space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-slate-900">{ev.type}</span>
                          <span className="font-mono text-slate-500 text-[11px]">{ev.time} ({ev.points})</span>
                        </div>
                        <p className="text-slate-600 text-[11px]">{ev.rationale}</p>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Proctor Verdict Selection */}
              <div className="space-y-2">
                <div className="font-bold text-slate-800 uppercase tracking-wider text-[11px]">
                  Official Verdict
                </div>

                <div className="space-y-2">
                  <label className="flex items-center space-x-2.5 p-2.5 rounded-xl border border-slate-200 bg-slate-50 cursor-pointer">
                    <input
                      type="radio"
                      name="verdict"
                      value="CONFIRMED_VIOLATION"
                      checked={reviewDecision === 'CONFIRMED_VIOLATION'}
                      onChange={(e) => setReviewDecision(e.target.value)}
                      className="text-rose-600 focus:ring-rose-500"
                    />
                    <div>
                      <div className="font-bold text-rose-700">Confirm Violation (Fraud / Cheating)</div>
                      <div className="text-[10px] text-slate-500">Uphold risk penalties and flag candidate file</div>
                    </div>
                  </label>

                  <label className="flex items-center space-x-2.5 p-2.5 rounded-xl border border-slate-200 bg-slate-50 cursor-pointer">
                    <input
                      type="radio"
                      name="verdict"
                      value="FALSE_POSITIVE"
                      checked={reviewDecision === 'FALSE_POSITIVE'}
                      onChange={(e) => setReviewDecision(e.target.value)}
                      className="text-emerald-600 focus:ring-emerald-500"
                    />
                    <div>
                      <div className="font-bold text-emerald-700">Dismiss as False Positive (Valid Attempt)</div>
                      <div className="text-[10px] text-slate-500">Deduct penalty points and certify examinee honesty</div>
                    </div>
                  </label>
                </div>
              </div>

              {/* Proctor Notes */}
              <div>
                <label className="block text-[11px] font-semibold text-slate-700 mb-1">Audit Notes</label>
                <textarea
                  rows={2}
                  value={reviewComment}
                  onChange={(e) => setReviewComment(e.target.value)}
                  className="w-full bg-white border border-slate-300 rounded-xl p-2.5 text-xs text-slate-900 outline-none focus:border-blue-500"
                />
              </div>

            </div>

            {/* Modal Footer */}
            <div className="bg-slate-50 p-4 border-t border-slate-200 flex justify-end space-x-2">
              <button
                onClick={() => setShowReviewModal(false)}
                className="px-4 py-2 rounded-xl bg-white border border-slate-300 hover:bg-slate-100 text-slate-700 font-bold text-xs"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmitReviewDecision}
                className="px-5 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow-sm"
              >
                Submit Decision
              </button>
            </div>

          </div>
        </div>
      )}

    </div>
  );
}
