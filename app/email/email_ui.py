"""
Email Campaigns UI
Streamlit UI for managing mailboxes and sending emails
"""
from __future__ import annotations

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional

from app.email.mailbox_pool import MailboxPool
from app.email.rate_limiter import RateLimiter
from app.email.smtp_pool import SMTPConnectionPool
from app.database.db import get_all_leads, get_connection, get_recent_searches, get_leads_by_search


def render_email_sender_page():
    """Render the Email Campaigns/Sender page"""
    st.markdown('<p class="app-title">📧 Email Campaigns</p>', unsafe_allow_html=True)
    st.markdown('<p class="app-subtitle">Manage mailboxes and send bulk emails to extracted leads</p>', unsafe_allow_html=True)
    
    pool = MailboxPool()
    
    # ── Tabs for Email Features ─────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs(["📬 Mailboxes", "📨 Create Campaign", "📊 Campaign Queue"])
    
    # ── TAB 1: Mailbox Management ───────────────────────────────────────────
    with tab1:
        st.markdown("### 📬 Mailbox Management")
        st.caption("Add and manage email accounts for sending campaigns")
        
        # Add Mailbox Form
        with st.expander("➕ Add New Mailbox", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                # Keep all options visible: Gmail / Outlook / Custom SMTP / AWS SES
                provider = st.selectbox(
                    "Provider", 
                    ["gmail", "outlook", "custom", "aws_ses"], 
                    key="add_provider",
                    help="Choose Gmail/Outlook/Custom SMTP or AWS SES (single-account, cheap bulk sending)"
                )

                # Dynamic labels so Gmail/Outlook still feel natural
                if provider == "aws_ses":
                    name_label = "Name (e.g., 'AWS SES Production')"
                    email_label = "Email Address (verified in AWS SES)"
                else:
                    name_label = "Name (e.g., 'Gmail #1')"
                    email_label = "Email Address"

                name = st.text_input(name_label, key="add_name")
                email = st.text_input(email_label, key="add_email")
                
                # AWS SES fields
                if provider == "aws_ses":
                    st.info("💡 **AWS SES**: Single account, very cheap ($0.10/1k emails). See `AWS_SES_SETUP_GUIDE.md` for setup steps.")
                    aws_access_key = st.text_input(
                        "AWS Access Key ID",
                        type="password",
                        key="add_aws_key",
                        help="Get from: AWS Console → IAM → Users → Security credentials",
                    )
                    aws_secret_key = st.text_input(
                        "AWS Secret Key",
                        type="password",
                        key="add_aws_secret",
                        help="Save securely - only shown once!",
                    )
                    aws_region = st.selectbox(
                        "AWS Region", 
                        ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"],
                        index=0,
                        key="add_aws_region",
                        help="Choose region closest to you",
                    )
                    daily_limit = st.number_input(
                        "Daily Limit (approximate, based on AWS quota)", 
                        value=200,
                        min_value=1,
                        max_value=1_000_000,
                        key="add_limit",
                        help="You can adjust this after AWS approves higher limits.",
                    )
                    smtp_host = None
                    smtp_port = None
                    smtp_username = None
                    smtp_password = None
                
                # SMTP providers (Gmail, Outlook, Custom)
                else:
                    if provider == "custom":
                        smtp_host = st.text_input("SMTP Host", value="smtp.example.com", key="add_host")
                        smtp_port = st.number_input(
                            "SMTP Port",
                            value=587,
                            min_value=1,
                            max_value=65535,
                            key="add_port",
                        )
                    elif provider == "gmail":
                        smtp_host = st.text_input(
                            "SMTP Host",
                            value="smtp.gmail.com",
                            disabled=True,
                            key="add_host",
                        )
                        smtp_port = st.number_input("SMTP Port", value=587, disabled=True, key="add_port")
                    else:  # outlook
                        smtp_host = st.text_input(
                            "SMTP Host",
                            value="smtp-mail.outlook.com",
                            disabled=True,
                            key="add_host",
                        )
                        smtp_port = st.number_input("SMTP Port", value=587, disabled=True, key="add_port")
                    
                    aws_access_key = None
                    aws_secret_key = None
                    aws_region = None
            
            with col2:
                # SMTP credentials (Gmail / Outlook / Custom)
                if provider != "aws_ses":
                    smtp_username = st.text_input(
                        "SMTP Username (usually email)",
                        value=email if 'email' in locals() else "",
                        key="add_username",
                    )
                    smtp_password = st.text_input(
                        "SMTP Password (App Password)",
                        type="password",
                        key="add_password",
                        help="For Gmail/Outlook: generate an App Password from account security settings.",
                    )
                    daily_limit = st.number_input(
                        "Daily Limit",
                        value=500 if provider == "gmail" else 300,
                        min_value=1,
                        max_value=10_000,
                        key="add_limit",
                        help="Gmail: ~500/day, Outlook: ~300/day (you can lower this to stay safe).",
                    )
            
            if st.button("➕ Add Mailbox", type="primary", use_container_width=True):
                # Validate based on provider type
                if provider == "aws_ses":
                    if not name or not email or not aws_access_key or not aws_secret_key:
                        st.error("Please fill in all AWS SES fields")
                    else:
                        try:
                            # Store AWS credentials in api_key_encrypted field
                            # Format: "access_key:secret_key:region"
                            api_key_value = f"{aws_access_key}:{aws_secret_key}:{aws_region}"
                            mailbox_id = pool.add_mailbox(
                                name=name,
                                email=email,
                                provider=provider,
                                smtp_host="",  # Not used for API providers
                                smtp_port=0,   # Not used for API providers
                                smtp_username="",  # Not used for API providers
                                smtp_password="",  # Not used for API providers
                                api_key=api_key_value,  # Store AWS credentials here
                                daily_limit=daily_limit
                            )
                            st.success(f"✅ AWS SES mailbox added! ID: {mailbox_id}")
                            st.info("💡 Make sure your email is verified in AWS SES Console!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error adding mailbox: {str(e)}")
                else:
                    # SMTP providers
                    if not name or not email or not smtp_password:
                        st.error("Please fill in all required fields")
                    else:
                        try:
                            mailbox_id = pool.add_mailbox(
                                name=name,
                                email=email,
                                provider=provider,
                                smtp_host=smtp_host,
                                smtp_port=int(smtp_port),
                                smtp_username=smtp_username or email,
                                smtp_password=smtp_password,
                                daily_limit=daily_limit
                            )
                            st.success(f"✅ Mailbox added! ID: {mailbox_id}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error adding mailbox: {str(e)}")
        
        # List Mailboxes
        st.markdown("### 📋 Active Mailboxes")
        mailboxes = pool.get_all_mailboxes()
        
        if not mailboxes:
            st.info("No mailboxes added yet. Add one above to get started.")
        else:
            # Display mailboxes in a nice table
            mb_data = []
            for mb in mailboxes:
                mb_data.append({
                    "ID": mb['id'],
                    "Name": mb['name'],
                    "Email": mb['email'],
                    "Provider": mb['provider'].upper(),
                    "Status": "✅ Active" if mb['is_active'] else "❌ Inactive",
                    "Sent Today": f"{mb['sent_today']}/{mb['daily_limit']}",
                    "Total Sent": mb['sent_total'],
                    "Errors": mb['error_count'],
                    "Last Used": mb['last_used'][:19] if mb['last_used'] else "Never"
                })
            
            df = pd.DataFrame(mb_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Mailbox Actions
            st.markdown("#### 🔧 Mailbox Actions")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                test_mb_id = st.number_input("Test Mailbox ID", min_value=1, value=1, key="test_mb_id")
                if st.button("🔍 Test Connection", use_container_width=True):
                    try:
                        if pool.test_connection(int(test_mb_id)):
                            st.success(f"✅ Mailbox #{test_mb_id} connection OK!")
                        else:
                            st.error(f"❌ Mailbox #{test_mb_id} connection failed")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
            
            with col2:
                deactivate_mb_id = st.number_input("Deactivate Mailbox ID", min_value=1, value=1, key="deactivate_mb_id")
                if st.button("⏸️ Deactivate", use_container_width=True):
                    try:
                        pool.deactivate_mailbox(int(deactivate_mb_id))
                        st.success(f"✅ Mailbox #{deactivate_mb_id} deactivated")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
            
            with col3:
                st.caption("**Total Capacity:**")
                total_capacity = sum(mb['daily_limit'] for mb in mailboxes if mb['is_active'])
                total_sent_today = sum(mb['sent_today'] for mb in mailboxes if mb['is_active'])
                st.metric("", f"{total_sent_today}/{total_capacity}", f"{total_capacity - total_sent_today} remaining")
    
    # ── TAB 2: Create Campaign ───────────────────────────────────────────────
    with tab2:
        st.markdown("### 📨 Create Email Campaign")
        st.caption("Select leads and create a campaign to send emails")
        
        # Merged leads from Saved Leads (when user clicked "Use for Email Campaign")
        merged_from_saved = st.session_state.get("merged_leads_for_email", [])
        lead_sources = ["From Sessions (Extractor)", "All Leads", "Import CSV"]
        if merged_from_saved:
            lead_sources = ["Merged from Saved Leads"] + lead_sources
            if "leads_source" not in st.session_state or st.session_state.leads_source not in lead_sources:
                st.session_state.leads_source = "Merged from Saved Leads"
        
        # Select Leads
        st.markdown("#### 1️⃣ Select Leads")
        leads_source = st.radio("Lead Source", lead_sources, key="leads_source")
        
        selected_leads = []
        
        if leads_source == "Merged from Saved Leads" and merged_from_saved:
            st.success(f"✅ {len(merged_from_saved)} merged leads ready from Saved Leads")
            leads_with_emails = [l for l in merged_from_saved if l.get("email") and "@" in str(l.get("email", ""))]
            st.info(f"📧 {len(leads_with_emails)} leads with email addresses")
            if leads_with_emails:
                preview_cols = [c for c in ["contact_name", "email", "phone"] if c in (leads_with_emails[0] or {})]
                if not preview_cols:
                    preview_cols = ["email"]
                preview_df = pd.DataFrame(leads_with_emails[:50])[preview_cols]
                st.dataframe(preview_df, use_container_width=True, hide_index=True)
                target_sends = st.number_input("Target Emails to Send", min_value=1, max_value=len(leads_with_emails), value=min(1000, len(leads_with_emails)), key="target_merged")
                selected_leads = leads_with_emails[:target_sends]
        
        elif leads_source == "From Sessions (Extractor)":
            try:
                # Get all search sessions
                sessions = get_recent_searches(limit=100)
                
                if not sessions:
                    st.warning("No extraction sessions found. Run some searches in the Live Extractor first!")
                else:
                    st.info(f"Found {len(sessions)} extraction sessions")
                    
                    # Session selection with checkboxes
                    st.markdown("**Select Sessions to Merge:**")
                    
                    # Group sessions by date for easier selection
                    sessions_by_date = {}
                    for session in sessions:
                        date_str = session['created_at'][:10] if session.get('created_at') else "Unknown"
                        if date_str not in sessions_by_date:
                            sessions_by_date[date_str] = []
                        sessions_by_date[date_str].append(session)
                    
                    # Initialize session selection in session state
                    if "selected_session_ids" not in st.session_state:
                        st.session_state.selected_session_ids = []
                    
                    # Show sessions grouped by date
                    for date_str in sorted(sessions_by_date.keys(), reverse=True):
                        with st.expander(f"📅 {date_str} ({len(sessions_by_date[date_str])} sessions)", expanded=False):
                            for session in sessions_by_date[date_str]:
                                session_id = session['id']
                                query = session.get('query', 'Unknown query')[:60]
                                num_leads = session.get('num_leads', 0)
                                created_at = session.get('created_at', '')[:19] if session.get('created_at') else 'Unknown'
                                
                                # Checkbox for each session
                                is_selected = st.checkbox(
                                    f"Session #{session_id}: {query}... ({num_leads} leads) - {created_at}",
                                    value=session_id in st.session_state.selected_session_ids,
                                    key=f"session_{session_id}"
                                )
                                
                                if is_selected and session_id not in st.session_state.selected_session_ids:
                                    st.session_state.selected_session_ids.append(session_id)
                                elif not is_selected and session_id in st.session_state.selected_session_ids:
                                    st.session_state.selected_session_ids.remove(session_id)
                    
                    # Quick selection buttons
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button("✅ Select All Sessions", use_container_width=True):
                            st.session_state.selected_session_ids = [s['id'] for s in sessions]
                            st.rerun()
                    with col2:
                        if st.button("❌ Clear Selection", use_container_width=True):
                            st.session_state.selected_session_ids = []
                            st.rerun()
                    with col3:
                        if st.button("📅 Select Today's Sessions", use_container_width=True):
                            today = datetime.now().strftime('%Y-%m-%d')
                            st.session_state.selected_session_ids = [
                                s['id'] for s in sessions 
                                if s.get('created_at', '').startswith(today)
                            ]
                            st.rerun()
                    
                    # Show selected sessions summary
                    if st.session_state.selected_session_ids:
                        selected_sessions = [s for s in sessions if s['id'] in st.session_state.selected_session_ids]
                        total_leads = sum(s.get('num_leads', 0) for s in selected_sessions)
                        
                        st.success(f"✅ {len(selected_sessions)} session(s) selected - {total_leads} total leads")
                        
                        # Load leads from selected sessions
                        all_session_leads = []
                        for session_id in st.session_state.selected_session_ids:
                            session_leads = get_leads_by_search(session_id)
                            # Add session info to each lead
                            for lead in session_leads:
                                lead['session_id'] = session_id
                                lead['session_query'] = next((s['query'] for s in sessions if s['id'] == session_id), 'Unknown')
                            all_session_leads.extend(session_leads)
                        
                        # Filter leads with emails
                        leads_with_emails = [l for l in all_session_leads if l.get('email') and '@' in str(l.get('email', ''))]
                        
                        st.info(f"📧 {len(leads_with_emails)} leads with email addresses (out of {len(all_session_leads)} total)")
                        
                        if leads_with_emails:
                            # Show preview with session info
                            preview_data = []
                            for lead in leads_with_emails[:50]:  # Show first 50
                                preview_data.append({
                                    'Session': f"#{lead.get('session_id', '?')}",
                                    'Query': lead.get('session_query', '')[:30] + '...' if len(lead.get('session_query', '')) > 30 else lead.get('session_query', ''),
                                    'Name': lead.get('contact_name', ''),
                                    'Email': lead.get('email', ''),
                                    'Phone': lead.get('phone', ''),
                                })
                            
                            if preview_data:
                                preview_df = pd.DataFrame(preview_data)
                                st.dataframe(preview_df, use_container_width=True, hide_index=True)
                            
                            # Campaign planning: Limit by target send count
                            st.markdown("**📊 Campaign Planning:**")
                            col_plan1, col_plan2 = st.columns(2)
                            with col_plan1:
                                target_sends = st.number_input(
                                    "Target Emails to Send",
                                    min_value=1,
                                    max_value=len(leads_with_emails),
                                    value=min(1000, len(leads_with_emails)),
                                    key="target_sends",
                                    help="Limit campaign to this many emails (useful for testing or capacity planning)"
                                )
                            with col_plan2:
                                dedupe_emails = st.checkbox(
                                    "Remove Duplicate Emails",
                                    value=True,
                                    key="dedupe_emails",
                                    help="If same email appears in multiple sessions, use only once"
                                )
                            
                            # Apply deduplication if requested
                            if dedupe_emails:
                                seen_emails = set()
                                unique_leads = []
                                for lead in leads_with_emails:
                                    email = lead.get('email', '').lower().strip()
                                    if email and email not in seen_emails:
                                        seen_emails.add(email)
                                        unique_leads.append(lead)
                                leads_with_emails = unique_leads
                                st.caption(f"After deduplication: {len(leads_with_emails)} unique emails")
                            
                            # Limit to target sends
                            selected_leads = leads_with_emails[:target_sends]
                            
                            if len(leads_with_emails) > target_sends:
                                st.warning(f"⚠️ Limiting to {target_sends} emails (out of {len(leads_with_emails)} available)")
                        else:
                            st.warning("No leads with email addresses found in selected sessions.")
                    else:
                        st.info("👆 Select one or more sessions above to create a campaign")
                        
            except Exception as e:
                st.error(f"Error loading sessions: {str(e)}")
                import traceback
                st.code(traceback.format_exc())
        
        elif leads_source == "All Leads":
            try:
                all_leads = get_all_leads(limit=10000)
                if not all_leads:
                    st.warning("No leads found in database. Extract some leads first!")
                else:
                    # Filter leads with emails
                    leads_with_emails = [l for l in all_leads if l.get('email') and '@' in str(l.get('email', ''))]
                    
                    st.info(f"Found {len(leads_with_emails)} leads with email addresses (out of {len(all_leads)} total)")
                    
                    if leads_with_emails:
                        # Show preview
                        preview_df = pd.DataFrame(leads_with_emails[:100])[['contact_name', 'email', 'phone', 'business_name']]
                        st.dataframe(preview_df, use_container_width=True, hide_index=True)
                        
                        # Select all or filter
                        use_all = st.checkbox("Use all leads with emails", value=True, key="use_all_leads")
                        if not use_all:
                            max_leads = st.number_input("Max leads to use", min_value=1, max_value=len(leads_with_emails), value=min(100, len(leads_with_emails)), key="max_leads")
                            selected_leads = leads_with_emails[:max_leads]
                        else:
                            selected_leads = leads_with_emails
            except Exception as e:
                st.error(f"Error loading leads: {str(e)}")
        else:
            uploaded_file = st.file_uploader("Upload CSV", type=['csv'], key="csv_upload")
            if uploaded_file:
                try:
                    df = pd.read_csv(uploaded_file)
                    st.dataframe(df.head(10), use_container_width=True)
                    
                    # Map columns
                    email_col = st.selectbox("Email Column", df.columns.tolist(), key="email_col")
                    name_col = st.selectbox("Name Column (optional)", [None] + df.columns.tolist(), key="name_col")
                    
                    if st.button("Load Leads", key="load_csv"):
                        selected_leads = []
                        for _, row in df.iterrows():
                            email = str(row[email_col]).strip() if email_col and pd.notna(row.get(email_col)) else ""
                            if '@' in email:
                                selected_leads.append({
                                    'email': email,
                                    'contact_name': str(row[name_col]).strip() if name_col and pd.notna(row.get(name_col)) else "",
                                    'phone': "",
                                    'business_name': ""
                                })
                        st.success(f"Loaded {len(selected_leads)} leads from CSV")
                except Exception as e:
                    st.error(f"Error reading CSV: {str(e)}")
        
        if selected_leads:
            # Generate smart campaign name based on selection
            if leads_source == "From Sessions (Extractor)" and st.session_state.selected_session_ids:
                session_count = len(st.session_state.selected_session_ids)
                if session_count == 1:
                    campaign_default_name = f"Session #{st.session_state.selected_session_ids[0]} - {datetime.now().strftime('%Y-%m-%d')}"
                else:
                    campaign_default_name = f"Merged {session_count} Sessions - {datetime.now().strftime('%Y-%m-%d')}"
            else:
                campaign_default_name = f"Campaign {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
            st.success(f"✅ {len(selected_leads)} leads selected")
            
            # Show session summary if from sessions
            if leads_source == "From Sessions (Extractor)" and st.session_state.selected_session_ids:
                sessions = get_recent_searches(limit=100)
                selected_sessions = [s for s in sessions if s['id'] in st.session_state.selected_session_ids]
                session_ids_display = ', '.join([f'#{s["id"]}' for s in selected_sessions[:5]])
                if len(selected_sessions) > 5:
                    session_ids_display += '...'
                st.caption(f"📋 Sessions: {session_ids_display}")
            
            # Email Template
            st.markdown("#### 2️⃣ Email Template")
            campaign_name = st.text_input("Campaign Name", value=campaign_default_name, key="campaign_name")
            
            col1, col2 = st.columns(2)
            with col1:
                subject_template = st.text_input("Subject", value="Hello {{name}}", key="subject_template",
                                                help="Use {{name}} or {{email}} for personalization")
            with col2:
                use_html = st.checkbox("HTML Email", value=True, key="use_html")
            
            body_template = st.text_area("Email Body", height=200, 
                                       value="""<p>Hello {{name}},</p>
<p>We found your contact information and would like to reach out.</p>
<p>Best regards,<br>Lead Extractor Pro</p>""",
                                       help="Use {{name}}, {{email}}, {{phone}} for personalization",
                                       key="body_template")
            
            # Mailbox Selection
            st.markdown("#### 3️⃣ Mailbox Selection")
            active_mailboxes = [mb for mb in pool.get_all_mailboxes() if mb['is_active']]
            if not active_mailboxes:
                st.error("No active mailboxes! Add a mailbox first.")
            else:
                mailbox_option = st.radio("Mailbox Strategy", 
                                        ["Auto-rotate (use all active mailboxes)", "Use specific mailbox"],
                                        key="mailbox_strategy")
                
                selected_mailbox_id = None
                if mailbox_option == "Use specific mailbox":
                    mb_choices = {f"{mb['name']} ({mb['email']}) - {mb['sent_today']}/{mb['daily_limit']} remaining": mb['id'] 
                                 for mb in active_mailboxes}
                    selected_mb_name = st.selectbox("Select Mailbox", list(mb_choices.keys()), key="select_mb")
                    selected_mailbox_id = mb_choices[selected_mb_name]
            
            # Create Campaign Button
            st.markdown("#### 4️⃣ Start Campaign")
            if st.button("🚀 Create & Start Campaign", type="primary", use_container_width=True):
                if not campaign_name or not subject_template or not body_template:
                    st.error("Please fill in campaign name, subject, and body")
                elif not selected_leads:
                    st.error("Please select at least one lead")
                elif not active_mailboxes:
                    st.error("No active mailboxes available")
                else:
                    # Create campaign in database
                    conn = get_connection()
                    
                    # Store session info in campaign name or notes (we'll add notes field later if needed)
                    # For now, include session IDs in campaign name if from sessions
                    final_campaign_name = campaign_name
                    if leads_source == "From Sessions (Extractor)" and st.session_state.selected_session_ids:
                        session_ids_str = ','.join(map(str, st.session_state.selected_session_ids))
                        final_campaign_name = f"{campaign_name} [Sessions: {session_ids_str}]"
                    
                    cursor = conn.execute(
                        """INSERT INTO email_campaigns 
                           (name, subject_template, body_template, status, total_recipients)
                           VALUES (?, ?, ?, 'draft', ?)""",
                        (final_campaign_name, subject_template, body_template, len(selected_leads))
                    )
                    campaign_id = cursor.lastrowid
                    
                    # Add emails to queue
                    limiter = RateLimiter()
                    smtp_pool = SMTPConnectionPool(max_connections_per_mailbox=5)
                    
                    queued_count = 0
                    for lead in selected_leads:
                        # Personalize subject and body
                        subject = subject_template.replace("{{name}}", lead.get('contact_name', '')).replace("{{email}}", lead.get('email', ''))
                        body = body_template.replace("{{name}}", lead.get('contact_name', '')).replace("{{email}}", lead.get('email', '')).replace("{{phone}}", lead.get('phone', ''))
                        
                        # Get available mailbox
                        if selected_mailbox_id:
                            mailbox = pool._get_mailbox_by_id(selected_mailbox_id)
                        else:
                            mailbox = pool.get_available_mailbox()
                        
                        if not mailbox:
                            st.warning(f"⚠️ No available mailboxes for lead {lead.get('email')}. Skipping...")
                            continue
                        
                        # Add to queue
                        conn.execute(
                            """INSERT INTO email_queue 
                               (campaign_id, mailbox_id, recipient_email, recipient_name, subject, body, status)
                               VALUES (?, ?, ?, ?, ?, ?, 'pending')""",
                            (campaign_id, mailbox['id'], lead.get('email'), lead.get('contact_name', ''), subject, body)
                        )
                        queued_count += 1
                    
                    conn.commit()
                    conn.close()
                    
                    st.success(f"✅ Campaign '{campaign_name}' created! {queued_count} emails queued.")
                    st.info("💡 Note: Email sending will be implemented in Phase 2 (background workers). For now, emails are queued in the database.")
                    if "merged_leads_for_email" in st.session_state:
                        del st.session_state.merged_leads_for_email
                    st.rerun()
    
    # ── TAB 3: Campaign Queue ────────────────────────────────────────────────
    with tab3:
        st.markdown("### 📊 Campaign Queue & Status")
        st.caption("View campaign progress and email queue")
        
        # List Campaigns
        conn = get_connection()
        campaigns = conn.execute(
            """SELECT id, name, status, total_recipients, sent_count, failed_count, created_at
               FROM email_campaigns
               ORDER BY created_at DESC
               LIMIT 20"""
        ).fetchall()
        conn.close()
        
        if not campaigns:
            st.info("No campaigns created yet. Create one in the 'Create Campaign' tab.")
        else:
            for campaign in campaigns:
                campaign_id = campaign['id']
                with st.expander(f"📧 {campaign['name']} - {campaign['status'].upper()} ({campaign['sent_count']}/{campaign['total_recipients']} sent)", expanded=False):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Recipients", campaign['total_recipients'])
                    with col2:
                        st.metric("Sent", campaign['sent_count'])
                    with col3:
                        st.metric("Failed", campaign['failed_count'])
                    
                    # Queue Status
                    conn = get_connection()
                    queue_stats = conn.execute(
                        """SELECT status, COUNT(*) as count
                           FROM email_queue
                           WHERE campaign_id = ?
                           GROUP BY status""",
                        (campaign_id,)
                    ).fetchall()
                    conn.close()
                    
                    if queue_stats:
                        st.markdown("**Queue Status:**")
                        for stat in queue_stats:
                            st.write(f"- {stat['status']}: {stat['count']}")
                    
                    # Show recent queue items
                    conn = get_connection()
                    recent_queue = conn.execute(
                        """SELECT recipient_email, status, attempts, error_message, sent_at
                           FROM email_queue
                           WHERE campaign_id = ?
                           ORDER BY id DESC
                           LIMIT 10"""
                    ).fetchall()
                    conn.close()
                    
                    if recent_queue:
                        st.markdown("**Recent Emails:**")
                        queue_df = pd.DataFrame(recent_queue)
                        st.dataframe(queue_df, use_container_width=True, hide_index=True)
