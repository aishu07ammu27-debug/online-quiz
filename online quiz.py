import json
import os
import streamlit as st

DATA_FILE = "quizzes.json"

# --- ADMIN CREDENTIALS ---
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "password123"

# --- DEMO STUDENT CREDENTIALS ---
# (Key: Username, Value: Password)
STUDENT_USERS = {
    "student1": "pass123",
    "student2": "pass123",
}


# --- DATA MODELS ---
class Question:

    def __init__(self, prompt, options, correct_option):
        self.prompt = prompt
        self.options = options
        self.correct_option = correct_option

    def to_dict(self):
        return {
            "prompt": self.prompt,
            "options": self.options,
            "correct_option": self.correct_option,
        }

    @staticmethod
    def from_dict(data):
        return Question(data["prompt"], data["options"], data["correct_option"])


class Quiz:

    def __init__(self, title):
        self.title = title
        self.questions = []

    def add_question(self, question):
        self.questions.append(question)

    def to_dict(self):
        return {
            "title": self.title,
            "questions": [q.to_dict() for q in self.questions],
        }

    @staticmethod
    def from_dict(data):
        quiz = Quiz(data["title"])
        quiz.questions = [Question.from_dict(q) for q in data["questions"]]
        return quiz


# --- DATA PERSISTENCE HELPERS ---
def load_data():
    quizzes = {}
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                for title, quiz_data in data.items():
                    quizzes[title] = Quiz.from_dict(quiz_data)
        except json.JSONDecodeError:
            quizzes = {}

    if not quizzes:
        da_quiz = Quiz("Data Analysis Basics")
        questions_data = [
            (
                "What type of data is represented by categories or names?",
                [
                    "Quantitative data",
                    "Qualitative / Categorical data",
                    "Numerical data",
                    "Continuous data",
                ],
                2,
            ),
            (
                "Which statistical measure represents the average of a set of numbers?",
                ["Median", "Mode", "Mean", "Range"],
                3,
            ),
            (
                "In data analysis, what does 'EDA' stand for?",
                [
                    "Exploratory Data Analysis",
                    "Essential Data Algorithm",
                    "External Data Analytics",
                    "Electronic Data Array",
                ],
                1,
            ),
        ]
        for prompt, options, correct in questions_data:
            da_quiz.add_question(Question(prompt, options, correct))
        quizzes["Data Analysis Basics"] = da_quiz
        save_data(quizzes)

    return quizzes


def save_data(quizzes):
    data = {title: quiz.to_dict() for title, quiz in quizzes.items()}
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


# --- INITIALIZE SESSION STATE ---
if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

if "student_logged_in" not in st.session_state:
    st.session_state.student_logged_in = False
    st.session_state.student_user = ""


# --- STREAMLIT UI APP ---
st.set_page_config(page_title="Quiz Dashboard", page_icon="📝", layout="wide")

quizzes = load_data()

st.sidebar.title("📌 Navigation")
app_mode = st.sidebar.radio("Select Portal", ["Student Portal", "Admin Portal"])

# Sidebar Logout Actions
if app_mode == "Admin Portal" and st.session_state.admin_logged_in:
    st.sidebar.divider()
    if st.sidebar.button("Log Out Admin"):
        st.session_state.admin_logged_in = False
        st.rerun()

elif app_mode == "Student Portal" and st.session_state.student_logged_in:
    st.sidebar.divider()
    st.sidebar.write(f"Logged in as: **{st.session_state.student_user}**")
    if st.sidebar.button("Log Out Student"):
        st.session_state.student_logged_in = False
        st.session_state.student_user = ""
        st.rerun()


# --- STUDENT PORTAL ---
if app_mode == "Student Portal":
    st.header("🎓 Student Portal")

    # STUDENT LOGIN SCREEN
    if not st.session_state.student_logged_in:
        st.subheader("🔑 Student Login")
        with st.form("student_login_form"):
            stu_username = st.text_input("Username")
            stu_password = st.text_input("Password", type="password")
            stu_login_btn = st.form_submit_button("Login")

            if stu_login_btn:
                if (
                    stu_username in STUDENT_USERS
                    and STUDENT_USERS[stu_username] == stu_password
                ):
                    st.session_state.student_logged_in = True
                    st.session_state.student_user = stu_username
                    st.success(f"Welcome, {stu_username}!")
                    st.rerun()
                else:
                    st.error("Invalid student username or password.")

    # STUDENT DASHBOARD (LOGGED IN)
    else:
        if not quizzes:
            st.info("No quizzes available. Ask an administrator to create one!")
        else:
            quiz_titles = list(quizzes.keys())
            selected_quiz_title = st.selectbox(
                "Select a Quiz to Take:", quiz_titles
            )

            quiz = quizzes[selected_quiz_title]

            if not quiz.questions:
                st.warning("This quiz has no questions yet.")
            else:
                st.subheader(f"Quiz: {quiz.title}")
                st.divider()

                with st.form(key="take_quiz_form"):
                    user_answers = {}
                    for idx, q in enumerate(quiz.questions):
                        st.write(f"**Question {idx + 1}:** {q.prompt}")
                        choice = st.radio(
                            "Select your answer:",
                            q.options,
                            key=f"q_{idx}",
                            index=None,
                        )
                        user_answers[idx] = choice
                        st.divider()

                    submit_button = st.form_submit_button(
                        label="Submit Quiz", type="primary"
                    )

                if submit_button:
                    if any(ans is None for ans in user_answers.values()):
                        st.error(
                            "Please answer all questions before submitting!"
                        )
                    else:
                        score = 0
                        for idx, q in enumerate(quiz.questions):
                            selected_option_idx = (
                                q.options.index(user_answers[idx]) + 1
                            )
                            if selected_option_idx == q.correct_option:
                                score += 1

                        total = len(quiz.questions)
                        percentage = (score / total) * 100

                        st.balloons()
                        st.success(
                            f"**Quiz Finished!** {st.session_state.student_user}, your score is **{score}/{total}** ({percentage:.1f}%)"
                        )


# --- ADMIN PORTAL ---
elif app_mode == "Admin Portal":
    st.header("⚙️ Admin Portal")

    # ADMIN LOGIN SCREEN
    if not st.session_state.admin_logged_in:
        st.subheader("🔒 Admin Login")
        with st.form("admin_login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            login_btn = st.form_submit_button("Login")

            if login_btn:
                if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
                    st.session_state.admin_logged_in = True
                    st.success("Logged in successfully!")
                    st.rerun()
                else:
                    st.error("Invalid username or password.")
    else:
        # LOGGED-IN ADMIN CONTROLS
        tab1, tab2 = st.tabs(["Create Quiz", "Add Question"])

        # Tab 1: Create Quiz
        with tab1:
            st.subheader("Create a New Quiz")
            new_quiz_title = st.text_input("Enter Quiz Title:")
            if st.button("Create Quiz"):
                if not new_quiz_title.strip():
                    st.error("Quiz title cannot be empty.")
                elif new_quiz_title in quizzes:
                    st.warning("A quiz with this title already exists.")
                else:
                    quizzes[new_quiz_title] = Quiz(new_quiz_title)
                    save_data(quizzes)
                    st.success(f"Quiz '{new_quiz_title}' created successfully!")
                    st.rerun()

        # Tab 2: Add Question
        with tab2:
            st.subheader("Add Question to Existing Quiz")
            if not quizzes:
                st.info("No quizzes available. Create one first!")
            else:
                selected_quiz = st.selectbox(
                    "Select Quiz:", list(quizzes.keys())
                )
                prompt = st.text_input("Enter Question Prompt:")

                col1, col2 = st.columns(2)
                with col1:
                    opt1 = st.text_input("Option 1:")
                    opt2 = st.text_input("Option 2:")
                with col2:
                    opt3 = st.text_input("Option 3:")
                    opt4 = st.text_input("Option 4:")

                correct = st.selectbox(
                    "Select Correct Option:",
                    [1, 2, 3, 4],
                    format_func=lambda x: f"Option {x}",
                )

                if st.button("Add Question"):
                    options = [
                        opt1.strip(),
                        opt2.strip(),
                        opt3.strip(),
                        opt4.strip(),
                    ]
                    if not prompt.strip() or any(not o for o in options):
                        st.error("Please fill in all options and the prompt.")
                    else:
                        q = Question(prompt, options, correct)
                        quizzes[selected_quiz].add_question(q)
                        save_data(quizzes)
                        st.success("Question added successfully!")
                        st.rerun()
