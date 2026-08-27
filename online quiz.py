# -*- coding: utf-8 -*-
"""
Created on Mon Aug 24 12:42:31 2026

@author: acer
"""

from flask import (
    Flask, request, redirect, url_for, session,
    render_template_string, flash, send_file
)
import sqlite3
import csv
import io
import secrets
import socket
from datetime import datetime
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash


# ============================================================
# APPLICATION CONFIGURATION
# ============================================================

app = Flask(__name__)

# Change this in a real deployment
app.secret_key = "ONLINE_QUIZ_SECRET_KEY_2026"

DATABASE = "online_quiz.db"

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def init_database():

    conn = get_db()
    cursor = conn.cursor()

    # --------------------------------------------------------
    # USERS
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT NOT NULL,
            email TEXT,
            role TEXT DEFAULT 'student',
            created_at TEXT NOT NULL
        )
    """)

    # --------------------------------------------------------
    # QUIZZES
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quizzes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            duration INTEGER DEFAULT 30,
            pass_percentage REAL DEFAULT 40,
            share_code TEXT UNIQUE NOT NULL,
            is_published INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)

    # --------------------------------------------------------
    # QUESTIONS
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quiz_id INTEGER NOT NULL,
            question_text TEXT NOT NULL,
            option_a TEXT NOT NULL,
            option_b TEXT NOT NULL,
            option_c TEXT NOT NULL,
            option_d TEXT NOT NULL,
            correct_answer TEXT NOT NULL,
            marks INTEGER DEFAULT 1,
            FOREIGN KEY (quiz_id)
                REFERENCES quizzes(id)
                ON DELETE CASCADE
        )
    """)

    # --------------------------------------------------------
    # ATTEMPTS
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quiz_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            score REAL DEFAULT 0,
            total_marks REAL DEFAULT 0,
            percentage REAL DEFAULT 0,
            grade TEXT,
            started_at TEXT,
            submitted_at TEXT,
            FOREIGN KEY (quiz_id)
                REFERENCES quizzes(id)
                ON DELETE CASCADE,
            FOREIGN KEY (student_id)
                REFERENCES users(id)
                ON DELETE CASCADE
        )
    """)

    # --------------------------------------------------------
    # ANSWERS
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            attempt_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            selected_answer TEXT,
            is_correct INTEGER DEFAULT 0,
            marks_obtained REAL DEFAULT 0,
            FOREIGN KEY (attempt_id)
                REFERENCES attempts(id)
                ON DELETE CASCADE,
            FOREIGN KEY (question_id)
                REFERENCES questions(id)
                ON DELETE CASCADE
        )
    """)

    # --------------------------------------------------------
    # DEFAULT ADMIN
    # --------------------------------------------------------

    admin = cursor.execute(
        "SELECT id FROM users WHERE username = ?",
        (ADMIN_USERNAME,)
    ).fetchone()

    if not admin:

        cursor.execute("""
            INSERT INTO users
            (
                username,
                password,
                full_name,
                email,
                role,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            ADMIN_USERNAME,
            generate_password_hash(ADMIN_PASSWORD),
            "System Administrator",
            "admin@example.com",
            "admin",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

    conn.commit()
    conn.close()


# ============================================================
# LOGIN DECORATORS
# ============================================================

def login_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if "user_id" not in session:

            flash(
                "Please login first.",
                "warning"
            )

            return redirect(
                url_for("login")
            )

        return function(*args, **kwargs)

    return wrapper


def admin_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if session.get("role") != "admin":

            flash(
                "Admin access required.",
                "danger"
            )

            return redirect(
                url_for("login")
            )

        return function(*args, **kwargs)

    return wrapper


# ============================================================
# MAIN HTML TEMPLATE
# ============================================================

BASE_HTML = """
<!DOCTYPE html>

<html>

<head>

<meta charset="UTF-8">

<meta name="viewport"
      content="width=device-width, initial-scale=1.0">

<title>{{ title }}</title>

<style>

* {
    box-sizing: border-box;
}

body {

    margin: 0;

    font-family:
    Arial,
    Helvetica,
    sans-serif;

    background: #f4f7fb;

    color: #172033;
}


/* NAVIGATION */

.navbar {

    background: #101d3c;

    color: white;

    padding: 16px 5%;

    display: flex;

    justify-content:
    space-between;

    align-items: center;

    flex-wrap: wrap;

}

.navbar h2 {

    margin: 0;

}

.navbar a {

    color: white;

    text-decoration: none;

    margin-left: 20px;

    font-weight: bold;

}


/* CONTAINER */

.container {

    width: 92%;

    max-width: 1250px;

    margin: 30px auto;

}


/* HERO */

.hero {

    background:
    linear-gradient(
        135deg,
        #102a56,
        #2463a5
    );

    color: white;

    padding: 45px;

    border-radius: 18px;

    margin-bottom: 30px;

}

.hero h1 {

    font-size: 38px;

    margin-bottom: 10px;

}


/* CARD */

.card {

    background: white;

    border-radius: 16px;

    padding: 25px;

    margin-bottom: 25px;

    box-shadow:
    0 5px 20px
    rgba(0,0,0,0.08);

}


/* GRID */

.grid {

    display: grid;

    grid-template-columns:
    repeat(
        auto-fit,
        minmax(220px, 1fr)
    );

    gap: 20px;

}


/* STAT */

.stat {

    background: white;

    padding: 25px;

    border-radius: 15px;

    box-shadow:
    0 4px 15px
    rgba(0,0,0,0.08);

}

.stat h2 {

    color: #174a87;

    font-size: 32px;

    margin: 5px 0;

}


/* FORM */

input,
textarea,
select {

    width: 100%;

    padding: 13px;

    margin: 7px 0 15px;

    border:
    1px solid #ccd3df;

    border-radius: 8px;

    font-size: 15px;

}

textarea {

    min-height: 100px;

}


/* BUTTON */

button,
.btn {

    display: inline-block;

    border: none;

    padding: 12px 20px;

    border-radius: 8px;

    background: #1769aa;

    color: white;

    text-decoration: none;

    cursor: pointer;

    font-weight: bold;

}

.btn-success {

    background: #198754;

}

.btn-danger {

    background: #dc3545;

}

.btn-warning {

    background: #d98c00;

}

.btn-secondary {

    background: #5d6675;

}

.btn-small {

    padding: 8px 12px;

    font-size: 13px;

}


/* TABLE */

table {

    width: 100%;

    border-collapse: collapse;

    margin-top: 15px;

}

th,
td {

    padding: 13px;

    border-bottom:
    1px solid #e0e4ea;

    text-align: left;

}

th {

    background: #eef3f9;

}


/* BADGES */

.badge {

    padding: 6px 10px;

    border-radius: 20px;

    font-size: 12px;

    font-weight: bold;

}

.badge-green {

    background: #d1f2df;

    color: #08783d;

}

.badge-red {

    background: #ffd9dd;

    color: #a80014;

}

.badge-blue {

    background: #dcecff;

    color: #12518e;

}


/* ALERT */

.alert {

    padding: 14px;

    border-radius: 8px;

    margin-bottom: 20px;

}

.alert-success {

    background: #d1f2df;

}

.alert-danger {

    background: #ffd9dd;

}

.alert-warning {

    background: #fff0c2;

}


/* QUESTION */

.question {

    border-left:
    5px solid #1769aa;

    padding: 20px;

    margin-bottom: 25px;

    background: #f9fbfe;

    border-radius: 10px;

}

.option {

    display: block;

    padding: 12px;

    background: white;

    border:
    1px solid #dce2ea;

    margin: 8px 0;

    border-radius: 8px;

    cursor: pointer;

}

.option:hover {

    background: #eef6ff;

}


/* TIMER */

.timer {

    position: sticky;

    top: 10px;

    z-index: 10;

    background: #fff3cd;

    color: #6c5000;

    padding: 15px;

    text-align: center;

    font-size: 20px;

    font-weight: bold;

    border-radius: 10px;

    margin-bottom: 20px;

}


/* LOGIN */

.login-box {

    max-width: 500px;

    margin: 70px auto;

}


/* CENTER */

.center {

    text-align: center;

}


/* RESULT */

.result-circle {

    font-size: 50px;

    font-weight: bold;

    color: #1769aa;

}


/* SHARE LINK */

.link-box {

    background: #eef5ff;

    padding: 15px;

    border-radius: 10px;

    word-break: break-all;

}


/* FOOTER */

footer {

    margin-top: 50px;

    background: #101d3c;

    color: white;

    text-align: center;

    padding: 25px;

}


/* MOBILE */

@media(max-width: 700px) {

    .hero h1 {

        font-size: 28px;

    }

    .navbar {

        gap: 15px;

    }

    table {

        display: block;

        overflow-x: auto;

    }

}

</style>

</head>


<body>


<nav class="navbar">

<h2>Online Quiz System</h2>


<div>

{% if session.get("user_id") %}

    {% if session.get("role") == "admin" %}

        <a href="{{ url_for('admin_dashboard') }}">
            Admin Portal
        </a>

        <a href="{{ url_for('admin_students') }}">
            Students
        </a>

    {% else %}

        <a href="{{ url_for('student_dashboard') }}">
            Student Portal
        </a>

    {% endif %}

    <a href="{{ url_for('logout') }}">
        Logout
    </a>

{% else %}

    <a href="{{ url_for('home') }}">
        Home
    </a>

    <a href="{{ url_for('login') }}">
        Login
    </a>

    <a href="{{ url_for('register') }}">
        Register
    </a>

{% endif %}

</div>

</nav>


<div class="container">


{% with messages =
get_flashed_messages(
with_categories=true
) %}

    {% for category, message in messages %}

        <div class="alert alert-{{ category }}">
            {{ message }}
        </div>

    {% endfor %}

{% endwith %}


{{ content|safe }}


</div>


<footer>

Advanced Online Quiz Management System

<br><br>

Python Flask + SQLite

</footer>


</body>

</html>
"""


# ============================================================
# PAGE RENDER FUNCTION
# ============================================================

def page(title, content, **kwargs):

    return render_template_string(

        BASE_HTML,

        title=title,

        content=render_template_string(
            content,
            **kwargs
        )

    )


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    content = """

    <div class="hero">

        <h1>
            Online Quiz Management System
        </h1>

        <p>

        Advanced online examination platform
        for students and administrators.

        </p>

        <br>

        <a class="btn"
           href="{{ url_for('login') }}">

            Login

        </a>

        <a class="btn btn-success"
           href="{{ url_for('register') }}">

            Student Registration

        </a>

    </div>


    <div class="grid">


        <div class="card">

            <h2>
                Student Portal
            </h2>

            <p>

            Students can register,
            login, attend quizzes,
            submit answers and
            view results.

            </p>

        </div>


        <div class="card">

            <h2>
                Admin Portal
            </h2>

            <p>

            Admin can create quizzes,
            add questions, publish quizzes
            and monitor student performance.

            </p>

        </div>


        <div class="card">

            <h2>
                Performance Analytics
            </h2>

            <p>

            View attempts, scores,
            averages, highest score,
            lowest score and question
            performance.

            </p>

        </div>


        <div class="card">

            <h2>
                Quiz Sharing
            </h2>

            <p>

            Every quiz receives a unique
            link which can be shared
            with students.

            </p>

        </div>


    </div>

    """

    return page(
        "Online Quiz System",
        content
    )


# ============================================================
# STUDENT REGISTRATION
# ============================================================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if request.method == "POST":

        username = request.form[
            "username"
        ].strip()

        password = request.form[
            "password"
        ]

        full_name = request.form[
            "full_name"
        ].strip()

        email = request.form.get(
            "email",
            ""
        ).strip()


        if not username or \
           not password or \
           not full_name:

            flash(
                "Please fill all required fields.",
                "danger"
            )

            return redirect(
                url_for("register")
            )


        conn = get_db()


        try:

            conn.execute("""
                INSERT INTO users
                (
                    username,
                    password,
                    full_name,
                    email,
                    role,
                    created_at
                )
                VALUES (?, ?, ?, ?, 'student', ?)
            """, (

                username,

                generate_password_hash(
                    password
                ),

                full_name,

                email,

                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

            ))


            conn.commit()

            flash(
                "Registration successful. Please login.",
                "success"
            )

            return redirect(
                url_for("login")
            )


        except sqlite3.IntegrityError:

            flash(
                "Username already exists.",
                "danger"
            )


        finally:

            conn.close()


    content = """

    <div class="card login-box">

        <h1>
            Student Registration
        </h1>


        <form method="POST">


            <label>
                Full Name
            </label>

            <input
                type="text"
                name="full_name"
                required
            >


            <label>
                Username
            </label>

            <input
                type="text"
                name="username"
                required
            >


            <label>
                Email
            </label>

            <input
                type="email"
                name="email"
            >


            <label>
                Password
            </label>

            <input
                type="password"
                name="password"
                required
            >


            <button type="submit">

                Create Student Account

            </button>


        </form>


    </div>

    """

    return page(
        "Student Registration",
        content
    )


# ============================================================
# LOGIN
# ============================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        username = request.form[
            "username"
        ].strip()

        password = request.form[
            "password"
        ]


        conn = get_db()


        user = conn.execute(

            """
            SELECT *
            FROM users
            WHERE username = ?
            """,

            (username,)

        ).fetchone()


        conn.close()


        if user and check_password_hash(

            user["password"],

            password

        ):

            session.clear()


            session["user_id"] = \
                user["id"]

            session["username"] = \
                user["username"]

            session["full_name"] = \
                user["full_name"]

            session["role"] = \
                user["role"]


            if user["role"] == "admin":

                return redirect(
                    url_for(
                        "admin_dashboard"
                    )
                )


            return redirect(
                url_for(
                    "student_dashboard"
                )
            )


        flash(
            "Invalid username or password.",
            "danger"
        )


    content = """

    <div class="card login-box">

        <h1>
            Login
        </h1>


        <form method="POST">


            <label>
                Username
            </label>

            <input
                type="text"
                name="username"
                required
            >


            <label>
                Password
            </label>

            <input
                type="password"
                name="password"
                required
            >


            <button type="submit">

                Login

            </button>


        </form>


        <hr>


        <p>

        New student?

        <a href="{{ url_for('register') }}">

            Register here

        </a>

        </p>


        <p>

        <b>Default Admin Login</b>

        </p>

        <p>

        Username:
        <b>admin</b>

        <br>

        Password:
        <b>admin123</b>

        </p>


    </div>

    """

    return page(
        "Login",
        content
    )


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    flash(
        "You have been logged out.",
        "success"
    )

    return redirect(
        url_for("home")
    )


# ============================================================
# STUDENT DASHBOARD
# ============================================================

@app.route("/student")
@login_required
def student_dashboard():

    if session.get("role") != "student":

        return redirect(
            url_for("admin_dashboard")
        )


    conn = get_db()


    quizzes = conn.execute("""

        SELECT

            q.*,

            COUNT(
                DISTINCT qu.id
            ) AS question_count

        FROM quizzes q

        LEFT JOIN questions qu
            ON q.id = qu.quiz_id

        WHERE q.is_published = 1

        GROUP BY q.id

        ORDER BY q.created_at DESC

    """).fetchall()


    attempts = conn.execute("""

        SELECT

            a.*,

            q.title

        FROM attempts a

        JOIN quizzes q
            ON a.quiz_id = q.id

        WHERE a.student_id = ?

        ORDER BY
            a.submitted_at DESC

    """, (

        session["user_id"],

    )).fetchall()


    conn.close()


    content = """

    <div class="hero">

        <h1>

        Welcome,
        {{ session["full_name"] }}

        </h1>

        <p>
            Student Portal
        </p>

    </div>


    <div class="card">

        <h2>
            Available Quizzes
        </h2>


        {% if quizzes %}


        <div class="grid">


        {% for quiz in quizzes %}


        <div class="card">

            <h2>
                {{ quiz["title"] }}
            </h2>


            <p>
                {{ quiz["description"] }}
            </p>


            <p>

            Questions:
            <b>
                {{ quiz["question_count"] }}
            </b>

            </p>


            <p>

            Duration:
            <b>
                {{ quiz["duration"] }} minutes
            </b>

            </p>


            <p>

            Pass Mark:
            <b>
                {{ quiz["pass_percentage"] }}%
            </b>

            </p>


            <a class="btn"
               href="{{ url_for(
                   'take_quiz',
                   code=quiz['share_code']
               ) }}">

                Attend Quiz

            </a>


        </div>


        {% endfor %}


        </div>


        {% else %}


        <p>
            No quizzes available.
        </p>


        {% endif %}


    </div>


    <div class="card">

        <h2>
            My Previous Results
        </h2>


        {% if attempts %}


        <table>


        <tr>

            <th>Quiz</th>

            <th>Score</th>

            <th>Percentage</th>

            <th>Grade</th>

            <th>Date</th>

            <th>View</th>

        </tr>


        {% for attempt in attempts %}


        <tr>

            <td>
                {{ attempt["title"] }}
            </td>


            <td>

                {{ attempt["score"] }}

                /

                {{ attempt["total_marks"] }}

            </td>


            <td>

                {{ "%.2f"|format(
                    attempt["percentage"]
                ) }}%

            </td>


            <td>
                {{ attempt["grade"] }}
            </td>


            <td>
                {{ attempt["submitted_at"] }}
            </td>


            <td>

                <a
                    class="btn btn-small"
                    href="{{ url_for(
                        'student_result',
                        attempt_id=attempt['id']
                    ) }}"
                >

                    View

                </a>

            </td>


        </tr>


        {% endfor %}


        </table>


        {% else %}


        <p>
            No attempts yet.
        </p>


        {% endif %}


    </div>

    """


    return page(

        "Student Dashboard",

        content,

        quizzes=quizzes,

        attempts=attempts

    )


# ============================================================
# TAKE QUIZ
# ============================================================

@app.route(
    "/quiz/<code>",
    methods=["GET", "POST"]
)
@login_required
def take_quiz(code):

    if session.get("role") != "student":

        flash(
            "Only students can attend quizzes.",
            "danger"
        )

        return redirect(
            url_for("admin_dashboard")
        )


    conn = get_db()


    quiz = conn.execute("""

        SELECT *

        FROM quizzes

        WHERE share_code = ?

        AND is_published = 1

    """, (

        code,

    )).fetchone()


    if not quiz:

        conn.close()

        return page(

            "Quiz Not Found",

            """

            <div class="card center">

                <h1>
                    Quiz Not Found
                </h1>

                <p>
                    This quiz link is invalid
                    or the quiz is unavailable.
                </p>

            </div>

            """

        )


    questions = conn.execute("""

        SELECT *

        FROM questions

        WHERE quiz_id = ?

        ORDER BY id

    """, (

        quiz["id"],

    )).fetchall()


    previous = conn.execute("""

        SELECT id

        FROM attempts

        WHERE quiz_id = ?

        AND student_id = ?

    """, (

        quiz["id"],

        session["user_id"]

    )).fetchone()


    if previous:

        conn.close()

        return page(

            "Already Attempted",

            f"""

            <div class="card center">

                <h1>
                    Quiz Already Attempted
                </h1>

                <p>
                    You have already submitted
                    this quiz.
                </p>

                <a class="btn"
                   href="{url_for(
                       'student_result',
                       attempt_id=previous['id']
                   )}">

                    View Result

                </a>

            </div>

            """

        )


    # --------------------------------------------------------
    # SUBMIT QUIZ
    # --------------------------------------------------------

    if request.method == "POST":

        started_at = session.get(
            "quiz_started_at_" +
            str(quiz["id"])
        )


        if not started_at:

            started_at = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )


        score = 0

        total_marks = 0


        conn.execute("""

            INSERT INTO attempts

            (
                quiz_id,
                student_id,
                score,
                total_marks,
                percentage,
                grade,
                started_at,
                submitted_at
            )

            VALUES
            (?, ?, 0, 0, 0, '', ?, ?)

        """, (

            quiz["id"],

            session["user_id"],

            started_at,

            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

        ))


        attempt_id = conn.execute(
            "SELECT last_insert_rowid()"
        ).fetchone()[0]


        # ----------------------------------------------------
        # EVALUATE QUESTIONS
        # ----------------------------------------------------

        for question in questions:

            qid = str(
                question["id"]
            )


            selected = request.form.get(

                "question_" + qid,

                ""

            )


            correct = \
                question["correct_answer"]


            marks = \
                question["marks"]


            total_marks += marks


            is_correct = (
                selected == correct
            )


            obtained = (
                marks
                if is_correct
                else 0
            )


            if is_correct:

                score += marks


            conn.execute("""

                INSERT INTO answers

                (
                    attempt_id,
                    question_id,
                    selected_answer,
                    is_correct,
                    marks_obtained
                )

                VALUES (?, ?, ?, ?, ?)

            """, (

                attempt_id,

                question["id"],

                selected,

                int(is_correct),

                obtained

            ))


        percentage = (

            (score / total_marks) * 100

            if total_marks > 0

            else 0

        )


        # ----------------------------------------------------
        # GRADE
        # ----------------------------------------------------

        if percentage >= 90:

            grade = "A+"

        elif percentage >= 80:

            grade = "A"

        elif percentage >= 70:

            grade = "B"

        elif percentage >= 60:

            grade = "C"

        elif percentage >= quiz[
            "pass_percentage"
        ]:

            grade = "D"

        else:

            grade = "F"


        conn.execute("""

            UPDATE attempts

            SET

                score = ?,

                total_marks = ?,

                percentage = ?,

                grade = ?,

                submitted_at = ?

            WHERE id = ?

        """, (

            score,

            total_marks,

            percentage,

            grade,

            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),

            attempt_id

        ))


        conn.commit()

        conn.close()


        session.pop(

            "quiz_started_at_" +
            str(quiz["id"]),

            None

        )


        return redirect(

            url_for(

                "student_result",

                attempt_id=attempt_id

            )

        )


    # --------------------------------------------------------
    # START TIMER
    # --------------------------------------------------------

    key = (

        "quiz_started_at_" +
        str(quiz["id"])

    )


    if key not in session:

        session[key] = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )


    conn.close()


    content = """

    <div class="hero">

        <h1>
            {{ quiz["title"] }}
        </h1>

        <p>
            {{ quiz["description"] }}
        </p>

        <p>

        Total Questions:

        <b>
            {{ questions|length }}
        </b>

        </p>

    </div>


    <div class="timer">

        Time Remaining:

        <span id="timer">
            {{ quiz["duration"] }}:00
        </span>

    </div>


    <form
        method="POST"
        id="quizForm"
    >


    {% for question in questions %}


    <div class="question">


        <h3>

        Q{{ loop.index }}.

        {{ question["question_text"] }}

        </h3>


        <p>

        Marks:

        <b>
            {{ question["marks"] }}
        </b>

        </p>


        <label class="option">

            <input
                type="radio"
                name="question_{{ question['id'] }}"
                value="A"
            >

            A.
            {{ question["option_a"] }}

        </label>


        <label class="option">

            <input
                type="radio"
                name="question_{{ question['id'] }}"
                value="B"
            >

            B.
            {{ question["option_b"] }}

        </label>


        <label class="option">

            <input
                type="radio"
                name="question_{{ question['id'] }}"
                value="C"
            >

            C.
            {{ question["option_c"] }}

        </label>


        <label class="option">

            <input
                type="radio"
                name="question_{{ question['id'] }}"
                value="D"
            >

            D.
            {{ question["option_d"] }}

        </label>


    </div>


    {% endfor %}


    <div class="card center">


        <button
            type="submit"
            class="btn-success"
            onclick="return confirm(
                'Are you sure you want to submit the quiz?'
            )"
        >

            Submit Quiz

        </button>


    </div>


    </form>


    <script>


    let totalSeconds =
        {{ quiz["duration"] }} * 60;


    function updateTimer() {


        let minutes =
            Math.floor(
                totalSeconds / 60
            );


        let seconds =
            totalSeconds % 60;


        document.getElementById(
            "timer"
        ).innerHTML =

            minutes +
            ":" +
            String(seconds)
                .padStart(2, "0");


        if (totalSeconds <= 0) {


            alert(
                "Time is over. The quiz will be submitted."
            );


            document.getElementById(
                "quizForm"
            ).submit();


        }

        else {


            totalSeconds--;

            setTimeout(
                updateTimer,
                1000
            );

        }

    }


    updateTimer();


    </script>

    """


    return page(

        quiz["title"],

        content,

        quiz=quiz,

        questions=questions

    )


# ============================================================
# STUDENT RESULT
# ============================================================

@app.route(
    "/result/<int:attempt_id>"
)
@login_required
def student_result(attempt_id):

    conn = get_db()


    attempt = conn.execute("""

        SELECT

            a.*,

            q.title,

            q.pass_percentage

        FROM attempts a

        JOIN quizzes q
            ON a.quiz_id = q.id

        WHERE a.id = ?

        AND a.student_id = ?

    """, (

        attempt_id,

        session["user_id"]

    )).fetchone()


    if not attempt:

        conn.close()

        return page(

            "Result",

            """

            <div class="card center">

                <h1>
                    Result Not Found
                </h1>

            </div>

            """

        )


    answers = conn.execute("""

        SELECT

            ans.*,

            q.question_text,

            q.correct_answer

        FROM answers ans

        JOIN questions q
            ON ans.question_id = q.id

        WHERE ans.attempt_id = ?

        ORDER BY ans.id

    """, (

        attempt_id,

    )).fetchall()


    conn.close()


    passed = (

        attempt["percentage"]

        >= attempt["pass_percentage"]

    )


    content = """

    <div class="card center">


        <h1>
            {{ attempt["title"] }}
        </h1>


        <div class="result-circle">

            {{ "%.2f"|format(
                attempt["percentage"]
            ) }}%

        </div>


        <h2>

            {{ attempt["score"] }}

            /

            {{ attempt["total_marks"] }}

        </h2>


        {% if passed %}


        <span class="badge badge-green">

            PASS

        </span>


        {% else %}


        <span class="badge badge-red">

            FAIL

        </span>


        {% endif %}


        <h3>

            Grade:
            {{ attempt["grade"] }}

        </h3>


    </div>


    <div class="card">


        <h2>
            Answer Review
        </h2>


        {% for answer in answers %}


        <div class="question">


            <h3>

                Q{{ loop.index }}.

                {{ answer["question_text"] }}

            </h3>


            <p>

                Your Answer:

                <b>

                {% if answer["selected_answer"] %}

                    {{ answer["selected_answer"] }}

                {% else %}

                    Not Answered

                {% endif %}

                </b>

            </p>


            <p>

                Correct Answer:

                <b>
                    {{ answer["correct_answer"] }}
                </b>

            </p>


            {% if answer["is_correct"] %}


            <span class="badge badge-green">

                Correct

            </span>


            {% else %}


            <span class="badge badge-red">

                Incorrect

            </span>


            {% endif %}


        </div>


        {% endfor %}


    </div>


    <a
        class="btn"
        href="{{ url_for(
            'student_dashboard'
        ) }}"
    >

        Back to Dashboard

    </a>

    """


    return page(

        "Quiz Result",

        content,

        attempt=attempt,

        answers=answers

    )


# ============================================================
# ADMIN DASHBOARD
# ============================================================

@app.route("/admin")
@admin_required
def admin_dashboard():

    conn = get_db()


    total_quizzes = conn.execute(

        "SELECT COUNT(*) FROM quizzes"

    ).fetchone()[0]


    published_quizzes = conn.execute(

        """
        SELECT COUNT(*)
        FROM quizzes
        WHERE is_published = 1
        """

    ).fetchone()[0]


    total_students = conn.execute(

        """
        SELECT COUNT(*)
        FROM users
        WHERE role = 'student'
        """

    ).fetchone()[0]


    total_attempts = conn.execute(

        "SELECT COUNT(*) FROM attempts"

    ).fetchone()[0]


    average_score = conn.execute("""

        SELECT AVG(percentage)

        FROM attempts

    """).fetchone()[0]


    quizzes = conn.execute("""

        SELECT

            q.*,

            COUNT(
                DISTINCT qu.id
            ) AS question_count,

            COUNT(
                DISTINCT a.id
            ) AS attempt_count

        FROM quizzes q

        LEFT JOIN questions qu
            ON q.id = qu.quiz_id

        LEFT JOIN attempts a
            ON q.id = a.quiz_id

        GROUP BY q.id

        ORDER BY q.created_at DESC

    """).fetchall()


    conn.close()


    if average_score is None:

        average_score = 0


    content = """

    <div class="hero">


        <h1>
            Admin Portal
        </h1>


        <p>

            Quiz Management
            and Student Analytics

        </p>


        <a
            class="btn btn-success"
            href="{{ url_for(
                'create_quiz'
            ) }}"
        >

            + Create New Quiz

        </a>


    </div>


    <div class="grid">


        <div class="stat">

            <p>
                Total Quizzes
            </p>

            <h2>
                {{ total_quizzes }}
            </h2>

        </div>


        <div class="stat">

            <p>
                Published Quizzes
            </p>

            <h2>
                {{ published_quizzes }}
            </h2>

        </div>


        <div class="stat">

            <p>
                Registered Students
            </p>

            <h2>
                {{ total_students }}
            </h2>

        </div>


        <div class="stat">

            <p>
                Total Attempts
            </p>

            <h2>
                {{ total_attempts }}
            </h2>

        </div>


        <div class="stat">

            <p>
                Average Score
            </p>

            <h2>

                {{ "%.2f"|format(
                    average_score
                ) }}%

            </h2>

        </div>


    </div>


    <div class="card">


        <h2>
            Quiz Management
        </h2>


        {% if quizzes %}


        <table>


        <tr>

            <th>
                Quiz
            </th>

            <th>
                Questions
            </th>

            <th>
                Students Attempted
            </th>

            <th>
                Status
            </th>

            <th>
                Quiz Link
            </th>

            <th>
                Actions
            </th>

        </tr>


        {% for quiz in quizzes %}


        <tr>


            <td>

                <b>
                    {{ quiz["title"] }}
                </b>

                <br>

                <small>
                    {{ quiz["created_at"] }}
                </small>

            </td>


            <td>
                {{ quiz["question_count"] }}
            </td>


            <td>
                {{ quiz["attempt_count"] }}
            </td>


            <td>


            {% if quiz["is_published"] %}


                <span class="badge badge-green">

                    Published

                </span>


            {% else %}


                <span class="badge badge-red">

                    Draft

                </span>


            {% endif %}


            </td>


            <td>


            {% if quiz["is_published"] %}


                <a
                    href="{{ url_for(
                        'take_quiz',
                        code=quiz['share_code'],
                        _external=True
                    ) }}"
                    target="_blank"
                >

                    Open Quiz Link

                </a>


            {% else %}

                Not Published

            {% endif %}


            </td>


            <td>


                <a
                    class="btn btn-small"
                    href="{{ url_for(
                        'manage_quiz',
                        quiz_id=quiz['id']
                    ) }}"
                >

                    Manage

                </a>


                <a
                    class="btn btn-small btn-warning"
                    href="{{ url_for(
                        'quiz_results',
                        quiz_id=quiz['id']
                    ) }}"
                >

                    Results

                </a>


            </td>


        </tr>


        {% endfor %}


        </table>


        {% else %}


        <p>
            No quizzes created yet.
        </p>


        {% endif %}


    </div>

    """


    return page(

        "Admin Dashboard",

        content,

        total_quizzes=total_quizzes,

        published_quizzes=
            published_quizzes,

        total_students=
            total_students,

        total_attempts=
            total_attempts,

        average_score=
            average_score,

        quizzes=quizzes

    )


# ============================================================
# CREATE QUIZ
# ============================================================

@app.route(
    "/admin/create-quiz",
    methods=["GET", "POST"]
)
@admin_required
def create_quiz():

    if request.method == "POST":


        title = request.form[
            "title"
        ].strip()


        description = request.form[
            "description"
        ].strip()


        duration = int(

            request.form.get(
                "duration",
                30
            )

        )


        pass_percentage = float(

            request.form.get(
                "pass_percentage",
                40
            )

        )


        share_code = \
            secrets.token_urlsafe(8)


        conn = get_db()


        conn.execute("""

            INSERT INTO quizzes

            (
                title,
                description,
                duration,
                pass_percentage,
                share_code,
                is_published,
                created_at
            )

            VALUES
            (?, ?, ?, ?, ?, 0, ?)

        """, (

            title,

            description,

            duration,

            pass_percentage,

            share_code,

            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

        ))


        quiz_id = conn.execute(

            "SELECT last_insert_rowid()"

        ).fetchone()[0]


        conn.commit()

        conn.close()


        flash(
            "Quiz created successfully.",
            "success"
        )


        return redirect(

            url_for(

                "manage_quiz",

                quiz_id=quiz_id

            )

        )


    content = """

    <div class="card">


        <h1>
            Create New Quiz
        </h1>


        <form method="POST">


            <label>
                Quiz Title
            </label>


            <input
                type="text"
                name="title"
                placeholder="Example: Python Programming Quiz"
                required
            >


            <label>
                Quiz Description
            </label>


            <textarea
                name="description"
                placeholder="Enter quiz description"
                required
            ></textarea>


            <label>
                Duration (Minutes)
            </label>


            <input
                type="number"
                name="duration"
                value="30"
                min="1"
                max="300"
                required
            >


            <label>
                Pass Percentage
            </label>


            <input
                type="number"
                name="pass_percentage"
                value="40"
                min="0"
                max="100"
                step="0.1"
                required
            >


            <button type="submit">

                Create Quiz

            </button>


        </form>


    </div>

    """


    return page(

        "Create Quiz",

        content

    )


# ============================================================
# MANAGE QUIZ
# ============================================================

@app.route(
    "/admin/quiz/<int:quiz_id>",
    methods=["GET", "POST"]
)
@admin_required
def manage_quiz(quiz_id):

    conn = get_db()


    quiz = conn.execute(

        """
        SELECT *
        FROM quizzes
        WHERE id = ?
        """,

        (quiz_id,)

    ).fetchone()


    if not quiz:

        conn.close()

        return redirect(
            url_for("admin_dashboard")
        )


    # --------------------------------------------------------
    # ADD QUESTION
    # --------------------------------------------------------

    if request.method == "POST":


        question_text = request.form[
            "question_text"
        ].strip()


        option_a = request.form[
            "option_a"
        ].strip()


        option_b = request.form[
            "option_b"
        ].strip()


        option_c = request.form[
            "option_c"
        ].strip()


        option_d = request.form[
            "option_d"
        ].strip()


        correct_answer = request.form[
            "correct_answer"
        ]


        marks = int(

            request.form.get(
                "marks",
                1
            )

        )


        conn.execute("""

            INSERT INTO questions

            (
                quiz_id,
                question_text,
                option_a,
                option_b,
                option_c,
                option_d,
                correct_answer,
                marks
            )

            VALUES
            (?, ?, ?, ?, ?, ?, ?, ?)

        """, (

            quiz_id,

            question_text,

            option_a,

            option_b,

            option_c,

            option_d,

            correct_answer,

            marks

        ))


        conn.commit()

        conn.close()


        flash(
            "Question added successfully.",
            "success"
        )


        return redirect(

            url_for(

                "manage_quiz",

                quiz_id=quiz_id

            )

        )


    questions = conn.execute("""

        SELECT *

        FROM questions

        WHERE quiz_id = ?

        ORDER BY id

    """, (

        quiz_id,

    )).fetchall()


    conn.close()


    content = """

    <div class="card">


        <h1>
            {{ quiz["title"] }}
        </h1>


        <p>
            {{ quiz["description"] }}
        </p>


        <div class="grid">


            <div class="stat">

                <p>
                    Duration
                </p>

                <h2>
                    {{ quiz["duration"] }} min
                </h2>

            </div>


            <div class="stat">

                <p>
                    Questions
                </p>

                <h2>
                    {{ questions|length }}
                </h2>

            </div>


            <div class="stat">

                <p>
                    Pass Mark
                </p>

                <h2>
                    {{ quiz["pass_percentage"] }}%
                </h2>

            </div>


        </div>


    </div>


    <div class="card">


        <h2>
            Quiz Sharing
        </h2>


        {% if quiz["is_published"] %}


            <p>

                Share this link with
                your students:

            </p>


            <div class="link-box">


                <b>

                {{ url_for(

                    'take_quiz',

                    code=quiz['share_code'],

                    _external=True

                ) }}

                </b>


            </div>


            <br>


            <a
                class="btn btn-warning"
                href="{{ url_for(
                    'toggle_quiz',
                    quiz_id=quiz['id']
                ) }}"
            >

                Unpublish Quiz

            </a>


        {% else %}


            <p>

                Quiz is currently
                a draft.

            </p>


            <a
                class="btn btn-success"
                href="{{ url_for(
                    'toggle_quiz',
                    quiz_id=quiz['id']
                ) }}"
            >

                Publish Quiz

            </a>


        {% endif %}


    </div>


    <div class="card">


        <h2>
            Add Question
        </h2>


        <form method="POST">


            <label>
                Question
            </label>


            <textarea
                name="question_text"
                required
            ></textarea>


            <label>
                Option A
            </label>


            <input
                type="text"
                name="option_a"
                required
            >


            <label>
                Option B
            </label>


            <input
                type="text"
                name="option_b"
                required
            >


            <label>
                Option C
            </label>


            <input
                type="text"
                name="option_c"
                required
            >


            <label>
                Option D
            </label>


            <input
                type="text"
                name="option_d"
                required
            >


            <label>
                Correct Answer
            </label>


            <select
                name="correct_answer"
                required
            >

                <option value="A">
                    A
                </option>

                <option value="B">
                    B
                </option>

                <option value="C">
                    C
                </option>

                <option value="D">
                    D
                </option>

            </select>


            <label>
                Marks
            </label>


            <input
                type="number"
                name="marks"
                value="1"
                min="1"
                max="100"
                required
            >


            <button type="submit">

                Add Question

            </button>


        </form>


    </div>


    <div class="card">


        <h2>
            Questions
        </h2>


        {% if questions %}


            {% for question in questions %}


            <div class="question">


                <h3>

                    Q{{ loop.index }}.

                    {{ question[
                        "question_text"
                    ] }}

                </h3>


                <p>
                    A.
                    {{ question["option_a"] }}
                </p>


                <p>
                    B.
                    {{ question["option_b"] }}
                </p>


                <p>
                    C.
                    {{ question["option_c"] }}
                </p>


                <p>
                    D.
                    {{ question["option_d"] }}
                </p>


                <p>

                    Correct Answer:

                    <b>
                        {{ question[
                            "correct_answer"
                        ] }}
                    </b>

                </p>


                <p>

                    Marks:

                    <b>
                        {{ question["marks"] }}
                    </b>

                </p>


                <a
                    class="btn btn-danger btn-small"
                    href="{{ url_for(
                        'delete_question',
                        question_id=question['id']
                    ) }}"
                    onclick="return confirm(
                        'Delete this question?'
                    )"
                >

                    Delete Question

                </a>


            </div>


            {% endfor %}


        {% else %}


            <p>
                No questions added yet.
            </p>


        {% endif %}


    </div>

    """


    return page(

        "Manage Quiz",

        content,

        quiz=quiz,

        questions=questions

    )


# ============================================================
# PUBLISH / UNPUBLISH
# ============================================================

@app.route(
    "/admin/toggle/<int:quiz_id>"
)
@admin_required
def toggle_quiz(quiz_id):

    conn = get_db()


    quiz = conn.execute(

        """
        SELECT *
        FROM quizzes
        WHERE id = ?
        """,

        (quiz_id,)

    ).fetchone()


    if quiz:

        new_status = (

            0
            if quiz["is_published"]
            else 1

        )


        conn.execute("""

            UPDATE quizzes

            SET is_published = ?

            WHERE id = ?

        """, (

            new_status,

            quiz_id

        ))


        conn.commit()


    conn.close()


    return redirect(

        url_for(

            "manage_quiz",

            quiz_id=quiz_id

        )

    )


# ============================================================
# DELETE QUESTION
# ============================================================

@app.route(
    "/admin/delete-question/<int:question_id>"
)
@admin_required
def delete_question(question_id):

    conn = get_db()


    question = conn.execute("""

        SELECT quiz_id

        FROM questions

        WHERE id = ?

    """, (

        question_id,

    )).fetchone()


    if question:

        quiz_id = \
            question["quiz_id"]


        conn.execute(

            """
            DELETE FROM questions
            WHERE id = ?
            """,

            (question_id,)

        )


        conn.commit()

        conn.close()


        return redirect(

            url_for(

                "manage_quiz",

                quiz_id=quiz_id

            )

        )


    conn.close()


    return redirect(

        url_for(
            "admin_dashboard"
        )

    )


# ============================================================
# QUIZ RESULTS
# ============================================================

@app.route(
    "/admin/results/<int:quiz_id>"
)
@admin_required
def quiz_results(quiz_id):

    conn = get_db()


    quiz = conn.execute(

        """
        SELECT *
        FROM quizzes
        WHERE id = ?
        """,

        (quiz_id,)

    ).fetchone()


    if not quiz:

        conn.close()

        return redirect(
            url_for(
                "admin_dashboard"
            )
        )


    results = conn.execute("""

        SELECT

            a.id,

            u.full_name,

            u.username,

            u.email,

            a.score,

            a.total_marks,

            a.percentage,

            a.grade,

            a.started_at,

            a.submitted_at

        FROM attempts a

        JOIN users u
            ON a.student_id = u.id

        WHERE a.quiz_id = ?

        ORDER BY
            a.percentage DESC

    """, (

        quiz_id,

    )).fetchall()


    statistics = conn.execute("""

        SELECT

            COUNT(*) AS total_attempts,

            AVG(percentage)
                AS average_percentage,

            MAX(percentage)
                AS highest_percentage,

            MIN(percentage)
                AS lowest_percentage

        FROM attempts

        WHERE quiz_id = ?

    """, (

        quiz_id,

    )).fetchone()


    question_stats = conn.execute("""

        SELECT

            q.id,

            q.question_text,

            COUNT(ans.id)
                AS answer_count,

            SUM(ans.is_correct)
                AS correct_count

        FROM questions q

        LEFT JOIN answers ans

            ON q.id =
               ans.question_id

        WHERE q.quiz_id = ?

        GROUP BY q.id

        ORDER BY q.id

    """, (

        quiz_id,

    )).fetchall()


    conn.close()


    content = """

    <div class="hero">


        <h1>
            {{ quiz["title"] }}
        </h1>


        <p>
            Student Performance Analytics
        </p>


        <a
            class="btn btn-success"
            href="{{ url_for(
                'export_results',
                quiz_id=quiz['id']
            ) }}"
        >

            Export Results CSV

        </a>


    </div>


    <div class="grid">


        <div class="stat">

            <p>
                Students Attempted
            </p>

            <h2>
                {{ statistics[
                    "total_attempts"
                ] or 0 }}
            </h2>

        </div>


        <div class="stat">

            <p>
                Average Score
            </p>

            <h2>

                {{ "%.2f"|format(
                    statistics[
                        "average_percentage"
                    ] or 0
                ) }}%

            </h2>

        </div>


        <div class="stat">

            <p>
                Highest Score
            </p>

            <h2>

                {{ "%.2f"|format(
                    statistics[
                        "highest_percentage"
                    ] or 0
                ) }}%

            </h2>

        </div>


        <div class="stat">

            <p>
                Lowest Score
            </p>

            <h2>

                {{ "%.2f"|format(
                    statistics[
                        "lowest_percentage"
                    ] or 0
                ) }}%

            </h2>

        </div>


    </div>


    <div class="card">


        <h2>
            Student Results
        </h2>


        {% if results %}


        <input
            type="text"
            id="searchBox"
            placeholder="Search student..."
            onkeyup="searchTable()"
        >


        <table id="resultsTable">


        <tr>

            <th>
                Student
            </th>

            <th>
                Username
            </th>

            <th>
                Score
            </th>

            <th>
                Percentage
            </th>

            <th>
                Grade
            </th>

            <th>
                Submitted
            </th>

            <th>
                Details
            </th>

        </tr>


        {% for result in results %}


        <tr>


            <td>
                {{ result["full_name"] }}
            </td>


            <td>
                {{ result["username"] }}
            </td>


            <td>

                {{ result["score"] }}

                /

                {{ result["total_marks"] }}

            </td>


            <td>

                {{ "%.2f"|format(
                    result["percentage"]
                ) }}%

            </td>


            <td>
                {{ result["grade"] }}
            </td>


            <td>
                {{ result["submitted_at"] }}
            </td>


            <td>


                <a
                    class="btn btn-small"
                    href="{{ url_for(
                        'admin_attempt_details',
                        attempt_id=result['id']
                    ) }}"
                >

                    View

                </a>


            </td>


        </tr>


        {% endfor %}


        </table>


        {% else %}


        <p>

            No students have attempted
            this quiz yet.

        </p>


        {% endif %}


    </div>


    <div class="card">


        <h2>
            Question-wise Performance
        </h2>


        <table>


        <tr>

            <th>
                Question
            </th>

            <th>
                Attempts
            </th>

            <th>
                Correct
            </th>

            <th>
                Success Rate
            </th>

        </tr>


        {% for question
           in question_stats %}


        <tr>


            <td>
                {{ question[
                    "question_text"
                ] }}
            </td>


            <td>
                {{ question[
                    "answer_count"
                ] }}
            </td>


            <td>
                {{ question[
                    "correct_count"
                ] or 0 }}
            </td>


            <td>


            {% if question[
                "answer_count"
            ] %}


                {{ "%.2f"|format(

                    (

                        (
                            question[
                                "correct_count"
                            ] or 0
                        )

                        /

                        question[
                            "answer_count"
                        ]

                    )

                    * 100

                ) }}%


            {% else %}

                0%

            {% endif %}


            </td>


        </tr>


        {% endfor %}


        </table>


    </div>


    <script>


    function searchTable() {


        let input =
            document.getElementById(
                "searchBox"
            );


        let filter =
            input.value.toLowerCase();


        let table =
            document.getElementById(
                "resultsTable"
            );


        let rows =
            table.getElementsByTagName(
                "tr"
            );


        for (
            let i = 1;
            i < rows.length;
            i++
        ) {


            let text =
                rows[i]
                .innerText
                .toLowerCase();


            rows[i].style.display =

                text.includes(filter)
                ? ""
                : "none";


        }


    }


    </script>

    """


    return page(

        "Quiz Results",

        content,

        quiz=quiz,

        results=results,

        statistics=statistics,

        question_stats=question_stats

    )


# ============================================================
# ADMIN ATTEMPT DETAILS
# ============================================================

@app.route(
    "/admin/attempt/<int:attempt_id>"
)
@admin_required
def admin_attempt_details(attempt_id):

    conn = get_db()


    attempt = conn.execute("""

        SELECT

            a.*,

            u.full_name,

            u.username,

            u.email,

            q.title

        FROM attempts a

        JOIN users u
            ON a.student_id = u.id

        JOIN quizzes q
            ON a.quiz_id = q.id

        WHERE a.id = ?

    """, (

        attempt_id,

    )).fetchone()


    answers = conn.execute("""

        SELECT

            ans.*,

            q.question_text,

            q.correct_answer

        FROM answers ans

        JOIN questions q
            ON ans.question_id = q.id

        WHERE ans.attempt_id = ?

        ORDER BY ans.id

    """, (

        attempt_id,

    )).fetchall()


    conn.close()


    if not attempt:

        return redirect(

            url_for(
                "admin_dashboard"
            )

        )


    content = """

    <div class="hero">


        <h1>
            Student Attempt Details
        </h1>


        <p>
            {{ attempt["full_name"] }}
        </p>


    </div>


    <div class="card">


        <h2>
            Student Information
        </h2>


        <p>

            Name:

            <b>
                {{ attempt["full_name"] }}
            </b>

        </p>


        <p>

            Username:

            <b>
                {{ attempt["username"] }}
            </b>

        </p>


        <p>

            Email:

            <b>
                {{ attempt["email"] }}
            </b>

        </p>


        <p>

            Quiz:

            <b>
                {{ attempt["title"] }}
            </b>

        </p>


        <p>

            Score:

            <b>

                {{ attempt["score"] }}

                /

                {{ attempt["total_marks"] }}

            </b>

        </p>


        <p>

            Percentage:

            <b>

                {{ "%.2f"|format(
                    attempt["percentage"]
                ) }}%

            </b>

        </p>


        <p>

            Grade:

            <b>
                {{ attempt["grade"] }}
            </b>

        </p>


    </div>


    <div class="card">


        <h2>
            Answer Details
        </h2>


        <table>


        <tr>

            <th>
                Question
            </th>

            <th>
                Selected
            </th>

            <th>
                Correct
            </th>

            <th>
                Status
            </th>

            <th>
                Marks
            </th>

        </tr>


        {% for answer in answers %}


        <tr>


            <td>
                {{ answer[
                    "question_text"
                ] }}
            </td>


            <td>

                {{ answer[
                    "selected_answer"
                ] or "Not Answered" }}

            </td>


            <td>
                {{ answer[
                    "correct_answer"
                ] }}
            </td>


            <td>


            {% if answer["is_correct"] %}


                <span
                    class="badge badge-green"
                >

                    Correct

                </span>


            {% else %}


                <span
                    class="badge badge-red"
                >

                    Incorrect

                </span>


            {% endif %}


            </td>


            <td>
                {{ answer[
                    "marks_obtained"
                ] }}
            </td>


        </tr>


        {% endfor %}


        </table>


    </div>

    """


    return page(

        "Attempt Details",

        content,

        attempt=attempt,

        answers=answers

    )


# ============================================================
# EXPORT RESULTS
# ============================================================

@app.route(
    "/admin/export/<int:quiz_id>"
)
@admin_required
def export_results(quiz_id):

    conn = get_db()


    quiz = conn.execute(

        """
        SELECT title
        FROM quizzes
        WHERE id = ?
        """,

        (quiz_id,)

    ).fetchone()


    results = conn.execute("""

        SELECT

            u.full_name,

            u.username,

            u.email,

            a.score,

            a.total_marks,

            a.percentage,

            a.grade,

            a.started_at,

            a.submitted_at

        FROM attempts a

        JOIN users u
            ON a.student_id = u.id

        WHERE a.quiz_id = ?

        ORDER BY
            a.percentage DESC

    """, (

        quiz_id,

    )).fetchall()


    conn.close()


    output = io.StringIO()


    writer = csv.writer(
        output
    )


    writer.writerow([

        "Student Name",

        "Username",

        "Email",

        "Score",

        "Total Marks",

        "Percentage",

        "Grade",

        "Started At",

        "Submitted At"

    ])


    for row in results:


        writer.writerow([

            row["full_name"],

            row["username"],

            row["email"],

            row["score"],

            row["total_marks"],

            row["percentage"],

            row["grade"],

            row["started_at"],

            row["submitted_at"]

        ])


    memory_file = io.BytesIO()


    memory_file.write(

        output
        .getvalue()
        .encode("utf-8")

    )


    memory_file.seek(0)


    filename = (

        quiz["title"]
        .replace(" ", "_")

        +

        "_results.csv"

    )


    return send_file(

        memory_file,

        mimetype="text/csv",

        as_attachment=True,

        download_name=filename

    )


# ============================================================
# ADMIN STUDENT MANAGEMENT
# ============================================================

@app.route(
    "/admin/students"
)
@admin_required
def admin_students():

    conn = get_db()


    students = conn.execute("""

        SELECT

            u.id,

            u.full_name,

            u.username,

            u.email,

            u.created_at,

            COUNT(a.id)
                AS attempt_count,

            AVG(a.percentage)
                AS average_percentage

        FROM users u

        LEFT JOIN attempts a

            ON u.id =
               a.student_id

        WHERE u.role = 'student'

        GROUP BY u.id

        ORDER BY u.full_name

    """).fetchall()


    conn.close()


    content = """

    <div class="card">


        <h1>
            Student Management
        </h1>


        <input
            type="text"
            id="studentSearch"
            placeholder="Search students..."
            onkeyup="filterStudents()"
        >


        <table id="studentTable">


        <tr>

            <th>
                Name
            </th>

            <th>
                Username
            </th>

            <th>
                Email
            </th>

            <th>
                Attempts
            </th>

            <th>
                Average Score
            </th>

            <th>
                Registered
            </th>

        </tr>


        {% for student in students %}


        <tr>


            <td>
                {{ student["full_name"] }}
            </td>


            <td>
                {{ student["username"] }}
            </td>


            <td>
                {{ student["email"] }}
            </td>


            <td>
                {{ student["attempt_count"] }}
            </td>


            <td>


            {% if student[
                "average_percentage"
            ] %}


                {{ "%.2f"|format(

                    student[
                        "average_percentage"
                    ]

                ) }}%


            {% else %}

                No attempts

            {% endif %}


            </td>


            <td>
                {{ student["created_at"] }}
            </td>


        </tr>


        {% endfor %}


        </table>


    </div>


    <script>


    function filterStudents() {


        let input =
            document.getElementById(
                "studentSearch"
            );


        let filter =
            input.value.toLowerCase();


        let rows =
            document.getElementById(
                "studentTable"
            )
            .getElementsByTagName(
                "tr"
            );


        for (
            let i = 1;
            i < rows.length;
            i++
        ) {


            let text =
                rows[i]
                .innerText
                .toLowerCase();


            rows[i].style.display =

                text.includes(filter)
                ? ""
                : "none";


        }


    }


    </script>

    """


    return page(

        "Student Management",

        content,

        students=students

    )


# ============================================================
# ADMIN MENU
# ============================================================

@app.route(
    "/admin/menu"
)
@admin_required
def admin_menu():

    content = """

    <div class="hero">

        <h1>
            Administration Center
        </h1>

    </div>


    <div class="grid">


        <div class="card">

            <h2>
                Quiz Management
            </h2>

            <p>
                Create and manage quizzes.
            </p>

            <a
                class="btn"
                href="{{ url_for(
                    'admin_dashboard'
                ) }}"
            >

                Manage Quizzes

            </a>

        </div>


        <div class="card">

            <h2>
                Create Quiz
            </h2>

            <p>
                Create a new examination.
            </p>

            <a
                class="btn btn-success"
                href="{{ url_for(
                    'create_quiz'
                ) }}"
            >

                Create Quiz

            </a>

        </div>


        <div class="card">

            <h2>
                Students
            </h2>

            <p>
                View registered students.
            </p>

            <a
                class="btn"
                href="{{ url_for(
                    'admin_students'
                ) }}"
            >

                View Students

            </a>

        </div>


    </div>

    """


    return page(

        "Administration Center",

        content

    )


# ============================================================
# 404 ERROR
# ============================================================

@app.errorhandler(404)
def page_not_found(error):

    return page(

        "Page Not Found",

        """

        <div class="card center">

            <h1>
                404
            </h1>

            <h2>
                Page Not Found
            </h2>

            <a
                class="btn"
                href="/"
            >

                Go Home

            </a>

        </div>

        """

    ), 404


# ============================================================
# 500 ERROR
# ============================================================

@app.errorhandler(500)
def internal_error(error):

    return page(

        "Server Error",

        """

        <div class="card center">

            <h1>
                500
            </h1>

            <h2>
                Internal Server Error
            </h2>

            <p>
                Check the Spyder console
                for more information.
            </p>

        </div>

        """

    ), 500


# ============================================================
# GET LOCAL IP ADDRESS
# ============================================================

def get_local_ip():

    try:

        hostname = socket.gethostname()

        local_ip = socket.gethostbyname(
            hostname
        )

        return local_ip

    except Exception:

        return "127.0.0.1"


# ============================================================
# APPLICATION START
# ============================================================

if __name__ == "__main__":


    # Create database
    init_database()


    # Get local IP
    local_ip = get_local_ip()


    print()
    print("=" * 70)

    print(
        "        ONLINE QUIZ MANAGEMENT SYSTEM"
    )

    print("=" * 70)

    print()


    print(
        "ADMIN LOGIN"
    )

    print(
        "Username : admin"
    )

    print(
        "Password : admin123"
    )

    print()


    print(
        "LOCAL ACCESS"
    )

    print(
        "http://127.0.0.1:5000"
    )

    print()


    print(
        "NETWORK ACCESS"
    )

    print(
        "http://" +
        local_ip +
        ":5000"
    )

    print()


    print(
        "Students connected to the same Wi-Fi"
    )

    print(
        "can use the NETWORK ACCESS address."
    )

    print()


    print("=" * 70)

    print()


    # IMPORTANT FOR SPYDER:
    # debug=False prevents Flask's
    # watchdog auto-reloader from
    # causing SystemExit: 1.

    app.run(

        host="0.0.0.0",

        port=5000,

        debug=False,

        use_reloader=False

    )
