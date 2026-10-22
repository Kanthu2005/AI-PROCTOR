import React, { useState, useEffect } from 'react';
import { api } from '../api';
import { useAuth } from '../context/AuthContext';
import { 
  FileText, 
  Plus, 
  Settings2, 
  ShieldAlert, 
  Clock, 
  Award, 
  Layers, 
  Shuffle, 
  Lock, 
  Eye, 
  UserPlus, 
  CheckCircle2, 
  Trash2, 
  ChevronRight, 
  ChevronLeft,
  Search, 
  Filter, 
  Sparkles, 
  Check, 
  X,
  Code2,
  Database,
  HelpCircle,
  AlertCircle,
  Play,
  ArrowRight,
  Calendar
} from 'lucide-react';

export default function AssessmentBuilder({ onOpenCandidateInvite, onLaunchCandidateExam, initialCreate = false }) {
  const { user } = useAuth();
  const [assessments, setAssessments] = useState([]);
  const [availableQuestions, setAvailableQuestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchFilter, setSearchFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');

  // Wizard modal state
  const [showWizardModal, setShowWizardModal] = useState(initialCreate);
  const [currentStep, setCurrentStep] = useState(1); // 1 to 5

  // Open modal if initialCreate prop changes
  useEffect(() => {
    if (initialCreate) {
      setShowWizardModal(true);
      setCurrentStep(1);
    }
  }, [initialCreate]);

  // Step 1: Basic Info
  const [title, setTitle] = useState('Python Backend Developer');
  const [description, setDescription] = useState('Backend developer screening assessment');
  const [sectionTitle, setSectionTitle] = useState('Core Assessment Section');
  const [sectionCutOff, setSectionCutOff] = useState(0);
  const [duration, setDuration] = useState(90);
  const [totalMarks, setTotalMarks] = useState(100);
  const [passingMarks, setPassingMarks] = useState(60);
  const [startDate, setStartDate] = useState('2026-10-15T09:00');
  const [endDate, setEndDate] = useState('2026-10-20T18:00');
  const [attemptLimit, setAttemptLimit] = useState(1);

  // Quick Schedule Modal state
  const [scheduleModalOpen, setScheduleModalOpen] = useState(false);
  const [schedulingAssessment, setSchedulingAssessment] = useState(null);
  const [modalStartTime, setModalStartTime] = useState('');
  const [modalEndTime, setModalEndTime] = useState('');

  // Step 2: Questions Selection & Filter
  const [qSearch, setQSearch] = useState('');
  const [qCategory, setQCategory] = useState('ALL');
  const [qDifficulty, setQDifficulty] = useState('ALL');
  const [qType, setQType] = useState('ALL');
  const [selectedQuestionIds, setSelectedQuestionIds] = useState([]);

  // Step 3: Rules
  const [navigationMode, setNavigationMode] = useState('FREE'); // 'FREE' or 'FORWARD_ONLY'
  const [allowPrev, setAllowPrev] = useState(true);
  const [allowNext, setAllowNext] = useState(true);
  const [allowJump, setAllowJump] = useState(false);
  const [randomizeQuestions, setRandomizeQuestions] = useState(true);
  const [randomizeOptions, setRandomizeOptions] = useState(true);
  const [negativeMarking, setNegativeMarking] = useState(true);
  const [correctAnswerMarks, setCorrectAnswerMarks] = useState(2);
  const [wrongAnswerPenalty, setWrongAnswerPenalty] = useState(0.5);

  // Step 4: Proctoring Configuration
  const [identityVerification, setIdentityVerification] = useState(true);
  const [webcamRequired, setWebcamRequired] = useState(true);
  const [micRequired, setMicRequired] = useState(true);
  const [fullscreenRequired, setFullscreenRequired] = useState(true);
  const [tabSwitchDetection, setTabSwitchDetection] = useState(true);
  const [multipleFaceDetection, setMultipleFaceDetection] = useState(true);
  const [faceMissingDetection, setFaceMissingDetection] = useState(true);
  const [copyPasteDetection, setCopyPasteDetection] = useState(true);
  const [rightClickDetection, setRightClickDetection] = useState(true);
  const [devToolsDetection, setDevToolsDetection] = useState(true);

  // Risk Thresholds
  const [riskFaceMissing, setRiskFaceMissing] = useState(20);
  const [riskMultipleFaces, setRiskMultipleFaces] = useState(40);
  const [riskTabSwitch, setRiskTabSwitch] = useState(10);
  const [riskFullscreenExit, setRiskFullscreenExit] = useState(10);
  const [riskCameraDisabled, setRiskCameraDisabled] = useState(30);
  const [riskIdentityMismatch, setRiskIdentityMismatch] = useState(50);

  // Default seeded assessments
  const defaultAssessments = [
    {
      id: 'python-backend',
      title: 'Python Backend Developer',
      description: 'Senior backend engineering assessment testing Python internals, algorithms, and system design.',
      status: 'PUBLISHED',
      total_duration_minutes: 90,
      total_marks: 100,
      question_count: 37,
      candidates_count: 124,
      token: 'ABC123',
      rules: {
        webcam: true,
        fullscreen: true,
        negative_marking: true
      }
    },
    {
      id: 'java-dev',
      title: 'Java Developer',
      description: 'Spring Boot, concurrency, JVM optimization, and microservice architectures.',
      status: 'SCHEDULED',
      total_duration_minutes: 90,
      total_marks: 100,
      question_count: 40,
      candidates_count: 80,
      token: 'JAVA_EXP',
      rules: {
        webcam: true,
        fullscreen: true,
        negative_marking: true
      }
    },
    {
      id: 'sql-assessment',
      title: 'SQL & Database Specialist',
      description: 'Complex joins, window functions, indexing strategies, and query performance tuning.',
      status: 'DRAFT',
      total_duration_minutes: 60,
      total_marks: 75,
      question_count: 30,
      candidates_count: 0,
      token: 'SQL_TEST',
      rules: {
        webcam: false,
        fullscreen: true,
        negative_marking: false
      }
    }
  ];

  // Default questions for Step 2
  const defaultQuestions = [
    {
      id: 'q_1',
      title: 'Which decorator defines a class static method in Python?',
      description: 'Evaluates knowledge of Python built-in method decorators and class namespaces.',
      question_type: 'MCQ_SINGLE',
      difficulty: 'EASY',
      tags: ['python', 'oop'],
      marks: 2.0
    },
    {
      id: 'q_2',
      title: 'Implement find_max(arr) without built-in max()',
      description: 'Write an efficient linear search algorithm with edge case handling.',
      question_type: 'CODING',
      difficulty: 'MEDIUM',
      tags: ['python', 'algorithms'],
      marks: 10.0
    },
    {
      id: 'q_3',
      title: 'What is the space complexity of Quicksort in the worst case?',
      description: 'Tests recursion depth stack frame memory consumption.',
      question_type: 'MCQ_SINGLE',
      difficulty: 'MEDIUM',
      tags: ['dsa', 'algorithms'],
      marks: 2.0
    },
    {
      id: 'q_4',
      title: 'In PostgreSQL, which index type is best for B-tree range queries?',
      description: 'Tests relational database engine storage engines and query planner optimization.',
      question_type: 'MCQ_SINGLE',
      difficulty: 'HARD',
      tags: ['sql', 'database'],
      marks: 3.0
    },
    {
      id: 'q_5',
      title: 'Explain the difference between threading and multiprocessing in Python (GIL)',
      description: 'Global Interpreter Lock CPU vs I/O bound concurrency.',
      question_type: 'MCQ_SINGLE',
      difficulty: 'HARD',
      tags: ['python', 'concurrency'],
      marks: 4.0
    }
  ];

  useEffect(() => {
    loadData();
  }, [user]);

  const loadData = async () => {
    try {
      setLoading(true);
      const orgId = user?.org_id || 'test_org';
      const [assessList, qList] = await Promise.all([
        api.listAssessments(orgId).catch(() => []),
        api.listQuestions(orgId).catch(() => [])
      ]);

      setAssessments(assessList || []);
      const questionsArray = Array.isArray(qList) ? qList : (qList?.items || []);
      setAvailableQuestions(questionsArray);
      setSelectedQuestionIds([]);
    } catch (e) {
      console.error('Failed to load assessment data:', e);
      setAssessments([]);
      setAvailableQuestions([]);
      setSelectedQuestionIds([]);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleQuestion = (qId) => {
    setSelectedQuestionIds(prev => 
      prev.includes(qId) ? prev.filter(id => id !== qId) : [...prev, qId]
    );
  };

  const handleCreateAssessment = async (intent = 'PUBLISH') => {
    try {
      setLoading(true);
      const orgId = user?.org_id || 'test_org';
      
      // Filter questions to only valid IDs (either real UUIDs or questions present in DB)
      const validDbQuestionIds = availableQuestions
        .filter(q => selectedQuestionIds.includes(q.id) && q.id && !q.id.startsWith('mock_'))
        .map(q => q.id);

      const parsedDuration = parseInt(duration) || 60;
      const parsedMarks = parseFloat(totalMarks) || 100.0;
      const parsedPassing = totalMarks > 0 ? (passingMarks / totalMarks) * 100 : 50.0;

      const backendPayload = {
        org_id: orgId,
        title: title || 'New Assessment',
        description: description || 'Comprehensive assessment',
        instructions: `Assessment rules: ${parsedDuration} minutes, passing marks ${passingMarks}. Zero-tolerance proctoring active.`,
        total_duration_minutes: parsedDuration,
        total_marks: parsedMarks,
        passing_percentage: parsedPassing,
        max_attempts: parseInt(attemptLimit) || 1,
        start_time: startDate ? new Date(startDate).toISOString() : null,
        end_time: endDate ? new Date(endDate).toISOString() : null,
        rules: {
          navigation_mode: navigationMode,
          randomize_questions: Boolean(randomizeQuestions),
          randomize_options: Boolean(randomizeOptions),
          negative_marking_enabled: Boolean(negativeMarking),
          webcam_proctoring_enabled: Boolean(webcamRequired),
          full_screen_enforced: Boolean(fullscreenRequired),
          max_tab_switches_allowed: 3,
          devtools_block_enabled: Boolean(devToolsDetection),
          copy_paste_blocked: Boolean(copyPasteDetection)
        },
        sections: [
          {
            title: sectionTitle || 'Core Assessment Section',
            duration_minutes: parsedDuration,
            order_index: 0,
            cut_off_marks: parseFloat(sectionCutOff) || 0.0,
            questions: validDbQuestionIds.map((qid, idx) => ({
              question_id: qid,
              positive_marks: parseFloat(correctAnswerMarks) || 2.0,
              negative_marks: parseFloat(wrongAnswerPenalty) || 0.5,
              order_index: idx
            }))
          }
        ]
      };

      let created = null;
      try {
        created = await api.createAssessment(backendPayload);
        if (created && created.id) {
          if (intent === 'PUBLISH') {
            await api.publishAssessment(created.id);
            created.status = 'PUBLISHED';
          } else if (intent === 'SCHEDULE') {
            await api.scheduleAssessment(
              created.id,
              new Date(startDate).toISOString(),
              new Date(endDate).toISOString()
            );
            created.status = 'SCHEDULED';
          } else if (intent === 'LIVE') {
            await api.goLiveAssessment(created.id);
            created.status = 'LIVE';
          }
        }
      } catch (err) {
        console.warn('API sync fallback:', err);
      }

      const initialStatus = intent === 'PUBLISH' ? 'PUBLISHED' : (intent === 'SCHEDULE' ? 'SCHEDULED' : (intent === 'LIVE' ? 'LIVE' : 'DRAFT'));
      const newAssessment = created || {
        id: `assess_${Date.now()}`,
        org_id: orgId,
        title: title || 'New Assessment',
        description: description || 'Comprehensive assessment',
        total_duration_minutes: parsedDuration,
        total_marks: parsedMarks,
        passing_percentage: parsedPassing,
        status: initialStatus,
        question_count: selectedQuestionIds.length,
        candidates_count: 0
      };

      setAssessments(prev => [newAssessment, ...prev.filter(a => a.id !== newAssessment.id)]);
      setShowWizardModal(false);
      setCurrentStep(1);
      alert(`Assessment "${newAssessment.title}" created with status ${newAssessment.status}!`);
    } catch (e) {
      alert(`Assessment creation failed: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handlePublishDirect = async (assessId) => {
    try {
      setLoading(true);
      await api.publishAssessment(assessId);
      setAssessments(prev => prev.map(a => a.id === assessId ? { ...a, status: 'PUBLISHED' } : a));
      alert('Assessment successfully transitioned to PUBLISHED state!');
    } catch (err) {
      alert(`Publish failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleGoLive = async (assessId) => {
    try {
      setLoading(true);
      await api.goLiveAssessment(assessId);
      setAssessments(prev => prev.map(a => a.id === assessId ? { ...a, status: 'LIVE' } : a));
      alert('Assessment is now LIVE for candidates!');
    } catch (err) {
      alert(`Go Live failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const openScheduleModal = (assessment) => {
    setSchedulingAssessment(assessment);
    const now = new Date();
    setModalStartTime(now.toISOString().slice(0, 16));
    const later = new Date(now.getTime() + 72 * 3600 * 1000);
    setModalEndTime(later.toISOString().slice(0, 16));
    setScheduleModalOpen(true);
  };

  const handleConfirmSchedule = async () => {
    if (!schedulingAssessment || !modalStartTime || !modalEndTime) return;
    try {
      setLoading(true);
      const startIso = new Date(modalStartTime).toISOString();
      const endIso = new Date(modalEndTime).toISOString();
      await api.scheduleAssessment(schedulingAssessment.id, startIso, endIso);
      setAssessments(prev => prev.map(a => a.id === schedulingAssessment.id ? { ...a, status: 'SCHEDULED', start_time: startIso, end_time: endIso } : a));
      setScheduleModalOpen(false);
      setSchedulingAssessment(null);
      alert('Assessment successfully scheduled!');
    } catch (err) {
      alert(`Scheduling failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleCloseAssessment = async (assessId) => {
    if (!confirm('Are you sure you want to CLOSE this assessment? No further attempts will be allowed.')) return;
    try {
      setLoading(true);
      await api.closeAssessment(assessId);
      setAssessments(prev => prev.map(a => a.id === assessId ? { ...a, status: 'CLOSED' } : a));
      alert('Assessment closed successfully.');
    } catch (err) {
      alert(`Close failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleDuplicateAssessment = async (assessId) => {
    try {
      setLoading(true);
      const dup = await api.duplicateAssessment(assessId);
      setAssessments(prev => [dup, ...prev]);
      alert('Assessment duplicated as DRAFT with frozen question versions!');
    } catch (err) {
      alert(`Duplicate failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Filter questions for Step 2
  const filteredQuestions = availableQuestions.filter(q => {
    const matchesSearch = !qSearch || q.title.toLowerCase().includes(qSearch.toLowerCase()) || (q.description && q.description.toLowerCase().includes(qSearch.toLowerCase()));
    const matchesCat = qCategory === 'ALL' || (q.tags && q.tags.some(t => t.toLowerCase() === qCategory.toLowerCase()));
    const matchesDiff = qDifficulty === 'ALL' || q.difficulty === qDifficulty;
    const matchesType = qType === 'ALL' || q.question_type === qType;
    return matchesSearch && matchesCat && matchesDiff && matchesType;
  });

  // Filter assessments list
  const filteredAssessments = assessments.filter(a => {
    const matchSearch = !searchFilter || a.title?.toLowerCase().includes(searchFilter.toLowerCase());
    const matchStatus = statusFilter === 'ALL' || a.status === statusFilter;
    return matchSearch && matchStatus;
  });

  return (
    <div className="space-y-6 text-slate-800 font-['Plus_Jakarta_Sans',sans-serif]">
      
      {/* Top Banner Card */}
      <div className="dash-card bg-white border border-slate-200/90 p-6 rounded-2xl shadow-sm flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Assessments</h1>
            <span className="text-xs bg-blue-50 text-blue-700 border border-blue-200 px-2.5 py-0.5 rounded-full font-bold">
              Test Manager
            </span>
          </div>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Author, configure rules, calibrate AI proctoring thresholds, and publish evaluations.
          </p>
        </div>

        <button
          onClick={() => {
            setCurrentStep(1);
            setShowWizardModal(true);
          }}
          className="px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow-md shadow-blue-500/25 flex items-center justify-center space-x-2 transition"
        >
          <Plus className="w-4 h-4" />
          <span>+ Create Assessment</span>
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="dash-card bg-white border border-slate-200/90 p-4 rounded-2xl shadow-sm flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search assessments..."
            value={searchFilter}
            onChange={(e) => setSearchFilter(e.target.value)}
            className="w-full bg-slate-50 focus:bg-white border border-slate-200 focus:border-blue-500 rounded-xl pl-9 pr-3 py-2 text-xs text-slate-900 placeholder-slate-400 outline-none transition"
          />
        </div>

        <div className="flex items-center space-x-2 w-full sm:w-auto">
          <Filter className="w-4 h-4 text-slate-400" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-slate-50 focus:bg-white border border-slate-200 text-xs text-slate-700 rounded-xl px-3 py-2 outline-none font-semibold focus:border-blue-500"
          >
            <option value="ALL">All Statuses</option>
            <option value="DRAFT">Draft</option>
            <option value="PUBLISHED">Published</option>
            <option value="SCHEDULED">Scheduled</option>
            <option value="LIVE">Live</option>
            <option value="CLOSED">Closed</option>
          </select>
        </div>
      </div>

      {/* Assessment Cards List */}
      <div className="space-y-4">
        {filteredAssessments.length === 0 ? (
          <div className="dash-card bg-white border border-slate-200 p-12 rounded-2xl text-center space-y-3">
            <FileText className="w-10 h-10 text-slate-300 mx-auto" />
            <div className="text-sm font-bold text-slate-700">No assessments found</div>
            <p className="text-xs text-slate-500">Try adjusting your search criteria or create a new assessment.</p>
          </div>
        ) : (
          filteredAssessments.map((a) => {
            const isLive = a.status === 'LIVE';
            const isPublished = a.status === 'PUBLISHED';
            const isScheduled = a.status === 'SCHEDULED';
            const isClosed = a.status === 'CLOSED';
            const isDraft = !a.status || a.status === 'DRAFT';
            
            return (
              <div 
                key={a.id} 
                className="dash-card bg-white border border-slate-200 hover:border-blue-400 p-6 rounded-2xl transition space-y-4 shadow-sm"
              >
                <div className="flex items-start justify-between flex-wrap gap-2">
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2.5">
                      <h3 className="text-lg font-extrabold text-slate-900">{a.title}</h3>
                      {isLive && (
                        <span className="text-[11px] font-bold px-2.5 py-0.5 rounded-full border bg-emerald-50 text-emerald-700 border-emerald-200 flex items-center space-x-1">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-ping mr-1"></span>
                          🟢 Live
                        </span>
                      )}
                      {isPublished && (
                        <span className="text-[11px] font-bold px-2.5 py-0.5 rounded-full border bg-blue-50 text-blue-700 border-blue-200">
                          🔵 Published
                        </span>
                      )}
                      {isScheduled && (
                        <span className="text-[11px] font-bold px-2.5 py-0.5 rounded-full border bg-amber-50 text-amber-700 border-amber-200">
                          🟡 Scheduled
                        </span>
                      )}
                      {isClosed && (
                        <span className="text-[11px] font-bold px-2.5 py-0.5 rounded-full border bg-rose-50 text-rose-700 border-rose-200">
                          🔴 Closed
                        </span>
                      )}
                      {isDraft && (
                        <span className="text-[11px] font-bold px-2.5 py-0.5 rounded-full border bg-slate-100 text-slate-600 border-slate-200">
                          ⚪ Draft
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-slate-500">
                      {a.description || 'Screening assessment with proctored anti-cheat telemetry.'}
                    </p>
                    <div className="text-xs font-mono font-medium text-slate-600 pt-1">
                      {a.question_count || (a.sections ? a.sections.reduce((acc, s) => acc + (s.questions?.length || 0), 0) : 0)} Questions • {a.total_duration_minutes || 90} min • {a.total_marks || 100} Marks • Max Attempts: {a.max_attempts || 1}
                    </div>
                  </div>

                  <div className="text-right">
                    <span className="text-xs font-mono font-bold text-slate-700 bg-slate-100 px-3 py-1.5 rounded-xl border border-slate-200 inline-block">
                      {a.candidates_count || 0} Candidates
                    </span>
                  </div>
                </div>

                <div className="flex flex-wrap items-center justify-between text-xs pt-3 border-t border-slate-100 gap-3">
                  <div className="flex items-center space-x-4 text-slate-500 text-xs">
                    <span>Fullscreen: <strong className="text-slate-800 font-bold">{a.rules?.fullscreen !== false ? 'ON' : 'OFF'}</strong></span>
                    <span>Webcam: <strong className="text-slate-800 font-bold">{a.rules?.webcam !== false ? 'ON' : 'OFF'}</strong></span>
                    <span>Negative Marking: <strong className="text-slate-800 font-bold">{a.rules?.negative_marking !== false ? 'ON' : 'OFF'}</strong></span>
                  </div>

                  <div className="flex flex-wrap items-center gap-1.5">
                    {/* DRAFT actions */}
                    {isDraft && (
                      <>
                        <button
                          onClick={() => handlePublishDirect(a.id)}
                          className="px-3 py-1.5 rounded-xl bg-blue-50 hover:bg-blue-100 text-blue-700 font-bold text-xs border border-blue-200 transition"
                        >
                          Publish
                        </button>
                        <button
                          onClick={() => openScheduleModal(a)}
                          className="px-3 py-1.5 rounded-xl bg-amber-50 hover:bg-amber-100 text-amber-700 font-bold text-xs border border-amber-200 transition flex items-center space-x-1"
                        >
                          <Calendar className="w-3.5 h-3.5" />
                          <span>Schedule</span>
                        </button>
                        <button
                          onClick={() => handleGoLive(a.id)}
                          className="px-3 py-1.5 rounded-xl bg-emerald-50 hover:bg-emerald-100 text-emerald-700 font-bold text-xs border border-emerald-200 transition"
                        >
                          Go Live
                        </button>
                      </>
                    )}

                    {/* PUBLISHED / SCHEDULED actions */}
                    {(isPublished || isScheduled) && (
                      <button
                        onClick={() => handleGoLive(a.id)}
                        className="px-3 py-1.5 rounded-xl bg-emerald-50 hover:bg-emerald-100 text-emerald-700 font-bold text-xs border border-emerald-200 transition"
                      >
                        Go Live Now
                      </button>
                    )}

                    {/* Close action for active assessments */}
                    {!isClosed && !isDraft && (
                      <button
                        onClick={() => handleCloseAssessment(a.id)}
                        className="px-3 py-1.5 rounded-xl bg-rose-50 hover:bg-rose-100 text-rose-700 font-bold text-xs border border-rose-200 transition"
                      >
                        Close
                      </button>
                    )}

                    {/* Duplicate button */}
                    <button
                      onClick={() => handleDuplicateAssessment(a.id)}
                      className="px-3 py-1.5 rounded-xl bg-slate-50 hover:bg-slate-100 text-slate-700 font-bold text-xs border border-slate-200 transition"
                    >
                      Duplicate
                    </button>

                    <button
                      onClick={() => onLaunchCandidateExam && onLaunchCandidateExam(a.token || a.sample_token || '')}
                      className="px-3.5 py-1.5 rounded-xl bg-blue-50 hover:bg-blue-100 text-blue-700 font-bold text-xs border border-blue-200 transition flex items-center space-x-1.5"
                    >
                      <Play className="w-3.5 h-3.5" />
                      <span>Launch Test Engine</span>
                    </button>
                    
                    <button
                      onClick={() => onOpenCandidateInvite && onOpenCandidateInvite(a)}
                      className="px-3.5 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow-sm transition flex items-center space-x-1.5"
                    >
                      <UserPlus className="w-3.5 h-3.5" />
                      <span>Invite Candidates</span>
                    </button>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* 5-Step Create Assessment Wizard Modal */}
      {showWizardModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white max-w-3xl w-full rounded-2xl border border-slate-200 shadow-2xl overflow-hidden my-8">
            
            {/* Modal Header */}
            <div className="bg-slate-50 p-6 border-b border-slate-200">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-2">
                  <span className="text-xs font-bold text-blue-600 uppercase tracking-widest">
                    Create Assessment Wizard
                  </span>
                </div>
                <button
                  onClick={() => setShowWizardModal(false)}
                  className="p-1 rounded-lg text-slate-400 hover:text-slate-700 transition"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Steps Progress Breadcrumb */}
              <div className="grid grid-cols-5 gap-2 text-center text-xs font-bold font-mono">
                {[
                  { num: 1, label: 'Basic Info' },
                  { num: 2, label: 'Questions' },
                  { num: 3, label: 'Rules' },
                  { num: 4, label: 'Proctoring' },
                  { num: 5, label: 'Publish' },
                ].map((s) => (
                  <div
                    key={s.num}
                    onClick={() => setCurrentStep(s.num)}
                    className={`p-2.5 rounded-xl border cursor-pointer transition ${
                      currentStep === s.num
                        ? 'bg-blue-600 text-white border-blue-600 shadow-sm'
                        : currentStep > s.num
                        ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                        : 'bg-slate-100 text-slate-500 border-slate-200'
                    }`}
                  >
                    <div>Step {s.num}</div>
                    <div className="text-[10px] font-normal truncate mt-0.5">{s.label}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Modal Body */}
            <div className="p-6 space-y-6 max-h-[65vh] overflow-y-auto">
              
              {/* STEP 1: Basic Information */}
              {currentStep === 1 && (
                <div className="space-y-4">
                  <h3 className="text-base font-bold text-slate-900 flex items-center space-x-2">
                    <span>Step 1 — Basic Information & Sections</span>
                  </h3>

                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">Assessment Name *</label>
                    <input
                      type="text"
                      value={title}
                      onChange={(e) => setTitle(e.target.value)}
                      placeholder="e.g. Python Backend Developer"
                      className="w-full bg-white border border-slate-300 rounded-xl px-3.5 py-2.5 text-xs text-slate-900 outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 font-medium"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">Description</label>
                    <textarea
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      rows={2}
                      placeholder="Backend developer screening assessment"
                      className="w-full bg-white border border-slate-300 rounded-xl px-3.5 py-2 text-xs text-slate-900 outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-semibold text-slate-700 mb-1">Core Section Title</label>
                      <input
                        type="text"
                        value={sectionTitle}
                        onChange={(e) => setSectionTitle(e.target.value)}
                        placeholder="e.g. Core Engineering Section"
                        className="w-full bg-white border border-slate-300 rounded-xl px-3.5 py-2 text-xs text-slate-900 outline-none focus:border-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-slate-700 mb-1">Section Cut-off Marks</label>
                      <input
                        type="number"
                        value={sectionCutOff}
                        onChange={(e) => setSectionCutOff(e.target.value)}
                        className="w-full bg-white border border-slate-300 rounded-xl px-3.5 py-2 text-xs text-slate-900 font-mono outline-none focus:border-blue-500"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <label className="block text-xs font-semibold text-slate-700 mb-1">Duration (minutes)</label>
                      <input
                        type="number"
                        value={duration}
                        onChange={(e) => setDuration(e.target.value)}
                        className="w-full bg-white border border-slate-300 rounded-xl px-3.5 py-2 text-xs text-slate-900 font-mono outline-none focus:border-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-slate-700 mb-1">Total Marks</label>
                      <input
                        type="number"
                        value={totalMarks}
                        onChange={(e) => setTotalMarks(e.target.value)}
                        className="w-full bg-white border border-slate-300 rounded-xl px-3.5 py-2 text-xs text-slate-900 font-mono outline-none focus:border-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-slate-700 mb-1">Passing Marks</label>
                      <input
                        type="number"
                        value={passingMarks}
                        onChange={(e) => setPassingMarks(e.target.value)}
                        className="w-full bg-white border border-slate-300 rounded-xl px-3.5 py-2 text-xs text-slate-900 font-mono outline-none focus:border-blue-500"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <label className="block text-xs font-semibold text-slate-700 mb-1">Attempt Limit</label>
                      <input
                        type="number"
                        min="1"
                        max="10"
                        value={attemptLimit}
                        onChange={(e) => setAttemptLimit(e.target.value)}
                        className="w-full bg-white border border-slate-300 rounded-xl px-3 py-1.5 text-xs text-slate-900 font-mono outline-none focus:border-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-slate-700 mb-1">Start Window</label>
                      <input
                        type="datetime-local"
                        value={startDate}
                        onChange={(e) => setStartDate(e.target.value)}
                        className="w-full bg-white border border-slate-300 rounded-xl px-3 py-1.5 text-xs text-slate-900 outline-none focus:border-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-slate-700 mb-1">End Window</label>
                      <input
                        type="datetime-local"
                        value={endDate}
                        onChange={(e) => setEndDate(e.target.value)}
                        className="w-full bg-white border border-slate-300 rounded-xl px-3 py-1.5 text-xs text-slate-900 outline-none focus:border-blue-500"
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* STEP 2: Questions Selection */}
              {currentStep === 2 && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-base font-bold text-slate-900">
                      Step 2 — Select Questions ({selectedQuestionIds.length} Selected)
                    </h3>
                    <span className="text-xs font-mono font-bold text-blue-600 bg-blue-50 px-2.5 py-1 rounded-lg border border-blue-200">
                      {selectedQuestionIds.length} / {availableQuestions.length} Questions
                    </span>
                  </div>

                  {/* Filters */}
                  <div className="grid grid-cols-4 gap-2">
                    <input
                      type="text"
                      placeholder="Search questions..."
                      value={qSearch}
                      onChange={(e) => setQSearch(e.target.value)}
                      className="bg-white border border-slate-300 rounded-xl px-3 py-1.5 text-xs text-slate-900 outline-none focus:border-blue-500"
                    />
                    <select
                      value={qCategory}
                      onChange={(e) => setQCategory(e.target.value)}
                      className="bg-white border border-slate-300 text-xs text-slate-700 rounded-xl px-2 py-1.5 outline-none focus:border-blue-500"
                    >
                      <option value="ALL">All Categories</option>
                      <option value="python">Python</option>
                      <option value="dsa">DSA</option>
                      <option value="sql">SQL</option>
                    </select>
                    <select
                      value={qDifficulty}
                      onChange={(e) => setQDifficulty(e.target.value)}
                      className="bg-white border border-slate-300 text-xs text-slate-700 rounded-xl px-2 py-1.5 outline-none focus:border-blue-500"
                    >
                      <option value="ALL">All Difficulties</option>
                      <option value="EASY">Easy</option>
                      <option value="MEDIUM">Medium</option>
                      <option value="HARD">Hard</option>
                    </select>
                    <select
                      value={qType}
                      onChange={(e) => setQType(e.target.value)}
                      className="bg-white border border-slate-300 text-xs text-slate-700 rounded-xl px-2 py-1.5 outline-none focus:border-blue-500"
                    >
                      <option value="ALL">All Types</option>
                      <option value="MCQ_SINGLE">MCQ Single</option>
                      <option value="MCQ_MULTIPLE">MCQ Multiple</option>
                      <option value="TRUE_FALSE">True / False</option>
                      <option value="DESCRIPTIVE">Descriptive</option>
                      <option value="CODING">Coding (Multi-Language)</option>
                    </select>

                  </div>

                  {/* Questions List */}
                  <div className="border border-slate-200 rounded-xl divide-y divide-slate-100 max-h-72 overflow-y-auto">
                    {filteredQuestions.map((q) => {
                      const isSelected = selectedQuestionIds.includes(q.id);
                      return (
                        <div
                          key={q.id}
                          onClick={() => handleToggleQuestion(q.id)}
                          className={`p-3 text-xs flex items-center justify-between cursor-pointer transition ${
                            isSelected ? 'bg-blue-50/70 border-l-4 border-blue-600' : 'hover:bg-slate-50'
                          }`}
                        >
                          <div className="flex items-center space-x-3">
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={() => {}}
                              className="rounded text-blue-600 focus:ring-blue-500 w-4 h-4 cursor-pointer"
                            />
                            <div>
                              <div className="font-bold text-slate-900">{q.title}</div>
                              <div className="text-[11px] text-slate-500 font-mono">
                                Type: {q.question_type} • Diff: {q.difficulty} • Marks: {q.marks || 2}
                              </div>
                            </div>
                          </div>

                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            q.difficulty === 'HARD' ? 'bg-rose-50 text-rose-700 border border-rose-200' :
                            q.difficulty === 'MEDIUM' ? 'bg-amber-50 text-amber-700 border border-amber-200' :
                            'bg-emerald-50 text-emerald-700 border border-emerald-200'
                          }`}>
                            {q.difficulty}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* STEP 3: Examination Rules */}
              {currentStep === 3 && (
                <div className="space-y-4">
                  <h3 className="text-base font-bold text-slate-900">Step 3 — Candidate Rules & Navigation</h3>

                  {/* Navigation Mode */}
                  <div className="p-4 rounded-xl border border-slate-200 bg-slate-50 space-y-2">
                    <label className="block text-xs font-bold text-slate-900 mb-1">
                      Candidate Navigation Rule
                    </label>
                    <div className="grid grid-cols-2 gap-3">
                      <label className={`p-3 rounded-xl border cursor-pointer flex items-start space-x-2.5 transition ${
                        navigationMode === 'FREE' ? 'bg-blue-50/70 border-blue-500 ring-1 ring-blue-500' : 'bg-white border-slate-200'
                      }`}>
                        <input
                          type="radio"
                          name="navMode"
                          value="FREE"
                          checked={navigationMode === 'FREE'}
                          onChange={() => setNavigationMode('FREE')}
                          className="mt-0.5 text-blue-600 focus:ring-blue-500"
                        />
                        <div>
                          <div className="text-xs font-bold text-slate-900">Free Navigation</div>
                          <div className="text-[10px] text-slate-500">Candidates can freely jump between questions and review previous answers.</div>
                        </div>
                      </label>

                      <label className={`p-3 rounded-xl border cursor-pointer flex items-start space-x-2.5 transition ${
                        navigationMode === 'FORWARD_ONLY' ? 'bg-blue-50/70 border-blue-500 ring-1 ring-blue-500' : 'bg-white border-slate-200'
                      }`}>
                        <input
                          type="radio"
                          name="navMode"
                          value="FORWARD_ONLY"
                          checked={navigationMode === 'FORWARD_ONLY'}
                          onChange={() => setNavigationMode('FORWARD_ONLY')}
                          className="mt-0.5 text-blue-600 focus:ring-blue-500"
                        />
                        <div>
                          <div className="text-xs font-bold text-slate-900">Forward-Only (Linear)</div>
                          <div className="text-[10px] text-slate-500">Strictly sequential navigation. Once a question is answered/skipped, candidates cannot return.</div>
                        </div>
                      </label>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <label className="flex items-center space-x-2.5 p-3 rounded-xl border border-slate-200 bg-slate-50 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={randomizeQuestions}
                        onChange={(e) => setRandomizeQuestions(e.target.checked)}
                        className="rounded text-blue-600 focus:ring-blue-500 w-4 h-4"
                      />
                      <div>
                        <div className="text-xs font-bold text-slate-900">Randomize Questions</div>
                        <div className="text-[10px] text-slate-500">Shuffle question order per candidate</div>
                      </div>
                    </label>

                    <label className="flex items-center space-x-2.5 p-3 rounded-xl border border-slate-200 bg-slate-50 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={randomizeOptions}
                        onChange={(e) => setRandomizeOptions(e.target.checked)}
                        className="rounded text-blue-600 focus:ring-blue-500 w-4 h-4"
                      />
                      <div>
                        <div className="text-xs font-bold text-slate-900">Randomize Options</div>
                        <div className="text-[10px] text-slate-500">Shuffle MCQ options order</div>
                      </div>
                    </label>
                  </div>

                  {/* Marking Scheme */}
                  <div className="p-4 rounded-xl border border-slate-200 bg-slate-50 space-y-3">
                    <label className="flex items-center space-x-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={negativeMarking}
                        onChange={(e) => setNegativeMarking(e.target.checked)}
                        className="rounded text-blue-600 focus:ring-blue-500 w-4 h-4"
                      />
                      <span className="text-xs font-bold text-slate-900">Enable Negative Marking</span>
                    </label>

                    {negativeMarking && (
                      <div className="grid grid-cols-2 gap-4 pt-2">
                        <div>
                          <label className="block text-[11px] font-semibold text-slate-600 mb-1">Correct Answer Marks</label>
                          <input
                            type="number"
                            value={correctAnswerMarks}
                            onChange={(e) => setCorrectAnswerMarks(e.target.value)}
                            className="w-full bg-white border border-slate-300 rounded-lg px-2.5 py-1.5 text-xs text-slate-900 font-mono outline-none"
                          />
                        </div>
                        <div>
                          <label className="block text-[11px] font-semibold text-slate-600 mb-1">Wrong Answer Penalty</label>
                          <input
                            type="number"
                            step="0.25"
                            value={wrongAnswerPenalty}
                            onChange={(e) => setWrongAnswerPenalty(e.target.value)}
                            className="w-full bg-white border border-slate-300 rounded-lg px-2.5 py-1.5 text-xs text-rose-600 font-mono outline-none"
                          />
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* STEP 4: Proctoring Settings */}
              {currentStep === 4 && (
                <div className="space-y-4">
                  <h3 className="text-base font-bold text-slate-900">Step 4 — AI Proctoring Configuration</h3>

                  <div className="grid grid-cols-2 gap-3">
                    <label className="flex items-center space-x-2.5 p-3 rounded-xl border border-slate-200 bg-slate-50 cursor-pointer">
                      <input 
                        type="checkbox" 
                        checked={webcamRequired} 
                        onChange={(e) => setWebcamRequired(e.target.checked)} 
                        className="rounded text-blue-600 focus:ring-blue-500 w-4 h-4" 
                      />
                      <div>
                        <div className="text-xs font-bold text-slate-900">Webcam Surveillance</div>
                        <div className="text-[10px] text-slate-500">Live facial recognition & gaze audit</div>
                      </div>
                    </label>

                    <label className="flex items-center space-x-2.5 p-3 rounded-xl border border-slate-200 bg-slate-50 cursor-pointer">
                      <input 
                        type="checkbox" 
                        checked={fullscreenRequired} 
                        onChange={(e) => setFullscreenRequired(e.target.checked)} 
                        className="rounded text-blue-600 focus:ring-blue-500 w-4 h-4" 
                      />
                      <div>
                        <div className="text-xs font-bold text-slate-900">Fullscreen Lockdown</div>
                        <div className="text-[10px] text-slate-500">Restricts multi-monitor & OS shortcuts</div>
                      </div>
                    </label>

                    <label className="flex items-center space-x-2.5 p-3 rounded-xl border border-slate-200 bg-slate-50 cursor-pointer">
                      <input 
                        type="checkbox" 
                        checked={tabSwitchDetection} 
                        onChange={(e) => setTabSwitchDetection(e.target.checked)} 
                        className="rounded text-blue-600 focus:ring-blue-500 w-4 h-4" 
                      />
                      <div>
                        <div className="text-xs font-bold text-slate-900">Tab Switch Detection</div>
                        <div className="text-[10px] text-slate-500">Logs window blur events & strikes</div>
                      </div>
                    </label>

                    <label className="flex items-center space-x-2.5 p-3 rounded-xl border border-slate-200 bg-slate-50 cursor-pointer">
                      <input 
                        type="checkbox" 
                        checked={multipleFaceDetection} 
                        onChange={(e) => setMultipleFaceDetection(e.target.checked)} 
                        className="rounded text-blue-600 focus:ring-blue-500 w-4 h-4" 
                      />
                      <div>
                        <div className="text-xs font-bold text-slate-900">Multiple Face Alert</div>
                        <div className="text-[10px] text-slate-500">Flags impersonation and bystanders</div>
                      </div>
                    </label>

                    <label className="flex items-center space-x-2.5 p-3 rounded-xl border border-slate-200 bg-slate-50 cursor-pointer">
                      <input 
                        type="checkbox" 
                        checked={copyPasteDetection} 
                        onChange={(e) => setCopyPasteDetection(e.target.checked)} 
                        className="rounded text-blue-600 focus:ring-blue-500 w-4 h-4" 
                      />
                      <div>
                        <div className="text-xs font-bold text-slate-900">Clipboard Block</div>
                        <div className="text-[10px] text-slate-500">Prevents copy, cut, and paste</div>
                      </div>
                    </label>

                    <label className="flex items-center space-x-2.5 p-3 rounded-xl border border-slate-200 bg-slate-50 cursor-pointer">
                      <input 
                        type="checkbox" 
                        checked={devToolsDetection} 
                        onChange={(e) => setDevToolsDetection(e.target.checked)} 
                        className="rounded text-blue-600 focus:ring-blue-500 w-4 h-4" 
                      />
                      <div>
                        <div className="text-xs font-bold text-slate-900">DevTools Block</div>
                        <div className="text-[10px] text-slate-500">Detects F12 and inspect elements</div>
                      </div>
                    </label>
                  </div>
                </div>
              )}

              {/* STEP 5: Publish & Confirmation */}
              {currentStep === 5 && (
                <div className="space-y-4">
                  <h3 className="text-base font-bold text-slate-900 flex items-center space-x-2">
                    <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                    <span>Step 5 — Ready to Finalize Assessment</span>
                  </h3>

                  <div className="dash-card bg-slate-50 border border-slate-200 p-5 rounded-xl space-y-3 text-xs">
                    <div className="grid grid-cols-2 gap-3 text-slate-700">
                      <div>Assessment: <strong className="text-slate-900">{title}</strong></div>
                      <div>Section: <strong className="text-slate-900">{sectionTitle}</strong></div>
                      <div>Duration: <strong className="text-slate-900">{duration} minutes</strong></div>
                      <div>Questions: <strong className="text-blue-600">{selectedQuestionIds.length} Selected</strong></div>
                      <div>Passing Marks: <strong className="text-emerald-600">{passingMarks} / {totalMarks}</strong></div>
                      <div>Navigation: <strong className="text-slate-900">{navigationMode === 'FREE' ? 'Free Navigation' : 'Forward-Only'}</strong></div>
                      <div>Attempt Limit: <strong className="text-slate-900">{attemptLimit}</strong></div>
                      <div>Start Window: <strong className="text-slate-900">{startDate || 'Immediate'}</strong></div>
                    </div>

                    <div className="p-3 bg-white rounded-lg border border-slate-200 text-[11px] text-slate-600 space-y-1">
                      <div>• Proctoring Enforced: Webcam, Mic, Fullscreen & Anti-cheat tracking.</div>
                      <div>• Scoring: +{correctAnswerMarks} for correct, -{wrongAnswerPenalty} negative penalty.</div>
                      <div>• Assessment questions will be frozen to protect active attempts from changes.</div>
                    </div>
                  </div>
                </div>
              )}

            </div>

            {/* Modal Footer */}
            <div className="bg-slate-50 p-4 border-t border-slate-200 flex items-center justify-between">
              {currentStep > 1 ? (
                <button
                  onClick={() => setCurrentStep(prev => prev - 1)}
                  className="px-4 py-2 rounded-xl bg-white border border-slate-300 hover:bg-slate-100 text-slate-700 font-bold text-xs flex items-center space-x-1"
                >
                  <ChevronLeft className="w-4 h-4" />
                  <span>Previous</span>
                </button>
              ) : <div />}

              {currentStep < 5 ? (
                <button
                  onClick={() => setCurrentStep(prev => prev + 1)}
                  className="px-5 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs flex items-center space-x-1 shadow-md shadow-blue-500/25"
                >
                  <span>Save & Continue</span>
                  <ChevronRight className="w-4 h-4" />
                </button>
              ) : (
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => handleCreateAssessment('DRAFT')}
                    className="px-4 py-2 rounded-xl bg-white border border-slate-300 hover:bg-slate-100 text-slate-700 font-bold text-xs shadow-sm"
                  >
                    Save Draft
                  </button>
                  <button
                    onClick={() => handleCreateAssessment('SCHEDULE')}
                    className="px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-600 text-white font-bold text-xs shadow-sm flex items-center space-x-1"
                  >
                    <Calendar className="w-3.5 h-3.5" />
                    <span>Schedule</span>
                  </button>
                  <button
                    onClick={() => handleCreateAssessment('PUBLISH')}
                    className="px-5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs flex items-center space-x-1.5 shadow-md shadow-emerald-600/25"
                  >
                    <Sparkles className="w-4 h-4" />
                    <span>Publish Assessment</span>
                  </button>
                </div>
              )}
            </div>

          </div>
        </div>
      )}

      {/* Quick Schedule Modal */}
      {scheduleModalOpen && schedulingAssessment && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white max-w-md w-full rounded-2xl border border-slate-200 shadow-2xl p-6 space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100">
              <div className="flex items-center space-x-2">
                <Calendar className="w-5 h-5 text-amber-600" />
                <h3 className="text-base font-extrabold text-slate-900">Schedule Assessment</h3>
              </div>
              <button onClick={() => setScheduleModalOpen(false)} className="text-slate-400 hover:text-slate-700">
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-xs text-slate-500">
              Set availability window for <strong>{schedulingAssessment.title}</strong>. Candidates will only be able to take the test between these timestamps.
            </p>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Start Window *</label>
                <input
                  type="datetime-local"
                  required
                  value={modalStartTime}
                  onChange={(e) => setModalStartTime(e.target.value)}
                  className="w-full bg-white border border-slate-300 rounded-xl px-3 py-2 text-xs text-slate-900 outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">End Window *</label>
                <input
                  type="datetime-local"
                  required
                  value={modalEndTime}
                  onChange={(e) => setModalEndTime(e.target.value)}
                  className="w-full bg-white border border-slate-300 rounded-xl px-3 py-2 text-xs text-slate-900 outline-none focus:border-blue-500"
                />
              </div>
            </div>

            <div className="flex items-center justify-end space-x-2 pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setScheduleModalOpen(false)}
                className="px-4 py-2 rounded-xl border border-slate-200 text-xs font-bold text-slate-600 hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmSchedule}
                disabled={!modalStartTime || !modalEndTime}
                className="px-4 py-2 rounded-xl bg-amber-600 hover:bg-amber-700 text-white text-xs font-bold shadow-sm disabled:opacity-50"
              >
                Confirm Schedule
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
