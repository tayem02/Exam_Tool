import streamlit as st
import pandas as pd
import numpy as np
import fitz as fitz
import openai
import time

st.set_page_config(page_title="PDF Quiz Generator", layout="wide")

# Custom CSS for layout and styling
st.markdown("""
<style>
 .card {
 background-color: #000000;
 border-radius: 10px;
 padding: 20px;
 box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
 margin: 10px;
 border: 2px solid #ddd; /* Border around the card */
 text-align: center;
 height: auto; /* Auto height to fit content */
 overflow: hidden; /* Prevent overflow of text */
 }

 .card h4 {
 color: #333;
 font-size: 18px;
 margin-bottom: 5px;
 margin-top: 0;
 }

 .metric-value {
 font-size: 30px; /* Font size for the value */
 font-weight: bold;
 color: #4CAF50; /* Color for the value */
 margin-top: 0;
 }

 .correct-answer {
 color: green;
 font-weight: bold;
 }

 .wrong-answer {
 color: red;
 font-weight: bold;
 }
</style>
""", unsafe_allow_html=True)

# Function to extract text from PDF
from PyPDF2 import PdfReader

def extract_text_from_pdf(file):
    text = ""
    reader = PdfReader(file)
    for page in reader.pages:
        text += page.extract_text()
    return text

# Function to generate questions using OpenAI API
def generate_questions(text, num_questions, difficulty, model, api_key):
    openai.api_key = api_key

    messages = [
        {"role": "system", "content": "You are a helpful assistant that creates multiple-choice questions."},
        {"role": "user", "content": f"Extract {num_questions} multiple-choice questions that cover all the topics in the text with {difficulty} difficulty level. Provide each question with four options, and mark the correct answer clearly:\n\n{text}"}
    ]

    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            max_tokens=2000
        )
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        st.error(f"Error generating questions: {e}")
        return ""


# Function to parse generated questions into a structured format
def parse_questions(raw_questions):
    questions = []
    for question in raw_questions.split("\n\n"):
        if question.strip():
            try:
                parts = question.split("\n")
                q = parts[0]  # The question text
                options = parts[1:]  # The list of options
                correct = options[0]  # Assume the first option is correct (adjust if API marks it differently)
                questions.append({"question": q, "options": options, "correct": correct})
            except IndexError:
                st.warning(f"Skipping malformed question: {question}")
    return questions


# Streamlit App
def main():
    st.title("PDF Quiz Generator and Solver")

    uploaded_file = st.file_uploader("Upload your PDF file", type="pdf")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        num_questions = st.number_input("Number of questions to generate", min_value=1, value=5)
    with col2:
        difficulty = st.selectbox("Select Difficulty Level", ["Easy", "Medium", "Hard"])
    with col3:
        api_key = st.text_input("Enter your OpenAI API Key", type="password")
    with col4:
        model = st.selectbox("Select Model", ["gpt-3.5-turbo"])


    if uploaded_file is not None and st.button("Generate Quiz"):
        with st.spinner("Extracting text and generating questions..."):
            pdf_text = extract_text_from_pdf(uploaded_file)
            raw_questions = generate_questions(pdf_text, num_questions, difficulty, model, api_key)
            questions = parse_questions(raw_questions)

        st.session_state["questions"] = questions
        st.session_state["start_time"] = time.time()
        st.session_state["results_displayed"] = False

    if "questions" in st.session_state:
        st.header("Quiz")
        user_answers = []
        for i, question in enumerate(st.session_state["questions"]):
            st.subheader(f"Q{i + 1}: {question['question']}")
            answer = st.radio(
                label=f"Choose the correct answer for Q{i + 1}",
                options=question["options"],
                key=f"question_{i}"
            )
            user_answers.append({"question": question, "selected": answer})

        if st.button("Submit"):
            with st.spinner("Evaluating your answers..."):
                correct_answers = sum(1 for ans in user_answers if ans["selected"] == ans["question"]["correct"])
                total_time = time.time() - st.session_state["start_time"]

                st.session_state["correct_answers"] = correct_answers
                st.session_state["total_time"] = total_time
                st.session_state["results_displayed"] = True

    if "results_displayed" in st.session_state and st.session_state["results_displayed"]:
        st.success("Overview Metrics")
        metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)

        with metrics_col1:
            st.markdown(
                f"<h4 class='card'>Correct Answers <br> <br> <span style='color: green;'>"
                f"{st.session_state['correct_answers']}/{num_questions}</span></h4>",
                unsafe_allow_html=True
            )

        with metrics_col2:
            st.markdown(
                f"<h4 class='card'>Percentage <br> <br> <span style='color: green;'>"
                f"{(st.session_state['correct_answers'] / num_questions) * 100:.2f}%</span></h4>",
                unsafe_allow_html=True
            )

        with metrics_col3:
            st.markdown(
                f"<h4 class='card'>Total Time <br> <br> <span style='color: green;'>"
                f"{st.session_state['total_time']:.2f} seconds</span></h4>",
                unsafe_allow_html=True
            )

        with metrics_col4:
            st.markdown(
                f"<h4 class='card'>Average Time per Question <br> <br> <span style='color: green;'>"
                f"{st.session_state['total_time'] / num_questions:.2f} seconds</span></h4>",
                unsafe_allow_html=True
            )

        if st.button("Show Correct Answers"):
            st.header("Correct Answers")
            for i, ans in enumerate(user_answers):
                question = ans["question"]
                selected = ans["selected"]
                correct = question["correct"]
                color = "green" if selected == correct else "red"
                st.markdown(
                    f"<p><strong>Q{i + 1}: {question['question']}</strong><br>"
                    f"Your Answer: <span style='color: {color};'>{selected}</span><br>"
                    f"Correct Answer: <span style='color: green;'>{correct}</span></p>",
                    unsafe_allow_html=True
                )

if __name__ == "__main__":
    main()
