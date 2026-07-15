import sys
import os

# Add current directory to path so we can import rag_pipeline
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    print("Importing rag_pipeline...")
    import rag_pipeline
    print(f"rag_pipeline imported.")
    
    print(f"KB Type: {type(rag_pipeline.KB)}")
    if isinstance(rag_pipeline.KB, list):
        print(f"KB Length: {len(rag_pipeline.KB)}")
        if len(rag_pipeline.KB) > 0:
            print(f"First Entry: {rag_pipeline.KB[0]}")
            print(f"Last Entry: {rag_pipeline.KB[-1]}")
    else:
        print(f"KB Content: {rag_pipeline.KB}")

except Exception as e:
    print(f"Error: {e}")
