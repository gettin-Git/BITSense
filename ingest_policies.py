import os
import json
import time
import gc
import fitz  # PyMuPDF
from datetime import datetime
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_classic.retrievers import ParentDocumentRetriever
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_classic.storage import LocalFileStore, create_kv_docstore
from config import POLICIES_DIR, CHROMA_DB_DIR, LOCAL_FILE_STORE_DIR, EMBEDDING_MODEL

STATE_FILE = os.path.join(os.path.dirname(__file__), "data", "ingestion_state.json")
STAGING_DIR = os.path.join(os.path.dirname(__file__), "data", "staging")

def get_processed_files():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_processed_files(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def ingest_data():
    if not os.path.exists(POLICIES_DIR):
        print(f"Directory {POLICIES_DIR} does not exist.")
        return

    processed_state = get_processed_files()
    
    print(f"Scanning for new or modified PDFs in {POLICIES_DIR}...")
    start_time = time.time()
    
    # 1. Boot up the AI embedding model FIRST so it doesn't compete for memory later
    print("Initializing HuggingFace Embeddings Model (Low Memory Mode)...")
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'batch_size': 4}
    )
    os.makedirs(LOCAL_FILE_STORE_DIR, exist_ok=True)
    vectorstore = Chroma(collection_name="policies_child_chunks", embedding_function=embeddings, persist_directory=CHROMA_DB_DIR)
    store = create_kv_docstore(LocalFileStore(LOCAL_FILE_STORE_DIR))
    
    parent_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
    child_splitter = RecursiveCharacterTextSplitter(chunk_size=200, chunk_overlap=0)

    print("Initializing ParentDocumentRetriever...")
    retriever = ParentDocumentRetriever(
        vectorstore=vectorstore,
        docstore=store,
        child_splitter=child_splitter,
        parent_splitter=parent_splitter,
    )
    
    # 2. Automatically detect and purge deleted PDFs from the database
    current_files = set(f for f in os.listdir(POLICIES_DIR) if f.lower().endswith(".pdf"))
    deleted_files = []
    for filename in list(processed_state.keys()):
        if filename not in current_files:
            print(f"🗑️ Notice: '{filename}' was removed from the folder. Purging it from the database...")
            try:
                vectorstore._collection.delete(where={"source": filename})
            except Exception:
                pass
            deleted_files.append(filename)
            
    for filename in deleted_files:
        del processed_state[filename]

    # 3. STREAMING ARCHITECTURE: Process one file at a time, end-to-end
    processed_count = 0
    blacklist = ["0e5b96f97c1813bb75f6c28532c2ecc7-Paper-Conference.pdf"]
    
    for filename in os.listdir(POLICIES_DIR):
        if filename in blacklist:
            print(f"🚫 Skipping blacklisted file: {filename}")
            continue
            
        if filename.lower().endswith(".pdf"):
            filepath = os.path.join(POLICIES_DIR, filename)
            mtime = os.path.getmtime(filepath)
            
            if filename not in processed_state or processed_state[filename] < mtime:
                print(f"Processing new/updated file: {filename}")
                
                # Clean up old chunks
                try:
                    vectorstore._collection.delete(where={"source": filename})
                except Exception:
                    pass

                try:
                    # Load and Ingest ONE page at a time using PyMuPDF (C-based, Zero Memory Leak)
                    t0 = time.time()
                    print(f"  -> Ingesting {filename} using PyMuPDF and Garbage Collection...")
                    
                    pdf_doc = fitz.open(filepath)
                    
                    # Extract True PDF Internal Metadata Date
                    mod_date = None
                    raw_date = pdf_doc.metadata.get('modDate') or pdf_doc.metadata.get('creationDate')
                    if raw_date and raw_date.startswith('D:'):
                        try:
                            mod_date = datetime.strptime(raw_date[2:16], "%Y%m%d%H%M%S").strftime('%Y-%m-%d %H:%M:%S')
                        except Exception:
                            pass
                    if not mod_date:
                        mod_date = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S') # Fallback
                    # Look for associated metadata in policies folder or staging
                    meta_path = os.path.join(POLICIES_DIR, filename + ".meta.json")
                    if not os.path.exists(meta_path):
                        meta_path = os.path.join(STAGING_DIR, filename + ".meta.json")
                    source_url = "Unknown URL"
                    screenshot_path = ""
                    if os.path.exists(meta_path):
                        with open(meta_path, "r") as mf:
                            try:
                                mdata = json.load(mf)
                                source_url = mdata.get("source_url", source_url)
                                screenshot_path = mdata.get("screenshot", screenshot_path)
                            except: pass
                            
                    page_count = len(pdf_doc)
                    
                    if page_count == 0:
                        print(f"  ⚠️ WARNING: '{filename}' is empty. Skipping.")
                        continue
                    
                    for page_num in range(page_count):
                        try:
                            print(f"    - Extracting page {page_num+1}/{page_count}...")
                            page = pdf_doc.load_page(page_num)
                            text = page.get_text("text").strip()
                            
                            if text:
                                doc = Document(
                                    page_content=f"[Document: {filename}, Last Modified: {mod_date}]\n\n" + text,
                                    metadata={
                                        "source": filename, 
                                        "source_url": source_url, 
                                        "screenshot": screenshot_path, 
                                        "page": page_num
                                    }
                                )
                                print(f"    - Vectorizing page {page_num+1}/{page_count}...")
                                retriever.add_documents([doc], ids=None)
                                
                            del page
                            del text
                            gc.collect()
                        except Exception as e:
                            print(f"    ❌ ERROR on page {page_num+1}: {e}")
                            
                    pdf_doc.close()
                    del pdf_doc
                    gc.collect()
                        
                    t1 = time.time()
                    print(f"  ✅ Done processing {page_count} pages in {t1-t0:.2f} seconds!")
                    
                    # Save state so we don't re-process if a future file crashes
                    processed_state[filename] = mtime
                    save_processed_files(processed_state)
                    processed_count += 1
                    
                except Exception as e:
                    print(f"  ❌ CRITICAL ERROR loading {filename}: {e}. Skipping this corrupt file.")

    if processed_count == 0:
        print("No new documents found. Database is already up to date!")
    else:
        total_time = time.time() - start_time
        print(f"✅ Ingestion complete. Successfully streamed and vectorized {processed_count} files in {total_time:.2f} seconds!")

if __name__ == "__main__":
    ingest_data()
