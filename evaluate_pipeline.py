import pandas as pd
import os
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_classic.storage import LocalFileStore, create_kv_docstore
from langchain_classic.retrievers import ParentDocumentRetriever
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import EVAL_QUESTIONS_CSV, JUDGE_MODEL, GOOGLE_API_KEY, CHROMA_DB_DIR, LOCAL_FILE_STORE_DIR, EMBEDDING_MODEL
from crew import run_query

def load_retriever():
    embeddings = GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL, google_api_key=GOOGLE_API_KEY)
    vectorstore = Chroma(collection_name="policies_child_chunks", embedding_function=embeddings, persist_directory=CHROMA_DB_DIR)
    store = create_kv_docstore(LocalFileStore(LOCAL_FILE_STORE_DIR))
    parent_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
    child_splitter = RecursiveCharacterTextSplitter(chunk_size=200, chunk_overlap=0)
    
    return ParentDocumentRetriever(
        vectorstore=vectorstore,
        docstore=store,
        child_splitter=child_splitter,
        parent_splitter=parent_splitter,
    )

def run_evaluation():
    if not os.path.exists(EVAL_QUESTIONS_CSV):
        print(f"Error: {EVAL_QUESTIONS_CSV} not found.")
        return
        
    df = pd.read_csv(EVAL_QUESTIONS_CSV)
    
    questions = df['question'].tolist()
    ground_truths = df['ground_truth'].tolist()
    
    answers = []
    contexts = []
    
    retriever = load_retriever()
    
    print("Running queries through the Crew pipeline...")
    for q in questions:
        print(f"Processing query: {q}")
        # Get answer from Crew
        answer = run_query(q)
        answers.append(answer)
        
        # Get contexts from Retriever
        docs = retriever.invoke(q)
        contexts.append([doc.page_content for doc in docs])
        
    data = {
        "question": questions,
        "answer": answers,
        "contexts": contexts,
        "ground_truth": ground_truths
    }
    
    dataset = Dataset.from_dict(data)
    
    # Initialize Judge LLM
    judge_llm = ChatGoogleGenerativeAI(model=JUDGE_MODEL, google_api_key=GOOGLE_API_KEY)
    judge_embeddings = GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL, google_api_key=GOOGLE_API_KEY)
    
    print("Running Ragas evaluation...")
    result = evaluate(
        dataset=dataset,
        metrics=[
            context_precision,
            context_recall,
            faithfulness,
            answer_relevancy,
        ],
        llm=judge_llm,
        embeddings=judge_embeddings
    )
    
    print("\n--- Evaluation Results ---")
    print(result)
    
    output_path = os.path.join(os.path.dirname(__file__), "data", "eval_results.csv")
    result.to_pandas().to_csv(output_path, index=False)
    print(f"Results saved to {output_path}")

if __name__ == "__main__":
    run_evaluation()
