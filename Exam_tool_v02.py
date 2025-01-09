import streamlit as st
import pandas as pd
import numpy as np
import fitz  # PyMuPDF
import openai
import time
import re

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
 border: 2px solid #ddd;
 text-align: center;
 height: auto;
 overflow: hidden;
 }

 .card h4 {
 color: #333;
 font-size: 18px;
 margin-bottom: 5px;
 margin-top: 0;
 }

 .metric-value {
 font-size: 30px;
 font-weight: bold;
 color: #4CAF50;
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
def extract_text_from_pdf(file):
    text = ""
    pdf_document = fitz.open(stream=file.read(), filetype="pdf")
    for page in pdf_document:
        text += page.get_text()
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
            max_tokens=10000
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
                q = parts[0].strip()  # Question text
                options = []
                correct_answer = None

                # Extract options and clean them
                for option in parts[1:]:
                    match = re.match(r"^[A-D]\)", option.strip())  # Match options A), B), C), D)
                    if match:
                        options.append(option.strip())

                # Extract correct answer (e.g., "Correct Answer: C")
                correct_match = re.search(r"Correct Answer: ([A-D])", " ".join(parts))
                if correct_match:
                    correct_letter = correct_match.group(1)
                    correct_answer = next(
                        opt for opt in options if opt.startswith(f"{correct_letter})")
                    )

                # Validate the extracted question
                if len(options) == 4 and correct_answer:
                    questions.append({
                        "question": q,
                        "options": options,
                        "correct": correct_answer
                    })
                else:
                    st.warning(f"Skipping invalid question: {q}")
                    st.write(f"Options: {options}, Correct Answer: {correct_answer}")

            except Exception as e:
                st.warning(f"Error parsing question: {question}")
                st.write(f"Error Details: {e}")

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
        model = st.selectbox("Select Model", ["gpt-3.5-turbo", "gpt-4"])

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
            st.markdown(f"<h4 class='card'>Correct Answers<br><br><span class='metric-value'>{st.session_state['correct_answers']}/{num_questions}</span></h4>", unsafe_allow_html=True)
        with metrics_col2:
            st.markdown(f"<h4 class='card'>Percentage<br><br><span class='metric-value'>{(st.session_state['correct_answers'] / num_questions) * 100:.2f}%</span></h4>", unsafe_allow_html=True)
        with metrics_col3:
            st.markdown(f"<h4 class='card'>Total Time<br><br><span class='metric-value'>{st.session_state['total_time']:.2f} seconds</span></h4>", unsafe_allow_html=True)
        with metrics_col4:
            st.markdown(f"<h4 class='card'>Avg. Time per Question<br><br><span class='metric-value'>{st.session_state['total_time'] / num_questions:.2f} seconds</span></h4>", unsafe_allow_html=True)

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
