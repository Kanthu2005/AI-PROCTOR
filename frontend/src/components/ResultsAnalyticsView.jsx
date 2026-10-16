import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { 
  BarChart3, 
  Trophy, 
  Users, 
  TrendingUp, 
  CheckCircle2, 
  XCircle, 
  Clock, 
  Target, 
  HelpCircle,
  ShieldCheck,
  ChevronDown,
  Sparkles,
  AlertTriangle,
  Award,
  Download,
  Search,
  Filter,
  Eye,
  X
} from 'lucide-react';

export default function ResultsAnalyticsView() {
  const { user } = useAuth();
  const [selectedAssessment, setSelectedAssessment] = useState('Python Backend Developer');
  const [selectedQuestionNumber, setSelectedQuestionNumber] = useState(17);
  const [search, setSearch] = useState('');
  const [selectedCandidateDetail, setSelectedCandidateDetail] = useState(null);

  // Question Analytics data
  const questionAnalyticsData = {
    17: {
      number: 17,
      title: 'Time complexity of Binary Search',
      prompt: 'What is the time complexity of searching an element in a sorted array using binary search?',
      attempts: 250,
      correct: 42,
      wrong: 51,
      skipped: 7,
      difficulty: 'HIGH',
      avgTime: '2m 14s'
    },
    1: {
      number: 1,
      title: 'CPython GIL Architecture',
      prompt: 'What does GIL stand for in CPython and what is its operational purpose?',
      attempts: 248,
      correct: 68,
      wrong: 24,
      skipped: 8,
      difficulty: 'MEDIUM',
      avgTime: '1m 32s'
    },
    36: {
      number: 36,
      title: 'Maximum Element in an Array (Coding)',
      prompt: 'Find the maximum element in an array with linear time and constant auxiliary memory.',
      attempts: 215,
      correct: 78,
      wrong: 16,
      skipped: 6,
      difficulty: 'MEDIUM',
      avgTime: '8m 45s'
    }
  };

  const activeQ = questionAnalyticsData[selectedQuestionNumber] || questionAnalyticsData[17];

  // Candidate Ranking data
  const rankings = [
    { rank: 1, candidate: 'Rahul Sharma', email: 'rahul@gmail.com', score: 92, percentile: 99.8, accuracy: '95%', time: '34m 12s', risk: 'LOW', status: 'PASSED' },
    { rank: 2, candidate: 'Priya Reddy', email: 'priya@gmail.com', score: 89, percentile: 99.2, accuracy: '91%', time: '42m 05s', risk: 'HIGH', status: 'FLAGGED' },
    { rank: 3, candidate: 'Arjun Kumar', email: 'arjun@gmail.com', score: 86, percentile: 98.7, accuracy: '88%', time: '39m 50s', risk: 'MEDIUM', status: 'PASSED' },
    { rank: 4, candidate: 'Sneha Rao', email: 'sneha@gmail.com', score: 84, percentile: 97.9, accuracy: '86%', time: '29m 14s', risk: 'LOW', status: 'PASSED' },
    { rank: 5, candidate: 'Vikram Mehta', email: 'vikram@gmail.com', score: 81, percentile: 95.4, accuracy: '84%', time: '45m 10s', risk: 'LOW', status: 'PASSED' },
    { rank: 6, candidate: 'Ananya Iyer', email: 'ananya@gmail.com', score: 79, percentile: 92.1, accuracy: '82%', time: '41m 20s', risk: 'LOW', status: 'PASSED' },
    { rank: 7, candidate: 'Karthik Raja', email: 'karthik@gmail.com', score: 58, percentile: 64.3, accuracy: '62%', time: '52m 10s', risk: 'LOW', status: 'FAILED' }
  ];

  // Histogram data
  const distributionData = [
    { label: '0-20%', height: '20%', count: 18 },
    { label: '21-40%', height: '35%', count: 42 },
    { label: '41-60%', height: '70%', count: 125 },
    { label: '61-80%', height: '100%', count: 184 },
    { label: '81-100%', height: '55%', count: 52 },
  ];

  // Export CSV handler
  const handleExportCSV = () => {
    const headers = ['Rank', 'Candidate', 'Email', 'Score', 'Percentile', 'Accuracy', 'Time Taken', 'Integrity Risk', 'Status'];
    const rows = rankings.map(r => [
      r.rank,
      `"${r.candidate}"`,
      r.email,
      r.score,
      `${r.percentile}%`,
      r.accuracy,
      `"${r.time}"`,
      r.risk,
      r.status
    ]);
    
    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map(e => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `${selectedAssessment.replace(/\s+/g, '_')}_Merit_List.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const filteredRankings = rankings.filter(r => 
    !search || r.candidate.toLowerCase().includes(search.toLowerCase()) || r.email.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6 text-slate-800 font-['Plus_Jakarta_Sans',sans-serif]">
      
      {/* Top Banner Card */}
      <div className="dash-card bg-white border border-slate-200/90 p-6 rounded-2xl shadow-sm flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Assessment Analytics</h1>
            <span className="text-xs bg-blue-50 text-blue-700 border border-blue-200 px-2.5 py-0.5 rounded-full font-bold">
              Cohort Intelligence
            </span>
          </div>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Psychometric item discrimination, score distributions, and candidate merit ranking.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-2">
            <label className="text-xs font-semibold text-slate-600">Cohort:</label>
            <select
              value={selectedAssessment}
              onChange={(e) => setSelectedAssessment(e.target.value)}
              className="bg-slate-50 border border-slate-200 text-xs text-slate-800 rounded-xl px-3 py-2 outline-none font-semibold focus:border-blue-500"
            >
              <option value="Python Backend Developer">Python Backend Developer</option>
              <option value="Java Developer">Java Developer</option>
              <option value="SQL Assessment">SQL Assessment</option>
            </select>
          </div>

          <button
            onClick={handleExportCSV}
            className="px-3.5 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow-sm transition flex items-center space-x-1.5"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export CSV</span>
          </button>
        </div>
      </div>

      {/* Cohort Overview Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="dash-card bg-white border border-slate-200/90 p-5 rounded-2xl text-center shadow-sm">
          <div className="text-xs font-bold text-slate-500 uppercase tracking-wider">Candidates</div>
          <div className="text-3xl font-extrabold text-slate-900 font-mono mt-1">500</div>
          <div className="text-[11px] text-slate-400 mt-0.5">Total registered</div>
        </div>

        <div className="dash-card bg-white border border-slate-200/90 p-5 rounded-2xl text-center shadow-sm">
          <div className="text-xs font-bold text-slate-500 uppercase tracking-wider">Completed</div>
          <div className="text-3xl font-extrabold text-blue-600 font-mono mt-1">421</div>
          <div className="text-[11px] text-slate-400 mt-0.5">84.2% completion rate</div>
        </div>

        <div className="dash-card bg-white border border-slate-200/90 p-5 rounded-2xl text-center shadow-sm">
          <div className="text-xs font-bold text-slate-500 uppercase tracking-wider">Passed</div>
          <div className="text-3xl font-extrabold text-emerald-600 font-mono mt-1">238</div>
          <div className="text-[11px] text-slate-400 mt-0.5">56.5% pass rate (≥ 60%)</div>
        </div>

        <div className="dash-card bg-white border border-slate-200/90 p-5 rounded-2xl text-center shadow-sm">
          <div className="text-xs font-bold text-slate-500 uppercase tracking-wider">Average Score</div>
          <div className="text-3xl font-extrabold text-purple-600 font-mono mt-1">68.4%</div>
          <div className="text-[11px] text-slate-400 mt-0.5">Standard Dev: ± 12.3%</div>
        </div>
      </div>

      {/* Middle Row: Score Distribution Graph + Proctoring Threat Metrics */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Score Distribution Histogram */}
        <div className="lg:col-span-8 dash-card bg-white border border-slate-200/90 p-6 rounded-2xl space-y-4 shadow-sm">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <div>
              <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
                SCORE DISTRIBUTION
              </h2>
              <p className="text-xs text-slate-400">Normal bell curve distribution across examinees</p>
            </div>
            <span className="text-xs font-mono font-bold text-blue-600 bg-blue-50 px-2.5 py-1 rounded-lg border border-blue-200">
              Median: 71%
            </span>
          </div>

          {/* Histogram Chart */}
          <div className="h-44 flex items-end justify-between gap-4 pt-4 px-4 bg-slate-50/60 rounded-xl border border-slate-100">
            {distributionData.map((d, i) => (
              <div key={i} className="flex-1 flex flex-col items-center gap-2 h-full justify-end group">
                <span className="text-[11px] font-mono font-bold text-slate-700">
                  {d.count}
                </span>
                <div 
                  className="w-full bg-gradient-to-t from-blue-600 to-indigo-500 rounded-t-lg transition-all duration-300 group-hover:brightness-110 shadow-sm"
                  style={{ height: d.height }}
                />
                <span className="text-[10px] font-mono font-bold text-slate-500 pb-1">
                  {d.label}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Proctoring Threat Metrics */}
        <div className="lg:col-span-4 dash-card bg-white border border-slate-200/90 p-6 rounded-2xl flex flex-col justify-between space-y-4 shadow-sm">
          <div className="space-y-1">
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
              PROCTORING THREATS
            </h2>
            <p className="text-xs text-slate-500">Summary of real-time security breaches</p>
          </div>

          <div className="space-y-3">
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/80">
              <div className="flex justify-between items-center text-xs">
                <div>
                  <span className="font-bold text-slate-800">Tab Switch Incidents</span>
                  <div className="text-[11px] text-slate-400 font-mono mt-0.5">42 candidates flagged</div>
                </div>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-200">
                  Medium
                </span>
              </div>
            </div>

            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/80">
              <div className="flex justify-between items-center text-xs">
                <div>
                  <span className="font-bold text-slate-800">Face Missing Anomaly</span>
                  <div className="text-[11px] text-slate-400 font-mono mt-0.5">18 candidates flagged</div>
                </div>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-50 text-rose-700 border border-rose-200">
                  High
                </span>
              </div>
            </div>

            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/80">
              <div className="flex justify-between items-center text-xs">
                <div>
                  <span className="font-bold text-slate-800">Multiple Faces Detected</span>
                  <div className="text-[11px] text-slate-400 font-mono mt-0.5">6 candidates flagged</div>
                </div>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-800 border border-rose-300">
                  Critical
                </span>
              </div>
            </div>
          </div>

          <div className="text-[11px] text-slate-500 pt-2 border-t border-slate-100">
            Disqualification threshold: 3 tab switches or confirmed multi-face breach.
          </div>
        </div>

      </div>

      {/* Question Analytics Card */}
      <div className="dash-card bg-white border border-slate-200/90 p-6 rounded-2xl space-y-5 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-3 border-b border-slate-100">
          <div>
            <h2 className="text-base font-extrabold text-slate-900 flex items-center space-x-2">
              <HelpCircle className="w-4 h-4 text-blue-600" />
              <span>Question Analytics — Item Discrimination</span>
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">Inspect item difficulty, pass rates, and time allocation</p>
          </div>

          <div className="flex items-center space-x-2">
            <span className="text-xs font-semibold text-slate-600">Select Question:</span>
            <select
              value={selectedQuestionNumber}
              onChange={(e) => setSelectedQuestionNumber(parseInt(e.target.value))}
              className="bg-slate-50 border border-slate-200 text-xs text-slate-800 rounded-xl px-3 py-1.5 outline-none font-semibold focus:border-blue-500 font-mono"
            >
              <option value={17}>Question #17 (Binary Search)</option>
              <option value={1}>Question #1 (CPython GIL)</option>
              <option value={36}>Question #36 (Coding Array Max)</option>
            </select>
          </div>
        </div>

        {/* Question Details View */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
          <div className="lg:col-span-6 space-y-2">
            <div className="text-xs font-mono font-bold text-blue-600">
              Question #{activeQ.number} • {activeQ.title}
            </div>
            <div className="text-sm font-semibold text-slate-800 leading-snug">
              "{activeQ.prompt}"
            </div>
            <div className="text-xs text-slate-500 pt-2 font-mono">
              Total Attempts: <strong className="text-slate-900">{activeQ.attempts}</strong>
            </div>
          </div>

          <div className="lg:col-span-6 grid grid-cols-3 gap-3 text-center">
            <div className="p-3.5 bg-emerald-50/70 rounded-xl border border-emerald-200">
              <div className="text-[11px] text-emerald-800 font-semibold font-mono">Correct</div>
              <div className="text-xl font-black text-emerald-700 font-mono mt-1">{activeQ.correct}%</div>
            </div>
            <div className="p-3.5 bg-rose-50/70 rounded-xl border border-rose-200">
              <div className="text-[11px] text-rose-800 font-semibold font-mono">Wrong</div>
              <div className="text-xl font-black text-rose-700 font-mono mt-1">{activeQ.wrong}%</div>
            </div>
            <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200">
              <div className="text-[11px] text-slate-600 font-semibold font-mono">Skipped</div>
              <div className="text-xl font-black text-slate-700 font-mono mt-1">{activeQ.skipped}%</div>
            </div>

            <div className="col-span-3 flex items-center justify-between px-3 py-2 bg-slate-50 rounded-xl border border-slate-200 text-xs font-mono text-slate-700">
              <span>Difficulty: <strong className="text-rose-600">{activeQ.difficulty}</strong></span>
              <span>Average Time: <strong className="text-blue-700">{activeQ.avgTime}</strong></span>
            </div>
          </div>
        </div>
      </div>

      {/* Candidate Ranking Leaderboard */}
      <div className="dash-card bg-white border border-slate-200/90 p-6 rounded-2xl space-y-4 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-3 border-b border-slate-100">
          <div>
            <h2 className="text-base font-extrabold text-slate-900 flex items-center space-x-2">
              <Trophy className="w-4 h-4 text-amber-500" />
              <span>Candidate Ranking Leaderboard</span>
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">Ranked by composite score, percentile rank, and accuracy rate</p>
          </div>

          <div className="relative w-full sm:w-64">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search candidate..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-slate-50 focus:bg-white border border-slate-200 focus:border-blue-500 rounded-xl pl-9 pr-3 py-1.5 text-xs text-slate-900 outline-none transition"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-100 text-slate-500 font-bold text-[11px]">
                <th className="py-3 px-4">Rank</th>
                <th className="py-3 px-4">Candidate</th>
                <th className="py-3 px-4">Score</th>
                <th className="py-3 px-4">Percentile</th>
                <th className="py-3 px-4">Accuracy</th>
                <th className="py-3 px-4">Integrity Risk</th>
                <th className="py-3 px-4 text-right">Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-medium">
              {filteredRankings.map((r) => (
                <tr 
                  key={r.rank} 
                  onClick={() => setSelectedCandidateDetail(r)}
                  className="hover:bg-slate-50 transition cursor-pointer"
                >
                  <td className="py-3.5 px-4 font-mono font-bold">
                    {r.rank === 1 && <span className="text-amber-500 font-black">🥇 #1</span>}
                    {r.rank === 2 && <span className="text-slate-600 font-bold">🥈 #2</span>}
                    {r.rank === 3 && <span className="text-amber-700 font-bold">🥉 #3</span>}
                    {r.rank > 3 && <span className="text-slate-500">#{r.rank}</span>}
                  </td>
                  <td className="py-3.5 px-4">
                    <div className="font-bold text-slate-900 text-sm">{r.candidate}</div>
                    <div className="text-[11px] text-slate-400">{r.email}</div>
                  </td>
                  <td className="py-3.5 px-4 font-mono font-black text-blue-600 text-sm">
                    {r.score}/100
                  </td>
                  <td className="py-3.5 px-4 font-mono text-slate-700 font-semibold">
                    {r.percentile}%
                  </td>
                  <td className="py-3.5 px-4 font-mono text-emerald-700 font-semibold">
                    {r.accuracy}
                  </td>
                  <td className="py-3.5 px-4">
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                      r.risk === 'HIGH' ? 'bg-rose-50 text-rose-700 border-rose-200' :
                      r.risk === 'MEDIUM' ? 'bg-amber-50 text-amber-700 border-amber-200' :
                      'bg-emerald-50 text-emerald-700 border-emerald-200'
                    }`}>
                      {r.risk} RISK
                    </span>
                  </td>
                  <td className="py-3.5 px-4 font-mono text-slate-500 text-right">
                    {r.time}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Candidate Drilldown Modal */}
      {selectedCandidateDetail && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white max-w-md w-full rounded-2xl border border-slate-200 shadow-2xl p-6 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div>
                <h3 className="font-extrabold text-slate-900 text-base">{selectedCandidateDetail.candidate}</h3>
                <p className="text-xs text-slate-500">{selectedCandidateDetail.email}</p>
              </div>
              <button
                onClick={() => setSelectedCandidateDetail(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-700"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                <div className="text-[11px] text-slate-500 font-semibold">Overall Score</div>
                <div className="text-xl font-black text-blue-600 font-mono mt-0.5">{selectedCandidateDetail.score} / 100</div>
              </div>
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                <div className="text-[11px] text-slate-500 font-semibold">Rank</div>
                <div className="text-xl font-black text-amber-600 font-mono mt-0.5">#{selectedCandidateDetail.rank} of 250</div>
              </div>
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                <div className="text-[11px] text-slate-500 font-semibold">Accuracy</div>
                <div className="text-xl font-black text-emerald-600 font-mono mt-0.5">{selectedCandidateDetail.accuracy}</div>
              </div>
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                <div className="text-[11px] text-slate-500 font-semibold">Integrity Risk</div>
                <div className={`text-xl font-black font-mono mt-0.5 ${
                  selectedCandidateDetail.risk === 'HIGH' ? 'text-rose-600' : 'text-emerald-600'
                }`}>
                  {selectedCandidateDetail.risk}
                </div>
              </div>
            </div>

            <button
              onClick={() => {
                alert(`Evaluation certificate generated for ${selectedCandidateDetail.candidate}.`);
                setSelectedCandidateDetail(null);
              }}
              className="w-full py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow-sm transition"
            >
              Download Verified Report PDF
            </button>
          </div>
        </div>
      )}

    </div>
  );
}
