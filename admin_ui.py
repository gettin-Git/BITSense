import streamlit as st
import os
import json
import shutil
import base64

st.set_page_config(page_title="Document Approval Dashboard", layout="wide", page_icon="🛡️")

STAGING_DIR = os.path.join(os.path.dirname(__file__), "data", "staging")
POLICIES_DIR = os.path.join(os.path.dirname(__file__), "data", "policies")

os.makedirs(STAGING_DIR, exist_ok=True)
os.makedirs(POLICIES_DIR, exist_ok=True)

st.title("🛡️ Rapid Document Approval Dashboard")
st.markdown("Review scavenged PDFs before they are injected into the AI's knowledge base. Rejecting a document ensures it is never downloaded again.")

# Get list of metadata files in staging
meta_files = [f for f in os.listdir(STAGING_DIR) if f.endswith(".meta.json")]

if not meta_files:
    st.success("🎉 No pending documents! Run `python scavenge_docs.py` to find more.")
    st.stop()

# We only process the first document in the queue (makes it a rapid-fire queue)
current_meta = meta_files[0]
meta_path = os.path.join(STAGING_DIR, current_meta)

try:
    with open(meta_path, "r") as f:
        meta = json.load(f)
except Exception as e:
    st.error(f"Failed to read metadata: {e}")
    os.remove(meta_path)
    st.rerun()

source_url = meta.get("source_url")
pdf_path = meta.get("pdf_path")
pdf_name = meta.get("pdf_name")
screenshot = meta.get("screenshot")

st.subheader(f"📄 Pending Document: `{pdf_name}`")
st.markdown(f"**Found directly on:** [{source_url}]({source_url})")
st.markdown(f"*(Queue remaining: {len(meta_files)})*")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 📸 Source Page Screenshot")
    if screenshot and os.path.exists(screenshot):
        st.image(screenshot, use_container_width=True)
    else:
        st.warning("No screenshot available for this source page.")

with col2:
    st.markdown("### 🔍 PDF Viewer")
    if pdf_path and os.path.exists(pdf_path):
        # Read PDF as base64 to embed in an iframe
        with open(pdf_path, "rb") as f:
            base64_pdf = base64.b64encode(f.read()).decode('utf-8')
        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="700" type="application/pdf"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)
    else:
        st.error("The raw PDF file is missing from the disk!")

SCREENSHOTS_DIR = os.path.join(os.path.dirname(__file__), "data", "screenshots")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

# Actions
st.markdown("---")
col3, col4, col5 = st.columns([1, 2, 2])

with col4:
    if st.button("✅ APPROVE (Move to AI Policies)", use_container_width=True, type="primary"):
        if os.path.exists(pdf_path):
            # Move PDF to active policies folder
            dest_pdf = os.path.join(POLICIES_DIR, pdf_name)
            shutil.move(pdf_path, dest_pdf)
            
            # Keep screenshot in permanent screenshots dir for user verification
            perm_screenshot = ""
            if screenshot and os.path.exists(screenshot):
                perm_screenshot = os.path.join(SCREENSHOTS_DIR, os.path.basename(screenshot))
                shutil.copyfile(screenshot, perm_screenshot)
                
            # Move metadata to policies dir for ingest_policies.py
            dest_meta = os.path.join(POLICIES_DIR, pdf_name + ".meta.json")
            meta["pdf_path"] = dest_pdf
            if perm_screenshot:
                meta["screenshot"] = perm_screenshot
            with open(dest_meta, "w") as mf:
                json.dump(meta, mf, indent=4)
                
        # Clean up staging meta file
        if os.path.exists(meta_path):
            os.remove(meta_path)
        st.rerun()

with col5:
    if st.button("❌ REJECT (Delete forever)", use_container_width=True):
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        if os.path.exists(meta_path):
            os.remove(meta_path)
        st.rerun()
