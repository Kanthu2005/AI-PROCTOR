import pytest
from app.models.question import QuestionType, DifficultyLevel


def test_create_all_supported_question_types(client, test_org, author_headers):
    """
    Acceptance criteria:
    Every supported type can be created:
    1. Single-answer MCQ
    2. Multiple-select MCQ
    3. True/false
    4. Descriptive answer
    5. Python coding
    """
    # 1. Single-answer MCQ
    payload_mcq_single = {
        "org_id": test_org.id,
        "title": "Python Dictionary Key Lookup Time Complexity",
        "description": "What is the average time complexity of a key lookup in a Python dictionary?",
        "question_type": "MCQ_SINGLE",
        "difficulty": "EASY",
        "default_positive_marks": 2.0,
        "default_negative_marks": 0.5,
        "tags": ["python", "data-structures"],
        "options": [
            {"id": "opt_1", "text": "O(1)", "is_correct": True, "explanation": "Hash table lookups take average O(1) time"},
            {"id": "opt_2", "text": "O(n)", "is_correct": False},
            {"id": "opt_3", "text": "O(log n)", "is_correct": False},
            {"id": "opt_4", "text": "O(n^2)", "is_correct": False}
        ]
    }
    res_single = client.post("/api/v1/questions", json=payload_mcq_single, headers=author_headers)
    assert res_single.status_code == 201, res_single.text
    data_single = res_single.json()
    assert data_single["question_type"] == "MCQ_SINGLE"
    assert data_single["current_version_number"] == 1
    assert len(data_single["current_version"]["options"]) == 4

    # 2. Multiple-select MCQ
    payload_mcq_multi = {
        "org_id": test_org.id,
        "title": "Python Built-in Sequence Types",
        "description": "Select all built-in sequence types in Python.",
        "question_type": "MCQ_MULTIPLE",
        "difficulty": "MEDIUM",
        "default_positive_marks": 3.0,
        "default_negative_marks": 1.0,
        "tags": ["python", "types"],
        "options": [
            {"id": "opt_a", "text": "list", "is_correct": True},
            {"id": "opt_b", "text": "tuple", "is_correct": True},
            {"id": "opt_c", "text": "set", "is_correct": False},
            {"id": "opt_d", "text": "str", "is_correct": True}
        ]
    }
    res_multi = client.post("/api/v1/questions", json=payload_mcq_multi, headers=author_headers)
    assert res_multi.status_code == 201, res_multi.text
    data_multi = res_multi.json()
    assert data_multi["question_type"] == "MCQ_MULTIPLE"
    assert sum(1 for o in data_multi["current_version"]["options"] if o["is_correct"]) == 3

    # 3. True/False
    payload_tf = {
        "org_id": test_org.id,
        "title": "Tuples In-place Modification",
        "description": "Tuples in Python can be modified in-place after creation.",
        "question_type": "TRUE_FALSE",
        "difficulty": "EASY",
        "default_positive_marks": 1.0,
        "default_negative_marks": 0.5,
        "tags": ["python", "immutability"],
        "options": [
            {"id": "true", "text": "True", "is_correct": False},
            {"id": "false", "text": "False", "is_correct": True}
        ]
    }
    res_tf = client.post("/api/v1/questions", json=payload_tf, headers=author_headers)
    assert res_tf.status_code == 201, res_tf.text
    data_tf = res_tf.json()
    assert data_tf["question_type"] == "TRUE_FALSE"
    assert len(data_tf["current_version"]["options"]) == 2

    # 4. Descriptive
    payload_desc = {
        "org_id": test_org.id,
        "title": "Explain ACID Properties in Relational Databases",
        "description": "Discuss Atomicity, Consistency, Isolation, and Durability with real-world banking transaction examples.",
        "question_type": "DESCRIPTIVE",
        "difficulty": "MEDIUM",
        "default_positive_marks": 5.0,
        "default_negative_marks": 0.0,
        "tags": ["database", "rdbms"],
        "descriptive_details": {
            "evaluation_criteria": "Accuracy of each letter (40%), Real-world examples (40%), Clarity (20%)",
            "expected_answer": "Atomicity ensures all-or-nothing; Consistency maintains constraints...",
            "min_words": 50,
            "max_words": 500
        }
    }
    res_desc = client.post("/api/v1/questions", json=payload_desc, headers=author_headers)
    assert res_desc.status_code == 201, res_desc.text
    data_desc = res_desc.json()
    assert data_desc["question_type"] == "DESCRIPTIVE"
    assert data_desc["current_version"]["descriptive_details"]["min_words"] == 50

    # 5. Python Coding
    payload_coding = {
        "org_id": test_org.id,
        "title": "Reverse Words in a String",
        "description": "Given a line of text, reverse the words while maintaining single space separators.",
        "question_type": "CODING",
        "difficulty": "MEDIUM",
        "default_positive_marks": 10.0,
        "default_negative_marks": 0.0,
        "tags": ["python", "strings"],
        "coding_details": {
            "starter_code": "import sys\nline = sys.stdin.read().strip()\n# Write solution\n",
            "language": "python",
            "test_cases": [
                {"input": "the sky is blue\n", "expected_output": "blue is sky the", "is_hidden": False},
                {"input": "hello world\n", "expected_output": "world hello", "is_hidden": True}
            ]
        }
    }
    res_coding = client.post("/api/v1/questions", json=payload_coding, headers=author_headers)
    assert res_coding.status_code == 201, res_coding.text
    data_coding = res_coding.json()
    assert data_coding["question_type"] == "CODING"
    assert len(data_coding["current_version"]["coding_details"]["test_cases"]) == 2


def test_mcq_single_validation_rejects_invalid_correct_count(client, test_org, author_headers):
    # 0 correct options
    payload_zero_correct = {
        "org_id": test_org.id,
        "title": "Zero Correct MCQ",
        "question_type": "MCQ_SINGLE",
        "options": [
            {"id": "1", "text": "A", "is_correct": False},
            {"id": "2", "text": "B", "is_correct": False}
        ]
    }
    res = client.post("/api/v1/questions", json=payload_zero_correct, headers=author_headers)
    assert res.status_code == 422

    # Multiple correct options for MCQ_SINGLE
    payload_two_correct = {
        "org_id": test_org.id,
        "title": "Two Correct MCQ Single",
        "question_type": "MCQ_SINGLE",
        "options": [
            {"id": "1", "text": "A", "is_correct": True},
            {"id": "2", "text": "B", "is_correct": True}
        ]
    }
    res2 = client.post("/api/v1/questions", json=payload_two_correct, headers=author_headers)
    assert res2.status_code == 422


def test_mcq_multiple_validation_requires_at_least_one_correct(client, test_org, author_headers):
    payload_zero = {
        "org_id": test_org.id,
        "title": "Zero Correct Multi",
        "question_type": "MCQ_MULTIPLE",
        "options": [
            {"id": "1", "text": "A", "is_correct": False},
            {"id": "2", "text": "B", "is_correct": False}
        ]
    }
    res = client.post("/api/v1/questions", json=payload_zero, headers=author_headers)
    assert res.status_code == 422


def test_coding_validation_requires_test_cases(client, test_org, author_headers):
    payload_no_tc = {
        "org_id": test_org.id,
        "title": "Coding with no test cases",
        "question_type": "CODING",
        "coding_details": {
            "starter_code": "def solve(): pass",
            "test_cases": []
        }
    }
    res = client.post("/api/v1/questions", json=payload_no_tc, headers=author_headers)
    assert res.status_code == 422


def test_question_editing_reloads_and_preserves_fields_version_increment(client, test_org, author_headers):
    """
    Acceptance criteria:
    - Editing creates an incremented version
    - Reloading preserves all fields
    """
    create_payload = {
        "org_id": test_org.id,
        "title": "Initial Title v1",
        "description": "Initial Description",
        "question_type": "MCQ_SINGLE",
        "difficulty": "EASY",
        "default_positive_marks": 2.0,
        "default_negative_marks": 0.5,
        "tags": ["tag1", "tag2"],
        "options": [
            {"id": "opt_1", "text": "Choice 1", "is_correct": True},
            {"id": "opt_2", "text": "Choice 2", "is_correct": False}
        ]
    }
    res_create = client.post("/api/v1/questions", json=create_payload, headers=author_headers)
    assert res_create.status_code == 201
    q_id = res_create.json()["id"]

    # Update question
    update_payload = {
        "title": "Updated Title v2",
        "description": "Updated Description v2",
        "difficulty": "HARD",
        "default_positive_marks": 4.0,
        "options": [
            {"id": "opt_1", "text": "Choice 1 Modified", "is_correct": True},
            {"id": "opt_2", "text": "Choice 2 Modified", "is_correct": False}
        ]
    }
    res_update = client.put(f"/api/v1/questions/{q_id}", json=update_payload, headers=author_headers)
    assert res_update.status_code == 200
    updated_data = res_update.json()
    assert updated_data["version_number"] == 2
    assert updated_data["title"] == "Updated Title v2"
    assert updated_data["difficulty"] == "HARD"
    assert updated_data["default_positive_marks"] == 4.0

    # Fetch question to verify persistence and preservation
    res_get = client.get(f"/api/v1/questions/{q_id}", headers=author_headers)
    assert res_get.status_code == 200
    get_data = res_get.json()
    assert get_data["current_version_number"] == 2
    assert get_data["current_version"]["title"] == "Updated Title v2"
    assert len(get_data["all_versions"]) == 2
    # Verify Version 1 is preserved intact
    v1 = next(v for v in get_data["all_versions"] if v["version_number"] == 1)
    assert v1["title"] == "Initial Title v1"


def test_candidate_api_sanitization_never_leaks_answers_or_hidden_tests(client, test_org, recruiter_headers, candidate_headers, db):
    """
    Acceptance criteria:
    - Correct answers and hidden test cases never leak through candidate APIs.
    """
    # 1. Create a coding question with 1 public and 1 hidden test case
    coding_payload = {
        "org_id": test_org.id,
        "title": "Secret Test Case Coding Question",
        "question_type": "CODING",
        "coding_details": {
            "starter_code": "def solve(): pass",
            "test_cases": [
                {"input": "public_in", "expected_output": "public_out", "is_hidden": False},
                {"input": "SUPER_SECRET_HIDDEN_INPUT", "expected_output": "SECRET_OUTPUT", "is_hidden": True}
            ]
        }
    }
    res_q = client.post("/api/v1/questions", json=coding_payload, headers=recruiter_headers)
    assert res_q.status_code == 201
    q_coding_id = res_q.json()["id"]

    # 2. Create an MCQ question with marked correct option and explanation
    mcq_payload = {
        "org_id": test_org.id,
        "title": "Secret MCQ Answer Question",
        "question_type": "MCQ_SINGLE",
        "options": [
            {"id": "opt_a", "text": "Correct Answer Secret", "is_correct": True, "explanation": "Top secret leak"},
            {"id": "opt_b", "text": "Wrong Answer", "is_correct": False}
        ]
    }
    res_mcq = client.post("/api/v1/questions", json=mcq_payload, headers=recruiter_headers)
    assert res_mcq.status_code == 201
    q_mcq_id = res_mcq.json()["id"]

    # 3. Create an assessment containing both questions
    assess_payload = {
        "org_id": test_org.id,
        "title": "Sanitization Verification Assessment",
        "total_duration_minutes": 60,
        "sections": [
            {
                "title": "Section 1",
                "duration_minutes": 60,
                "order_index": 0,
                "questions": [
                    {"question_id": q_coding_id, "positive_marks": 10.0, "order_index": 0},
                    {"question_id": q_mcq_id, "positive_marks": 2.0, "order_index": 1}
                ]
            }
        ]
    }
    res_assess = client.post("/api/v1/assessments", json=assess_payload, headers=recruiter_headers)
    assert res_assess.status_code == 201
    assess_id = res_assess.json()["id"]
    client.post(f"/api/v1/assessments/{assess_id}/publish", headers=recruiter_headers)

    # 4. Invite candidate and start attempt
    invite_res = client.post("/api/v1/candidates/bulk-invite", json={
        "assessment_id": assess_id,
        "candidates": [{"email": "sanitization.candidate@example.com", "full_name": "Sanitization Candidate"}],
        "expires_in_hours": 48
    }, headers=recruiter_headers)
    assert invite_res.status_code == 201
    token = invite_res.json()["invited_candidates"][0]["invitation_token"]

    client.post(f"/api/v1/candidates/invitations/{token}/system-check", json={
        "camera_ok": True,
        "microphone_ok": True,
        "browser_compatible": True,
        "fullscreen_supported": True
    })

    res_start = client.post(f"/api/v1/attempts/start?invitation_token={token}")
    assert res_start.status_code == 200
    candidate_exam_data = res_start.json()

    # Raw JSON string verification: check for any leaks
    import json
    raw_response_str = json.dumps(candidate_exam_data)
    assert "SUPER_SECRET_HIDDEN_INPUT" not in raw_response_str, "CRITICAL: Hidden test case input leaked in candidate payload!"
    assert "SECRET_OUTPUT" not in raw_response_str, "CRITICAL: Hidden test case output leaked in candidate payload!"
    assert "Top secret leak" not in raw_response_str, "CRITICAL: Option explanation leaked in candidate payload!"

    # Verify options in candidate response do NOT contain 'is_correct'
    questions = candidate_exam_data["sections"][0]["questions"]
    for q in questions:
        for opt in q.get("options", []):
            assert "is_correct" not in opt, f"CRITICAL: 'is_correct' found in candidate option: {opt}"
