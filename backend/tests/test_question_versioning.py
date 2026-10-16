import pytest


def test_create_mcq_single_creates_version_1(client, test_org, author_headers):
    payload = {
        "org_id": test_org.id,
        "title": "Python List Mutability",
        "description": "Are Python lists mutable or immutable?",
        "question_type": "MCQ_SINGLE",
        "difficulty": "EASY",
        "default_positive_marks": 2.0,
        "default_negative_marks": 0.5,
        "tags": ["python", "basics"],
        "options": [
            {"id": "opt_1", "text": "Mutable", "is_correct": True, "explanation": "Lists can be modified in-place"},
            {"id": "opt_2", "text": "Immutable", "is_correct": False, "explanation": "Tuples are immutable, lists are mutable"}
        ]
    }
    response = client.post("/api/v1/questions", json=payload, headers=author_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["current_version_number"] == 1
    assert data["current_version"]["title"] == "Python List Mutability"
    assert len(data["current_version"]["options"]) == 2


def test_create_mcq_multiple_select(client, test_org, author_headers):
    payload = {
        "org_id": test_org.id,
        "title": "Immutable Types in Python",
        "description": "Select all types that are immutable in Python.",
        "question_type": "MCQ_MULTIPLE",
        "difficulty": "MEDIUM",
        "default_positive_marks": 3.0,
        "default_negative_marks": 1.0,
        "tags": ["python", "types"],
        "options": [
            {"id": "opt_a", "text": "tuple", "is_correct": True},
            {"id": "opt_b", "text": "str", "is_correct": True},
            {"id": "opt_c", "text": "list", "is_correct": False},
            {"id": "opt_d", "text": "int", "is_correct": True}
        ]
    }
    response = client.post("/api/v1/questions", json=payload, headers=author_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["question_type"] == "MCQ_MULTIPLE"
    assert sum(1 for o in data["current_version"]["options"] if o["is_correct"]) == 3


def test_create_coding_question_with_test_cases(client, test_org, author_headers):
    payload = {
        "org_id": test_org.id,
        "title": "Sum Array Elements",
        "description": "Write a Python script reading input from stdin and printing the sum of elements.",
        "question_type": "CODING",
        "difficulty": "EASY",
        "default_positive_marks": 10.0,
        "coding_details": {
            "starter_code": "import sys\n# write your solution here\n",
            "language": "python",
            "test_cases": [
                {"input": "1 2 3", "expected_output": "6", "is_hidden": False, "time_limit_ms": 2000},
                {"input": "10 -5 2", "expected_output": "7", "is_hidden": True, "time_limit_ms": 2000}
            ]
        }
    }
    response = client.post("/api/v1/questions", json=payload, headers=author_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["question_type"] == "CODING"
    assert len(data["current_version"]["coding_details"]["test_cases"]) == 2


def test_create_sql_question(client, test_org, author_headers):
    payload = {
        "org_id": test_org.id,
        "title": "Top Department Salaries",
        "description": "Write SQL to find the highest earning employee per department.",
        "question_type": "SQL",
        "difficulty": "HARD",
        "default_positive_marks": 15.0,
        "sql_details": {
            "schema_sql": "CREATE TABLE employees (id INT, dept_id INT, salary INT);",
            "solution_sql": "SELECT dept_id, MAX(salary) FROM employees GROUP BY dept_id;",
            "test_queries": ["SELECT * FROM employees;"]
        }
    }
    response = client.post("/api/v1/questions", json=payload, headers=author_headers)
    assert response.status_code == 201
    assert response.json()["question_type"] == "SQL"


def test_question_update_creates_version_2(client, test_org, author_headers):
    # Create question
    create_payload = {
        "org_id": test_org.id,
        "title": "Original Title v1",
        "description": "Original Description",
        "question_type": "MCQ_SINGLE",
        "default_positive_marks": 2.0,
        "options": [{"id": "1", "text": "A", "is_correct": True}]
    }
    q_res = client.post("/api/v1/questions", json=create_payload, headers=author_headers)
    assert q_res.status_code == 201
    q_id = q_res.json()["id"]

    # Update question
    update_payload = {
        "title": "Updated Title v2",
        "description": "Refined Description with more context",
        "default_positive_marks": 4.0
    }
    up_res = client.put(f"/api/v1/questions/{q_id}", json=update_payload, headers=author_headers)
    assert up_res.status_code == 200
    v2_data = up_res.json()
    assert v2_data["version_number"] == 2
    assert v2_data["title"] == "Updated Title v2"
    assert v2_data["default_positive_marks"] == 4.0

    # Fetch question to check current version number
    get_res = client.get(f"/api/v1/questions/{q_id}", headers=author_headers)
    assert get_res.json()["current_version_number"] == 2


def test_question_version_immutability(client, test_org, author_headers):
    # Create v1
    create_payload = {
        "org_id": test_org.id,
        "title": "Immutable Question v1",
        "description": "v1 text",
        "question_type": "MCQ_SINGLE",
        "default_positive_marks": 1.0,
        "options": [{"id": "1", "text": "Opt1", "is_correct": True}]
    }
    q_res = client.post("/api/v1/questions", json=create_payload, headers=author_headers)
    q_id = q_res.json()["id"]
    v1_id = q_res.json()["current_version"]["id"]

    # Update to v2
    client.put(f"/api/v1/questions/{q_id}", json={"title": "Altered in v2"}, headers=author_headers)
    # Update to v3
    client.put(f"/api/v1/questions/{q_id}", json={"title": "Altered again in v3"}, headers=author_headers)

    # Verify v1 is still completely intact in database
    v1_res = client.get(f"/api/v1/questions/{q_id}/versions/{v1_id}", headers=author_headers)
    assert v1_res.status_code == 200
    v1_data = v1_res.json()
    assert v1_data["version_number"] == 1
    assert v1_data["title"] == "Immutable Question v1"
    assert v1_data["default_positive_marks"] == 1.0
