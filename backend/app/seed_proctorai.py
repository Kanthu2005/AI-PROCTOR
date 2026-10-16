from datetime import datetime, timezone, timedelta
import logging
from sqlalchemy.orm import Session

from app.database import SessionLocal, engine, Base
from app.models.user import Organization, User, Role
from app.models.question import Question, QuestionVersion, QuestionType, DifficultyLevel
from app.models.assessment import Assessment, AssessmentRule, Section, SectionQuestion, NavigationMode
from app.models.candidate import CandidateInvitation, CandidateStatus
from app.models.attempt import Attempt, AttemptStatus, RiskLevel, HumanReviewStatus
from app.models.proctoring import ProctoringIncident, EventType, IncidentSeverity
from app.utils.security import hash_password

logger = logging.getLogger("proctorai.seed")


def seed_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # 1. Organization
        org = db.query(Organization).filter(Organization.slug == "acme").first()
        if not org:
            org = Organization(
                name="Acme Corp",
                slug="acme",
                domain="acme.com",
                is_active=True
            )
            db.add(org)
            db.flush()

        # 2. Users
        def get_or_create_user(email, full_name, role, password):
            u = db.query(User).filter(User.email == email).first()
            if not u:
                u = User(
                    email=email,
                    hashed_password=hash_password(password),
                    full_name=full_name,
                    role=role,
                    org_id=org.id,
                    is_active=True
                )
                db.add(u)
                db.flush()
            return u

        recruiter = get_or_create_user("recruiter@acme.com", "Kanthu Naik", Role.RECRUITER, "Recruit@12345")
        platform_admin = get_or_create_user("admin@intellitest.ai", "Platform Administrator", Role.PLATFORM_ADMIN, "Admin@12345")
        proctor = get_or_create_user("proctor@acme.com", "David AI Proctor", Role.PROCTOR, "Proctor@12345")
        author = get_or_create_user("author@acme.com", "Carol Question Author", Role.QUESTION_AUTHOR, "Author@12345")
        candidate_user = get_or_create_user("candidate@example.com", "Rahul Sharma", Role.CANDIDATE, "Candidate@12345")

        # 3. Questions
        questions_data = [
            {
                "title": "Time complexity of Binary Search",
                "desc": "What is the time complexity of searching an element in a sorted array of size n using binary search?",
                "type": QuestionType.MCQ_SINGLE,
                "difficulty": DifficultyLevel.MEDIUM,
                "topic": "Algorithms",
                "tags": ["DSA", "Algorithms", "Binary Search"],
                "positive": 2.0,
                "negative": 0.5,
                "options": [
                    {"id": "opt_1", "text": "O(n)", "is_correct": False, "explanation": "Linear search is O(n)."},
                    {"id": "opt_2", "text": "O(log n)", "is_correct": True, "explanation": "Binary search divides the search space in half each iteration."},
                    {"id": "opt_3", "text": "O(n²)", "is_correct": False, "explanation": "Quadratic complexity is typical of nested loops."},
                    {"id": "opt_4", "text": "O(1)", "is_correct": False, "explanation": "Constant time lookup is characteristic of hash tables."}
                ]
            },
            {
                "title": "Python Static Method Decorator",
                "desc": "Which decorator is used to define a method inside a class that does not require an instance or class reference?",
                "type": QuestionType.MCQ_SINGLE,
                "difficulty": DifficultyLevel.EASY,
                "topic": "Python Core",
                "tags": ["Python", "OOP", "Decorators"],
                "positive": 2.0,
                "negative": 0.5,
                "options": [
                    {"id": "opt_21", "text": "@classmethod", "is_correct": False, "explanation": "Requires cls parameter."},
                    {"id": "opt_22", "text": "@staticmethod", "is_correct": True, "explanation": "Defines a static method independent of self or cls."},
                    {"id": "opt_23", "text": "@property", "is_correct": False, "explanation": "Used for getter/setter attributes."},
                    {"id": "opt_24", "text": "@abstractmethod", "is_correct": False, "explanation": "Enforces subclass implementation."}
                ]
            },
            {
                "title": "CPython GIL Architecture",
                "desc": "What does GIL stand for in CPython, and what is its primary operational purpose?",
                "type": QuestionType.MCQ_SINGLE,
                "difficulty": DifficultyLevel.MEDIUM,
                "topic": "Python Internals",
                "tags": ["Python", "CPython", "Concurrency"],
                "positive": 2.0,
                "negative": 0.5,
                "options": [
                    {"id": "opt_31", "text": "Global Interpreter Lock", "is_correct": True, "explanation": "A mutex that prevents multiple native threads from executing Python bytecodes simultaneously."},
                    {"id": "opt_32", "text": "General Interface Layer", "is_correct": False, "explanation": "Incorrect."},
                    {"id": "opt_33", "text": "Graph Inspection Logic", "is_correct": False, "explanation": "Incorrect."},
                    {"id": "opt_34", "text": "Garbage Index List", "is_correct": False, "explanation": "Incorrect."}
                ]
            },
            {
                "title": "FIFO Data Structure",
                "desc": "Which data structure follows the First-In, First-Out (FIFO) access order for insertion and deletion?",
                "type": QuestionType.MCQ_SINGLE,
                "difficulty": DifficultyLevel.EASY,
                "topic": "Data Structures",
                "tags": ["DSA", "Data Structures"],
                "positive": 2.0,
                "negative": 0.5,
                "options": [
                    {"id": "opt_41", "text": "Queue", "is_correct": True, "explanation": "Queue is strictly First-In, First-Out."},
                    {"id": "opt_42", "text": "Stack", "is_correct": False, "explanation": "Stack is Last-In, First-Out (LIFO)."},
                    {"id": "opt_43", "text": "Binary Search Tree", "is_correct": False, "explanation": "Hierarchical tree."},
                    {"id": "opt_44", "text": "Max-Heap", "is_correct": False, "explanation": "Priority based."}
                ]
            },
            {
                "title": "Maximum Element in an Array",
                "desc": "Write a program in Python to read an integer n followed by n integers, and output the maximum element.",
                "type": QuestionType.CODING,
                "difficulty": DifficultyLevel.MEDIUM,
                "topic": "Algorithms & Coding",
                "tags": ["Python", "Coding", "Arrays"],
                "positive": 20.0,
                "negative": 0.0,
                "coding_details": {
                    "language": "python",
                    "starter_code": "def solve():\n    n = int(input())\n    arr = list(map(int, input().split()))\n    print(max(arr))\n\nif __name__ == '__main__':\n    solve()\n",
                    "sample_input": "5\n10 20 5 30 15",
                    "sample_output": "30",
                    "test_cases": [
                        {"input": "5\n10 20 5 30 15\n", "expected_output": "30", "is_hidden": False},
                        {"input": "3\n-5 -1 -10\n", "expected_output": "-1", "is_hidden": False},
                        {"input": "4\n100 250 50 175\n", "expected_output": "250", "is_hidden": True}
                    ]
                }
            },
            {
                "title": "Department Average Salary Filter",
                "desc": "Write a SQL query to retrieve department names and their average salaries where average salary exceeds 60,000.",
                "type": QuestionType.SQL,
                "difficulty": DifficultyLevel.MEDIUM,
                "topic": "Database & SQL",
                "tags": ["SQL", "Databases", "Aggregation"],
                "positive": 10.0,
                "negative": 0.0,
                "sql_details": {
                    "schema_sql": "CREATE TABLE employees (id INT, name VARCHAR(50), dept VARCHAR(50), salary INT);",
                    "solution_sql": "SELECT dept, AVG(salary) as avg_sal FROM employees GROUP BY dept HAVING AVG(salary) > 60000;",
                    "sample_data": "Engineering: $95,000 | Sales: $55,000 | Product: $82,000",
                    "test_queries": ["SELECT dept, AVG(salary) as avg_sal FROM employees GROUP BY dept HAVING AVG(salary) > 60000;"]
                }
            },
            {
                "title": "Python Built-in Mutable Collections",
                "desc": "Select all built-in Python collection types that are mutable in-place.",
                "type": QuestionType.MCQ_MULTIPLE,
                "difficulty": DifficultyLevel.MEDIUM,
                "topic": "Python Core",
                "tags": ["Python", "Collections", "Mutability"],
                "positive": 3.0,
                "negative": 1.0,
                "options": [
                    {"id": "ms_1", "text": "list", "is_correct": True, "explanation": "Lists support append, pop, and index reassignment."},
                    {"id": "ms_2", "text": "dict", "is_correct": True, "explanation": "Dictionaries allow key insertion and modification."},
                    {"id": "ms_3", "text": "tuple", "is_correct": False, "explanation": "Tuples are strictly immutable."},
                    {"id": "ms_4", "text": "set", "is_correct": True, "explanation": "Sets support add and remove operations."}
                ]
            },
            {
                "title": "Python Strings are Mutable",
                "desc": "In Python, string instances (str) can be modified in-place after instantiation.",
                "type": QuestionType.TRUE_FALSE,
                "difficulty": DifficultyLevel.EASY,
                "topic": "Python Core",
                "tags": ["Python", "Strings", "Immutability"],
                "positive": 1.0,
                "negative": 0.5,
                "options": [
                    {"id": "tf_1", "text": "True", "is_correct": False, "explanation": "Strings in Python are immutable."},
                    {"id": "tf_2", "text": "False", "is_correct": True, "explanation": "Strings cannot be modified in-place."}
                ]
            },
            {
                "title": "Default HTTP Port for Secure Web Traffic",
                "desc": "Enter the default standardized TCP port number utilized for HTTPS encrypted web traffic:",
                "type": QuestionType.FILL_IN_BLANK,
                "difficulty": DifficultyLevel.EASY,
                "topic": "Networking",
                "tags": ["Networking", "Web", "Security"],
                "positive": 2.0,
                "negative": 0.0,
                "options": [
                    {"id": "fib_1", "text": "443", "is_correct": True, "explanation": "HTTPS runs on TCP port 443 by default."}
                ],
                "explanation": "Accepted standard answer: 443"
            },
            {
                "title": "Explain Database Normalization and BCNF",
                "desc": "Describe the core principles of database normalization. Detail the difference between 3NF and Boyce-Codd Normal Form (BCNF), including redundancy elimination and dependency preservation trade-offs.",
                "type": QuestionType.DESCRIPTIVE,
                "difficulty": DifficultyLevel.HARD,
                "topic": "Database Architecture",
                "tags": ["Databases", "System Design", "Normalization"],
                "positive": 15.0,
                "negative": 0.0,
                "explanation": "Grading Rubric: 1) Definitions of 1NF, 2NF, 3NF (5 pts). 2) BCNF strict condition: for every functional dependency X -> Y, X must be a superkey (5 pts). 3) Trade-offs regarding functional dependency preservation in BCNF (5 pts)."
            }
        ]

        seeded_q_versions = []
        for qd in questions_data:
            existing_qv = db.query(QuestionVersion).filter(QuestionVersion.title == qd["title"]).first()
            if not existing_qv:
                q = Question(
                    org_id=org.id,
                    question_type=qd["type"],
                    current_version_number=1,
                    is_active=True
                )
                db.add(q)
                db.flush()

                qv = QuestionVersion(
                    question_id=q.id,
                    version_number=1,
                    title=qd["title"],
                    description=qd["desc"],
                    question_type=qd["type"],
                    difficulty=qd["difficulty"],
                    default_positive_marks=qd["positive"],
                    default_negative_marks=qd["negative"],
                    tags=qd["tags"],
                    topic=qd.get("topic", "General"),
                    options=qd.get("options", []),
                    coding_details=qd.get("coding_details", {}),
                    sql_details=qd.get("sql_details", {}),
                    explanation=qd.get("explanation"),
                    review_status="APPROVED",
                    is_published=True,
                    created_by_id=author.id
                )
                db.add(qv)
                db.flush()
                seeded_q_versions.append(qv)
            else:
                seeded_q_versions.append(existing_qv)

        # 4. Assessments
        # Main Demo Assessment: Python Backend Developer
        assess_python = db.query(Assessment).filter(Assessment.title == "Python Backend Developer").first()
        if not assess_python:
            assess_python = Assessment(
                org_id=org.id,
                title="Python Backend Developer",
                description="Backend developer screening assessment covering Python, SQL, DSA & live coding.",
                instructions="Read each question carefully. Live webcam and anti-cheat tracking are enforced.",
                total_duration_minutes=90,
                passing_percentage=60.0,
                is_active=True,
                created_by_id=recruiter.id
            )
            db.add(assess_python)
            db.flush()

            # Rules
            rules = AssessmentRule(
                assessment_id=assess_python.id,
                navigation_mode=NavigationMode.FREE,
                section_wise_breaks=False,
                randomize_questions=False,
                randomize_options=False,
                negative_marking_enabled=True,
                negative_marking_formula="(correct * positive_marks) - (wrong * negative_marks)",
                full_screen_enforced=True,
                max_tab_switches_allowed=3,
                webcam_proctoring_enabled=True,
                devtools_block_enabled=True,
                copy_paste_blocked=True
            )
            db.add(rules)

            # Section 1: MCQs & Knowledge
            sec1 = Section(
                assessment_id=assess_python.id,
                title="Section 1 — Python, DSA & SQL Core",
                duration_minutes=45,
                order_index=0,
                cut_off_marks=20.0
            )
            db.add(sec1)
            db.flush()

            # Link first 5 questions to Section 1
            for idx, qv in enumerate(seeded_q_versions[:5]):
                sq = SectionQuestion(
                    section_id=sec1.id,
                    question_id=qv.question_id,
                    question_version_id=qv.id,
                    positive_marks=qv.default_positive_marks,
                    negative_marks=qv.default_negative_marks,
                    order_index=idx
                )
                db.add(sq)

            # Section 2: Live Coding Sandbox
            sec2 = Section(
                assessment_id=assess_python.id,
                title="Section 2 — Algorithmic Coding Challenge",
                duration_minutes=45,
                order_index=1,
                cut_off_marks=10.0
            )
            db.add(sec2)
            db.flush()

            # Link coding question to Section 2
            if len(seeded_q_versions) >= 5:
                coding_qv = seeded_q_versions[4]  # Maximum Element
                sq_code = SectionQuestion(
                    section_id=sec2.id,
                    question_id=coding_qv.question_id,
                    question_version_id=coding_qv.id,
                    positive_marks=20.0,
                    negative_marks=0.0,
                    order_index=0
                )
                db.add(sq_code)

        # Assessment 2: Java Developer
        assess_java = db.query(Assessment).filter(Assessment.title == "Java Developer").first()
        if not assess_java:
            assess_java = Assessment(
                org_id=org.id,
                title="Java Developer",
                description="Enterprise Java, Spring Boot, Microservices & Multithreading.",
                instructions="Complete all questions within 90 minutes.",
                total_duration_minutes=90,
                passing_percentage=60.0,
                is_active=True,
                created_by_id=recruiter.id
            )
            db.add(assess_java)
            db.flush()

            rules_java = AssessmentRule(
                assessment_id=assess_java.id,
                navigation_mode=NavigationMode.FREE,
                full_screen_enforced=True,
                max_tab_switches_allowed=3,
                webcam_proctoring_enabled=True
            )
            db.add(rules_java)

        # Assessment 3: SQL Assessment
        assess_sql = db.query(Assessment).filter(Assessment.title == "SQL Assessment").first()
        if not assess_sql:
            assess_sql = Assessment(
                org_id=org.id,
                title="SQL Assessment",
                description="Relational database design, subqueries, CTEs, and query optimization.",
                instructions="Draft assessment awaiting publishing.",
                total_duration_minutes=60,
                passing_percentage=60.0,
                is_active=False,
                created_by_id=recruiter.id
            )
            db.add(assess_sql)
            db.flush()

            rules_sql = AssessmentRule(
                assessment_id=assess_sql.id,
                navigation_mode=NavigationMode.FREE,
                full_screen_enforced=False,
                webcam_proctoring_enabled=False
            )
            db.add(rules_sql)

        db.commit()

        # 5. Candidate Invitations & Attempts for Live Demo
        now = datetime.now(timezone.utc)
        candidates_seed = [
            {
                "name": "Rahul Sharma",
                "email": "candidate@example.com",
                "token": "ABC123",
                "status": CandidateStatus.REGISTERED,
                "attempt_status": None,
                "risk_score": 0.0,
                "risk_level": RiskLevel.LOW,
                "tab_switches": 0,
                "incidents": []
            },
            {
                "name": "Priya Reddy",
                "email": "priya@gmail.com",
                "token": "PRIYA123",
                "status": CandidateStatus.IN_PROGRESS,
                "attempt_status": AttemptStatus.IN_PROGRESS,
                "risk_score": 72.0,
                "risk_level": RiskLevel.HIGH,
                "tab_switches": 2,
                "incidents": [
                    {"type": EventType.TAB_SWITCH, "pts": 15.0, "time_offset_min": -20, "sev": IncidentSeverity.MEDIUM},
                    {"type": EventType.DEVTOOLS_OPEN, "pts": 40.0, "time_offset_min": -14, "sev": IncidentSeverity.CRITICAL},
                    {"type": EventType.FACE_MISSING, "pts": 17.0, "time_offset_min": -5, "sev": IncidentSeverity.HIGH}
                ]
            },
            {
                "name": "Arjun Kumar",
                "email": "arjun@gmail.com",
                "token": "ARJUN123",
                "status": CandidateStatus.IN_PROGRESS,
                "attempt_status": AttemptStatus.IN_PROGRESS,
                "risk_score": 43.0,
                "risk_level": RiskLevel.MEDIUM,
                "tab_switches": 1,
                "incidents": [
                    {"type": EventType.TAB_SWITCH, "pts": 10.0, "time_offset_min": -18, "sev": IncidentSeverity.MEDIUM},
                    {"type": EventType.COPY_PASTE_ATTEMPT, "pts": 15.0, "time_offset_min": -12, "sev": IncidentSeverity.LOW},
                    {"type": EventType.FACE_MISSING, "pts": 18.0, "time_offset_min": -6, "sev": IncidentSeverity.MEDIUM}
                ]
            },
            {
                "name": "Sneha Rao",
                "email": "sneha@gmail.com",
                "token": "SNEHA123",
                "status": CandidateStatus.SUBMITTED,
                "attempt_status": AttemptStatus.SUBMITTED,
                "risk_score": 12.0,
                "risk_level": RiskLevel.LOW,
                "tab_switches": 0,
                "score": 84.0,
                "passed": True,
                "incidents": []
            }
        ]

        for c_seed in candidates_seed:
            inv = db.query(CandidateInvitation).filter(CandidateInvitation.invitation_token == c_seed["token"]).first()
            if not inv:
                inv = CandidateInvitation(
                    assessment_id=assess_python.id,
                    org_id=org.id,
                    email=c_seed["email"],
                    full_name=c_seed["name"],
                    invitation_token=c_seed["token"],
                    expires_at=now + timedelta(days=7),
                    status=c_seed["status"],
                    system_check_passed=True
                )
                db.add(inv)
                db.flush()

            # Attempt
            att = db.query(Attempt).filter(Attempt.invitation_id == inv.id).first()
            if not att and c_seed.get("attempt_status") is not None:
                att = Attempt(
                    invitation_id=inv.id,
                    assessment_id=assess_python.id,
                    candidate_email=inv.email,
                    candidate_name=inv.full_name,
                    status=c_seed["attempt_status"],
                    started_at=now - timedelta(minutes=30),
                    server_expiry_at=now + timedelta(minutes=60),
                    total_score=c_seed.get("score", 0.0),
                    total_max_marks=100.0,
                    percentage=(c_seed.get("score", 0.0) / 100.0) * 100.0,
                    is_passed=c_seed.get("passed", False),
                    risk_score=c_seed["risk_score"],
                    risk_level=c_seed["risk_level"],
                    human_review_status=HumanReviewStatus.PENDING,
                    tab_switch_count=c_seed["tab_switches"]
                )
                db.add(att)
                db.flush()

                # Seed Incidents
                for inc_info in c_seed.get("incidents", []):
                    incident = ProctoringIncident(
                        attempt_id=att.id,
                        event_type=inc_info["type"],
                        severity=inc_info["sev"],
                        risk_points=inc_info["pts"],
                        metadata_json={"simulated": True, "note": "Automated security detection"},
                        snapshot_data=inc_info.get("snapshot", None),
                        occurred_at=now + timedelta(minutes=inc_info["time_offset_min"])
                    )
                    db.add(incident)

        db.commit()
        logger.info("ProctorAI database seeded successfully with rich demo data.")
    except Exception as e:
        logger.error(f"Error seeding ProctorAI data: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
