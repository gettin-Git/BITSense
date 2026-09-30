import os
import shutil

print("🚨 EMERGENCY CLEANUP INITIATED 🚨")

# 1. Nuke the corrupted ChromaDB
db_path = os.path.join("data", "db", "chroma")
if os.path.exists(db_path):
    print("-> Destroying corrupted ChromaDB...")
    shutil.rmtree(db_path, ignore_errors=True)

# 2. Wipe the ledger
ledger_path = os.path.join("data", "ingestion_state.json")
if os.path.exists(ledger_path):
    print("-> Wiping ledger...")
    with open(ledger_path, "w") as f:
        f.write("{}")

print("✅ Cleanup complete! You can safely run the RAG builder now.")
