"""Lead Manager UI Page - Upload, validate, and manage external leads."""

import streamlit as st
import pandas as pd
from io import BytesIO
from app.lead_manager import (
    upload_leads_from_file,
    get_external_leads,
    get_external_leads_by_domain,
    get_domain_statistics,
    compare_with_extracted_leads,
    delete_external_leads,
    save_external_leads,
)
from app.lead_manager.domain_filter import (
    extract_domain,
    filter_leads_by_domain,
    group_leads_by_domain,
    get_domain_stats,
)
from app.lead_manager.validator import validate_email
from app.export.exporter import export_to_csv, export_to_excel
from app.utils.download_ui import download_button_with_fallback


def render_lead_manager_page():
    """Render the Lead Manager page."""
    
    st.markdown('<p class="app-title">Lead Manager</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="app-subtitle">Upload external leads, validate against extracted leads, and manage by domain.</p>',
        unsafe_allow_html=True,
    )
    
    # Create tabs for different functionality
    tab1, tab2, tab3, tab4 = st.tabs([
        "📤 Upload Leads",
        "🔍 View & Filter",
        "📊 Domain Analysis",
        "🔗 Duplicate Check"
    ])
    
    # ─── TAB 1: Upload Leads ─────────────────────────────────────────────
    with tab1:
        st.markdown("### Upload External Leads")
        st.caption("Supported formats: TXT (one email per line), CSV, XLSX, JSON")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            uploaded_file = st.file_uploader(
                "Choose a file",
                type=["txt", "csv", "xlsx", "json"],
                help="Upload a file with email leads"
            )
        
        with col2:
            st.empty()  # Spacing
        
        if uploaded_file:
            st.info(f"📄 Selected: {uploaded_file.name}")
            
            # Read file content
            file_content = uploaded_file.read()
            file_name = uploaded_file.name
            
            # Show preview
            if st.checkbox("Preview file content", value=True):
                try:
                    # Show first few lines/rows
                    if file_name.endswith('.txt'):
                        text_content = file_content.decode('utf-8', errors='ignore')
                        lines = text_content.split('\n')[:10]
                        st.code('\n'.join(lines), language='text')
                    elif file_name.endswith('.json'):
                        text_content = file_content.decode('utf-8', errors='ignore')
                        st.code(text_content[:500], language='json')
                    else:
                        st.text("Binary file - preview not available")
                except Exception as e:
                    st.error(f"Preview error: {str(e)}")
            
            # Parse file
            if st.button("Parse & Validate Leads", key="parse_leads"):
                with st.spinner("Parsing file..."):
                    leads, messages = upload_leads_from_file(file_content, file_name)
                    
                    # Show messages
                    for msg in messages:
                        if "Successfully" in msg or "Parsed" in msg:
                            st.success(msg)
                        elif "Error" in msg:
                            st.error(msg)
                        else:
                            st.info(msg)
                    
                    if leads:
                        st.markdown(f"### ✅ Ready to import: {len(leads)} leads")
                        
                        # Show preview table
                        df = pd.DataFrame(leads[:20])
                        st.dataframe(df, use_container_width=True)
                        
                        if len(leads) > 20:
                            st.caption(f"Showing 20 of {len(leads)} leads")
                        
                        # Validation summary
                        valid_count = 0
                        invalid_count = 0
                        
                        st.markdown("#### Validation Summary")
                        col_v1, col_v2 = st.columns(2)
                        
                        for lead in leads:
                            email = lead.get("email", "")
                            validation = validate_email(email)
                            if validation.is_valid:
                                valid_count += 1
                            else:
                                invalid_count += 1
                        
                        with col_v1:
                            st.metric("✅ Valid Emails", valid_count)
                        with col_v2:
                            st.metric("❌ Invalid Emails", invalid_count)
                        
                        # Import button
                        if st.button("✅ Import to Database", key="import_leads"):
                            with st.spinner("Importing leads..."):
                                count, import_messages = save_external_leads(leads, file_name=file_name)
                                
                                for msg in import_messages:
                                    if "Successfully" in msg:
                                        st.success(msg)
                                    elif "Error" in msg or "Invalid" in msg:
                                        st.warning(msg)
                                
                                if count > 0:
                                    st.balloons()
                                    st.session_state.refresh_lead_manager = True
                    else:
                        st.error("No valid leads found in file")
    
    # ─── TAB 2: View & Filter ───────────────────────────────────────────
    with tab2:
        st.markdown("### View External Leads")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            search_domain = st.text_input(
                "Filter by domain",
                placeholder="e.g., gmail.com",
                help="Leave blank to see all leads"
            )
        
        with col2:
            limit = st.selectbox(
                "Leads per page",
                options=[100, 500, 1000, 5000],
                index=1
            )
        
        with col3:
            if st.button("🔄 Refresh", key="refresh_leads"):
                st.session_state.refresh_lead_manager = True
        
        # Fetch leads
        if search_domain:
            leads = get_external_leads_by_domain(search_domain)
            st.caption(f"Filtered by domain: {search_domain}")
        else:
            leads = get_external_leads(limit=limit)
        
        if leads:
            st.success(f"Found {len(leads)} leads")
            
            # Convert to DataFrame
            df = pd.DataFrame(leads)
            
            # Display options
            col_d1, col_d2, col_d3 = st.columns(3)
            
            with col_d1:
                if st.button("📥 Export as CSV", key="export_csv_ext"):
                    csv_bytes = export_to_csv(leads, filename="external_leads.csv")
                    download_button_with_fallback(
                        label="⬇️ Download CSV",
                        data=csv_bytes,
                        file_name="external_leads.csv",
                        mime="text/csv"
                    )
            
            with col_d2:
                if st.button("📊 Export as Excel", key="export_excel_ext"):
                    excel_bytes = export_to_excel(leads, filename="external_leads.xlsx")
                    download_button_with_fallback(
                        label="⬇️ Download Excel",
                        data=excel_bytes,
                        file_name="external_leads.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            
            with col_d3:
                st.empty()
            
            # Display table
            st.dataframe(df, use_container_width=True, height=400)
            
            # Bulk actions
            st.markdown("#### Bulk Actions")
            col_ba1, col_ba2 = st.columns(2)
            
            with col_ba1:
                if st.button("🗑️ Delete All Shown", key="delete_all"):
                    if st.checkbox("Confirm deletion of all shown leads"):
                        lead_ids = [l["id"] for l in leads]
                        deleted, msg = delete_external_leads(lead_ids)
                        st.success(msg)
                        st.session_state.refresh_lead_manager = True
            
            with col_ba2:
                st.empty()
        
        else:
            st.info("No external leads found. Upload some leads to get started!")
    
    # ─── TAB 3: Domain Analysis ─────────────────────────────────────────
    with tab3:
        st.markdown("### Domain Analysis")
        st.caption("Statistics and breakdown of leads by domain")
        
        # Get stats
        with st.spinner("Loading domain statistics..."):
            domain_stats = get_domain_statistics()
        
        if domain_stats:
            # Summary metrics
            col_s1, col_s2, col_s3 = st.columns(3)
            
            with col_s1:
                st.metric("📊 Total Domains", len(domain_stats))
            
            with col_s2:
                total_leads = sum(domain_stats.values())
                st.metric("📧 Total Leads", total_leads)
            
            with col_s3:
                avg_per_domain = total_leads / len(domain_stats) if domain_stats else 0
                st.metric("📈 Avg per Domain", f"{avg_per_domain:.1f}")
            
            st.divider()
            
            # Domain breakdown
            st.markdown("#### Top Domains")
            
            # Create DataFrame for better visualization
            domain_df = pd.DataFrame(
                list(domain_stats.items())[:20],
                columns=["Domain", "Count"]
            )
            
            # Bar chart
            st.bar_chart(domain_df.set_index("Domain")["Count"])
            
            # Table
            st.dataframe(domain_df, use_container_width=True)
            
            if len(domain_stats) > 20:
                st.caption(f"Showing top 20 of {len(domain_stats)} domains")
            
            # Domain filter options
            st.markdown("#### Filter by Domain")
            
            top_domains = list(domain_stats.keys())[:10]
            selected_domain = st.selectbox(
                "Select domain to view leads",
                options=top_domains,
                key="domain_select"
            )
            
            if selected_domain:
                domain_leads = get_external_leads_by_domain(selected_domain)
                st.success(f"{len(domain_leads)} leads from {selected_domain}")
                
                df_domain = pd.DataFrame(domain_leads)
                st.dataframe(df_domain, use_container_width=True)
        
        else:
            st.info("No domain data available. Upload some leads first!")
    
    # ─── TAB 4: Duplicate Check ─────────────────────────────────────────
    with tab4:
        st.markdown("### Duplicate Check")
        st.caption("Compare external leads with extracted leads to find duplicates")
        
        # Get external leads count
        external_count = len(get_external_leads(limit=100000))
        st.metric("External Leads Available", external_count)
        
        if external_count > 0:
            # Option 1: Single email check
            st.markdown("#### Check Single Email")
            
            single_email = st.text_input(
                "Enter email to check",
                placeholder="user@example.com",
                key="single_check"
            )
            
            if single_email and st.button("🔍 Check Email", key="check_single"):
                match = compare_with_extracted_leads(single_email)
                
                if match:
                    st.warning("⚠️ Found in extracted leads!")
                    col_m1, col_m2 = st.columns(2)
                    
                    with col_m1:
                        st.markdown(f"**Email:** {match['email']}")
                        st.markdown(f"**Name:** {match.get('contact_name', 'N/A')}")
                        st.markdown(f"**Business:** {match.get('business_name', 'N/A')}")
                    
                    with col_m2:
                        st.markdown(f"**Match Type:** {match.get('match_type', 'N/A')}")
                        st.markdown(f"**Query:** {match.get('query', 'N/A')}")
                        st.markdown(f"**Found:** {match.get('created_at', 'N/A')}")
                else:
                    st.success("✅ Email not found in extracted leads - No duplicate!")
            
            # Option 2: Batch check
            st.divider()
            st.markdown("#### Batch Duplicate Check")
            st.caption("Check all external leads for duplicates in extracted leads")
            
            if st.button("🔄 Run Batch Check", key="batch_check"):
                with st.spinner("Checking for duplicates..."):
                    all_external = get_external_leads(limit=100000)
                    
                    duplicates = []
                    unique = []
                    
                    for lead in all_external:
                        match = compare_with_extracted_leads(lead["email"])
                        if match:
                            duplicates.append({
                                "email": lead["email"],
                                "domain": lead["domain"],
                                "found_query": match["query"],
                                "found_date": match["created_at"]
                            })
                        else:
                            unique.append(lead)
                    
                    col_b1, col_b2 = st.columns(2)
                    
                    with col_b1:
                        st.metric("🔗 Duplicates Found", len(duplicates))
                    with col_b2:
                        st.metric("✅ Unique", len(unique))
                    
                    if duplicates:
                        st.warning(f"Found {len(duplicates)} duplicates!")
                        
                        dup_df = pd.DataFrame(duplicates)
                        st.dataframe(dup_df, use_container_width=True)
                        
                        # Export duplicates
                        if st.button("📥 Export Duplicates", key="export_dup"):
                            csv_bytes = export_to_csv(duplicates, filename="duplicates.csv")
                            download_button_with_fallback(
                                label="⬇️ Download Duplicates CSV",
                                data=csv_bytes,
                                file_name="duplicates.csv",
                                mime="text/csv"
                            )
                    
                    if unique:
                        st.success(f"{len(unique)} leads are unique!")
        
        else:
            st.info("No external leads to check. Upload some leads first!")
