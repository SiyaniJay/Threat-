# dashboard.py

import streamlit as st
from main import (
    parse_eml,
    extract_email_parts,
    get_named_entities,
    get_relevance_score,
    summarize_email,
    classify_urgency,
    generate_report
)

st.set_page_config(page_title="Email Threat Analyzer", layout="wide")
st.title("Threat Analyser")

# --- Drag & Drop Upload ---
st.markdown("""
<style>
div.stFileUploader {
    border: 2px dashed #999;
    padding: 20px;
    border-radius: 10px;
    background-color: #f8f8f8;
}
</style>
""", unsafe_allow_html=True)

uploaded_file = st.file_uploader("🔻 Drag & drop a .eml file here or click to browse", type="eml")

if uploaded_file:
    msg = parse_eml(uploaded_file)
    result = extract_email_parts(msg)

    st.subheader("📄 Email Info")
    st.write(f"**Subject:** {result['subject']}")
    st.write(f"**From:** {result['from']}")
    st.text_area("📬 Body", result['body_text'], height=200)

    entities = get_named_entities(result['body_text'])
    score = get_relevance_score(result['body_text'])
    summary = summarize_email(result['body_text'])
    urgency = classify_urgency(
        result['body_text'],
        ["university", "callista", "ascender", "studylink", "financeone", "calumo", "student"],
        score
    )

    st.subheader("🧠 Analysis")
    st.write(f"**Named Entities:** {', '.join(entities) if entities else 'None found'}")
    st.write(f"**Urgency Level:** 🔺 {urgency}")
    st.write(f"**Similarity Score:** {round(score, 2)}")
    st.text_area("📝 Summary", summary, height=100)

    result.update({
        "entities": entities,
        "summary": summary,
        "similarity": round(score, 2),
        "urgency": urgency
    })