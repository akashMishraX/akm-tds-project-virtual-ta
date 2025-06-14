 
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
import json
import os
from dotenv import load_dotenv
from typing import Dict, Any

load_dotenv()

class VectorStoreBuilder:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"),
                                        model="text-embedding-3-small",
                                        base_url=os.getenv("EMBEDDINGS_BASE_URL"))
        self.persist_directory = "chroma_db"
    def clean_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Convert all metadata values to ChromaDB-compatible types"""
        if not isinstance(metadata, dict):
            return {}
            
        cleaned = {}
        for key, value in metadata.items():
            # Handle None values
            if value is None:
                cleaned[key] = None
                continue
                
            # Convert lists to comma-separated strings
            if isinstance(value, list):
                cleaned[key] = ', '.join(str(item) for item in value)
                continue
                
            # Convert other complex types to strings
            if not isinstance(value, (str, int, float, bool)):
                cleaned[key] = str(value)
            else:
                cleaned[key] = value
                
        return cleaned
    
    def load_processed_data(self, input_file: str):
        """Load and clean documents and metadata from JSON file"""
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading input file: {e}")
            return [], []
        
        documents = []
        metadatas = []
        
        for item in data:
            if not isinstance(item, dict):
                continue
                
            # Get document content
            content = item.get('page_content', '')
            if not content:
                continue
                
            documents.append(content)
            
            # Clean the metadata
            metadata = item.get('metadata', {})
            cleaned_metadata = self.clean_metadata(metadata)
            metadatas.append(cleaned_metadata)
        
        return documents, metadatas
    
    def build_vector_store(self, documents: list, metadatas: list):
        """Build and persist Chroma vector store"""
        if not documents:
            print("No documents to process")
            return None
            
        print(f"Building vector store with {len(documents)} documents...")
        print("Sample metadata:", metadatas[0] if metadatas else "No metadata")
        
        try:
            vectordb = Chroma.from_texts(
                texts=documents,
                embedding=self.embeddings,
                metadatas=metadatas,
                persist_directory=self.persist_directory
            )
            vectordb.persist()
            print("✅ Vector store created successfully")
            return vectordb
        except Exception as e:
            print(f"Error creating vector store: {e}")
            return None

if __name__ == "__main__":
    builder = VectorStoreBuilder()
    
    # Load and process data
    input_file = 'processed_data/tds_combined.json'
    print(f"Loading data from {input_file}...")
    documents, metadatas = builder.load_processed_data(input_file)
    
    if not documents:
        print("No documents loaded - check your input file")
    else:
        vectordb = builder.build_vector_store(documents, metadatas)
        
        if vectordb:
            retriever = vectordb.as_retriever(
                        search_type="mmr", 
                        search_kwargs={"k": 1, "fetch_k": 10})
            sample_query = "What is data science?"
            print(f"\nTesting with MMR query: '{sample_query}'")
            results = retriever.get_relevant_documents(sample_query)
            if results:
                print("Sample result (MMR):")
                print(results[0].page_content[:200] + "...")
                print("Metadata:", results[0].metadata)
            else:
                print("No results found for test query (MMR)")

             
    

            
     
         
    

 