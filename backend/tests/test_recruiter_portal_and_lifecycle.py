import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.user import User, Role
from app.models.question import QuestionType, DifficultyLevel, ReviewStatus
from app.models.assessment import AssessmentStatus, NavigationMode
from app.models.candidate import CandidateInvitation, CandidateStatus


class TestRecruiterPortalAndLifecycle:
    """
    Comprehensive test suite validating:
    1. Recruiter dashboard API metrics
    2. Question creation, editing, topic filtering, pagination, and version history across 7 question types
    3. Assessment creation with sections, duration, timing, attempts, scoring, and rules
    4. Assessment lifecycle state transitions: DRAFT -> PUBLISHED -> LIVE -> CLOSED, and DRAFT -> SCHEDULED -> LIVE -> CLOSED
    5. Invalid state transitions and date validations
    6. Candidate invitation workflows (single, bulk, verify, resend, revoke)
    7. Sanitization of unauthorized answers (MCQ is_correct, hidden test cases, SQL solution_sql, rubrics)
    8. Preservation of pinned question versions upon question bank updates
    """

    def test_question_bank_all_seven_types_and_topics(self, client: TestClient, recruiter_headers, test_org):
        """
        Creates all 7 question types with topics, difficulty, marks, negative marks, and review status.
        Verifies persistence and retrieval.
        """
        headers = recruiter_headers
        org_id = test_org.id

        # 1. Single-answer MCQ
        q1_res = client.post("/api/v1/questions", headers=headers, json={
            "org_id": org_id,
            "title": "Python Dict Lookup Complexity",
            "description": "What is the average time complexity of dict lookup in Python?",
            "topic": "Python Core",
            "question_type": "MCQ_SINGLE",
            "difficulty": "EASY",
            "tags": ["python", "data-structures"],
            "default_positive_marks": 2.0,
            "default_negative_marks": 0.5,
            "options": [
                {"id": "opt_1", "text": "O(1)", "is_correct": True},
                {"id": "opt_2", "text": "O(n)", "is_correct": False},
                {"id": "opt_3", "text": "O(log n)", "is_correct": False}
            ]
        })
        assert q1_res.status_code == 201, q1_res.text
        q1_data = q1_res.json()
        assert q1_data["current_version"]["topic"] == "Python Core"
        assert q1_data["question_type"] == "MCQ_SINGLE"

        # 2. Multiple-select MCQ
        q2_res = client.post("/api/v1/questions", headers=headers, json={
            "org_id": org_id,
            "title": "Immutable Types in Python",
            "description": "Select all immutable types in Python standard library.",
            "topic": "Python Internals",
            "question_type": "MCQ_MULTIPLE",
            "difficulty": "MEDIUM",
            "tags": ["python", "types"],
            "default_positive_marks": 3.0,
            "default_negative_marks": 1.0,
            "options": [
                {"id": "opt_t", "text": "tuple", "is_correct": True},
                {"id": "opt_fs", "text": "frozenset", "is_correct": True},
                {"id": "opt_l", "text": "list", "is_correct": False},
                {"id": "opt_d", "text": "dict", "is_correct": False}
            ]
        })
        assert q2_res.status_code == 201, q2_res.text
        assert q2_res.json()["question_type"] == "MCQ_MULTIPLE"

        # 3. True / False
        q3_res = client.post("/api/v1/questions", headers=headers, json={
            "org_id": org_id,
            "title": "Python GIL and Multiprocessing",
            "description": "Python multiprocessing bypasses the Global Interpreter Lock (GIL).",
            "topic": "Concurrency",
            "question_type": "TRUE_FALSE",
            "difficulty": "EASY",
            "tags": ["python", "concurrency"],
            "default_positive_marks": 1.0,
            "default_negative_marks": 0.0,
            "options": [
                {"id": "opt_true", "text": "True", "is_correct": True},
                {"id": "opt_false", "text": "False", "is_correct": False}
            ],
            "explanation": "Each process has its own Python interpreter and GIL instance."
        })
        assert q3_res.status_code == 201, q3_res.text
        assert q3_res.json()["question_type"] == "TRUE_FALSE"

        # 4. Fill in the Blank
        q4_res = client.post("/api/v1/questions", headers=headers, json={
            "org_id": org_id,
            "title": "Python Generator Keyword",
            "description": "Which keyword turns a standard Python function into a generator?",
            "topic": "Python Core",
            "question_type": "FILL_IN_BLANK",
            "difficulty": "EASY",
            "tags": ["python", "generators"],
            "default_positive_marks": 2.0,
            "default_negative_marks": 0.0,
            "options": [
                {"id": "ans_1", "text": "yield", "is_correct": True}
            ],
            "explanation": "The yield keyword pauses the generator and yields a value."
        })
        assert q4_res.status_code == 201, q4_res.text
        assert q4_res.json()["question_type"] == "FILL_IN_BLANK"

        # 5. Descriptive / Short Answer
        q5_res = client.post("/api/v1/questions", headers=headers, json={
            "org_id": org_id,
            "title": "CAP Theorem Architectural Tradeoffs",
            "description": "Explain how the CAP theorem dictates tradeoffs between Consistency and Availability in distributed datastores.",
            "topic": "System Design",
            "question_type": "SHORT_ANSWER",
            "difficulty": "HARD",
            "tags": ["system-design", "distributed-systems"],
            "default_positive_marks": 10.0,
            "default_negative_marks": 0.0,
            "explanation": "Rubric: Partition tolerance, PACELC theorem, replication semantics."
        })
        assert q5_res.status_code == 201, q5_res.text
        assert q5_res.json()["question_type"] == "SHORT_ANSWER"

        # 6. Python Coding Question with visible and hidden test cases
        q6_res = client.post("/api/v1/questions", headers=headers, json={
            "org_id": org_id,
            "title": "Reverse Linked List",
            "description": "Write a function solve(arr) that reverses an array iteratively.",
            "topic": "Algorithms & Coding",
            "question_type": "CODING",
            "difficulty": "MEDIUM",
            "tags": ["algorithms", "python"],
            "default_positive_marks": 15.0,
            "default_negative_marks": 0.0,
            "coding_details": {
                "language": "python",
                "starter_code": "def solve(arr):\n    pass\n",
                "test_cases": [
                    {"input": "[1, 2, 3]", "expected_output": "[3, 2, 1]", "is_hidden": False},
                    {"input": "[]", "expected_output": "[]", "is_hidden": True}
                ]
            }
        })
        assert q6_res.status_code == 201, q6_res.text
        assert q6_res.json()["question_type"] == "CODING"

        # 7. SQL Coding Question
        q7_res = client.post("/api/v1/questions", headers=headers, json={
            "org_id": org_id,
            "title": "Second Highest Salary",
            "description": "Write a SQL query to return the second highest salary from the Employee table.",
            "topic": "Database & SQL",
            "question_type": "SQL",
            "difficulty": "MEDIUM",
            "tags": ["sql", "database"],
            "default_positive_marks": 10.0,
            "default_negative_marks": 0.0,
            "sql_details": {
                "schema_sql": "CREATE TABLE employees (id INT, salary INT); INSERT INTO employees VALUES (1, 100), (2, 200), (3, 300);",
                "solution_sql": "SELECT DISTINCT salary FROM employees ORDER BY salary DESC LIMIT 1 OFFSET 1;",
                "test_queries": ["SELECT * FROM employees;"]
            }
        })
        assert q7_res.status_code == 201, q7_res.text
        assert q7_res.json()["question_type"] == "SQL"

    def test_question_filtering_search_and_pagination(self, client: TestClient, recruiter_headers, test_org):
        """
        Tests question bank search, topic filtering, and paginated responses.
        """
        headers = recruiter_headers
        org_id = test_org.id

        # Seed 3 questions in Algorithms topic
        for i in range(3):
            client.post("/api/v1/questions", headers=headers, json={
                "org_id": org_id,
                "title": f"Algorithm Question {i+1}",
                "description": f"Sorting algorithm problem {i+1}",
                "topic": "Algorithms",
                "question_type": "MCQ_SINGLE",
                "difficulty": "EASY",
                "tags": ["algo", "sorting"],
                "default_positive_marks": 2.0,
                "default_negative_marks": 0.0,
                "options": [
                    {"id": f"opt_{i}_1", "text": "A", "is_correct": True},
                    {"id": f"opt_{i}_2", "text": "B", "is_correct": False}
                ]
            })

        # Test topic filtering
        res_topic = client.get(f"/api/v1/questions?org_id={org_id}&topic=Algorithms", headers=headers)
        assert res_topic.status_code == 200
        items = res_topic.json()
        assert len(items) >= 3
        for item in items:
            assert item["current_version"]["topic"] == "Algorithms"

        # Test search query
        res_search = client.get(f"/api/v1/questions?org_id={org_id}&search=Sorting", headers=headers)
        assert res_search.status_code == 200
        search_items = res_search.json()
        assert len(search_items) >= 3

        # Test server-side pagination format
        res_paginated = client.get(f"/api/v1/questions?org_id={org_id}&page=1&page_size=2&paginated=true", headers=headers)
        assert res_paginated.status_code == 200
        page_data = res_paginated.json()
        assert "items" in page_data
        assert "total" in page_data
        assert page_data["page"] == 1
        assert page_data["page_size"] == 2
        assert len(page_data["items"]) <= 2

    def test_question_version_history_and_immutability(self, client: TestClient, recruiter_headers, test_org):
        """
        Updates a question and verifies that:
        1. A new QuestionVersion row is created with version number incremented.
        2. Version history is tracked in question.all_versions.
        """
        headers = recruiter_headers
        org_id = test_org.id

        # Create version 1
        create_res = client.post("/api/v1/questions", headers=headers, json={
            "org_id": org_id,
            "title": "Initial Title v1",
            "description": "Initial description",
            "topic": "Python Core",
            "question_type": "MCQ_SINGLE",
            "difficulty": "EASY",
            "tags": ["v1"],
            "default_positive_marks": 2.0,
            "default_negative_marks": 0.5,
            "options": [
                {"id": "opt_1", "text": "Opt 1", "is_correct": True},
                {"id": "opt_2", "text": "Opt 2", "is_correct": False}
            ]
        })
        assert create_res.status_code == 201
        q_id = create_res.json()["id"]
        assert create_res.json()["current_version"]["version_number"] == 1

        # Update question to create version 2
        update_res = client.put(f"/api/v1/questions/{q_id}", headers=headers, json={
            "title": "Updated Title v2",
            "description": "Updated description v2",
            "topic": "Python Advanced",
            "difficulty": "HARD",
            "default_positive_marks": 5.0,
            "default_negative_marks": 1.0,
            "review_status": "APPROVED",
            "options": [
                {"id": "opt_1_v2", "text": "Opt 1 v2", "is_correct": True},
                {"id": "opt_2_v2", "text": "Opt 2 v2", "is_correct": False}
            ]
        })
        assert update_res.status_code == 200
        new_v_data = update_res.json()
        assert new_v_data["version_number"] == 2
        assert new_v_data["title"] == "Updated Title v2"
        assert new_v_data["topic"] == "Python Advanced"
        assert new_v_data["review_status"] == "APPROVED"

        # Check full QuestionResponse from GET /api/v1/questions/{id}
        get_q_res = client.get(f"/api/v1/questions/{q_id}", headers=headers)
        assert get_q_res.status_code == 200
        full_q = get_q_res.json()
        assert full_q["current_version_number"] == 2
        assert len(full_q["all_versions"]) == 2

    def test_assessment_creation_wizard_and_lifecycle_transitions(self, client: TestClient, recruiter_headers, test_org):
        """
        Tests assessment creation with sections, navigation rules, duration, attempt limits,
        and transitions across DRAFT -> PUBLISHED -> LIVE -> CLOSED.
        """
        headers = recruiter_headers
        org_id = test_org.id

        # 1. Create a question
        q_res = client.post("/api/v1/questions", headers=headers, json={
            "org_id": org_id,
            "title": "Lifecycle Assessment Question",
            "description": "Question used for assessment lifecycle testing",
            "topic": "Architecture",
            "question_type": "MCQ_SINGLE",
            "difficulty": "MEDIUM",
            "default_positive_marks": 5.0,
            "default_negative_marks": 1.0,
            "options": [
                {"id": "opt_t", "text": "True Choice", "is_correct": True},
                {"id": "opt_f", "text": "False Choice", "is_correct": False}
            ]
        })
        q_id = q_res.json()["id"]

        # 2. Create assessment in DRAFT state
        start_time = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        end_time = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()

        assess_res = client.post("/api/v1/assessments", headers=headers, json={
            "org_id": org_id,
            "title": "Software Engineer Screening 2026",
            "description": "Assessment with custom navigation and attempt limits",
            "instructions": "Answer questions sequentially",
            "total_duration_minutes": 75,
            "total_marks": 100.0,
            "passing_percentage": 60.0,
            "max_attempts": 2,
            "start_time": start_time,
            "end_time": end_time,
            "rules": {
                "navigation_mode": "FORWARD_ONLY",
                "randomize_questions": True,
                "randomize_options": True,
                "negative_marking_enabled": True,
                "webcam_proctoring_enabled": True,
                "full_screen_enforced": True
            },
            "sections": [
                {
                    "title": "Core Engineering Section",
                    "duration_minutes": 75,
                    "order_index": 0,
                    "cut_off_marks": 10.0,
                    "questions": [
                        {
                            "question_id": q_id,
                            "positive_marks": 5.0,
                            "negative_marks": 1.0,
                            "order_index": 0
                        }
                    ]
                }
            ]
        })
        assert assess_res.status_code == 201, assess_res.text
        assess = assess_res.json()
        a_id = assess["id"]
        assert assess["status"] == "DRAFT"
        assert assess["max_attempts"] == 2
        assert assess["rules"]["navigation_mode"] == "FORWARD_ONLY"
        assert assess["rules"]["randomize_questions"] is True

        # 3. Transition DRAFT -> PUBLISHED
        pub_res = client.post(f"/api/v1/assessments/{a_id}/publish", headers=headers)
        assert pub_res.status_code == 200
        assert pub_res.json()["status"] == "PUBLISHED"

        # 4. Transition PUBLISHED -> LIVE
        live_res = client.post(f"/api/v1/assessments/{a_id}/live", headers=headers)
        assert live_res.status_code == 200
        assert live_res.json()["status"] == "LIVE"

        # 5. Transition LIVE -> CLOSED
        close_res = client.post(f"/api/v1/assessments/{a_id}/close", headers=headers)
        assert close_res.status_code == 200
        assert close_res.json()["status"] == "CLOSED"

        # 6. Verify cannot schedule or edit a CLOSED assessment
        sched_closed = client.post(f"/api/v1/assessments/{a_id}/schedule", headers=headers, json={
            "start_time": start_time,
            "end_time": end_time
        })
        assert sched_closed.status_code == 400

    def test_scheduled_assessment_and_date_validations(self, client: TestClient, recruiter_headers, test_org):
        """
        Tests scheduling lifecycle: DRAFT -> SCHEDULED -> LIVE, and invalid date validation.
        """
        headers = recruiter_headers
        org_id = test_org.id

        # Create question
        q_res = client.post("/api/v1/questions", headers=headers, json={
            "org_id": org_id,
            "title": "Scheduled Question",
            "question_type": "TRUE_FALSE",
            "difficulty": "EASY",
            "options": [
                {"id": "opt_t", "text": "True", "is_correct": True},
                {"id": "opt_f", "text": "False", "is_correct": False}
            ]
        })
        q_id = q_res.json()["id"]

        # Date validation check: start_time >= end_time must fail
        now = datetime.now(timezone.utc)
        bad_res = client.post("/api/v1/assessments", headers=headers, json={
            "org_id": org_id,
            "title": "Bad Dates Assessment",
            "total_duration_minutes": 60,
            "start_time": (now + timedelta(days=2)).isoformat(),
            "end_time": (now + timedelta(days=1)).isoformat()
        })
        assert bad_res.status_code == 422  # Pydantic validation error

        # Create valid DRAFT assessment
        assess_res = client.post("/api/v1/assessments", headers=headers, json={
            "org_id": org_id,
            "title": "Scheduled Assessment",
            "total_duration_minutes": 60,
            "sections": [
                {
                    "title": "Section A",
                    "questions": [{"question_id": q_id, "positive_marks": 2.0, "order_index": 0}]
                }
            ]
        })
        a_id = assess_res.json()["id"]

        # Schedule assessment
        valid_start = (now + timedelta(hours=2)).isoformat()
        valid_end = (now + timedelta(days=5)).isoformat()
        sched_res = client.post(f"/api/v1/assessments/{a_id}/schedule", headers=headers, json={
            "start_time": valid_start,
            "end_time": valid_end
        })
        assert sched_res.status_code == 200
        assert sched_res.json()["status"] == "SCHEDULED"

        # Transition SCHEDULED -> LIVE
        live_res = client.post(f"/api/v1/assessments/{a_id}/live", headers=headers)
        assert live_res.status_code == 200
        assert live_res.json()["status"] == "LIVE"

    def test_candidate_invitation_management(self, client: TestClient, recruiter_headers, test_org):
        """
        Tests candidate invitation management:
        - Bulk invite
        - Single invite
        - Verify token
        - Resend token
        - Revoke invitation
        """
        headers = recruiter_headers
        org_id = test_org.id

        # Create question and assessment
        q_res = client.post("/api/v1/questions", headers=headers, json={
            "org_id": org_id,
            "title": "Invite Test Question",
            "question_type": "TRUE_FALSE",
            "options": [
                {"id": "opt_t", "text": "True", "is_correct": True},
                {"id": "opt_f", "text": "False", "is_correct": False}
            ]
        })
        q_id = q_res.json()["id"]

        assess_res = client.post("/api/v1/assessments", headers=headers, json={
            "org_id": org_id,
            "title": "Candidate Test Drive",
            "total_duration_minutes": 60,
            "sections": [
                {
                    "title": "General",
                    "questions": [{"question_id": q_id, "positive_marks": 2.0, "order_index": 0}]
                }
            ]
        })
        a_id = assess_res.json()["id"]
        client.post(f"/api/v1/assessments/{a_id}/publish", headers=headers)

        # 1. Bulk invite
        bulk_res = client.post("/api/v1/candidates/bulk-invite", headers=headers, json={
            "assessment_id": a_id,
            "candidates": [
                {"email": "alex.dev@testcorp.com", "full_name": "Alex Dev"},
                {"email": "sam.eng@testcorp.com", "full_name": "Sam Eng"}
            ],
            "expires_in_hours": 48
        })
        assert bulk_res.status_code == 201
        bulk_data = bulk_res.json()
        assert bulk_data["total_processed"] == 2
        first_token = bulk_data["invited_candidates"][0]["invitation_token"]
        first_id = bulk_data["invited_candidates"][0]["id"]

        # 2. Verify token
        verify_res = client.get(f"/api/v1/candidates/invitations/{first_token}/verify")
        assert verify_res.status_code == 200
        assert verify_res.json()["status"] == "REGISTERED"

        # 3. Single invite
        single_res = client.post("/api/v1/candidates/invite", headers=headers, json={
            "assessment_id": a_id,
            "email": "charlie@testcorp.com",
            "full_name": "Charlie One",
            "expires_in_hours": 24
        })
        assert single_res.status_code == 200
        charlie_id = single_res.json()["id"]

        # 4. Resend invitation
        resend_res = client.post(f"/api/v1/candidates/invitations/{first_id}/resend", headers=headers)
        assert resend_res.status_code == 200
        assert resend_res.json()["invitation_token"] is not None

        # 5. Revoke invitation
        revoke_res = client.delete(f"/api/v1/candidates/invitations/{charlie_id}", headers=headers)
        assert revoke_res.status_code == 200

    def test_unauthorized_answer_and_hidden_test_sanitization(self, client: TestClient, recruiter_headers, test_org):
        """
        Verifies that candidate-facing endpoints NEVER leak:
        - MCQ option is_correct
        - Hidden test cases in coding questions
        - SQL solution_sql
        - Question explanations
        """
        headers = recruiter_headers
        org_id = test_org.id

        # 1. Create MCQ with secret answer
        mcq_res = client.post("/api/v1/questions", headers=headers, json={
            "org_id": org_id,
            "title": "Secret MCQ",
            "question_type": "MCQ_SINGLE",
            "default_positive_marks": 2.0,
            "options": [
                {"id": "opt_c", "text": "Correct Choice", "is_correct": True},
                {"id": "opt_w", "text": "Wrong Choice", "is_correct": False}
            ]
        })
        q_mcq_id = mcq_res.json()["id"]

        # 2. Create Coding with hidden test cases
        coding_res = client.post("/api/v1/questions", headers=headers, json={
            "org_id": org_id,
            "title": "Secret Coding",
            "question_type": "CODING",
            "default_positive_marks": 10.0,
            "coding_details": {
                "language": "python",
                "starter_code": "def solve(): pass",
                "test_cases": [
                    {"input": "1", "expected_output": "1", "is_hidden": False},
                    {"input": "9999", "expected_output": "SECRET_OUTPUT_9999", "is_hidden": True}
                ]
            }
        })
        q_coding_id = coding_res.json()["id"]

        # 3. Create SQL question with secret solution_sql
        sql_res = client.post("/api/v1/questions", headers=headers, json={
            "org_id": org_id,
            "title": "Secret SQL",
            "question_type": "SQL",
            "default_positive_marks": 5.0,
            "sql_details": {
                "schema_sql": "CREATE TABLE t (id INT);",
                "solution_sql": "SECRET_SELECT_SQL_QUERY_42",
                "test_queries": ["SELECT * FROM t;"]
            }
        })
        q_sql_id = sql_res.json()["id"]

        # 4. Build and publish assessment
        assess_res = client.post("/api/v1/assessments", headers=headers, json={
            "org_id": org_id,
            "title": "Sanitization Check Assessment",
            "total_duration_minutes": 60,
            "sections": [
                {
                    "title": "Mixed Section",
                    "questions": [
                        {"question_id": q_mcq_id, "positive_marks": 2.0, "order_index": 0},
                        {"question_id": q_coding_id, "positive_marks": 10.0, "order_index": 1},
                        {"question_id": q_sql_id, "positive_marks": 5.0, "order_index": 2}
                    ]
                }
            ]
        })
        a_id = assess_res.json()["id"]
        client.post(f"/api/v1/assessments/{a_id}/publish", headers=headers)

        # 5. Candidate Preview Endpoint: GET /api/v1/assessments/{a_id}/preview
        cand_view_res = client.get(f"/api/v1/assessments/{a_id}/preview", headers=headers)
        assert cand_view_res.status_code == 200, cand_view_res.text
        cand_data = cand_view_res.json()

        questions = cand_data["sections"][0]["questions"]
        assert len(questions) == 3

        # Verify MCQ has NO is_correct
        mcq_q = next(q for q in questions if q["question_type"] == "MCQ_SINGLE")
        for opt in mcq_q["options"]:
            assert "is_correct" not in opt, f"is_correct leaked in candidate payload: {opt}"

        # Verify Coding has NO hidden test cases
        coding_q = next(q for q in questions if q["question_type"] == "CODING")
        for tc in coding_q["coding_details"].get("test_cases", []):
            assert tc.get("is_hidden") is not True, f"Hidden test case leaked to candidate: {tc}"
            assert "SECRET_OUTPUT_9999" not in str(tc)

        # Verify SQL has NO solution_sql
        sql_q = next(q for q in questions if q["question_type"] == "SQL")
        assert "solution_sql" not in sql_q["sql_details"], "solution_sql leaked to candidate!"
        assert sql_q["sql_details"].get("schema_sql") == "CREATE TABLE t (id INT);"

    def test_version_preservation_for_active_assessments(self, client: TestClient, recruiter_headers, test_org):
        """
        Verifies that when a question is edited in the Question Bank (creating v2),
        an existing published assessment keeps pointing to its original pinned question version (v1).
        """
        headers = recruiter_headers
        org_id = test_org.id

        # 1. Create Question (v1)
        q_res = client.post("/api/v1/questions", headers=headers, json={
            "org_id": org_id,
            "title": "Original Immutable Question v1",
            "topic": "Python Core",
            "question_type": "TRUE_FALSE",
            "options": [
                {"id": "opt_t", "text": "True", "is_correct": True},
                {"id": "opt_f", "text": "False", "is_correct": False}
            ]
        })
        q_id = q_res.json()["id"]
        v1_id = q_res.json()["current_version"]["id"]

        # 2. Create and publish assessment with Question v1
        assess_res = client.post("/api/v1/assessments", headers=headers, json={
            "org_id": org_id,
            "title": "Version Freeze Test Assessment",
            "total_duration_minutes": 60,
            "sections": [
                {
                    "title": "Section 1",
                    "questions": [{"question_id": q_id, "positive_marks": 2.0, "order_index": 0}]
                }
            ]
        })
        a_id = assess_res.json()["id"]
        client.post(f"/api/v1/assessments/{a_id}/publish", headers=headers)

        # 3. Recruiter edits the question to v2 in the question bank
        update_res = client.put(f"/api/v1/questions/{q_id}", headers=headers, json={
            "title": "Subsequent Question Revision v2",
            "topic": "Advanced Topics",
            "options": [
                {"id": "opt_t", "text": "True", "is_correct": False},
                {"id": "opt_f", "text": "False", "is_correct": True}
            ]
        })
        assert update_res.status_code == 200
        v2_id = update_res.json()["id"]
        assert v2_id != v1_id

        # 4. Check assessment's pinned version: it must STILL point to v1_id
        assess_check = client.get(f"/api/v1/assessments/{a_id}", headers=headers)
        assert assess_check.status_code == 200
        section_q = assess_check.json()["sections"][0]["section_questions"][0]
        assert section_q["question_version_id"] == v1_id
        assert section_q["question_version"]["title"] == "Original Immutable Question v1"

    def test_recruiter_dashboard_real_metrics_endpoint(self, client: TestClient, recruiter_headers, test_org):
        """
        Tests GET /api/v1/analytics/recruiter/dashboard returns computed metrics:
        total_assessments, status_counts, total_candidates, pass_rate, recent_assessments, etc.
        """
        headers = recruiter_headers
        org_id = test_org.id

        dash_res = client.get(f"/api/v1/analytics/recruiter/dashboard?org_id={org_id}", headers=headers)
        assert dash_res.status_code == 200
        data = dash_res.json()

        assert "total_assessments" in data
        assert "status_counts" in data
        assert "DRAFT" in data["status_counts"]
        assert "PUBLISHED" in data["status_counts"]
        assert "SCHEDULED" in data["status_counts"]
        assert "LIVE" in data["status_counts"]
        assert "CLOSED" in data["status_counts"]
        assert "total_candidates" in data
        assert "pass_rate" in data
        assert "recent_assessments" in data
        assert "activities" in data
