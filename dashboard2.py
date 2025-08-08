import streamlit as st
import os
from pathlib import Path
from datetime import datetime
import time
import html
from main_copy import (
    parse_eml, extract_email_parts, summarize_email, get_named_entities, 
    classify_urgency, get_relevance_score, generate_report, 
    ask_sec_chatbot
)
import streamlit.components.v1 as components

# ── Config ─────────────────────────────────────────────────────────────────────
EMAIL_DIR = Path("/Users/jaysiyani/Desktop/Siyani2.0/onedrive copy")
REPORT_DIR = Path("reports")
REPORT_DIR.mkdir(exist_ok=True)

# ── Helper Functions & Classes ────────────────────────────────────────────────
class EMLAttachmentAnalyzer:
    @staticmethod
    def has_attachments(msg):
        try:
            return EMLAttachmentAnalyzer.check_message_for_attachments(msg)
        except Exception:
            return False
    
    @staticmethod
    def check_message_for_attachments(msg):
        if msg.is_multipart():
            for part in msg.walk():
                if part.get("Content-Disposition") and part.get("Content-Disposition").startswith("attachment"): return True
                if part.get_filename(): return True
        return False
    
    @staticmethod
    def get_attachment_info(msg):
        attachments = []
        try:
            if msg.is_multipart():
                for part in msg.walk():
                    is_attachment = False
                    if part.get("Content-Disposition") and "attachment" in part.get("Content-Disposition").lower(): is_attachment = True
                    elif part.get_filename(): is_attachment = True
                    
                    if is_attachment:
                        payload = part.get_payload(decode=True)
                        attachments.append({
                            'filename': part.get_filename() or f'unnamed_{len(attachments) + 1}',
                            'content_type': part.get_content_type() or 'unknown',
                            'size': len(payload) if payload else 0
                        })
        except Exception: pass
        return attachments

@st.cache_data(ttl=60)
def get_emails():
    data = []
    if not EMAIL_DIR.exists(): return []
    for f in sorted(EMAIL_DIR.glob("*.eml"), key=os.path.getctime, reverse=True):
        try:
            with open(f, "rb") as file_handle: msg = parse_eml(file_handle)
            parts = extract_email_parts(msg)
            summary = summarize_email(parts['body_text'])
            similarity = get_relevance_score(parts['body_text'])
            urgency = classify_urgency(parts['body_text'], ["university","student","canvas","Cobalt Strike"], similarity)
            entities = get_named_entities(parts['body_text'])
            has_attachments = EMLAttachmentAnalyzer.has_attachments(msg)
            attachments = EMLAttachmentAnalyzer.get_attachment_info(msg) if has_attachments else []
            data.append({
                "path": f, "filename": f.name, "subject": parts['subject'] or "No Subject", "from": parts['from'] or "Unknown Sender",
                "summary": summary, "urgency": urgency, "body": parts['body_text'], "entities": entities, "similarity_score": similarity,
                "has_attachments": has_attachments, "attachments": attachments, "attachment_count": len(attachments),
                "email_date": msg.get('Date', 'Unknown Date'), "email_id": msg.get('Message-ID', str(f)), "file_size": f.stat().st_size,
                "created_date": datetime.fromtimestamp(f.stat().st_ctime)
            })
        except Exception as e:
            print(f"Failed to process {f.name}: {e}")
            continue
    return data

def format_file_size(size_bytes):
    if size_bytes == 0: return "0 B"
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.1f} {size_names[i]}"

# ── Page Config & CSS ──────────────────────────────────────────────────────────
st.set_page_config("University Threat Triage", layout="wide", page_icon="⚠️", initial_sidebar_state="auto")

GLOBAL_STYLE = """
<style>
    :root {
        --critical-color: #ef4444;
        --medium-color: #f59e0b;
        --low-color: #eab308;
        --primary-bg: #1e293b;
        --secondary-bg: #334155;
        --border-color: #475569;
        --text-color: #cbd5e1;
        --subtle-text-color: #94a3b8;
        --accent-color: #3b82f6;
    }
    .stApp { background-color: #0f1419; }
    .kpi-card { background: var(--primary-bg); border: 1px solid var(--border-color); border-radius: 12px; padding: 1rem; }
    .kpi-number { font-size: 2rem; font-weight: 700; margin: 0; }
    .kpi-label { margin: 0; font-weight: 600; color: var(--text-color); }
    .kpi-sublabel { margin: 0.25rem 0 0 0; font-size: 0.8rem; color: var(--subtle-text-color); }
    body { background-color: #0f1419; color: #e2e8f0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    .threat-card { background: var(--primary-bg); border: 1px solid var(--border-color); border-left-width: 4px; border-radius: 8px; padding: 1rem; margin-bottom: 1rem; }
    .threat-card.critical { border-left-color: var(--critical-color); }
    .threat-card.medium { border-left-color: var(--medium-color); }
    .threat-card.low { border-left-color: var(--low-color); }
    .card-header { display: flex; align-items: center; justify-content: space-between; gap: 1rem; margin-bottom: 0.75rem; }
    .card-title { font-size: 1.1rem; font-weight: 600; }
    .card-title-icon { margin-right: 0.5rem; }
    .priority-badge { font-size: 0.7rem; font-weight: 700; padding: 0.25rem 0.6rem; border-radius: 1rem; }
    .priority-badge.critical { background: var(--critical-color); color: white; }
    .priority-badge.medium { background: var(--medium-color); color: white; }
    .priority-badge.low { background: var(--low-color); color: black; }
    .card-description { font-size: 0.9rem; color: var(--text-color); margin-bottom: 1rem; }
    .card-meta-row { display: flex; align-items: center; justify-content: space-between; gap: 1rem; margin-bottom: 1rem; font-size: 0.85rem; color: var(--subtle-text-color); }
    .meta-item { display: flex; align-items: center; gap: 0.5rem; }
    .risk-level { display: flex; align-items: center; gap: 0.5rem; }
    .risk-dots { display: flex; gap: 2px; }
    .dot { height: 10px; width: 10px; background-color: #4b5563; border-radius: 50%; }
    .dot.filled.critical { background-color: var(--critical-color); }
    .dot.filled.medium { background-color: var(--medium-color); }
    .dot.filled.low { background-color: var(--low-color); }
    .risk-score { font-weight: 600; color: white; }
    .triggers-container { margin-top: 1rem; }
    .triggers-label { font-size: 0.85rem; color: var(--subtle-text-color); margin-bottom: 0.5rem; }
    .trigger-tags { display: flex; flex-wrap: wrap; gap: 0.5rem; }
    .trigger-tag { background: var(--secondary-bg); border: 1px solid var(--border-color); padding: 0.2rem 0.6rem; font-size: 0.75rem; border-radius: 1rem; }
    .detail-card { background: var(--primary-bg); border: 1px solid var(--border-color); border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem; }
    .detail-card h3 { margin-top: 0; border-bottom: 1px solid var(--border-color); padding-bottom: 0.75rem; margin-bottom: 1rem; }
    .detail-list { list-style: none; padding: 0; }
    .detail-list li { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.5rem; }
</style>
"""
st.markdown(GLOBAL_STYLE, unsafe_allow_html=True)

# ── App Logic & State Initialization ──────────────────────────────────────────
if 'current_page' not in st.session_state: st.session_state.current_page = 'main'
if 'selected_email' not in st.session_state: st.session_state.selected_email = None
if 'filter_priority' not in st.session_state: st.session_state.filter_priority = 'ALL'
if 'sec_chat_messages' not in st.session_state: st.session_state.sec_chat_messages = []
emails = get_emails()

# =================================================================================
# SIDEBAR CHATBOT
# =================================================================================
with st.sidebar:
    st.title("🤖 FoundationSec AI")
    st.write("Your AI assistant for cybersecurity analysis.")
    st.markdown("---")
    
    # Message History
    for message in st.session_state.sec_chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # User Input
    if prompt := st.chat_input("Ask a security question..."):
        st.session_state.sec_chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
                response = ask_sec_chatbot(prompt)
                st.markdown(response)
        st.session_state.sec_chat_messages.append({"role": "assistant", "content": response})

# =================================================================================
# MAIN DASHBOARD PAGE
# =================================================================================
if st.session_state.current_page == 'main':
    
    st.markdown("### University Threat Triage Dashboard")
    
    total_threats, critical_count, medium_count, low_count = len(emails), len([e for e in emails if e['urgency'] == 'Red']), len([e for e in emails if e['urgency'] == 'Orange']), len([e for e in emails if e['urgency'] == 'Yellow'])
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1: st.markdown(f'<div class="kpi-card"><p class="kpi-number">{total_threats}</p><p class="kpi-label">Total Threats</p></div>', unsafe_allow_html=True)
    with kpi2: st.markdown(f'<div class="kpi-card"><p class="kpi-number" style="color:var(--critical-color);">{critical_count}</p><p class="kpi-label">Critical (RED)</p><p class="kpi-sublabel">Immediate Action Required</p></div>', unsafe_allow_html=True)
    with kpi3: st.markdown(f'<div class="kpi-card"><p class="kpi-number" style="color:var(--medium-color);">{medium_count}</p><p class="kpi-label">Medium (ORANGE)</p><p class="kpi-sublabel">Review Soon</p></div>', unsafe_allow_html=True)
    with kpi4: st.markdown(f'<div class="kpi-card"><p class="kpi-number" style="color:var(--low-color);">{low_count}</p><p class="kpi-label">Low (YELLOW)</p><p class="kpi-sublabel">Monitor</p></div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    with st.container():
        f_col1, f_col2, f_col3 = st.columns([2, 2, 1])
        with f_col1:
            st.markdown("##### ▽ Filter by Priority:")
            b_col1, b_col2, b_col3, b_col4 = st.columns(4)
            if b_col1.button("ALL", use_container_width=True): st.session_state.filter_priority = 'ALL'
            if b_col2.button("RED", use_container_width=True): st.session_state.filter_priority = 'Red'
            if b_col3.button("ORANGE", use_container_width=True): st.session_state.filter_priority = 'Orange'
            if b_col4.button("YELLOW", use_container_width=True): st.session_state.filter_priority = 'Yellow'
        with f_col2:
            st.markdown("##### Ｑ Search threats...")
            search_term = st.text_input("Search", key="search", placeholder="Search by subject, sender, or content...", label_visibility="collapsed")
    
    filtered_emails = [e for e in emails if (st.session_state.filter_priority == 'ALL' or e['urgency'] == st.session_state.filter_priority) and (not search_term or any(search_term.lower() in str(val).lower() for val in (e['subject'], e['from'], e['summary'])))]
    
    st.markdown("---")
    st.markdown(f"**Displaying {len(filtered_emails)} of {len(emails)} threats...**")
    
    for i, email_data in enumerate(filtered_emails):
        urgency_class = {"Red": "critical", "Orange": "medium", "Yellow": "low"}.get(email_data['urgency'], "low")
        priority_label = {"Red": "CRITICAL", "Orange": "MEDIUM", "Yellow": "LOW"}.get(email_data['urgency'], "UNKNOWN")
        risk_score = min(10, (email_data['similarity_score'] * 10) + (3 if urgency_class == 'critical' else 1 if urgency_class == 'medium' else 0))
        risk_dots_html = "".join([f'<span class="dot filled {urgency_class}"></span>' if j < int(risk_score) else '<span class="dot"></span>' for j in range(10)])
        trigger_tags_html = "".join(f'<div class="trigger-tag">{html.escape(entity)}</div>' for entity in email_data['entities'][:5])
        
        card_html = f"""
            <div class="threat-card {urgency_class}">
                <div class="card-header"><div class="card-title"><span class="card-title-icon">⚠️</span>{html.escape(email_data['subject'])}</div><div class="priority-badge {urgency_class}">{priority_label}</div></div>
                <div class="card-description">{html.escape(email_data['summary'])}</div>
                <div class="card-meta-row">
                    <div class="meta-item"><span>📅</span><span>{html.escape(email_data['created_date'].strftime('%d/%m/%Y'))}</span><span style="margin-left: 1rem;">🏢</span><span>{html.escape(email_data['from'])}</span></div>
                    <div class="risk-level"><span>Risk Level:</span><div class="risk-dots">{risk_dots_html}</div><div class="risk-score">{int(risk_score)}/10</div></div>
                </div>
                <div class="triggers-container"><div class="triggers-label">University Triggers Detected:</div><div class="trigger-tags">{trigger_tags_html}</div></div>
            </div>"""
        
        components.html(f"<html><head>{GLOBAL_STYLE}</head><body>{card_html}</body></html>", height=280)

        if st.button("View Full Report", key=f"details_{i}", use_container_width=True):
            st.session_state.selected_email = email_data
            st.session_state.current_page = 'detail'
            st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)

# =================================================================================
# DETAIL PAGE
# =================================================================================
elif st.session_state.current_page == 'detail' and st.session_state.selected_email:
    email_data = st.session_state.selected_email
    urgency_class = {"Red": "critical", "Orange": "medium", "Yellow": "low"}.get(email_data['urgency'], "low")
    
    if st.button("← Back to Dashboard"):
        st.session_state.current_page = 'main'
        st.rerun()
        
    st.markdown(f'<h2><span class="priority-badge {urgency_class}">{email_data["urgency"].upper()} PRIORITY</span> > {html.escape(email_data["subject"])}</h2>', unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])
    with col1:
        risk_score = min(10, (email_data['similarity_score'] * 10) + (3 if urgency_class == 'critical' else 1 if urgency_class == 'medium' else 0))
        overview_html = f"""
        <div class="detail-card">
            <h3>Threat Overview</h3>
            <div style="display: flex; justify-content: space-around; text-align: center;">
                <div><p style="font-size: 0.8rem; color: var(--subtle-text-color); margin: 0;">Date Reported</p><p>{html.escape(email_data['created_date'].strftime('%d/%m/%Y'))}</p></div>
                <div><p style="font-size: 0.8rem; color: var(--subtle-text-color); margin: 0;">Source</p><p>{html.escape(email_data['from'])}</p></div>
                <div><p style="font-size: 0.8rem; color: var(--subtle-text-color); margin: 0;">Risk Level</p><p>{int(risk_score)}/10</p></div>
                <div><p style="font-size: 0.8rem; color: var(--subtle-text-color); margin: 0;">Priority</p><p>{html.escape(email_data['urgency'].upper())}</p></div>
            </div>
        </div>"""
        st.markdown(overview_html, unsafe_allow_html=True)

        full_report_body = html.escape(email_data['body']).replace('\n', '<br>')
        report_html = f"""
        <div class="detail-card">
            <h3>Full Report</h3>
            <h4>CRITICAL SECURITY ADVISORY</h4>
            <p>{full_report_body}</p>
        </div>"""
        st.markdown(report_html, unsafe_allow_html=True)

        # --- ATTACHMENTS SECTION RESTORED ---
        if email_data['has_attachments']:
            attachment_items = ""
            for attachment in email_data['attachments']:
                attachment_items += f"<li>📄 {html.escape(attachment['filename'])} ({html.escape(format_file_size(attachment['size']))})</li>"
            
            attachments_html = f"""
            <div class="detail-card">
                <h3>Attachments</h3>
                <ul class="detail-list">{attachment_items}</ul>
            </div>
            """
            st.markdown(attachments_html, unsafe_allow_html=True)

    with col2:
        summary_html = f"""
        <div class="detail-card">
            <h3>Quick Summary</h3>
            <p>{html.escape(email_data['summary'])}</p>
        </div>"""
        st.markdown(summary_html, unsafe_allow_html=True)
        
        triggers_list = "".join(f'<li>🎯 {html.escape(e)}</li>' for e in email_data['entities'])
        st.markdown(f'<div class="detail-card"><h3>University Triggers Detected</h3><ul class="detail-list">{triggers_list}</ul></div>', unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class="detail-card">
            <h3>Affected Systems</h3>
            <ul class="detail-list">
                <li>⚠️ Canvas LMS</li>
                <li>⚠️ Student Information System</li>
                <li>⚠️ Grade Management</li>
            </ul>
        </div>""", unsafe_allow_html=True)

        st.markdown(f"""
        <div class="detail-card">
            <h3>Recommended Actions</h3>
            <ul class="detail-list">
                <li>✅ Immediately update Canvas</li>
                <li>✅ Conduct emergency security audit</li>
                <li>✅ Review and reset admin credentials</li>
                <li>✅ Implement additional monitoring</li>
            </ul>
        </div>""", unsafe_allow_html=True)
