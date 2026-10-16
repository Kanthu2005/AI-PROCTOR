import React, { useState, useEffect } from 'react';
import { api } from '../api';
import { useAuth } from '../context/AuthContext';
import { 
  Plus, 
  Search, 
  Filter, 
  Code2, 
  Database, 
  CheckCircle2, 
  HelpCircle, 
  FileText, 
  Tag, 
  Play, 
  Check, 
  AlertCircle,
  Clock,
  Sparkles,
  ArrowRight,
  BookOpen,
  Edit2,
  Trash2,
  X,
  History,
  Copy,
  ChevronLeft,
  ChevronRight,
  Layers,
  FileCode,
  CheckSquare,
  RotateCcw
} from 'lucide-react';

export default function QuestionBankManager() {
  const { user } = useAuth();
  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [totalCount, setTotalCount] = useState(0);

  // Filters & Pagination
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('ALL');
  const [difficultyFilter, setDifficultyFilter] = useState('ALL');
  const [reviewStatusFilter, setReviewStatusFilter] = useState('ALL');
  const [topicFilter, setTopicFilter] = useState('ALL');
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(6);

  // Modal States
  const [showFormModal, setShowFormModal] = useState(false);
  const [editingQuestionId, setEditingQuestionId] = useState(null); // null = Create, string = Edit
  const [showHistoryModal, setShowHistoryModal] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyQuestion, setHistoryQuestion] = useState(null);
  const [historyVersions, setHistoryVersions] = useState([]);

  // Form Fields
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [questionType, setQuestionType] = useState('MCQ_SINGLE');
  const [difficulty, setDifficulty] = useState('MEDIUM');
  const [topic, setTopic] = useState('Algorithms');
  const [tags, setTags] = useState('Python, DataStructures');
  const [positiveMarks, setPositiveMarks] = useState(2.0);
  const [negativeMarks, setNegativeMarks] = useState(0.5);
  const [reviewStatus, setReviewStatus] = useState('APPROVED');
  const [explanation, setExplanation] = useState('');

  // Options for MCQ / True-False / Fill-in-the-blank
  const [options, setOptions] = useState([
    { id: 'opt_1', text: 'Option A', is_correct: true },
    { id: 'opt_2', text: 'Option B', is_correct: false }
  ]);

  // Coding Question Fields
  const [starterCode, setStarterCode] = useState('def solve():\n    # Implement solution\n    pass\n');
  const [codingTestCases, setCodingTestCases] = useState([
    { input: '5\n1 2 3 4 5\n', expected_output: '5', is_hidden: false },
    { input: '3\n-1 -5 0\n', expected_output: '0', is_hidden: true }
  ]);

  // SQL Question Fields
  const [schemaSql, setSchemaSql] = useState('CREATE TABLE employees (\n  id INT PRIMARY KEY,\n  name VARCHAR(50),\n  salary INT\n);');
  const [solutionSql, setSolutionSql] = useState('SELECT name, salary FROM employees WHERE salary > 50000;');
  const [testQueries, setTestQueries] = useState('SELECT name, salary FROM employees WHERE salary > 50000;');

  useEffect(() => {
    loadQuestions();
  }, [user, search, typeFilter, difficultyFilter, reviewStatusFilter, topicFilter, currentPage, pageSize]);

  const loadQuestions = async () => {
    try {
      setLoading(true);
      const orgId = user?.org_id || 'test_org';
      const params = {
        search: search.trim() || undefined,
        type: typeFilter !== 'ALL' ? typeFilter : undefined,
        difficulty: difficultyFilter !== 'ALL' ? difficultyFilter : undefined,
        review_status: reviewStatusFilter !== 'ALL' ? reviewStatusFilter : undefined,
        topic: topicFilter !== 'ALL' ? topicFilter : undefined,
        page: currentPage,
        page_size: pageSize,
        paginated: true
      };

      const res = await api.listQuestions(orgId, params);
      if (res && res.items) {
        setQuestions(res.items);
        setTotalCount(res.total || 0);
      } else if (Array.isArray(res)) {
        setQuestions(res);
        setTotalCount(res.length);
      }
    } catch (err) {
      console.warn('Questions load fallback error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenCreate = () => {
    setEditingQuestionId(null);
    setTitle('');
    setDescription('');
    setQuestionType('MCQ_SINGLE');
    setDifficulty('MEDIUM');
    setTopic('General');
    setTags('Technical, Evaluation');
    setPositiveMarks(2.0);
    setNegativeMarks(0.5);
    setReviewStatus('APPROVED');
    setExplanation('');
    setOptions([
      { id: 'opt_1', text: 'Option A', is_correct: true },
      { id: 'opt_2', text: 'Option B', is_correct: false },
      { id: 'opt_3', text: 'Option C', is_correct: false },
      { id: 'opt_4', text: 'Option D', is_correct: false }
    ]);
    setStarterCode('def solve():\n    pass\n');
    setCodingTestCases([
      { input: '1 2\n', expected_output: '3', is_hidden: false }
    ]);
    setSchemaSql('CREATE TABLE records (id INT, value VARCHAR(50));');
    setSolutionSql('SELECT * FROM records;');
    setTestQueries('SELECT * FROM records;');
    setShowFormModal(true);
  };

  const handleOpenEdit = (q) => {
    const cv = q.current_version || {};
    setEditingQuestionId(q.id);
    setTitle(cv.title || '');
    setDescription(cv.description || '');
    setQuestionType(cv.question_type || q.question_type);
    setDifficulty(cv.difficulty || 'MEDIUM');
    setTopic(cv.topic || 'General');
    setTags(Array.isArray(cv.tags) ? cv.tags.join(', ') : 'Technical');
    setPositiveMarks(cv.default_positive_marks || 1.0);
    setNegativeMarks(cv.default_negative_marks || 0.0);
    setReviewStatus(cv.review_status || 'APPROVED');
    setExplanation(cv.explanation || '');

    if (cv.options && cv.options.length > 0) {
      setOptions(cv.options.map(o => ({ ...o })));
    } else {
      setOptions([
        { id: 'opt_1', text: 'Option A', is_correct: true },
        { id: 'opt_2', text: 'Option B', is_correct: false }
      ]);
    }

    if (cv.coding_details) {
      setStarterCode(cv.coding_details.starter_code || 'def solve():\n    pass\n');
      setCodingTestCases(cv.coding_details.test_cases || []);
    }

    if (cv.sql_details) {
      setSchemaSql(cv.sql_details.schema_sql || '');
      setSolutionSql(cv.sql_details.solution_sql || '');
      setTestQueries(Array.isArray(cv.sql_details.test_queries) ? cv.sql_details.test_queries.join('\n') : '');
    }

    setShowFormModal(true);
  };

  const handleOpenHistory = async (q) => {
    setHistoryQuestion(q);
    setShowHistoryModal(true);
    setHistoryLoading(true);
    try {
      const fullQ = await api.getQuestion(q.id);
      if (fullQ && fullQ.all_versions) {
        setHistoryVersions(fullQ.all_versions);
      } else {
        setHistoryVersions(q.all_versions || [q.current_version]);
      }
    } catch (err) {
      console.warn('History load fallback:', err);
      setHistoryVersions([q.current_version].filter(Boolean));
    } finally {
      setHistoryLoading(false);
    }
  };

  const handleSaveQuestion = async (e) => {
    e.preventDefault();
    try {
      setLoading(true);
      const orgId = user?.org_id || 'test_org';
      const parsedTags = tags.split(',').map(t => t.trim()).filter(Boolean);

      let payloadOptions = [];
      if (questionType === 'MCQ_SINGLE' || questionType === 'MCQ_MULTIPLE' || questionType === 'TRUE_FALSE') {
        payloadOptions = options.map((opt, idx) => ({
          id: opt.id || `opt_${idx + 1}`,
          text: opt.text,
          is_correct: Boolean(opt.is_correct),
          explanation: opt.explanation || undefined
        }));
      } else if (questionType === 'FILL_IN_BLANK') {
        payloadOptions = options.map((opt, idx) => ({
          id: opt.id || `fib_${idx + 1}`,
          text: opt.text,
          is_correct: true
        }));
      }

      const codingDetailsPayload = questionType === 'CODING' ? {
        language: 'python',
        starter_code: starterCode,
        test_cases: codingTestCases.map(tc => ({
          input: tc.input,
          expected_output: tc.expected_output,
          is_hidden: Boolean(tc.is_hidden),
          time_limit_ms: 2000,
          memory_limit_mb: 128
        }))
      } : undefined;

      const sqlDetailsPayload = questionType === 'SQL' ? {
        schema_sql: schemaSql,
        solution_sql: solutionSql,
        test_queries: testQueries.split('\n').filter(Boolean)
      } : undefined;

      if (editingQuestionId) {
        // UPDATE (Spawns a new QuestionVersion, keeping existing assessments immutable!)
        const updatePayload = {
          title,
          description,
          difficulty,
          topic,
          default_positive_marks: parseFloat(positiveMarks) || 1.0,
          default_negative_marks: parseFloat(negativeMarks) || 0.0,
          tags: parsedTags,
          explanation: explanation || undefined,
          options: payloadOptions,
          coding_details: codingDetailsPayload,
          sql_details: sqlDetailsPayload,
          review_status: reviewStatus,
          is_published: true
        };
        const updatedVersion = await api.updateQuestion(editingQuestionId, updatePayload);
        setShowFormModal(false);
        loadQuestions();
        alert(`Question updated! Created immutable Version ${updatedVersion.version_number}.`);
      } else {
        // CREATE Question + Version 1
        const createPayload = {
          org_id: orgId,
          title,
          description,
          question_type: questionType,
          difficulty,
          topic,
          default_positive_marks: parseFloat(positiveMarks) || 1.0,
          default_negative_marks: parseFloat(negativeMarks) || 0.0,
          tags: parsedTags,
          explanation: explanation || undefined,
          options: payloadOptions,
          coding_details: codingDetailsPayload,
          sql_details: sqlDetailsPayload,
          review_status: reviewStatus,
          is_published: true
        };
        await api.createQuestion(createPayload);
        setShowFormModal(false);
        loadQuestions();
        alert('New question created and persisted to Question Bank!');
      }
    } catch (err) {
      alert(`Save failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleDuplicateQuestion = async (qId) => {
    try {
      setLoading(true);
      await api.duplicateQuestion(qId);
      loadQuestions();
      alert('Question cloned as a new independent draft question!');
    } catch (err) {
      alert(`Duplicate failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleReviewQuestion = async (qId, statusVal) => {
    try {
      setLoading(true);
      await api.reviewQuestion(qId, statusVal);
      loadQuestions();
    } catch (err) {
      alert(`Status update failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteQuestion = async (qId) => {
    if (!confirm('Are you sure you want to delete this question? It will be marked inactive.')) return;
    try {
      setLoading(true);
      await api.deleteQuestion(qId);
      loadQuestions();
      alert('Question deleted.');
    } catch (err) {
      alert(`Delete failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));

  return (
    <div className="space-y-6 text-slate-800 font-['Plus_Jakarta_Sans',sans-serif]">
      
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight flex items-center gap-2">
            <span>Question Bank</span>
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-blue-100 text-blue-700">
              {totalCount} Total
            </span>
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Create, version, review, and filter technical questions across 7 question types.
          </p>
        </div>

        <button
          onClick={handleOpenCreate}
          className="px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow-md shadow-blue-500/25 flex items-center space-x-2 transition"
        >
          <Plus className="w-4 h-4" />
          <span>+ Create Question</span>
        </button>
      </div>

      {/* Multi-Criteria Search & Filters Bar */}
      <div className="bg-white rounded-2xl p-4 border border-slate-200/90 shadow-sm space-y-3">
        <div className="flex flex-col md:flex-row items-center gap-3">
          <div className="relative flex-1 w-full">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
            <input
              type="text"
              value={search}
              onChange={(e) => { setSearch(e.target.value); setCurrentPage(1); }}
              placeholder="Search by title, description, topic or tag..."
              className="w-full bg-slate-50 focus:bg-white border border-slate-200 focus:border-blue-500 rounded-xl pl-10 pr-4 py-2 text-xs sm:text-sm text-slate-900 outline-none transition"
            />
          </div>

          <div className="flex flex-wrap items-center gap-2 w-full md:w-auto">
            <select
              value={typeFilter}
              onChange={(e) => { setTypeFilter(e.target.value); setCurrentPage(1); }}
              className="bg-slate-50 border border-slate-200 text-xs text-slate-700 rounded-xl px-3 py-2 outline-none font-semibold cursor-pointer"
            >
              <option value="ALL">All Types</option>
              <option value="MCQ_SINGLE">MCQ Single</option>
              <option value="MCQ_MULTIPLE">MCQ Multiple</option>
              <option value="TRUE_FALSE">True / False</option>
              <option value="FILL_IN_BLANK">Fill in Blank</option>
              <option value="DESCRIPTIVE">Descriptive</option>
              <option value="CODING">Python Coding</option>
              <option value="SQL">SQL Query</option>
            </select>

            <select
              value={difficultyFilter}
              onChange={(e) => { setDifficultyFilter(e.target.value); setCurrentPage(1); }}
              className="bg-slate-50 border border-slate-200 text-xs text-slate-700 rounded-xl px-3 py-2 outline-none font-semibold cursor-pointer"
            >
              <option value="ALL">All Difficulties</option>
              <option value="EASY">Easy</option>
              <option value="MEDIUM">Medium</option>
              <option value="HARD">Hard</option>
            </select>

            <select
              value={reviewStatusFilter}
              onChange={(e) => { setReviewStatusFilter(e.target.value); setCurrentPage(1); }}
              className="bg-slate-50 border border-slate-200 text-xs text-slate-700 rounded-xl px-3 py-2 outline-none font-semibold cursor-pointer"
            >
              <option value="ALL">All Statuses</option>
              <option value="APPROVED">Approved</option>
              <option value="IN_REVIEW">In Review</option>
              <option value="DRAFT">Draft</option>
              <option value="PUBLISHED">Published</option>
            </select>
          </div>
        </div>
      </div>

      {/* Questions List */}
      <div className="space-y-3">
        {loading && questions.length === 0 ? (
          <div className="bg-white rounded-2xl p-12 text-center text-slate-400">
            <div className="animate-spin w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full mx-auto mb-2" />
            <p className="text-xs">Loading Question Bank items...</p>
          </div>
        ) : questions.length === 0 ? (
          <div className="bg-white rounded-2xl p-12 text-center text-slate-400 border border-slate-200">
            <BookOpen className="w-8 h-8 text-slate-300 mx-auto mb-2" />
            <p className="text-sm font-bold text-slate-700">No questions found</p>
            <p className="text-xs text-slate-400 mt-1">Try adjusting your filters or click "+ Create Question".</p>
          </div>
        ) : (
          questions.map((q) => {
            const cv = q.current_version || {};
            const qTypeLabel = cv.question_type || q.question_type;
            return (
              <div key={q.id} className="bg-white rounded-2xl p-5 border border-slate-200/90 shadow-xs hover:shadow-sm transition flex flex-col md:flex-row md:items-start justify-between gap-4">
                <div className="space-y-2 flex-1">
                  <div className="flex items-center space-x-2">
                    <span className="w-6 h-6 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center text-xs font-bold">
                      {qTypeLabel === 'CODING' ? <Code2 className="w-3.5 h-3.5" /> :
                       qTypeLabel === 'SQL' ? <Database className="w-3.5 h-3.5" /> :
                       qTypeLabel === 'TRUE_FALSE' ? <CheckSquare className="w-3.5 h-3.5" /> :
                       <HelpCircle className="w-3.5 h-3.5" />}
                    </span>
                    <h3 className="text-sm font-bold text-slate-900">
                      {cv.title || 'Untitled Question'}
                    </h3>
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
                      v{cv.version_number || q.current_version_number || 1}
                    </span>
                  </div>

                  <p className="text-xs text-slate-600 pl-8 leading-relaxed line-clamp-2">
                    {cv.description || 'No description provided.'}
                  </p>

                  {/* Metadata Chips: Topic, Difficulty, Tags, Marks, Review Status */}
                  <div className="flex flex-wrap items-center gap-1.5 pl-8 pt-1">
                    <span className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200">
                      {cv.topic || 'General'}
                    </span>
                    <span className={`px-2 py-0.5 rounded-md text-[10px] font-bold border ${
                      cv.difficulty === 'EASY' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
                      cv.difficulty === 'HARD' ? 'bg-rose-50 text-rose-700 border-rose-200' :
                      'bg-amber-50 text-amber-700 border-amber-200'
                    }`}>
                      {cv.difficulty || 'MEDIUM'}
                    </span>
                    <span className={`px-2 py-0.5 rounded-md text-[10px] font-bold border ${
                      cv.review_status === 'APPROVED' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
                      cv.review_status === 'IN_REVIEW' ? 'bg-amber-50 text-amber-700 border-amber-200' :
                      'bg-slate-100 text-slate-700 border-slate-200'
                    }`}>
                      {cv.review_status || 'APPROVED'}
                    </span>
                    {Array.isArray(cv.tags) && cv.tags.map((t, idx) => (
                      <span key={idx} className="px-2 py-0.5 rounded-md text-[10px] font-medium bg-slate-100 text-slate-600 border border-slate-200">
                        #{t}
                      </span>
                    ))}
                    <span className="text-[10px] font-mono font-semibold text-slate-500 pl-2">
                      +{cv.default_positive_marks ?? 1} marks / -{cv.default_negative_marks ?? 0} neg
                    </span>
                  </div>
                </div>

                {/* Actions: Edit, History, Review Toggle, Duplicate, Delete */}
                <div className="flex items-center space-x-1.5 self-end md:self-center flex-shrink-0">
                  <button
                    onClick={() => handleOpenEdit(q)}
                    className="p-1.5 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-100 border border-slate-200 transition"
                    title="Edit Question (Spawns a new version)"
                  >
                    <Edit2 className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => handleOpenHistory(q)}
                    className="p-1.5 rounded-lg text-xs font-semibold text-purple-700 hover:bg-purple-50 border border-purple-200 transition"
                    title="View Version History"
                  >
                    <History className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => handleReviewQuestion(q.id, cv.review_status === 'APPROVED' ? 'DRAFT' : 'APPROVED')}
                    className="px-2.5 py-1.5 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-100 border border-slate-200 transition"
                    title="Toggle Approval State"
                  >
                    {cv.review_status === 'APPROVED' ? 'Revoke' : 'Approve'}
                  </button>
                  <button
                    onClick={() => handleDuplicateQuestion(q.id)}
                    className="p-1.5 rounded-lg text-xs font-semibold text-blue-600 hover:bg-blue-50 border border-blue-200 transition"
                    title="Duplicate Question"
                  >
                    <Copy className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => handleDeleteQuestion(q.id)}
                    className="p-1.5 rounded-lg text-xs font-semibold text-rose-600 hover:bg-rose-50 border border-rose-200 transition"
                    title="Delete Question"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Pagination Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pt-2">
        <div className="text-xs text-slate-500 font-semibold">
          Showing Page {currentPage} of {totalPages} ({totalCount} questions)
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
            disabled={currentPage <= 1}
            className="px-3 py-1.5 rounded-xl border border-slate-200 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
            <span>Prev</span>
          </button>

          {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
            const pageNum = i + 1;
            return (
              <button
                key={pageNum}
                onClick={() => setCurrentPage(pageNum)}
                className={`w-8 h-8 rounded-xl text-xs font-bold transition ${
                  currentPage === pageNum ? 'bg-blue-600 text-white' : 'border border-slate-200 text-slate-700 hover:bg-slate-50'
                }`}
              >
                {pageNum}
              </button>
            );
          })}

          <button
            onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
            disabled={currentPage >= totalPages}
            className="px-3 py-1.5 rounded-xl border border-slate-200 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1"
          >
            <span>Next</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* CREATE & EDIT QUESTION MODAL */}
      {showFormModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl p-6 sm:p-8 max-w-2xl w-full border border-slate-200 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div>
                <h2 className="text-lg font-bold text-slate-900">
                  {editingQuestionId ? 'Edit Question (Creates New Version)' : 'Create New Question'}
                </h2>
                <p className="text-xs text-slate-500">
                  {editingQuestionId 
                    ? 'Changes will create an incremented version. Published assessments already using previous versions remain frozen and unaffected.' 
                    : 'Add a new question into the organization question bank.'}
                </p>
              </div>
              <button onClick={() => setShowFormModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSaveQuestion} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="sm:col-span-2">
                  <label className="block text-xs font-bold text-slate-700 mb-1">Question Title *</label>
                  <input
                    type="text"
                    required
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="e.g. What is the time complexity of binary search?"
                    className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3.5 py-2 text-xs text-slate-900 outline-none focus:border-blue-500 font-medium"
                  />
                </div>

                <div className="sm:col-span-2">
                  <label className="block text-xs font-bold text-slate-700 mb-1">Problem Statement / Description</label>
                  <textarea
                    rows={3}
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="Detailed question instructions, background, or code snippet..."
                    className="w-full bg-slate-50 border border-slate-300 rounded-xl p-3 text-xs text-slate-900 outline-none focus:border-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Question Type</label>
                  <select
                    value={questionType}
                    disabled={Boolean(editingQuestionId)}
                    onChange={(e) => setQuestionType(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3 py-2 text-xs text-slate-900 disabled:opacity-60"
                  >
                    <option value="MCQ_SINGLE">Single-Answer MCQ</option>
                    <option value="MCQ_MULTIPLE">Multiple-Select MCQ</option>
                    <option value="TRUE_FALSE">True / False</option>
                    <option value="FILL_IN_BLANK">Fill in the Blank</option>
                    <option value="DESCRIPTIVE">Descriptive / Subjective</option>
                    <option value="CODING">Python Coding</option>
                    <option value="SQL">SQL Coding</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Difficulty</label>
                  <select
                    value={difficulty}
                    onChange={(e) => setDifficulty(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3 py-2 text-xs text-slate-900"
                  >
                    <option value="EASY">Easy</option>
                    <option value="MEDIUM">Medium</option>
                    <option value="HARD">Hard</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Topic / Subject</label>
                  <input
                    type="text"
                    value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                    placeholder="e.g. Data Structures, SQL, Python"
                    className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3 py-2 text-xs text-slate-900"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Review Status</label>
                  <select
                    value={reviewStatus}
                    onChange={(e) => setReviewStatus(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3 py-2 text-xs text-slate-900"
                  >
                    <option value="APPROVED">Approved</option>
                    <option value="IN_REVIEW">In Review</option>
                    <option value="DRAFT">Draft</option>
                    <option value="PUBLISHED">Published</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Positive Marks</label>
                  <input
                    type="number"
                    step="0.5"
                    min="0"
                    value={positiveMarks}
                    onChange={(e) => setPositiveMarks(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3 py-2 text-xs text-slate-900"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Negative Marks</label>
                  <input
                    type="number"
                    step="0.25"
                    min="0"
                    value={negativeMarks}
                    onChange={(e) => setNegativeMarks(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3 py-2 text-xs text-slate-900"
                  />
                </div>
              </div>

              {/* Type-Specific Editors */}
              {/* 1. MCQ Single / Multiple / True-False */}
              {(questionType === 'MCQ_SINGLE' || questionType === 'MCQ_MULTIPLE' || questionType === 'TRUE_FALSE') && (
                <div className="space-y-2 p-3.5 bg-slate-50 border border-slate-200 rounded-2xl">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-bold text-slate-800">
                      Answer Options (Select correct answer)
                    </label>
                    {questionType !== 'TRUE_FALSE' && (
                      <button
                        type="button"
                        onClick={() => {
                          const n = options.length + 1;
                          setOptions([...options, { id: `opt_${n}`, text: `Option ${n}`, is_correct: false }]);
                        }}
                        className="text-[11px] font-bold text-blue-600 hover:text-blue-800"
                      >
                        + Add Choice
                      </button>
                    )}
                  </div>
                  <div className="space-y-2">
                    {options.map((opt, oIdx) => (
                      <div key={opt.id || oIdx} className="flex items-center space-x-2">
                        <input
                          type={questionType === 'MCQ_MULTIPLE' ? 'checkbox' : 'radio'}
                          name="correct_option_radio"
                          checked={opt.is_correct}
                          onChange={(e) => {
                            if (questionType === 'MCQ_MULTIPLE') {
                              setOptions(options.map((o, i) => i === oIdx ? { ...o, is_correct: e.target.checked } : o));
                            } else {
                              setOptions(options.map((o, i) => ({ ...o, is_correct: i === oIdx })));
                            }
                          }}
                          className="w-4 h-4 text-blue-600 rounded cursor-pointer"
                          title="Mark as correct answer"
                        />
                        <input
                          type="text"
                          value={opt.text}
                          onChange={(e) => {
                            const val = e.target.value;
                            setOptions(options.map((o, i) => i === oIdx ? { ...o, text: val } : o));
                          }}
                          placeholder={`Option ${oIdx + 1} text`}
                          className="flex-1 bg-white border border-slate-300 rounded-lg px-2.5 py-1.5 text-xs text-slate-800 outline-none"
                        />
                        {options.length > 2 && questionType !== 'TRUE_FALSE' && (
                          <button
                            type="button"
                            onClick={() => setOptions(options.filter((_, i) => i !== oIdx))}
                            className="text-slate-400 hover:text-rose-600 text-xs px-1"
                          >
                            ✕
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 2. Fill in the Blank */}
              {questionType === 'FILL_IN_BLANK' && (
                <div className="space-y-2 p-3.5 bg-slate-50 border border-slate-200 rounded-2xl">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-bold text-slate-800">
                      Accepted Answers for Blank
                    </label>
                    <button
                      type="button"
                      onClick={() => setOptions([...options, { id: `fib_${options.length + 1}`, text: '', is_correct: true }])}
                      className="text-[11px] font-bold text-blue-600 hover:text-blue-800"
                    >
                      + Add Accepted Answer
                    </button>
                  </div>
                  <div className="space-y-2">
                    {options.map((opt, oIdx) => (
                      <div key={oIdx} className="flex items-center space-x-2">
                        <span className="text-xs text-slate-400 font-mono">#{oIdx + 1}</span>
                        <input
                          type="text"
                          value={opt.text}
                          onChange={(e) => {
                            const val = e.target.value;
                            setOptions(options.map((o, i) => i === oIdx ? { ...o, text: val, is_correct: true } : o));
                          }}
                          placeholder="e.g. 443 or HTTPS"
                          className="flex-1 bg-white border border-slate-300 rounded-lg px-2.5 py-1.5 text-xs text-slate-800 outline-none"
                        />
                        {options.length > 1 && (
                          <button
                            type="button"
                            onClick={() => setOptions(options.filter((_, i) => i !== oIdx))}
                            className="text-slate-400 hover:text-rose-600 text-xs px-1"
                          >
                            ✕
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 3. Python Coding Details */}
              {questionType === 'CODING' && (
                <div className="space-y-3 p-3.5 bg-slate-50 border border-slate-200 rounded-2xl">
                  <div>
                    <label className="block text-xs font-bold text-slate-800 mb-1">Python Starter Code</label>
                    <textarea
                      rows={3}
                      value={starterCode}
                      onChange={(e) => setStarterCode(e.target.value)}
                      className="w-full bg-slate-900 text-emerald-400 font-mono text-xs border border-slate-700 rounded-xl p-3 outline-none"
                    />
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <label className="text-xs font-bold text-slate-800">Test Cases</label>
                      <button
                        type="button"
                        onClick={() => setCodingTestCases([...codingTestCases, { input: '', expected_output: '', is_hidden: false }])}
                        className="text-[11px] font-bold text-blue-600 hover:text-blue-800"
                      >
                        + Add Test Case
                      </button>
                    </div>

                    <div className="space-y-2">
                      {codingTestCases.map((tc, tcIdx) => (
                        <div key={tcIdx} className="p-2.5 bg-white border border-slate-200 rounded-xl space-y-1.5">
                          <div className="flex items-center justify-between text-[11px]">
                            <span className="font-bold text-slate-700">Test Case #{tcIdx + 1}</span>
                            <label className="flex items-center space-x-1 cursor-pointer">
                              <input
                                type="checkbox"
                                checked={tc.is_hidden}
                                onChange={(e) => {
                                  const checked = e.target.checked;
                                  setCodingTestCases(codingTestCases.map((t, i) => i === tcIdx ? { ...t, is_hidden: checked } : t));
                                }}
                                className="w-3.5 h-3.5 text-blue-600 rounded"
                              />
                              <span className="text-[11px] font-semibold text-slate-600">Hidden from Candidate</span>
                            </label>
                          </div>
                          <div className="grid grid-cols-2 gap-2">
                            <div>
                              <span className="text-[10px] text-slate-400 font-semibold">Standard Input</span>
                              <input
                                type="text"
                                value={tc.input}
                                onChange={(e) => {
                                  const val = e.target.value;
                                  setCodingTestCases(codingTestCases.map((t, i) => i === tcIdx ? { ...t, input: val } : t));
                                }}
                                placeholder="5\n10 20..."
                                className="w-full bg-slate-50 border border-slate-200 rounded-lg p-1.5 text-xs font-mono"
                              />
                            </div>
                            <div>
                              <span className="text-[10px] text-slate-400 font-semibold">Expected Output</span>
                              <input
                                type="text"
                                value={tc.expected_output}
                                onChange={(e) => {
                                  const val = e.target.value;
                                  setCodingTestCases(codingTestCases.map((t, i) => i === tcIdx ? { ...t, expected_output: val } : t));
                                }}
                                placeholder="30"
                                className="w-full bg-slate-50 border border-slate-200 rounded-lg p-1.5 text-xs font-mono"
                              />
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* 4. SQL Question Details */}
              {questionType === 'SQL' && (
                <div className="space-y-3 p-3.5 bg-slate-50 border border-slate-200 rounded-2xl">
                  <div>
                    <label className="block text-xs font-bold text-slate-800 mb-1">Schema SQL (Tables & Seed DDL)</label>
                    <textarea
                      rows={3}
                      value={schemaSql}
                      onChange={(e) => setSchemaSql(e.target.value)}
                      placeholder="CREATE TABLE ..."
                      className="w-full bg-slate-900 text-blue-300 font-mono text-xs border border-slate-700 rounded-xl p-3 outline-none"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-slate-800 mb-1">Reference Solution SQL (Hidden from candidates)</label>
                    <textarea
                      rows={2}
                      value={solutionSql}
                      onChange={(e) => setSolutionSql(e.target.value)}
                      placeholder="SELECT ..."
                      className="w-full bg-slate-900 text-emerald-400 font-mono text-xs border border-slate-700 rounded-xl p-3 outline-none"
                    />
                  </div>
                </div>
              )}

              {/* Explanation / Grading Rubric */}
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  Explanation / Grading Rubric (Hidden from candidate during exam)
                </label>
                <textarea
                  rows={2}
                  value={explanation}
                  onChange={(e) => setExplanation(e.target.value)}
                  placeholder="Official answer explanation or grading rubric guidelines..."
                  className="w-full bg-slate-50 border border-slate-300 rounded-xl p-2.5 text-xs text-slate-900 outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Tags (comma-separated)</label>
                <input
                  type="text"
                  value={tags}
                  onChange={(e) => setTags(e.target.value)}
                  placeholder="Python, Algorithms, Easy"
                  className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3.5 py-2 text-xs text-slate-900 outline-none"
                />
              </div>

              <div className="pt-3 border-t border-slate-100 flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setShowFormModal(false)}
                  className="px-4 py-2 rounded-xl border border-slate-300 text-xs font-semibold text-slate-600 hover:bg-slate-100"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow-md shadow-blue-500/25"
                >
                  {editingQuestionId ? 'Save As New Version' : 'Create Question'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* VERSION HISTORY MODAL */}
      {showHistoryModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl p-6 sm:p-8 max-w-xl w-full border border-slate-200 shadow-2xl space-y-4 max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div>
                <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <History className="w-5 h-5 text-purple-600" />
                  <span>Question Version History</span>
                </h2>
                <p className="text-xs text-slate-500">
                  {historyQuestion?.current_version?.title || 'Audit trail of immutable question versions.'}
                </p>
              </div>
              <button onClick={() => setShowHistoryModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            {historyLoading ? (
              <div className="p-8 text-center text-slate-400 text-xs">
                <div className="animate-spin w-5 h-5 border-2 border-purple-600 border-t-transparent rounded-full mx-auto mb-2" />
                Loading version revisions...
              </div>
            ) : historyVersions.length === 0 ? (
              <div className="p-8 text-center text-slate-400 text-xs">No version history available.</div>
            ) : (
              <div className="space-y-3">
                {historyVersions.map((v, idx) => (
                  <div key={v.id || idx} className="p-4 bg-slate-50 border border-slate-200 rounded-2xl space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <span className="px-2.5 py-0.5 rounded-full text-xs font-extrabold bg-purple-100 text-purple-800">
                          v{v.version_number}
                        </span>
                        <span className="text-xs font-bold text-slate-900">{v.title}</span>
                      </div>
                      <span className={`px-2 py-0.5 rounded-md text-[10px] font-bold border ${
                        v.review_status === 'APPROVED' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
                        'bg-slate-100 text-slate-700 border-slate-200'
                      }`}>
                        {v.review_status || 'APPROVED'}
                      </span>
                    </div>

                    <p className="text-xs text-slate-600 leading-relaxed">
                      {v.description || 'No description.'}
                    </p>

                    <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1 border-t border-slate-200/60 font-mono">
                      <span>Topic: {v.topic || 'General'} • Difficulty: {v.difficulty}</span>
                      <span>+{v.default_positive_marks} / -{v.default_negative_marks} pts</span>
                    </div>
                  </div>
                ))}
              </div>
            )}

            <div className="pt-2 flex justify-end">
              <button
                onClick={() => setShowHistoryModal(false)}
                className="px-4 py-2 rounded-xl border border-slate-200 text-xs font-semibold text-slate-700 hover:bg-slate-50"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
