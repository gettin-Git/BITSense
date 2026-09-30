import os
import shutil

def clear_all_data(delete_student_data: bool = False):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "data")
    
    # 1. Clear staging directory (all scavenged PDFs, screenshots, meta.json)
    staging_dir = os.path.join(data_dir, "staging")
    if os.path.exists(staging_dir):
        count = 0
        for item in os.listdir(staging_dir):
            item_path = os.path.join(staging_dir, item)
            try:
                if os.path.isfile(item_path) or os.path.islink(item_path):
                    os.remove(item_path)
                    count += 1
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                    count += 1
            except Exception as e:
                print(f"Error removing {item_path}: {e}")
        print(f"✅ Cleared staging directory: removed {count} files/folders from {staging_dir}")
    else:
        os.makedirs(staging_dir, exist_ok=True)

    # 2. Clear policies directory (all active PDFs)
    policies_dir = os.path.join(data_dir, "policies")
    if os.path.exists(policies_dir):
        count = 0
        for item in os.listdir(policies_dir):
            item_path = os.path.join(policies_dir, item)
            try:
                if os.path.isfile(item_path) or os.path.islink(item_path):
                    os.remove(item_path)
                    count += 1
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                    count += 1
            except Exception as e:
                print(f"Error removing {item_path}: {e}")
        print(f"✅ Cleared policies directory: removed {count} files/folders from {policies_dir}")
    else:
        os.makedirs(policies_dir, exist_ok=True)

    # 3. Clear Chroma Vector DB and Key-Value Store
    db_dir = os.path.join(data_dir, "db")
    if os.path.exists(db_dir):
        shutil.rmtree(db_dir, ignore_errors=True)
        os.makedirs(db_dir, exist_ok=True)
        print(f"✅ Wiped Chroma Vector Database and Store: {db_dir}")

    lfs_dir = os.path.join(data_dir, "local_file_store")
    if os.path.exists(lfs_dir):
        shutil.rmtree(lfs_dir, ignore_errors=True)
        print(f"✅ Wiped Parent Document Store: {lfs_dir}")

    # 4. Clear state & history tracking files
    state_file = os.path.join(data_dir, "ingestion_state.json")
    if os.path.exists(state_file):
        os.remove(state_file)
        print(f"✅ Deleted Ingestion Tracker File: {state_file}")

    history_file = os.path.join(data_dir, "scavenged_history.json")
    if os.path.exists(history_file):
        os.remove(history_file)
        print(f"✅ Deleted Scavenger Crawler History File: {history_file}")

    eval_results = os.path.join(data_dir, "eval_results.csv")
    if os.path.exists(eval_results):
        os.remove(eval_results)
        print(f"✅ Deleted Evaluation Results File: {eval_results}")

    # 5. Handle student records if requested
    student_csv = os.path.join(data_dir, "student_records.csv")
    if delete_student_data and os.path.exists(student_csv):
        os.remove(student_csv)
        print(f"✅ Deleted Student Records CSV: {student_csv}")

if __name__ == "__main__":
    print("🧹 Scrubbing all data, PDFs, vector DBs, and crawlers history...")
    clear_all_data(delete_student_data=True)
    print("--------------------------------------------------")
    print("🎉 All data has been completely wiped! Clean state restored.")

