from dotenv import load_dotenv
import streamlit as st
from langchain_google_genai import ChatGoogleGenerativeAI
import pdfplumber

load_dotenv()

def extract_text_from_pdf(uploaded_file):
    text = ""

    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

    return text.strip()

st.set_page_config(page_title="Blood Work Analyzer", layout="wide")

llm = ChatGoogleGenerativeAI(model="gemma-4-31b-it")

st.markdown("""
<style>
.scroll-box {
    height: 230px;
    overflow-y: auto;
    padding: 12px 16px;

    border: 1px solid rgba(128,128,128,0.45);
    border-radius: 10px;

    background-color: transparent;

    font-size: 0.9rem;
    line-height: 1.6;
}
.scroll-box p,
.scroll-box li,
.scroll-box div {
    color: var(--text-color);
}

.section-label {
    font-size: 1.1rem;
    font-weight: 600;
    margin-bottom: 6px;
}
</style>
""", unsafe_allow_html=True)

st.title("Blood Work Analyzer")

left_col, right_col = st.columns([1, 1])

with left_col:
    st.subheader("Blood Work Report")

    uploaded_file = st.file_uploader(
        "Upload Blood Report (.pdf or .txt)",
        type=["pdf", "txt"]
    )
    
    blood_report = st.text_area(
        label="Paste your report below",
        height=340,
        placeholder="Paste your blood work report here...",
        label_visibility="collapsed"
    )
    analyze_clicked = st.button("Analyze", type="primary", use_container_width=True)

with right_col:
    stats_box = st.empty()

    st.subheader("Health Summary")
    health_box = st.empty()
    health_box.markdown('<div class="scroll-box"></div>', unsafe_allow_html=True)

    st.subheader("Suggested Diet Plan")
    diet_box = st.empty()
    diet_box.markdown('<div class="scroll-box"></div>', unsafe_allow_html=True)

if analyze_clicked:

    report_text = ""

    # Uploaded file
    if uploaded_file is not None:

        if uploaded_file.type == "application/pdf":
            report_text = extract_text_from_pdf(uploaded_file)

        else:
            report_text = uploaded_file.read().decode("utf-8")

        if report_text:
            with st.expander("Extracted Report Preview"):
                st.text(report_text)

    # Manual paste
    elif blood_report.strip():
        report_text = blood_report

    if not report_text:
        with left_col:
            st.warning("Please upload a PDF or paste a blood work report before analyzing.")
    else:
        with st.spinner("Analyzing your blood work..."):

            # Stage 1: Extract and flag abnormal values
            extraction_prompt = f"""
You are a medical data extraction assistant. From the blood report below,
If the provided document is NOT a blood test report or does not contain laboratory test values with reference ranges, respond with exactly:

INVALID_REPORT

Do not generate any health summary or analysis.
Ohterwise, extract ALL test values and classify each one as HIGH, LOW, or NORMAL
based on the reference ranges provided in the report.

Format your response as:
- Test Name: value | Status: HIGH/LOW/NORMAL | Reference: range

Blood Report:
{report_text}
"""
            try:
                extraction_response = llm.invoke(extraction_prompt)
                extracted_values = extraction_response.text
                if extracted_values.strip() == "INVALID_REPORT":
                    st.error(
                    "The uploaded document is not a valid blood test report. Please upload a laboratory blood report or paste blood test results."
                    )
                    full_response = None
                else:
                    high_count = extracted_values.count("Status: HIGH")
                    low_count = extracted_values.count("Status: LOW")
                    normal_count = extracted_values.count("Status: NORMAL")
                    total_tests = high_count + low_count + normal_count

                    # Stage 2: Health summary and Indian diet plan
                    diet_prompt = f"""
You are a clinical nutritionist specializing in Indian dietary habits.

Based on the blood work analysis below, provide two clearly separated sections:

SECTION 1 - HEALTH SUMMARY:
Write 4-5 lines explaining the patient's condition in simple, non-technical language.

SECTION 2 - INDIAN DIET PLAN:
List foods to eat more of and foods to avoid, using commonly available Indian foods
like dal, sabzi, roti, rice, etc. Keep it practical and concise.

Blood Work Analysis:
{extracted_values}
"""
                    diet_response = llm.invoke(diet_prompt)
                    full_response = diet_response.text

            except Exception:
                st.error(
                    "Unable to analyze the report. The AI service may be temporarily unavailable or the API quota has been exceeded."
                )
                st.stop()

            if full_response is not None:
            # Split response into two sections
                if "SECTION 2" in full_response:
                    parts = full_response.split("SECTION 2")
                    health_summary = parts[0].replace("SECTION 1 - HEALTH SUMMARY:", "").replace("SECTION 1", "").strip()
                    diet_plan = ("SECTION 2" + parts[1]).replace("SECTION 2 - INDIAN DIET PLAN:", "").replace("SECTION 2", "").strip()
                else:
                    health_summary = full_response
                    diet_plan = ""

                # Render into fixed-height scrollable boxes
                stats_box.markdown(
                    f"""
                    ### Report Statistics

                    - **Tests Detected:** {total_tests}
                    - 🟢 **Normal:** {normal_count}
                    - 🟡 **High:** {high_count}
                    - 🔴 **Low:** {low_count}
                    """
                )
                health_box.markdown(
                    f'<div class="scroll-box">{health_summary}</div>',
                    unsafe_allow_html=True
                )
                diet_box.markdown(
                    f'<div class="scroll-box">{diet_plan if diet_plan else full_response}</div>',
                    unsafe_allow_html=True
                )

                download_content = f"""
                AI BLOOD REPORT ANALYSIS

                ========================
                HEALTH SUMMARY
                ========================

                {health_summary}

                ========================
                DIET PLAN
                ========================

                {diet_plan if diet_plan else full_response}

                ========================
                EXTRACTED BLOOD VALUES
                ========================

                {extracted_values}
                """

                st.download_button(
                    label="📄 Download Analysis Report",
                    data=download_content,
                    file_name="blood_report_analysis.txt",
                    mime="text/plain",
                    use_container_width=True
                )
