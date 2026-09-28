"""
Floating Chatbot UI and Slide-Out Panel for SynoFin Audit Assistant.
"""

import streamlit as st
from src.assistant.service import AuditAssistant, AuditContext
from src.assistant.knowledge import RuleKnowledgeBase


def render_floating_audit_assistant(context: Optional[AuditContext] = None):
    """
    Renders a fixed bottom-right floating trigger button and a right-side slide-out
    drawer panel. Always visible from application startup.
    """
    # Ensure session state variables
    if "assistant_open" not in st.session_state:
        st.session_state["assistant_open"] = False

    if "assistant_messages" not in st.session_state:
        st.session_state["assistant_messages"] = [
            {
                "role": "assistant",
                "content": "Hello! I am the **SynoFin Migration Audit Assistant**. You can ask me about validation rules, audit findings, affected loans, or remediation guidance."
            }
        ]

    # Floating trigger button CSS in bottom right
    st.markdown(
        """
        <style>
        .syno-floating-btn-container {
            position: fixed;
            bottom: 24px;
            right: 28px;
            z-index: 999999;
        }
        .syno-panel-card {
            background-color: #FFFFFF;
            border: 1px solid #CBD5E1;
            border-radius: 8px;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
            padding: 16px;
            margin-bottom: 20px;
        }
        .syno-panel-header {
            background: linear-gradient(135deg, #0B1B2B 0%, #102A43 100%);
            color: white;
            padding: 12px 16px;
            border-radius: 6px;
            margin-bottom: 12px;
        }
        .syno-panel-title {
            font-size: 16px;
            font-weight: 700;
            margin: 0;
            color: #FFFFFF;
        }
        .syno-panel-sub {
            font-size: 12px;
            color: #9FB3C8;
            margin: 2px 0 0 0;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # 1. Floating Toggle Button (Always visible at bottom right of sidebar / main layout)
    with st.sidebar:
        st.markdown("---")
        st.markdown("### SynoFin Assistant")
        if not st.session_state["assistant_open"]:
            if st.button("Open Audit Assistant", key="open_chat_btn", type="primary", use_container_width=True):
                st.session_state["assistant_open"] = True
                st.rerun()
        else:
            if st.button("Close Assistant Panel", key="close_chat_btn", use_container_width=True):
                st.session_state["assistant_open"] = False
                st.rerun()

    # 2. Slide-out Panel on the Right Side
    if st.session_state["assistant_open"]:
        active_context = context or AuditContext()
        assistant = AuditAssistant(active_context)

        st.markdown("---")
        with st.container():
            st.markdown(
                """
                <div class="syno-panel-header">
                    <div class="syno-panel-title">SynoFin Audit Assistant</div>
                    <div class="syno-panel-sub">Ask about validation rules, audit findings or migration data.</div>
                </div>
                """,
                unsafe_allow_html=True
            )

            # Rule Explorer tab & Chat tab
            tab_chat, tab_explorer = st.tabs(["Conversation", "Explore Validation Rules"])

            with tab_chat:
                # Quick Action Buttons
                st.caption("Quick Inquiries:")
                qc1, qc2, qc3, qc4, qc5 = st.columns(5)
                quick_clicked = None
                if qc1.button("Audit Summary", key="q_sum", use_container_width=True):
                    quick_clicked = "Audit Summary"
                if qc2.button("Explore Rules", key="q_rules", use_container_width=True):
                    quick_clicked = "What rules are applied to Customer?"
                if qc3.button("Explain Errors", key="q_err", use_container_width=True):
                    quick_clicked = "Why are there errors?"
                if qc4.button("Check a Loan", key="q_loan", use_container_width=True):
                    quick_clicked = "How do I check issues for a loan?"
                if qc5.button("How to Fix", key="q_fix", use_container_width=True):
                    quick_clicked = "How do I fix these errors?"

                # Scrollable Chat Container
                chat_box = st.container(height=360)
                with chat_box:
                    for msg in st.session_state["assistant_messages"]:
                        with st.chat_message(msg["role"]):
                            st.markdown(msg["content"])

                # Chat input
                user_msg = st.chat_input("Type any question about SynoFin migration rules, loans, or audit results...")
                prompt_to_send = quick_clicked or user_msg

                if prompt_to_send:
                    st.session_state["assistant_messages"].append({"role": "user", "content": prompt_to_send})
                    resp = assistant.ask(prompt_to_send)
                    st.session_state["assistant_messages"].append({"role": "assistant", "content": resp})
                    st.rerun()

            with tab_explorer:
                st.markdown("##### SynoFin Implemented Rule Catalog")
                all_mods = RuleKnowledgeBase.list_all_modules()
                chosen_mod = st.selectbox("Select Migration Module", options=all_mods, key="explorer_mod_select")

                if chosen_mod:
                    rules = RuleKnowledgeBase.get_module_rules(chosen_mod)
                    req_cols = RuleKnowledgeBase.get_module_required_columns(chosen_mod)

                    st.markdown(f"**Mandatory Fields ({len(req_cols)}):** `{'`, `'.join(req_cols)}`")
                    st.markdown(f"**Implemented Business Rules ({len(rules)}):**")

                    for r in rules:
                        with st.expander(f"{r.rule_id} — {r.field} ({r.severity.value if hasattr(r.severity, 'value') else r.severity})"):
                            st.write(f"**What it checks:** {r.description}")
                            st.write(f"**Field / Column:** `{r.field}`")
                            st.write(f"**Module:** {r.module}")
                            st.write(f"**Expected:** Values in column `{r.field}` must conform to rule requirements.")
                            st.info(f"**Fix Guidance:** Review column `{r.field}` in your source Excel sheet to resolve violations.")
