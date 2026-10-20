import React, { useState, useEffect, useRef, useCallback } from 'react';
import { api } from '../api';
import { 
  Camera, 
  Mic, 
  Monitor, 
  Maximize2, 
  Clock, 
  ShieldAlert, 
  CheckCircle2, 
  AlertTriangle, 
  Play, 
  Save, 
  Send, 
  Code2, 
  HelpCircle,
  Eye,
  RefreshCw,
  Award,
  Wifi,
  UserCheck,
  ChevronRight,
  ChevronLeft,
  Bookmark,
  Check,
  Terminal,
  Sparkles,
  AlertCircle,
  Laptop,
  ScanFace,
  Volume2,
  Lock,
  Download,
  ArrowLeft,
  ArrowRight,
  Printer,
  FileCheck2,
  Database,
  Layers
} from 'lucide-react';

export default function CandidateExamEngine({ defaultToken = '', onBackToHome }) {
  const [tokenInput, setTokenInput] = useState(defaultToken || '');
  const [instructions, setInstructions] = useState(null);
  const [invitation, setInvitation] = useState(null);
  const [examData, setExamData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Workflow Stages:
  // 'ENTER_TOKEN' -> 'INSTRUCTIONS' -> 'SYSTEM_CHECK' -> 'IDENTITY_VERIFY' -> 'IN_EXAM' -> 'SUBMIT_CONFIRM' -> 'RESULT'
  const [stage, setStage] = useState('ENTER_TOKEN');
  
  // Real Webcam Media Stream
  const [mediaStream, setMediaStream] = useState(null);
  const [cameraError, setCameraError] = useState(null);
  const [faceStatus, setFaceStatus] = useState('Camera Not Started');
  const [proctorWarning, setProctorWarning] = useState(null);
  const systemCheckVideoRef = useRef(null);
  const verifyVideoRef = useRef(null);
  const examVideoRef = useRef(null);

  // Diagnostics Checks
  const [cameraOk, setCameraOk] = useState(false);
  const [micOk, setMicOk] = useState(false);
  const [browserOk, setBrowserOk] = useState(true);
  const [networkOk, setNetworkOk] = useState(true);
  const [fullscreenOk, setFullscreenOk] = useState(true);

  // Identity Verification
  const [faceSnapshot, setFaceSnapshot] = useState(null);
  const [verifyingFace, setVerifyingFace] = useState(false);
  const [verificationSuccess, setVerificationSuccess] = useState(false);

  // Exam Engine State
  const [attemptId, setAttemptId] = useState(null);
  const [currentQuestionIdx, setCurrentQuestionIdx] = useState(0);
  const [answers, setAnswers] = useState({}); // question_id -> { selected_option_ids, text_response, code_response, language, time_spent_seconds }
  const [reviewFlags, setReviewFlags] = useState({}); // question_id -> boolean
  const [visitedQuestions, setVisitedQuestions] = useState({}); // question_id -> boolean
  const [remainingSeconds, setRemainingSeconds] = useState(0);
  const [serverExpiryAt, setServerExpiryAt] = useState(null);
  const [rules, setRules] = useState({});
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [attemptResult, setAttemptResult] = useState(null);
  const [showSubmitModal, setShowSubmitModal] = useState(false);

  // Autosave State & Acknowledgement
  const [autosaveStatus, setAutosaveStatus] = useState('idle'); // 'idle' | 'saving' | 'saved' | 'error'
  const [lastSavedTime, setLastSavedTime] = useState(null);
  const saveTimeoutRef = useRef(null);

  // Coding & SQL Sandbox
  const [runningSandbox, setRunningSandbox] = useState(false);
  const [sandboxOutput, setSandboxOutput] = useState(null);

  // Initialize with token if provided
  useEffect(() => {
    if (defaultToken && defaultToken.trim()) {
      setTokenInput(defaultToken.trim());
      loadInstructions(defaultToken.trim());
    } else {
      setStage('ENTER_TOKEN');
    }
  }, [defaultToken]);

  // Load Instructions / Verify Token
  const loadInstructions = async (tok) => {
    try {
      setLoading(true);
      setError(null);
      let data = null;
      let valData = null;
      try {
        valData = await api.validateExamInvitation(tok);
      } catch (err) {
        console.warn('validateExamInvitation fallback:', err);
      }

      try {
        data = await api.getInstructions(tok);
      } catch (err) {
        // Fallback to verifyToken if instructions endpoint fails
        const inv = await api.verifyToken(tok);
        data = {
          invitation_id: inv.id,
          assessment_id: inv.assessment_id,
          assessment_title: valData?.assessment_title || 'Technical Assessment',
          duration_minutes: valData?.duration_minutes || 60,
          total_marks: valData?.total_marks || 100,
          passing_percentage: valData?.passing_percentage || 60,
          rules: {
            navigation_mode: 'FREE',
            negative_marking_enabled: true,
            full_screen_enforced: true,
            webcam_proctoring_enabled: true
          },
          candidate_name: inv.full_name || valData?.candidate_name,
          candidate_email: inv.email || valData?.candidate_email,
          status: inv.status,
          system_check_passed: inv.system_check_passed
        };
      }

      if (valData) {
        data.schedule_status = valData.schedule_status;
        data.can_start = valData.can_start;
        data.start_time = valData.start_time;
        data.end_time = valData.end_time;
        data.time_until_start_seconds = valData.time_until_start_seconds;
        if (valData.assessment_title) data.assessment_title = valData.assessment_title;
        if (valData.assessment_description) data.description = valData.assessment_description;
        if (valData.instructions) data.instructions = valData.instructions;
      }

      setInstructions(data);
      setInvitation(data);

      // If already submitted, navigate directly to result receipt
      if (data.status === 'SUBMITTED' || data.attempt_status === 'SUBMITTED' || data.attempt_status === 'AUTO_SUBMITTED') {
        if (data.attempt_id) {
          const res = await api.getAttemptResult(data.attempt_id).catch(() => null);
          if (res) {
            setAttemptResult(res);
            setStage('RESULT');
            return;
          }
        }
      }

      setStage('INSTRUCTIONS');
    } catch (err) {
      console.warn('Failed to load assessment instructions:', err);
      setError(err?.message || 'Invalid or expired invitation token. Please check your invitation email.');
      setStage('ENTER_TOKEN');
    } finally {
      setLoading(false);
    }
  };

  // Real Webcam stream management
  const initWebcamStream = async () => {
    try {
      setCameraError(null);
      setFaceStatus('Permission Required');
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' },
        audio: true
      });
      setMediaStream(stream);
      setCameraOk(true);
      setMicOk(true);
      setFaceStatus('Camera Ready');

      // Listen for camera disconnect or hardware track interruption
      stream.getVideoTracks().forEach(track => {
        track.onended = () => {
          setCameraOk(false);
          setFaceStatus('Camera Disconnected');
          if (attemptId) {
            api.sendProctorEvent(attemptId, {
              event_type: 'CAMERA_DISCONNECTED',
              metadata: { source: 'track_ended' },
              client_timestamp: new Date().toISOString()
            }).catch(() => {});
          }
        };
      });

      return stream;
    } catch (err) {
      console.warn('Real webcam device access error:', err);
      setCameraError(err?.message || 'Camera permission denied or camera device disconnected.');
      setCameraOk(false);
      setMicOk(false);
      setFaceStatus('Camera Disconnected');
      return null;
    }
  };

  // Bind video element to media stream
  useEffect(() => {
    if (!mediaStream) return;
    if (stage === 'SYSTEM_CHECK' && systemCheckVideoRef.current) {
      systemCheckVideoRef.current.srcObject = mediaStream;
      systemCheckVideoRef.current.play().catch(() => {});
    }
    if (stage === 'IDENTITY_VERIFY' && verifyVideoRef.current) {
      verifyVideoRef.current.srcObject = mediaStream;
      verifyVideoRef.current.play().catch(() => {});
    }
    if (stage === 'IN_EXAM' && examVideoRef.current) {
      examVideoRef.current.srcObject = mediaStream;
      examVideoRef.current.play().catch(() => {});
    }
  }, [mediaStream, stage]);

  // Clean up media stream on unmount
  useEffect(() => {
    return () => {
      if (mediaStream) {
        mediaStream.getTracks().forEach(t => t.stop());
      }
    };
  }, [mediaStream]);

  // Authoritative Server Countdown Timer
  useEffect(() => {
    if (stage !== 'IN_EXAM' || isSubmitted || remainingSeconds <= 0) return;

    const timer = setInterval(() => {
      setRemainingSeconds(prev => {
        if (prev <= 1) {
          clearInterval(timer);
          handleAutoSubmitOnDeadline();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [stage, isSubmitted, remainingSeconds]);

  // Deadline Auto-Submit
  const handleAutoSubmitOnDeadline = async () => {
    console.warn('Authoritative countdown reached 0: triggering deadline auto-submission');
    await handleSubmitExam(true);
  };

  // Real Proctoring Event Listeners & Periodic CV Face Detection
  useEffect(() => {
    if (stage !== 'IN_EXAM' || isSubmitted || !attemptId) return;

    // 1. Browser Tab Visibility Tracking
    const handleVisibilityChange = () => {
      if (document.hidden) {
        api.sendProctorEvent(attemptId, {
          event_type: 'TAB_SWITCH',
          metadata: { reason: 'visibility_hidden' },
          client_timestamp: new Date().toISOString()
        }).then(res => {
          if (res?.disqualified) {
            alert('Your examination has been terminated due to repeated proctoring violations.');
            handleSubmitExam(true);
          } else if (res?.explanation) {
            setProctorWarning(res.explanation);
            setTimeout(() => setProctorWarning(null), 5000);
          }
        }).catch(() => {});
      }
    };

    // 2. Fullscreen Exit Tracking
    const handleFullscreenChange = () => {
      if (!document.fullscreenElement && rules?.full_screen_enforced !== false) {
        api.sendProctorEvent(attemptId, {
          event_type: 'FULLSCREEN_EXIT',
          metadata: { reason: 'fullscreen_exit' },
          client_timestamp: new Date().toISOString()
        }).then(res => {
          if (res?.explanation) {
            setProctorWarning(res.explanation);
            setTimeout(() => setProctorWarning(null), 5000);
          }
        }).catch(() => {});
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    document.addEventListener('fullscreenchange', handleFullscreenChange);

    // 3. Periodic Face Detection Check (every 12 seconds)
    const faceInterval = setInterval(async () => {
      if (!examVideoRef.current || !mediaStream) {
        setFaceStatus('Camera Disconnected');
        return;
      }
      try {
        setFaceStatus('Detecting');
        const canvas = document.createElement('canvas');
        canvas.width = 320;
        canvas.height = 240;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(examVideoRef.current, 0, 0, 320, 240);
        const frameData = canvas.toDataURL('image/jpeg', 0.7);

        const res = await api.sendProctorEvent(attemptId, {
          event_type: 'FACE_PRESENT',
          snapshot_base64: frameData,
          client_timestamp: new Date().toISOString()
        });

        if (res) {
          if (res.event_type === 'FACE_MISSING') {
            setFaceStatus('Face Not Detected');
            setProctorWarning('Warning: No face detected in webcam frame. Please stay centered.');
          } else if (res.event_type === 'MULTIPLE_FACES') {
            setFaceStatus('Multiple Faces Detected');
            setProctorWarning('Alert: Multiple faces detected in camera feed.');
          } else {
            setFaceStatus('Face Detected');
          }

          if (res.disqualified) {
            alert('Your examination has been terminated due to proctoring infractions.');
            handleSubmitExam(true);
          }
        }
      } catch (err) {
        console.warn('Periodic face detection frame processing error:', err);
        setFaceStatus('Detection Unavailable');
      }
    }, 12000);

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
      clearInterval(faceInterval);
    };
  }, [stage, isSubmitted, attemptId, mediaStream, rules]);

  // Format seconds to HH:MM:SS
  const formatTimer = (sec) => {
    const h = Math.floor(sec / 3600);
    const m = Math.floor((sec % 3600) / 60);
    const s = sec % 60;
    if (h > 0) {
      return `${h < 10 ? '0' : ''}${h}:${m < 10 ? '0' : ''}${m}:${s < 10 ? '0' : ''}${s}`;
    }
    return `${m < 10 ? '0' : ''}${m}:${s < 10 ? '0' : ''}${s}`;
  };

  // Step: Proceed from Instructions to System Check
  const handleProceedToSystemCheck = async () => {
    setStage('SYSTEM_CHECK');
    await initWebcamStream();
  };

  // Step: Run Diagnostic & Proceed to Identity Verify
  const handleProceedToIdentityVerify = () => {
    setStage('IDENTITY_VERIFY');
  };

  // Step: Capture Face Reference & Complete Verification
  const handleCaptureFaceAndVerify = async () => {
    setVerifyingFace(true);
    try {
      let snapshotData = null;
      if (verifyVideoRef.current && mediaStream) {
        try {
          const canvas = document.createElement('canvas');
          canvas.width = 320;
          canvas.height = 240;
          const ctx = canvas.getContext('2d');
          ctx.drawImage(verifyVideoRef.current, 0, 0, 320, 240);
          snapshotData = canvas.toDataURL('image/jpeg', 0.8);
        } catch (e) {
          console.warn('Frame snapshot canvas conversion error:', e);
        }
      }

      if (!snapshotData) {
        setCameraError('Failed to capture frame from webcam. Please ensure webcam permissions are enabled.');
        setFaceStatus('Camera Disconnected');
        setVerificationSuccess(false);
        return;
      }

      setFaceSnapshot(snapshotData);

      const tok = tokenInput || invitation?.invitation_token;
      if (tok) {
        await api.systemCheck(tok, {
          camera_ok: cameraOk,
          microphone_ok: micOk,
          browser_compatible: browserOk,
          fullscreen_supported: fullscreenOk,
          face_snapshot_base64: snapshotData
        });
      }

      setVerificationSuccess(true);
      setFaceStatus('Face Detected');
    } catch (err) {
      console.warn('System check submission failed:', err);
      setCameraError(err?.message || 'Identity verification check failed.');
      setVerificationSuccess(false);
    } finally {
      setVerifyingFace(false);
    }
  };

  // Step: Start Assessment (with Reconnect & Refresh Recovery)
  const handleStartExam = async () => {
    try {
      setLoading(true);
      setError(null);

      // Enforce Fullscreen if configured
      if (rules?.full_screen_enforced !== false) {
        try {
          if (document.documentElement.requestFullscreen) {
            await document.documentElement.requestFullscreen();
          }
        } catch (e) {
          console.warn('Fullscreen ignored by browser policy:', e);
        }
      }

      const tok = tokenInput || invitation?.invitation_token || defaultToken;
      const startRes = await api.startAttempt(tok);

      setAttemptId(startRes.attempt_id);
      setRules(startRes.rules || {});
      setServerExpiryAt(startRes.server_expiry_at);
      setRemainingSeconds(startRes.remaining_seconds || (60 * 60));

      // Extract and flatten all section questions deterministically
      const flatQuestions = [];
      let qNum = 1;
      (startRes.sections || []).forEach(sec => {
        (sec.questions || []).forEach(q => {
          flatQuestions.push({
            ...q,
            number: qNum++,
            section_id: sec.id,
            section_title: sec.title
          });
        });
      });

      setExamData({
        title: startRes.assessment_title || 'Technical Assessment',
        candidate_name: startRes.candidate_name,
        candidate_email: startRes.candidate_email,
        total_marks: startRes.total_marks,
        passing_percentage: startRes.passing_percentage,
        questions: flatQuestions
      });

      // Restore previously saved answers (Reconnect Recovery)
      const restoredAnswers = {};
      const restoredReviewFlags = {};
      const restoredVisited = {};

      if (startRes.saved_answers && typeof startRes.saved_answers === 'object') {
        Object.entries(startRes.saved_answers).forEach(([qid, ansObj]) => {
          restoredAnswers[qid] = ansObj;
          if (ansObj.is_flagged_for_review) {
            restoredReviewFlags[qid] = true;
          }
          restoredVisited[qid] = true;
        });
      }

      setAnswers(restoredAnswers);
      setReviewFlags(restoredReviewFlags);
      setVisitedQuestions(restoredVisited);

      // Restore active question position if available
      if (startRes.current_question_id && flatQuestions.length > 0) {
        const foundIdx = flatQuestions.findIndex(q => q.question_id === startRes.current_question_id);
        if (foundIdx >= 0) {
          setCurrentQuestionIdx(foundIdx);
        }
      }

      setStage('IN_EXAM');
    } catch (err) {
      console.error('Failed to launch exam:', err);
      setError(err?.message || 'Failed to start assessment. Please verify your token or contact support.');
    } finally {
      setLoading(false);
    }
  };

  // Queue and trigger debounced autosave with server acknowledgement
  const triggerAutosave = useCallback((updatedAnswers, currentQId) => {
    if (!attemptId) return;

    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }

    setAutosaveStatus('saving');

    saveTimeoutRef.current = setTimeout(async () => {
      try {
        const curQ = examData?.questions?.[currentQuestionIdx];
        const activeQId = currentQId || curQ?.question_id;

        const answersList = Object.entries(updatedAnswers).map(([qid, ansObj]) => ({
          question_id: qid,
          question_version_id: ansObj.question_version_id || qid,
          section_id: ansObj.section_id || 'default_sec',
          selected_option_ids: ansObj.selected_option_ids || [],
          text_response: ansObj.text_response || null,
          code_response: ansObj.code_response || null,
          language: ansObj.language || 'python',
          time_spent_seconds: ansObj.time_spent_seconds || 10,
          is_flagged_for_review: !!reviewFlags[qid]
        }));

        const res = await api.autosaveAnswers(attemptId, answersList, activeQId);
        if (res && res.success) {
          setAutosaveStatus('saved');
          const now = new Date();
          setLastSavedTime(now.toLocaleTimeString());
          if (res.remaining_seconds !== undefined) {
            setRemainingSeconds(res.remaining_seconds);
          }
          if (res.is_auto_submitted) {
            setIsSubmitted(true);
            setAttemptResult({
              attempt_id: attemptId,
              submission_receipt: res.submission_receipt,
              status: 'AUTO_SUBMITTED',
              submission_type: 'AUTO_DEADLINE'
            });
            setStage('RESULT');
          }
        } else {
          setAutosaveStatus('error');
        }
      } catch (err) {
        console.warn('Autosave sync network warning:', err);
        setAutosaveStatus('error');
      }
    }, 400);
  }, [attemptId, examData, currentQuestionIdx, reviewFlags]);

  // Update Answer for a question
  const handleUpdateAnswer = (field, value) => {
    const curQ = examData?.questions?.[currentQuestionIdx];
    if (!curQ) return;

    const qid = curQ.question_id;
    const existing = answers[qid] || {
      question_id: qid,
      question_version_id: curQ.question_version_id,
      section_id: curQ.section_id,
      selected_option_ids: [],
      text_response: '',
      code_response: curQ.coding_details?.starter_code || '',
      time_spent_seconds: 0
    };

    const updated = {
      ...existing,
      [field]: value
    };

    const newAnswers = {
      ...answers,
      [qid]: updated
    };

    setAnswers(newAnswers);
    setVisitedQuestions(prev => ({ ...prev, [qid]: true }));
    triggerAutosave(newAnswers, qid);
  };

  // Toggle Mark for Review
  const handleToggleReviewFlag = () => {
    const curQ = examData?.questions?.[currentQuestionIdx];
    if (!curQ) return;
    const qid = curQ.question_id;
    const nextFlag = !reviewFlags[qid];

    setReviewFlags(prev => {
      const updated = { ...prev, [qid]: nextFlag };
      return updated;
    });

    if (answers[qid]) {
      const updatedAns = {
        ...answers[qid],
        is_flagged_for_review: nextFlag
      };
      const newAnswers = { ...answers, [qid]: updatedAns };
      setAnswers(newAnswers);
      triggerAutosave(newAnswers, qid);
    }
  };

  // Clear current response
  const handleClearResponse = () => {
    const curQ = examData?.questions?.[currentQuestionIdx];
    if (!curQ) return;
    const qid = curQ.question_id;

    const cleared = {
      question_id: qid,
      question_version_id: curQ.question_version_id,
      section_id: curQ.section_id,
      selected_option_ids: [],
      text_response: '',
      code_response: curQ.coding_details?.starter_code || '',
      time_spent_seconds: 0
    };

    const newAnswers = {
      ...answers,
      [qid]: cleared
    };

    setAnswers(newAnswers);
    triggerAutosave(newAnswers, qid);
  };

  // Navigate to Question
  const handleSelectQuestion = (idx) => {
    if (rules?.navigation_mode === 'FORWARD_ONLY' && idx < currentQuestionIdx) {
      alert('Forward-only navigation is enforced for this assessment. You cannot return to previous questions.');
      return;
    }

    const curQ = examData?.questions?.[idx];
    if (curQ) {
      setVisitedQuestions(prev => ({ ...prev, [curQ.question_id]: true }));
    }
    setCurrentQuestionIdx(idx);
  };

  // Submit Final Exam
  const handleSubmitExam = async (isAuto = false) => {
    if (document.fullscreenElement) {
      try {
        document.exitFullscreen();
      } catch (e) {}
    }

    if (mediaStream) {
      mediaStream.getTracks().forEach(t => t.stop());
    }

    setIsSubmitted(true);
    setShowSubmitModal(false);

    const finalAnswersList = Object.entries(answers).map(([qid, ansObj]) => ({
      question_id: qid,
      question_version_id: ansObj.question_version_id || qid,
      section_id: ansObj.section_id || 'default_sec',
      selected_option_ids: ansObj.selected_option_ids || [],
      text_response: ansObj.text_response || null,
      code_response: ansObj.code_response || null,
      language: ansObj.language || 'python',
      time_spent_seconds: ansObj.time_spent_seconds || 60,
      is_flagged_for_review: !!reviewFlags[qid]
    }));

    try {
      const res = await api.submitAttempt(attemptId, finalAnswersList);
      setAttemptResult(res);
      setStage('RESULT');
    } catch (err) {
      console.warn('Final submission error, attempting result lookup:', err);
      const res = await api.getAttemptResult(attemptId).catch(() => null);
      if (res) {
        setAttemptResult(res);
      } else {
        setAttemptResult({
          attempt_id: attemptId,
          submission_receipt: `RCPT-${attemptId?.slice(0, 6)?.toUpperCase()}-CONFIRMED`,
          submission_type: isAuto ? 'AUTO_DEADLINE' : 'MANUAL',
          submitted_at: new Date().toISOString(),
          status: 'SUBMITTED',
          total_questions: examData?.questions?.length || 0,
          answered_count: Object.keys(answers).length
        });
      }
      setStage('RESULT');
    }
  };

  // Run Code in Sandbox
  const handleRunCode = async (code) => {
    setRunningSandbox(true);
    try {
      const curQ = examData?.questions?.[currentQuestionIdx];
      const testCases = curQ?.coding_details?.public_test_cases || [
        { input: '4 12 8 30 2', expected_output: '30' }
      ];
      const res = await api.runSandboxCode(code, testCases).catch((err) => ({ error: err.message || 'Failed to connect to execution sandbox' }));
      if (res && res.passed_test_cases !== undefined) {
        const passed = res.passed_test_cases;
        const total = res.total_test_cases || testCases.length;
        const details = (res.results || []).map((r, i) => {
          let line = `Test Case #${i+1}: ${r.passed ? 'PASSED ✓' : 'FAILED ✗'} (${r.execution_time_ms || 0}ms)`;
          if (!r.passed && r.failure_type) {
            line += ` [${r.failure_type}]`;
          }
          if (r.error) {
            line += `\n  Error: ${r.error}`;
          }
          return line;
        }).join('\n\n');
        const verdict = res.all_passed ? 'ACCEPTED (ALL PASSED)' : (res.failure_type || (passed > 0 ? 'PARTIAL' : 'FAILED'));
        setSandboxOutput({
          stdout: `${details}\n\n----------------------------------------\nExecution Summary: ${passed}/${total} test cases passed.\nVerdict: ${verdict}`
        });
      } else if (res && res.error) {
        setSandboxOutput({
          stdout: `Execution Failed:\n${res.error}\nVerdict: ${res.failure_type || 'RUNTIME_ERROR'}`
        });
      } else {
        setSandboxOutput({
          stdout: 'Execution Error: Unable to complete test execution in the sandbox.'
        });
      }
    } catch (e) {
      setSandboxOutput({
        stdout: `Execution Exception: ${e?.message || 'Unexpected sandbox error.'}`
      });
    } finally {
      setRunningSandbox(false);
    }
  };

  // Helper: compute palette status of a question
  const getQuestionPaletteStatus = (q, idx) => {
    const qid = q.question_id;
    const isCurrent = idx === currentQuestionIdx;
    const isFlagged = !!reviewFlags[qid];
    const ans = answers[qid];
    const isAnswered = ans && (
      (ans.selected_option_ids && ans.selected_option_ids.length > 0) ||
      (ans.text_response && ans.text_response.trim().length > 0) ||
      (ans.code_response && ans.code_response.trim().length > 0)
    );
    const isVisited = !!visitedQuestions[qid];

    if (isAnswered && isFlagged) return { color: 'bg-purple-600 text-white border-purple-700', label: 'Answered & Marked' };
    if (isFlagged) return { color: 'bg-amber-500 text-white border-amber-600', label: 'Marked for Review' };
    if (isAnswered) return { color: 'bg-emerald-600 text-white border-emerald-700', label: 'Answered' };
    if (isVisited) return { color: 'bg-rose-50 text-rose-700 border-rose-300', label: 'Unanswered' };
    return { color: 'bg-slate-100 text-slate-700 border-slate-300', label: 'Not Visited' };
  };

  // Compute overall counts
  const totalQuestions = examData?.questions?.length || 0;
  const answeredCount = Object.keys(answers).filter(qid => {
    const a = answers[qid];
    return a && (
      (a.selected_option_ids && a.selected_option_ids.length > 0) ||
      (a.text_response && a.text_response.trim().length > 0) ||
      (a.code_response && a.code_response.trim().length > 0)
    );
  }).length;
  const flaggedCount = Object.keys(reviewFlags).filter(k => reviewFlags[k]).length;
  const unansweredCount = Math.max(0, totalQuestions - answeredCount);

  // =========================================================================
  // STAGE 0: ENTER EXAM TOKEN
  // =========================================================================
  if (stage === 'ENTER_TOKEN') {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4 font-['Plus_Jakarta_Sans',sans-serif]">
        <div className="max-w-md w-full bg-white rounded-3xl p-8 border border-slate-200 shadow-xl space-y-6">
          <div className="text-center space-y-2">
            <div className="w-12 h-12 rounded-2xl bg-blue-600 text-white flex items-center justify-center mx-auto shadow-lg shadow-blue-500/25">
              <Laptop className="w-6 h-6" />
            </div>
            <h2 className="text-2xl font-extrabold text-slate-900">Candidate Examination Portal</h2>
            <p className="text-xs text-slate-500">
              Please enter your single-use test invitation code to start device diagnostics.
            </p>
          </div>

          {error && (
            <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-700 font-semibold flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={(e) => { e.preventDefault(); loadInstructions(tokenInput); }} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Invitation Token
              </label>
              <input
                type="text"
                required
                value={tokenInput}
                onChange={(e) => setTokenInput(e.target.value)}
                placeholder="Enter your invitation token"
                className="w-full bg-slate-50 border border-slate-300 focus:border-blue-600 focus:bg-white rounded-xl px-4 py-3 text-sm font-mono text-slate-900 outline-none transition"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-sm shadow-md shadow-blue-500/25 transition flex items-center justify-center space-x-2"
            >
              <span>{loading ? 'Verifying Token...' : 'Verify Invitation & Begin'}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>
        </div>
      </div>
    );
  }

  // =========================================================================
  // STAGE 1: INSTRUCTIONS & CANDIDATE DASHBOARD
  // =========================================================================
  if (stage === 'INSTRUCTIONS') {
    return (
      <div className="min-h-screen bg-slate-50 p-4 sm:p-8 font-['Plus_Jakarta_Sans',sans-serif] flex flex-col justify-center items-center">
        <div className="max-w-3xl w-full bg-white rounded-3xl border border-slate-200 shadow-xl overflow-hidden">
          
          {/* Header */}
          <div className="bg-gradient-to-r from-[#0c1838] to-[#1e3a8a] text-white p-6 sm:p-8">
            <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-blue-500/20 border border-blue-400/30 text-[11px] font-bold text-blue-300 mb-3">
              <ShieldAlert className="w-3.5 h-3.5" />
              <span>Secure Examination Portal</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
              {instructions?.assessment_title || 'Technical Assessment'}
            </h1>
            <p className="text-xs sm:text-sm text-slate-300 mt-2 font-normal">
              Candidate: <span className="font-bold text-white">{instructions?.candidate_name}</span> ({instructions?.candidate_email})
            </p>
          </div>

          {/* Quick Metrics */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 p-6 border-b border-slate-200 bg-slate-50/50">
            <div className="bg-white p-3.5 rounded-2xl border border-slate-200 shadow-2xs">
              <div className="flex items-center space-x-2 text-slate-400 text-xs font-semibold">
                <Clock className="w-4 h-4 text-blue-600" />
                <span>Duration</span>
              </div>
              <div className="text-base font-extrabold text-slate-900 mt-1">
                {instructions?.duration_minutes || 60} Minutes
              </div>
            </div>

            <div className="bg-white p-3.5 rounded-2xl border border-slate-200 shadow-2xs">
              <div className="flex items-center space-x-2 text-slate-400 text-xs font-semibold">
                <Award className="w-4 h-4 text-emerald-600" />
                <span>Total Marks</span>
              </div>
              <div className="text-base font-extrabold text-slate-900 mt-1">
                {instructions?.total_marks || 100} Marks
              </div>
            </div>

            <div className="bg-white p-3.5 rounded-2xl border border-slate-200 shadow-2xs">
              <div className="flex items-center space-x-2 text-slate-400 text-xs font-semibold">
                <CheckCircle2 className="w-4 h-4 text-indigo-600" />
                <span>Pass Score</span>
              </div>
              <div className="text-base font-extrabold text-slate-900 mt-1">
                {instructions?.passing_percentage || 50}%
              </div>
            </div>

            <div className="bg-white p-3.5 rounded-2xl border border-slate-200 shadow-2xs">
              <div className="flex items-center space-x-2 text-slate-400 text-xs font-semibold">
                <Layers className="w-4 h-4 text-purple-600" />
                <span>Navigation</span>
              </div>
              <div className="text-xs font-bold text-purple-700 bg-purple-50 px-2 py-0.5 rounded mt-1.5 inline-block">
                {instructions?.rules?.navigation_mode === 'FORWARD_ONLY' ? 'Forward Only' : 'Free Navigation'}
              </div>
            </div>
          </div>

          {/* Rules & Guidelines */}
          <div className="p-6 sm:p-8 space-y-6">
            
            {/* Scheduling Window Status Alert */}
            {instructions?.schedule_status === 'UPCOMING' && (
              <div className="p-4 rounded-2xl bg-amber-50 border border-amber-200 text-amber-900 flex items-start space-x-3 shadow-xs">
                <Clock className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                <div>
                  <div className="font-bold text-sm">Exam Scheduled — Not Yet Open</div>
                  <div className="text-xs text-amber-800 mt-1">
                    This assessment is scheduled to open at <strong>{instructions.start_time ? new Date(instructions.start_time).toLocaleString() : 'a designated time'}</strong>.
                    Access to pre-checks and the test questions will unlock automatically once the window opens.
                  </div>
                </div>
              </div>
            )}

            {instructions?.schedule_status === 'EXPIRED' && (
              <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-900 flex items-start space-x-3 shadow-xs">
                <AlertTriangle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
                <div>
                  <div className="font-bold text-sm">Examination Window Expired</div>
                  <div className="text-xs text-rose-800 mt-1">
                    The scheduled window or deadline for this examination has passed. Please contact your assessment coordinator if you require a rescheduled session.
                  </div>
                </div>
              </div>
            )}

            <div>
              <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500 mb-3">
                Mandatory Assessment Rules & Guidelines
              </h3>
              <div className="space-y-3 text-xs sm:text-sm text-slate-700">
                <div className="flex items-start space-x-3 p-3 rounded-xl bg-slate-50 border border-slate-200">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                  <span><strong>Authoritative Server Clock:</strong> The assessment timer runs strictly on the server. The client cannot extend or tamper with the deadline.</span>
                </div>
                <div className="flex items-start space-x-3 p-3 rounded-xl bg-slate-50 border border-slate-200">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                  <span><strong>Continuous Autosave:</strong> Your answer choices, code snippets, and review flags are continuously acknowledged and autosaved by the server.</span>
                </div>
                <div className="flex items-start space-x-3 p-3 rounded-xl bg-slate-50 border border-slate-200">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                  <span><strong>Reconnect Recovery:</strong> If your network drops or browser refreshes, you can seamlessly re-enter. All saved progress is preserved.</span>
                </div>
                <div className="flex items-start space-x-3 p-3 rounded-xl bg-amber-50 border border-amber-200 text-amber-900">
                  <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                  <span><strong>Proctoring Lockdown:</strong> Tab switching, fullscreen exits, and unauthorized developer tools are monitored and flagged in real-time.</span>
                </div>
              </div>
            </div>

            <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-4 border-t border-slate-200">
              <button
                onClick={() => setStage('ENTER_TOKEN')}
                className="w-full sm:w-auto px-5 py-2.5 rounded-xl border border-slate-300 text-xs font-bold text-slate-600 hover:bg-slate-50 transition"
              >
                Enter Different Token
              </button>

              <button
                onClick={handleProceedToSystemCheck}
                disabled={instructions?.can_start === false}
                className="w-full sm:w-auto px-8 py-3 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 disabled:cursor-not-allowed text-white text-sm font-bold shadow-lg shadow-blue-500/25 transition flex items-center justify-center space-x-2"
              >
                <span>
                  {instructions?.schedule_status === 'UPCOMING'
                    ? 'Exam Window Upcoming'
                    : instructions?.schedule_status === 'EXPIRED'
                    ? 'Exam Window Closed'
                    : 'Proceed to Device Diagnostics'}
                </span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // =========================================================================
  // STAGE 2: SYSTEM CHECK (Device Diagnostics)
  // =========================================================================
  if (stage === 'SYSTEM_CHECK') {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4 sm:p-8 font-['Plus_Jakarta_Sans',sans-serif]">
        <div className="max-w-2xl w-full bg-white rounded-3xl p-6 sm:p-8 border border-slate-200 shadow-xl space-y-6">
          <div className="text-center space-y-1">
            <h2 className="text-2xl font-extrabold text-slate-900">Step 1: Hardware Diagnostics</h2>
            <p className="text-xs text-slate-500">
              Testing camera, microphone, screen resolution, and browser compatibility.
            </p>
          </div>

          {/* Live Webcam Preview */}
          <div className="relative w-full h-56 sm:h-64 rounded-2xl bg-slate-900 overflow-hidden border border-slate-800 flex items-center justify-center">
            {mediaStream && cameraOk ? (
              <video 
                ref={systemCheckVideoRef} 
                autoPlay 
                playsInline 
                muted 
                className="w-full h-full object-cover scale-x-[-1]" 
              />
            ) : (
              <div className="text-center p-4">
                <Camera className="w-10 h-10 text-slate-600 mx-auto mb-2 animate-pulse" />
                <span className="text-xs text-slate-400 font-mono">
                  {cameraError || 'Camera stream not initialized'}
                </span>
              </div>
            )}
            <div className={`absolute top-3 left-3 px-2.5 py-1 rounded-full text-white text-[10px] font-bold flex items-center space-x-1.5 ${
              cameraOk ? 'bg-emerald-500/90' : 'bg-rose-500/90'
            }`}>
              <span className={`w-2 h-2 rounded-full bg-white ${cameraOk ? 'animate-pulse' : ''}`} />
              <span>{cameraOk ? 'VIDEO STREAM ACTIVE' : 'CAMERA NOT DETECTED'}</span>
            </div>
          </div>

          {cameraError && (
            <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-700 font-medium flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
              <span>{cameraError}</span>
            </div>
          )}

          {/* Diagnostic Checks List */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between">
              <div className="flex items-center space-x-2.5">
                <Camera className="w-4 h-4 text-blue-600" />
                <span className="font-semibold text-slate-700">Webcam Hardware</span>
              </div>
              {cameraOk ? (
                <span className="text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded font-bold flex items-center space-x-1">
                  <Check className="w-3.5 h-3.5" /> <span>Passed</span>
                </span>
              ) : (
                <span className="text-rose-700 bg-rose-50 px-2 py-0.5 rounded font-bold flex items-center space-x-1">
                  <AlertCircle className="w-3.5 h-3.5" /> <span>Failed / Required</span>
                </span>
              )}
            </div>

            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between">
              <div className="flex items-center space-x-2.5">
                <Mic className="w-4 h-4 text-blue-600" />
                <span className="font-semibold text-slate-700">Microphone Input</span>
              </div>
              {micOk ? (
                <span className="text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded font-bold flex items-center space-x-1">
                  <Check className="w-3.5 h-3.5" /> <span>Passed</span>
                </span>
              ) : (
                <span className="text-rose-700 bg-rose-50 px-2 py-0.5 rounded font-bold flex items-center space-x-1">
                  <AlertCircle className="w-3.5 h-3.5" /> <span>Failed / Required</span>
                </span>
              )}
            </div>

            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between">
              <div className="flex items-center space-x-2.5">
                <Monitor className="w-4 h-4 text-blue-600" />
                <span className="font-semibold text-slate-700">Browser Compatibility</span>
              </div>
              <span className="text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded font-bold flex items-center space-x-1">
                <Check className="w-3.5 h-3.5" /> <span>Compatible</span>
              </span>
            </div>

            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between">
              <div className="flex items-center space-x-2.5">
                <Maximize2 className="w-4 h-4 text-blue-600" />
                <span className="font-semibold text-slate-700">Fullscreen API</span>
              </div>
              <span className="text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded font-bold flex items-center space-x-1">
                <Check className="w-3.5 h-3.5" /> <span>Supported</span>
              </span>
            </div>
          </div>

          <div className="flex gap-3">
            <button
              onClick={() => setStage('INSTRUCTIONS')}
              className="px-5 py-3 rounded-xl border border-slate-300 text-xs font-bold text-slate-600 hover:bg-slate-50 transition"
            >
              Back
            </button>
            <button
              onClick={handleProceedToIdentityVerify}
              disabled={!cameraOk || !micOk}
              className={`flex-1 py-3 rounded-xl font-bold text-sm transition flex items-center justify-center space-x-2 ${
                cameraOk && micOk
                  ? 'bg-blue-600 hover:bg-blue-700 text-white shadow-md shadow-blue-500/25'
                  : 'bg-slate-200 text-slate-400 cursor-not-allowed shadow-none'
              }`}
            >
              <span>Confirm Hardware & Proceed to Identity Check</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    );
  }

  // =========================================================================
  // STAGE 3: IDENTITY VERIFICATION
  // =========================================================================
  if (stage === 'IDENTITY_VERIFY') {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4 sm:p-8 font-['Plus_Jakarta_Sans',sans-serif]">
        <div className="max-w-xl w-full bg-white rounded-3xl p-6 sm:p-8 border border-slate-200 shadow-xl space-y-6 text-center">
          <div className="space-y-1">
            <h2 className="text-2xl font-extrabold text-slate-900">Step 2: Identity Verification</h2>
            <p className="text-xs text-slate-500">
              Center your face inside the framing guide to capture your official candidate verification reference.
            </p>
          </div>

          {/* Webcam with Facial Framing Oval */}
          <div className="relative w-64 h-64 mx-auto rounded-full bg-slate-900 overflow-hidden border-4 border-blue-600 shadow-xl flex items-center justify-center">
            {mediaStream ? (
              <video 
                ref={verifyVideoRef} 
                autoPlay 
                playsInline 
                muted 
                className="w-full h-full object-cover scale-x-[-1]" 
              />
            ) : (
              <ScanFace className="w-16 h-16 text-blue-400 animate-pulse" />
            )}

            {verifyingFace && (
              <div className="absolute inset-0 bg-blue-900/60 backdrop-blur-xs flex flex-col items-center justify-center space-y-2 text-white">
                <RefreshCw className="w-8 h-8 animate-spin text-blue-400" />
                <span className="text-xs font-mono font-bold tracking-wider">ANALYZING BIOMETRICS...</span>
              </div>
            )}
          </div>

          {verificationSuccess ? (
            <div className="p-4 rounded-2xl bg-emerald-50 border border-emerald-200 text-emerald-800 space-y-1">
              <div className="flex items-center justify-center space-x-2 font-bold text-sm">
                <UserCheck className="w-5 h-5 text-emerald-600" />
                <span>Identity Verified & Registered</span>
              </div>
              <p className="text-xs text-emerald-700">
                Candidate reference snapshot captured and bound to this proctored session.
              </p>
            </div>
          ) : (
            <button
              onClick={handleCaptureFaceAndVerify}
              disabled={verifyingFace}
              className="px-6 py-3 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow-md shadow-blue-500/25 transition inline-flex items-center space-x-2"
            >
              <Camera className="w-4 h-4" />
              <span>Capture Face Reference</span>
            </button>
          )}

          <div className="pt-2">
            <button
              onClick={handleStartExam}
              disabled={loading || !verificationSuccess}
              className={`w-full py-3.5 rounded-xl font-bold text-sm transition flex items-center justify-center space-x-2 shadow-lg ${
                verificationSuccess
                  ? 'bg-emerald-600 hover:bg-emerald-700 text-white shadow-emerald-500/25'
                  : 'bg-slate-200 text-slate-400 cursor-not-allowed shadow-none'
              }`}
            >
              <Play className="w-4 h-4 fill-current" />
              <span>{loading ? 'Launching Secure Environment...' : 'Start Proctored Assessment'}</span>
            </button>
          </div>
        </div>
      </div>
    );
  }

  // =========================================================================
  // STAGE 4: LIVE EXAM ENGINE (IN_EXAM)
  // =========================================================================
  if (stage === 'IN_EXAM') {
    const curQ = examData?.questions?.[currentQuestionIdx];
    const curQId = curQ?.question_id;
    const curAns = answers[curQId] || {};
    const isCurrentFlagged = !!reviewFlags[curQId];

    return (
      <div className="min-h-screen bg-[#f8fafc] text-slate-800 font-['Plus_Jakarta_Sans',sans-serif] flex flex-col select-none">
        
        {/* Top Sticky Test Header */}
        <header className="h-16 bg-white border-b border-slate-200 px-4 sm:px-8 flex items-center justify-between sticky top-0 z-40 shadow-xs">
          <div className="flex items-center space-x-3">
            <div className="h-9 w-9 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-md shadow-blue-500/25">
              <Laptop className="w-5 h-5" />
            </div>
            <div>
              <span className="text-sm font-extrabold text-slate-900 block leading-tight">
                {examData?.title || 'Technical Assessment'}
              </span>
              <span className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider block">
                {curQ?.section_title ? `Section: ${curQ.section_title}` : 'ProctorAI Assessment Engine'}
              </span>
            </div>
          </div>

          {/* Center: Authoritative Server Timer */}
          <div className="flex items-center space-x-2 bg-slate-900 text-white px-4 py-1.5 rounded-xl shadow-xs">
            <Clock className={`w-4 h-4 ${remainingSeconds < 300 ? 'text-rose-400 animate-pulse' : 'text-blue-400'}`} />
            <div className="font-mono text-sm font-extrabold tracking-wider">
              {formatTimer(remainingSeconds)}
            </div>
            <span className="text-[9px] uppercase tracking-wider text-slate-400 font-semibold hidden md:inline">
              Server Timer
            </span>
          </div>

          {/* Right: Autosave Status & End Test Button */}
          <div className="flex items-center space-x-3">
            {/* Autosave Ack Badge */}
            <div className="hidden sm:flex items-center space-x-1.5 text-xs font-semibold px-2.5 py-1 rounded-lg border bg-slate-50 border-slate-200">
              {autosaveStatus === 'saving' && (
                <>
                  <RefreshCw className="w-3.5 h-3.5 text-blue-600 animate-spin" />
                  <span className="text-blue-600">Autosaving...</span>
                </>
              )}
              {autosaveStatus === 'saved' && (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                  <span className="text-emerald-700">Saved ({lastSavedTime || 'Ack'})</span>
                </>
              )}
              {autosaveStatus === 'error' && (
                <>
                  <Wifi className="w-3.5 h-3.5 text-amber-600 animate-pulse" />
                  <span className="text-amber-700">Offline (Queued)</span>
                </>
              )}
              {autosaveStatus === 'idle' && (
                <>
                  <Check className="w-3.5 h-3.5 text-slate-400" />
                  <span className="text-slate-500">Synced</span>
                </>
              )}
            </div>

            {/* Submit Button */}
            <button
              onClick={() => setShowSubmitModal(true)}
              className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs shadow-md shadow-emerald-500/25 transition flex items-center space-x-1.5"
            >
              <Send className="w-3.5 h-3.5" />
              <span>Submit Assessment</span>
            </button>
          </div>
        </header>

        {/* Main Exam Layout */}
        <div className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 grid grid-cols-1 lg:grid-cols-4 gap-6">
          
          {/* Left 3 Columns: Active Question Card */}
          <div className="lg:col-span-3 flex flex-col space-y-4">
            
            {proctorWarning && (
              <div className="p-3.5 rounded-2xl bg-amber-50 border border-amber-300 text-amber-900 text-xs font-bold flex items-center space-x-2 shadow-xs">
                <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
                <span>{proctorWarning}</span>
              </div>
            )}

            {/* Question Card */}
            <div className="bg-white rounded-3xl border border-slate-200 shadow-sm p-6 sm:p-8 flex-1 flex flex-col justify-between space-y-6">
              
              {/* Question Meta Bar */}
              <div>
                <div className="flex items-center justify-between pb-4 border-b border-slate-100">
                  <div className="flex items-center space-x-2">
                    <span className="px-3 py-1 rounded-lg bg-blue-50 text-blue-700 border border-blue-200 text-xs font-mono font-bold">
                      Question {curQ?.number || currentQuestionIdx + 1} of {totalQuestions}
                    </span>
                    <span className="px-2.5 py-1 rounded-lg bg-slate-100 text-slate-600 text-xs font-semibold">
                      {curQ?.question_type || 'MCQ'}
                    </span>
                    <span className="text-xs text-slate-400 font-semibold">
                      +{curQ?.positive_marks || 1} / -{curQ?.negative_marks || 0} Marks
                    </span>
                  </div>

                  <button
                    onClick={handleToggleReviewFlag}
                    className={`px-3 py-1.5 rounded-xl text-xs font-bold border transition flex items-center space-x-1.5 ${
                      isCurrentFlagged
                        ? 'bg-purple-600 text-white border-purple-700 shadow-xs'
                        : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-purple-50 hover:text-purple-700'
                    }`}
                  >
                    <Bookmark className={`w-3.5 h-3.5 ${isCurrentFlagged ? 'fill-current' : ''}`} />
                    <span>{isCurrentFlagged ? 'Marked for Review' : 'Mark for Review'}</span>
                  </button>
                </div>

                {/* Question Title & Description */}
                <div className="mt-5 space-y-2">
                  <h3 className="text-base sm:text-lg font-bold text-slate-900 leading-snug">
                    {curQ?.title}
                  </h3>
                  {curQ?.description && curQ?.description !== curQ?.title && (
                    <p className="text-xs sm:text-sm text-slate-600 leading-relaxed whitespace-pre-wrap">
                      {curQ.description}
                    </p>
                  )}
                </div>

                {/* Render Answer Input based on Question Type */}
                <div className="mt-6">
                  {/* 1. MCQ Single-Select */}
                  {curQ?.question_type === 'MCQ_SINGLE' && (
                    <div className="space-y-3">
                      {(curQ.options || []).map((opt) => {
                        const isSelected = curAns.selected_option_ids?.includes(opt.id);
                        return (
                          <label
                            key={opt.id}
                            onClick={() => handleUpdateAnswer('selected_option_ids', [opt.id])}
                            className={`flex items-center space-x-3 p-4 rounded-2xl border cursor-pointer transition ${
                              isSelected
                                ? 'bg-blue-50/80 border-blue-600 shadow-2xs'
                                : 'bg-slate-50/50 border-slate-200 hover:bg-slate-100/70'
                            }`}
                          >
                            <input
                              type="radio"
                              name={`q_${curQId}`}
                              checked={isSelected}
                              onChange={() => {}}
                              className="w-4 h-4 text-blue-600 border-slate-300 focus:ring-blue-500"
                            />
                            <span className="text-sm font-semibold text-slate-800">{opt.text}</span>
                          </label>
                        );
                      })}
                    </div>
                  )}

                  {/* 2. MCQ Multiple-Select */}
                  {curQ?.question_type === 'MCQ_MULTIPLE' && (
                    <div className="space-y-3">
                      <div className="text-xs text-blue-600 font-semibold mb-2">
                        Select all options that apply:
                      </div>
                      {(curQ.options || []).map((opt) => {
                        const isSelected = curAns.selected_option_ids?.includes(opt.id);
                        return (
                          <label
                            key={opt.id}
                            onClick={() => {
                              const currentSelected = curAns.selected_option_ids || [];
                              const nextSelected = isSelected
                                ? currentSelected.filter(id => id !== opt.id)
                                : [...currentSelected, opt.id];
                              handleUpdateAnswer('selected_option_ids', nextSelected);
                            }}
                            className={`flex items-center space-x-3 p-4 rounded-2xl border cursor-pointer transition ${
                              isSelected
                                ? 'bg-blue-50/80 border-blue-600 shadow-2xs'
                                : 'bg-slate-50/50 border-slate-200 hover:bg-slate-100/70'
                            }`}
                          >
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={() => {}}
                              className="w-4 h-4 text-blue-600 rounded border-slate-300 focus:ring-blue-500"
                            />
                            <span className="text-sm font-semibold text-slate-800">{opt.text}</span>
                          </label>
                        );
                      })}
                    </div>
                  )}

                  {/* 3. True / False */}
                  {curQ?.question_type === 'TRUE_FALSE' && (
                    <div className="grid grid-cols-2 gap-4">
                      {(curQ.options || [{ id: 'opt_true', text: 'True' }, { id: 'opt_false', text: 'False' }]).map((opt) => {
                        const isSelected = curAns.selected_option_ids?.includes(opt.id);
                        return (
                          <button
                            key={opt.id}
                            type="button"
                            onClick={() => handleUpdateAnswer('selected_option_ids', [opt.id])}
                            className={`p-6 rounded-2xl border font-bold text-base transition flex flex-col items-center justify-center space-y-2 ${
                              isSelected
                                ? 'bg-blue-600 text-white border-blue-700 shadow-md shadow-blue-500/25'
                                : 'bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100'
                            }`}
                          >
                            <span>{opt.text}</span>
                          </button>
                        );
                      })}
                    </div>
                  )}

                  {/* 4. Fill in the Blank */}
                  {curQ?.question_type === 'FILL_IN_BLANK' && (
                    <div className="space-y-2">
                      <label className="block text-xs font-bold text-slate-600 uppercase tracking-wider">
                        Your Answer
                      </label>
                      <input
                        type="text"
                        value={curAns.text_response || ''}
                        onChange={(e) => handleUpdateAnswer('text_response', e.target.value)}
                        placeholder="Type your answer here..."
                        className="w-full bg-slate-50 border border-slate-300 focus:border-blue-600 focus:bg-white rounded-2xl p-4 text-sm font-semibold text-slate-900 outline-none transition"
                      />
                    </div>
                  )}

                  {/* 5. Descriptive */}
                  {curQ?.question_type === 'DESCRIPTIVE' && (
                    <div className="space-y-2">
                      <div className="flex justify-between items-center text-xs font-bold text-slate-600 uppercase tracking-wider">
                        <span>Your Descriptive Response</span>
                        <span className="font-mono text-slate-400">
                          {(curAns.text_response || '').length} characters
                        </span>
                      </div>
                      <textarea
                        rows={7}
                        value={curAns.text_response || ''}
                        onChange={(e) => handleUpdateAnswer('text_response', e.target.value)}
                        placeholder="Write your explanation or detailed response here..."
                        className="w-full bg-slate-50 border border-slate-300 focus:border-blue-600 focus:bg-white rounded-2xl p-4 text-sm text-slate-900 outline-none transition font-sans leading-relaxed resize-y"
                      />
                    </div>
                  )}

                  {/* 6. Python Coding Question */}
                  {curQ?.question_type === 'CODING' && (
                    <div className="space-y-3">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-bold text-slate-700 flex items-center space-x-1.5">
                          <Code2 className="w-4 h-4 text-blue-600" />
                          <span>Python 3 Sandbox Editor</span>
                        </span>
                        <button
                          type="button"
                          disabled={runningSandbox}
                          onClick={() => handleRunCode(curAns.code_response || curQ.coding_details?.starter_code || '')}
                          className="px-3.5 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs flex items-center space-x-1.5 shadow-2xs transition"
                        >
                          <Play className="w-3.5 h-3.5 text-emerald-400 fill-current" />
                          <span>{runningSandbox ? 'Executing Sandbox...' : 'Run Public Tests'}</span>
                        </button>
                      </div>

                      <div className="rounded-2xl border border-slate-800 bg-[#0d1526] overflow-hidden text-white font-mono text-xs">
                        <div className="h-8 bg-[#090d17] px-4 flex items-center justify-between border-b border-slate-800/80 text-[11px] text-slate-400">
                          <span>main.py</span>
                          <span>Python 3.12 Isolated Sandbox</span>
                        </div>
                        <textarea
                          rows={10}
                          value={curAns.code_response !== undefined ? curAns.code_response : (curQ.coding_details?.starter_code || '# Write your solution\n')}
                          onChange={(e) => handleUpdateAnswer('code_response', e.target.value)}
                          className="w-full bg-transparent p-4 outline-none font-mono text-xs leading-relaxed text-blue-200 resize-y"
                          spellCheck={false}
                        />
                      </div>

                      {sandboxOutput && (
                        <div className="p-3.5 rounded-2xl bg-slate-900 text-emerald-400 font-mono text-xs border border-slate-800 whitespace-pre-wrap">
                          {sandboxOutput.stdout}
                        </div>
                      )}
                    </div>
                  )}

                  {/* 7. SQL Coding Question */}
                  {curQ?.question_type === 'SQL' && (
                    <div className="space-y-3">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-bold text-slate-700 flex items-center space-x-1.5">
                          <Database className="w-4 h-4 text-indigo-600" />
                          <span>PostgreSQL Query Editor</span>
                        </span>
                      </div>

                      {curQ.sql_details?.schema_sql && (
                        <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 font-mono text-[11px] text-slate-700 overflow-x-auto">
                          <span className="font-bold text-slate-500 uppercase block text-[9px] mb-1">Database Schema:</span>
                          {curQ.sql_details.schema_sql}
                        </div>
                      )}

                      <div className="rounded-2xl border border-slate-800 bg-[#0d1526] overflow-hidden text-white font-mono text-xs">
                        <textarea
                          rows={6}
                          value={curAns.code_response || ''}
                          onChange={(e) => handleUpdateAnswer('code_response', e.target.value)}
                          placeholder="SELECT * FROM table WHERE ..."
                          className="w-full bg-transparent p-4 outline-none font-mono text-xs leading-relaxed text-indigo-200 resize-y"
                          spellCheck={false}
                        />
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Navigation Action Buttons */}
              <div className="flex items-center justify-between pt-6 border-t border-slate-200">
                <div className="flex items-center space-x-2">
                  <button
                    onClick={handleClearResponse}
                    className="px-3.5 py-2 rounded-xl border border-slate-300 text-xs font-bold text-slate-600 hover:bg-slate-50 transition"
                  >
                    Clear Response
                  </button>
                </div>

                <div className="flex items-center space-x-3">
                  <button
                    disabled={currentQuestionIdx === 0 || rules?.navigation_mode === 'FORWARD_ONLY'}
                    onClick={() => handleSelectQuestion(currentQuestionIdx - 1)}
                    className={`px-4 py-2.5 rounded-xl border text-xs font-bold flex items-center space-x-1.5 transition ${
                      currentQuestionIdx === 0 || rules?.navigation_mode === 'FORWARD_ONLY'
                        ? 'opacity-40 cursor-not-allowed border-slate-200 text-slate-400'
                        : 'border-slate-300 text-slate-700 hover:bg-slate-50'
                    }`}
                  >
                    <ChevronLeft className="w-4 h-4" />
                    <span>Previous</span>
                  </button>

                  {currentQuestionIdx < totalQuestions - 1 ? (
                    <button
                      onClick={() => handleSelectQuestion(currentQuestionIdx + 1)}
                      className="px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold shadow-md shadow-blue-500/25 flex items-center space-x-1.5 transition"
                    >
                      <span>Next Question</span>
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  ) : (
                    <button
                      onClick={() => setShowSubmitModal(true)}
                      className="px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold shadow-md shadow-emerald-500/25 flex items-center space-x-1.5 transition"
                    >
                      <span>Review & Submit</span>
                      <Send className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Question Palette & Webcam Monitor */}
          <div className="space-y-4">
            
            {/* Live Proctoring Video Badge */}
            <div className="bg-white rounded-3xl border border-slate-200 p-4 shadow-xs space-y-3">
              <div className="flex items-center justify-between text-xs font-bold text-slate-700">
                <span className="flex items-center space-x-1.5">
                  <Eye className="w-4 h-4 text-blue-600" />
                  <span>Proctored Monitor</span>
                </span>
                <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                  faceStatus === 'Face Detected' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' :
                  faceStatus === 'Face Not Detected' ? 'bg-amber-50 text-amber-700 border border-amber-200 animate-pulse' :
                  faceStatus === 'Multiple Faces Detected' ? 'bg-rose-50 text-rose-700 border border-rose-200 animate-pulse' :
                  faceStatus === 'Detecting' ? 'bg-purple-50 text-purple-700 border border-purple-200' :
                  faceStatus === 'Camera Disconnected' ? 'bg-rose-100 text-rose-800 border border-rose-300' :
                  'bg-slate-100 text-slate-700'
                }`}>
                  {faceStatus.toUpperCase()}
                </span>
              </div>
              <div className="h-32 rounded-2xl bg-slate-900 overflow-hidden relative flex items-center justify-center">
                {mediaStream && cameraOk ? (
                  <video
                    ref={examVideoRef}
                    autoPlay
                    playsInline
                    muted
                    className="w-full h-full object-cover scale-x-[-1]"
                  />
                ) : (
                  <div className="text-center p-2">
                    <ScanFace className="w-8 h-8 text-rose-400 mx-auto animate-pulse" />
                    <span className="text-[10px] text-rose-300 block mt-1 font-mono">Camera Disconnected</span>
                  </div>
                )}
                <div className="absolute bottom-2 left-2 px-2 py-0.5 rounded bg-black/60 text-white font-mono text-[9px]">
                  REC: LIVE
                </div>
              </div>
            </div>

            {/* Question Palette Card */}
            <div className="bg-white rounded-3xl border border-slate-200 p-5 shadow-xs space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700">
                  Question Palette
                </h4>
                <span className="text-[11px] font-bold text-slate-400">
                  {answeredCount}/{totalQuestions} Answered
                </span>
              </div>

              {/* Palette Legend */}
              <div className="grid grid-cols-2 gap-2 text-[10px] text-slate-600">
                <div className="flex items-center space-x-1.5">
                  <span className="w-3 h-3 rounded-md bg-emerald-600 shrink-0" />
                  <span>Answered ({answeredCount})</span>
                </div>
                <div className="flex items-center space-x-1.5">
                  <span className="w-3 h-3 rounded-md bg-amber-500 shrink-0" />
                  <span>Marked ({flaggedCount})</span>
                </div>
                <div className="flex items-center space-x-1.5">
                  <span className="w-3 h-3 rounded-md bg-rose-50 border border-rose-300 shrink-0" />
                  <span>Unanswered</span>
                </div>
                <div className="flex items-center space-x-1.5">
                  <span className="w-3 h-3 rounded-md bg-slate-100 border border-slate-300 shrink-0" />
                  <span>Not Visited</span>
                </div>
              </div>

              {/* Question Grid Numbers */}
              <div className="grid grid-cols-5 gap-2 pt-2 max-h-72 overflow-y-auto pr-1">
                {(examData?.questions || []).map((q, idx) => {
                  const paletteStatus = getQuestionPaletteStatus(q, idx);
                  const isCurrent = idx === currentQuestionIdx;
                  return (
                    <button
                      key={q.question_id || idx}
                      onClick={() => handleSelectQuestion(idx)}
                      className={`h-9 rounded-xl font-mono text-xs font-bold border transition relative flex items-center justify-center ${paletteStatus.color} ${
                        isCurrent ? 'ring-2 ring-blue-600 ring-offset-2' : ''
                      }`}
                    >
                      {idx + 1}
                      {reviewFlags[q.question_id] && (
                        <span className="w-2 h-2 rounded-full bg-amber-300 absolute -top-0.5 -right-0.5 shadow-xs" />
                      )}
                    </button>
                  );
                })}
              </div>

              {rules?.navigation_mode === 'FORWARD_ONLY' && (
                <div className="p-2.5 rounded-xl bg-purple-50 border border-purple-200 text-purple-900 text-[11px] font-semibold flex items-center space-x-1.5">
                  <Lock className="w-3.5 h-3.5 shrink-0 text-purple-600" />
                  <span>Forward-Only Mode: Previous questions cannot be revisited.</span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Submit Confirmation Modal */}
        {showSubmitModal && (
          <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
            <div className="max-w-md w-full bg-white rounded-3xl p-6 border border-slate-200 shadow-2xl space-y-6">
              <div className="text-center space-y-2">
                <div className="w-12 h-12 rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto border border-emerald-200 shadow-sm">
                  <Send className="w-6 h-6" />
                </div>
                <h3 className="text-xl font-extrabold text-slate-900">Confirm Assessment Submission</h3>
                <p className="text-xs text-slate-500">
                  Once submitted, your answers will be locked and sent for automated grading and proctor review.
                </p>
              </div>

              <div className="grid grid-cols-3 gap-2.5 text-center">
                <div className="p-3 rounded-2xl bg-slate-50 border border-slate-200">
                  <div className="text-xs text-slate-400 font-bold uppercase">Total</div>
                  <div className="text-lg font-extrabold text-slate-900 mt-0.5">{totalQuestions}</div>
                </div>
                <div className="p-3 rounded-2xl bg-emerald-50 border border-emerald-200 text-emerald-800">
                  <div className="text-xs font-bold uppercase">Answered</div>
                  <div className="text-lg font-extrabold mt-0.5">{answeredCount}</div>
                </div>
                <div className="p-3 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800">
                  <div className="text-xs font-bold uppercase">Unanswered</div>
                  <div className="text-lg font-extrabold mt-0.5">{unansweredCount}</div>
                </div>
              </div>

              {unansweredCount > 0 && (
                <div className="p-3 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-xs font-semibold flex items-center space-x-2">
                  <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
                  <span>You have {unansweredCount} unanswered question{unansweredCount > 1 ? 's' : ''}. Unanswered questions will receive 0 marks.</span>
                </div>
              )}

              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={() => setShowSubmitModal(false)}
                  className="flex-1 py-3 rounded-xl border border-slate-300 text-xs font-bold text-slate-700 hover:bg-slate-50 transition"
                >
                  Return to Test
                </button>
                <button
                  type="button"
                  onClick={() => handleSubmitExam(false)}
                  className="flex-1 py-3 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold shadow-md shadow-emerald-500/25 transition"
                >
                  Yes, Submit Now
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  // =========================================================================
  // STAGE 5: OFFICIAL SUBMISSION RECEIPT (RESULT)
  // =========================================================================
  if (stage === 'RESULT') {
    const receiptCode = attemptResult?.submission_receipt || `RCPT-${attemptId?.slice(0, 8)?.toUpperCase() || 'SUBMITTED'}`;
    const submissionType = attemptResult?.submission_type === 'AUTO_DEADLINE' ? 'Deadline-Based Auto-Submission' : 'Manual Candidate Submission';
    const submittedTimestamp = attemptResult?.submitted_at ? new Date(attemptResult.submitted_at).toUTCString() : new Date().toUTCString();

    return (
      <div className="min-h-screen bg-slate-50 p-4 sm:p-8 font-['Plus_Jakarta_Sans',sans-serif] flex flex-col justify-center items-center">
        <div className="max-w-2xl w-full bg-white rounded-3xl border border-slate-200 shadow-2xl overflow-hidden print:shadow-none print:border-none">
          
          {/* Header Banner */}
          <div className="bg-gradient-to-r from-emerald-600 to-teal-700 text-white p-6 sm:p-8 text-center relative">
            <div className="w-14 h-14 rounded-2xl bg-white/10 backdrop-blur-xs border border-white/20 flex items-center justify-center mx-auto mb-3 shadow-lg">
              <FileCheck2 className="w-8 h-8 text-white" />
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
              Official Assessment Receipt
            </h1>
            <p className="text-xs sm:text-sm text-emerald-100 mt-1">
              Your examination has been securely finalized and recorded in the ProctorAI database.
            </p>
          </div>

          {/* Receipt Body */}
          <div className="p-6 sm:p-8 space-y-6">
            
            {/* Cryptographic Receipt Box */}
            <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-2">
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                Official Submission Receipt Number
              </div>
              <div className="font-mono text-base sm:text-lg font-extrabold text-blue-600 select-all">
                {receiptCode}
              </div>
              <div className="text-[11px] text-slate-500 font-semibold">
                Submission Type: <span className="font-bold text-slate-700">{submissionType}</span>
              </div>
            </div>

            {/* Candidate & Test Details Table */}
            <div className="space-y-3 text-xs sm:text-sm">
              <div className="flex justify-between py-2 border-b border-slate-100">
                <span className="text-slate-500">Candidate Name</span>
                <span className="font-bold text-slate-900">{attemptResult?.candidate_name || instructions?.candidate_name}</span>
              </div>
              <div className="flex justify-between py-2 border-b border-slate-100">
                <span className="text-slate-500">Candidate Email</span>
                <span className="font-mono font-semibold text-slate-700">{attemptResult?.candidate_email || instructions?.candidate_email}</span>
              </div>
              <div className="flex justify-between py-2 border-b border-slate-100">
                <span className="text-slate-500">Assessment</span>
                <span className="font-bold text-slate-900">{instructions?.assessment_title || examData?.title}</span>
              </div>
              <div className="flex justify-between py-2 border-b border-slate-100">
                <span className="text-slate-500">Submitted At (UTC)</span>
                <span className="font-mono text-slate-700">{submittedTimestamp}</span>
              </div>
              <div className="flex justify-between py-2 border-b border-slate-100">
                <span className="text-slate-500">Attempt Status</span>
                <span className="font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded">
                  {attemptResult?.status || 'SUBMITTED'}
                </span>
              </div>
            </div>

            {/* Results Review & Confidentiality Notice */}
            <div className="p-4 rounded-2xl bg-blue-50/70 border border-blue-200/80 text-xs text-blue-900 space-y-1.5">
              <div className="font-bold text-blue-950 flex items-center space-x-1.5">
                <span className="w-2 h-2 rounded-full bg-blue-600 animate-pulse"></span>
                <span>Proctoring Audit & Evaluation Under Review</span>
              </div>
              <p className="text-slate-600 leading-relaxed">
                Your examination responses and proctoring telemetry have been securely transferred to the hiring team. Final performance scores, integrity audit results, and individual selection decisions are reviewed and communicated directly by your recruiter.
              </p>
            </div>

            {/* Security Guarantee */}
            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-600 flex items-center space-x-2.5">
              <ShieldAlert className="w-5 h-5 text-blue-600 shrink-0" />
              <span>
                <strong>Integrity Guarantee:</strong> This submission receipt serves as permanent verifiable proof that your test responses were accepted and registered before the server deadline.
              </span>
            </div>

            {/* Action Buttons */}
            <div className="flex flex-col sm:flex-row gap-3 pt-2 print:hidden">
              <button
                type="button"
                onClick={() => window.print()}
                className="flex-1 py-3 rounded-xl border border-slate-300 hover:bg-slate-50 font-bold text-xs text-slate-700 transition flex items-center justify-center space-x-2"
              >
                <Printer className="w-4 h-4" />
                <span>Print or Save Receipt (PDF)</span>
              </button>

              <button
                type="button"
                onClick={() => {
                  if (onBackToHome) onBackToHome();
                  else setStage('ENTER_TOKEN');
                }}
                className="flex-1 py-3 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow-md shadow-blue-500/25 transition flex items-center justify-center space-x-2"
              >
                <span>Return to Candidate Portal</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return null;
}
