import os
import streamlit as st
import pandas as pd
from dotenv import load_dotenv

import excel_manager
from agents import run_agent_pipeline

# Page Configuration
st.set_page_config(
    page_title="AI Resume Parser & Candidate Management",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load existing environment variables
load_dotenv()

# Helper to save API key to local .env file
def save_api_key_to_env(api_key: str):
    env_path = ".env"
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            lines = f.readlines()
            
    updated = False
    new_lines = []
    for line in lines:
        if line.strip().startswith("GEMINI_API_KEY="):
            new_lines.append(f"GEMINI_API_KEY={api_key}\n")
            updated = True
        else:
            new_lines.append(line)
            
    if not updated:
        new_lines.append(f"GEMINI_API_KEY={api_key}\n")
        
    with open(env_path, "w") as f:
        f.writelines(new_lines)
    
    # Also update environment for the current process
    os.environ["GEMINI_API_KEY"] = api_key

# Custom CSS for modern premium dashboard UI
st.markdown("""
<style>
    /* Gradient Header Band */
    .header-band {
        background: linear-gradient(135deg, #6366F1 0%, #3B82F6 100%);
        padding: 2rem;
        border-radius: 12px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
    }
    .header-band h1 {
        color: white !important;
        margin: 0;
        font-family: 'Inter', sans-serif;
        font-weight: 800;
        font-size: 2.2rem;
    }
    .header-band p {
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
        font-size: 1.1rem;
    }
    
    /* Stats Cards styling */
    .stat-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 1.2rem;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.02);
    }
    .dark .stat-card {
        background-color: #1E293B;
        border-color: #334155;
    }
    
    /* Sidebar styling enhancements */
    .css-1542z7x {
        background-color: #F1F5F9;
    }
</style>
""", unsafe_allow_html=True)

# Load Gemini API key from environment
api_key = os.getenv("GEMINI_API_KEY", "")

# ----------------- SIDEBAR CONFIGURATION -----------------
with st.sidebar:
    st.image("https://img.icons8.com/color/96/resume.png", width=80)
    st.title("System Status")
    st.markdown("Interview Candidate Management Status Dashboard.")
    st.write("---")
    st.markdown("### 🤖 Agentic Pipeline")
    st.markdown("""
    - **Reader Agent**: Multi-format OCR scan
    - **Extraction Agent**: Gemini Schema parsing
    - **Validation Agent**: Entity & regex verification
    - **Storage Agent**: Excel record appending
    """)
    
    st.write("---")
    # Quick Statistics
    df_stats = excel_manager.load_excel_data()
    st.markdown("### 📊 Database Statistics")
    st.metric("Total Candidates Saved", len(df_stats))
    
    if len(df_stats) > 0:
        most_common_role = df_stats["Applied Role"].mode()
        if not most_common_role.empty:
            st.metric("Top Applied Role", most_common_role[0])

# ----------------- HEADER BAND -----------------
st.markdown("""
<div class="header-band">
    <h1>Interview Candidate Management System</h1>
    <p>AI-Powered Automatic Resume Parsing and Master Excel Centralization</p>
</div>
""", unsafe_allow_html=True)

# ----------------- MAIN TABS -----------------
tab1, tab2 = st.tabs(["📤 Upload & Process", "📊 Master Database"])

# ================= TAB 1: UPLOAD & PROCESS =================
with tab1:
    st.markdown("### Upload Resumes for Processing")
    st.markdown("Select digital PDF files, docx files, or scan paper hardcopies using a mobile/desktop camera.")

    # Show active Excel database information
    st.info(f"💾 **Active Excel Database:** `{os.path.basename(excel_manager.EXCEL_PATH)}`  \n"
            f"📍 **Full Storage Path:** `{excel_manager.EXCEL_PATH}`")

    # Verification warning for API Key
    if not api_key:
        st.error("⚠️ **System Error:** Gemini API Key is missing from the server environment `.env` file.")

    col_upload, col_camera = st.columns([1, 1])

    with col_upload:
        st.markdown("#### 📂 Upload Files")
        uploaded_files = st.file_uploader(
            "Choose Resume PDF, Image or Word files",
            type=["pdf", "jpg", "jpeg", "png", "docx"],
            accept_multiple_files=True
        )

    with col_camera:
        st.markdown("#### 📷 Mobile/Webcam Photo Capture")
        camera_file = st.camera_input("Take a photo of a physical copy resume")

    # Group all incoming files
    files_to_process = []
    
    if uploaded_files:
        for f in uploaded_files:
            files_to_process.append({
                "bytes": f.getvalue(),
                "name": f.name,
                "mime_type": f.type
            })
            
    if camera_file:
        files_to_process.append({
            "bytes": camera_file.getvalue(),
            "name": f"camera_scan_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.jpg",
            "mime_type": camera_file.type
        })

    # Action Trigger Button
    if files_to_process:
        st.write("---")
        st.markdown(f"#### 🚀 Found {len(files_to_process)} resume(s) ready to process.")
        
        if st.button("Start Parsing and Append to Excel", type="primary", disabled=not bool(api_key)):
            for file_info in files_to_process:
                # Use st.status for premium agent tracking
                with st.status(f"Processing candidate: {file_info['name']}...", expanded=True) as status:
                    
                    # Track steps inside status
                    def update_progress(step, msg):
                        emoji_map = {
                            "reader_start": "🔍",
                            "reader_done": "📖",
                            "extractor_start": "🧠",
                            "extractor_done": "⚙️",
                            "validator_start": "🛡️",
                            "validator_done": "✅",
                            "storage_start": "💾",
                            "storage_done": "📁",
                            "storage_error": "❌",
                            "pipeline_error": "🚨"
                        }
                        emoji = emoji_map.get(step, "➡️")
                        st.markdown(f"{emoji} **{msg}**")

                    result = run_agent_pipeline(
                        file_bytes=file_info["bytes"],
                        file_name=file_info["name"],
                        mime_type=file_info["mime_type"],
                        api_key=api_key,
                        progress_callback=update_progress
                    )
                    
                    if result["success"]:
                        status.update(
                            label=f"✓ Successfully processed and stored: {result['data']['Full Name']}", 
                            state="complete"
                        )
                        st.success(f"Added {result['data']['Full Name']} to Master Excel!")
                    else:
                        status.update(
                            label=f"✗ Failed to parse: {file_info['name']}", 
                            state="error"
                        )
                        st.error(f"Error details: {result['message']}")
            # Completed processing, updates will render on next action
            pass

# ================= TAB 2: MASTER DATABASE =================
with tab2:
    st.markdown("### Centralized Master Excel Sheet View")
    st.markdown("This sheet is stored directly on the server. You can view, search, edit cells, or download the final Excel file below.")
    
    # Reload dataframe
    df = excel_manager.load_excel_data()
    
    if df.empty:
        st.info("No candidates parsed yet. Upload resumes to see database rows here.")
    else:
        # Search & Filter
        col_search, col_stats = st.columns([2, 2])
        with col_search:
            search_query = st.text_input("🔍 Search Database (matches Name, Skills, Role, or Email)", "")
            
        if search_query:
            # Simple keyword match
            search_query = search_query.lower()
            df_filtered = df[
                df["Full Name"].str.lower().str.contains(search_query) |
                df["Skills"].str.lower().str.contains(search_query) |
                df["Applied Role"].str.lower().str.contains(search_query) |
                df["Email"].str.lower().str.contains(search_query)
            ]
        else:
            df_filtered = df
            
        st.write(f"Showing {len(df_filtered)} out of {len(df)} records.")
        
        # Display data in st.data_editor to allow inline modifications
        edited_df = st.data_editor(
            df_filtered,
            num_rows="dynamic",
            use_container_width=True,
            disabled=["S.No", "Parsed At"],  # Disable changing indexes and timestamps directly
            key="db_editor"
        )
        
        # Save edits back to excel
        if st.button("Save Changes to Excel Database", type="secondary"):
            # Re-merge changes back to master df
            # If rows were deleted or updated, we should save the edited frame
            # Let's rebuild/re-save the updated sheet
            success = excel_manager.save_excel_data(edited_df)
            if success:
                st.success("Excel database saved and updated successfully!")
                st.rerun()
            else:
                st.error("Failed to save changes. Make sure the file isn't open in another application.")

        # Download / Reset actions
        st.write("---")
        col_dl, col_reset = st.columns([1, 1])
        
        with col_dl:
            st.markdown("#### 📁 Download Excel Sheet")
            st.markdown("Download the centralized Excel spreadsheet directly to your device.")
            
            # Read file bytes for download
            if os.path.exists(excel_manager.EXCEL_PATH):
                with open(excel_manager.EXCEL_PATH, "rb") as excel_file:
                    excel_bytes = excel_file.read()
                    
                st.download_button(
                    label="⬇️ Download master_sheet.xlsx",
                    data=excel_bytes,
                    file_name="master_sheet.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.warning("File is empty or not created yet.")

        with col_reset:
            st.markdown("#### ⚠️ Reset Sheet")
            st.markdown("Permanently delete the database. *All candidate profiles will be lost!*")
            
            # Double confirmation reset
            understand_check = st.checkbox("I understand that resetting will delete the master Excel file.")
            if st.button("Delete and Reset Excel", type="primary", disabled=not understand_check):
                excel_manager.reset_excel_file()
                st.success("Excel sheet reset successfully!")
                st.rerun()


