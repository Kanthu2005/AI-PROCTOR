import pytest
from app.services.assessment_service import AssessmentService


def test_create_assessment_with_rules(client, test_org, recruiter_headers, author_headers):
    # First create a question
    q_res = client.post("/api/v1/questions", json={
        "org_id": test_org.id,
        "title": "Rule Q1",
        "description": "Rule Desc",
        "question_type": "MCQ_SINGLE",
        "options": [{"id": "1", "text": "Yes", "is_correct": True}]
    }, headers=author_headers)
    q_id = q_res.json()["id"]

    assess_payload = {
        "org_id": test_org.id,
        "title": "Full Stack Engineer Assessment",
        "description": "Comprehensive screening test",
        "total_duration_minutes": 45,
        "passing_percentage": 60.0,
        "rules": {
            "navigation_mode": "FREE",
            "section_wise_breaks": True,
            "randomize_questions": True,
            "randomize_options": True,
            "negative_marking_enabled": True,
            "negative_marking_formula": "(correct * positive_marks) - (wrong * negative_marks)",
            "full_screen_enforced": True,
            "max_tab_switches_allowed": 3,
            "webcam_proctoring_enabled": True,
            "devtools_block_enabled": True,
            "copy_paste_blocked": True
        },
        "sections": [
            {
                "title": "Core CS",
                "duration_minutes": 20,
                "order_index": 1,
                "cut_off_marks": 5.0,
                "questions": [
                    {
                        "question_id": q_id,
                        "positive_marks": 3.0,
                        "negative_marks": 1.0,
                        "order_index": 1
                    }
                ]
            }
        ]
    }
    response = client.post("/api/v1/assessments", json=assess_payload, headers=recruiter_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Full Stack Engineer Assessment"
    assert data["total_duration_minutes"] == 45
    assert data["rules"]["max_tab_switches_allowed"] == 3
    assert len(data["sections"]) == 1
    assert data["sections"][0]["section_questions"][0]["positive_marks"] == 3.0


def test_frozen_question_version_in_assessment(client, db, test_org, recruiter_headers, author_headers):
    # 1. Create question v1
    q_res = client.post("/api/v1/questions", json={
        "org_id": test_org.id,
        "title": "Freezing Test Q",
        "description": "Original text v1",
        "question_type": "MCQ_SINGLE",
        "options": [{"id": "1", "text": "Opt A", "is_correct": True}]
    }, headers=author_headers)
    q_id = q_res.json()["id"]
    v1_id = q_res.json()["current_version"]["id"]

    # 2. Create assessment referencing this question
    assess_res = client.post("/api/v1/assessments", json={
        "org_id": test_org.id,
        "title": "Frozen Test Assessment",
        "sections": [{
            "title": "Section 1",
            "order_index": 0,
            "questions": [{"question_id": q_id, "positive_marks": 2.0, "negative_marks": 0.5}]
        }]
    }, headers=recruiter_headers)
    assert assess_res.status_code == 201
    sq = assess_res.json()["sections"][0]["section_questions"][0]
    assert sq["question_version_id"] == v1_id

    # 3. Question Author updates question to v2
    client.put(f"/api/v1/questions/{q_id}", json={"title": "Altered in v2"}, headers=author_headers)

    # 4. Assessment's SectionQuestion STILL references v1_id!
    get_assess = client.get(f"/api/v1/assessments/{assess_res.json()['id']}", headers=recruiter_headers)
    reloaded_sq = get_assess.json()["sections"][0]["section_questions"][0]
    assert reloaded_sq["question_version_id"] == v1_id
    assert reloaded_sq["question_version"]["title"] == "Freezing Test Q"


def test_candidate_view_sanitization(client, db, test_org, recruiter_headers, author_headers):
    # Create question with answer
    q_res = client.post("/api/v1/questions", json={
        "org_id": test_org.id,
        "title": "Secret Answer Q",
        "description": "What is 2+2?",
        "question_type": "MCQ_SINGLE",
        "options": [
            {"id": "opt_4", "text": "4", "is_correct": True, "explanation": "2+2 equals 4"},
            {"id": "opt_5", "text": "5", "is_correct": False, "explanation": "Wrong"}
        ]
    }, headers=author_headers)
    q_id = q_res.json()["id"]

    assess_res = client.post("/api/v1/assessments", json={
        "org_id": test_org.id,
        "title": "Candidate Security Assessment",
        "sections": [{
            "title": "Math",
            "questions": [{"question_id": q_id, "positive_marks": 1.0}]
        }]
    }, headers=recruiter_headers)

    view = AssessmentService.get_candidate_assessment_view(db, assess_res.json()["id"])
    options = view["sections"][0]["questions"][0]["options"]
    for opt in options:
        assert "is_correct" not in opt
        assert "explanation" not in opt


def test_negative_marking_calculation_correct_answer():
    is_correct, score = AssessmentService.calculate_mcq_score(
        selected_option_ids=["opt_1"],
        correct_option_ids=["opt_1"],
        positive_marks=4.0,
        negative_marks=1.0,
        negative_marking_enabled=True
    )
    assert is_correct is True
    assert score == 4.0


def test_negative_marking_calculation_incorrect_answer():
    is_correct, score = AssessmentService.calculate_mcq_score(
        selected_option_ids=["opt_2"],
        correct_option_ids=["opt_1"],
        positive_marks=4.0,
        negative_marks=1.0,
        negative_marking_enabled=True
    )
    assert is_correct is False
    assert score == -1.0


def test_negative_marking_disabled_gives_zero_on_incorrect():
    is_correct, score = AssessmentService.calculate_mcq_score(
        selected_option_ids=["opt_wrong"],
        correct_option_ids=["opt_right"],
        positive_marks=3.0,
        negative_marks=1.0,
        negative_marking_enabled=False
    )
    assert is_correct is False
    assert score == 0.0


def test_unattempted_mcq_gives_zero_marks():
    is_correct, score = AssessmentService.calculate_mcq_score(
        selected_option_ids=[],
        correct_option_ids=["opt_1"],
        positive_marks=2.0,
        negative_marks=0.5,
        negative_marking_enabled=True
    )
    assert is_correct is False
    assert score == 0.0
