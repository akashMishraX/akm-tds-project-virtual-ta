from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional
import base64
from io import BytesIO
from PIL import Image
from langchain_core.messages import HumanMessage
from langchain.chains import RetrievalQA
from langchain_openai import ChatOpenAI

from langchain_community.vectorstores import Chroma

from langchain_openai import OpenAIEmbeddings
import os
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
import traceback

load_dotenv()

app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class QuestionRequest(BaseModel):
    question: str
    image: Optional[str] = None  # Base64 encoded image string

class LinkResponse(BaseModel):
    url: str
    text: str

class AnswerResponse(BaseModel):
    answer: str
    links: list[LinkResponse]

# Initialize components
# embeddings = OpenAIEmbeddings(openai_api_key=os.getenv('OPENAI_API_KEY'),
#             base_url=os.getenv("EMBEDDINGS_BASE_URL"),
#             model="text-embedding-3-small")
vectordb = Chroma(
        persist_directory="chroma_db",
        embedding_function=OpenAIEmbeddings(openai_api_key=os.getenv('OPENAI_API_KEY'),
            base_url=os.getenv("EMBEDDINGS_BASE_URL"),
            model="text-embedding-3-small"))
 
llm = ChatOpenAI( openai_api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL"),
            model="openai/gpt-3.5-turbo", temperature=0.7)
multimodal_llm = ChatOpenAI( openai_api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL"),
            model="openai/gpt-4-vision-preview", temperature=0, max_tokens=1024)
# Create retriever with MMR search type
retriever = vectordb.as_retriever(
    search_type="mmr",  # Maximal Marginal Relevance
    search_kwargs={"k": 5}
)
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
     
    chain_type="stuff",
    retriever=retriever ,
    return_source_documents=True
)
# def load_chroma():
#     # Extract if doesn't exist
#     if not os.path.exists('chroma_db'):
#         with tarfile.open('data/chroma_db.tar.gz', 'r:gz') as tar:
#             tar.extractall()
    
#     # Verify extraction
#     if not os.path.exists('chroma_db'):
#         raise RuntimeError("Failed to extract ChromaDB")
    
#     return Chroma(
#         persist_directory="chroma_db",
#         embedding_function=OpenAIEmbeddings(openai_api_key=os.getenv('OPENAI_API_KEY'),
#             base_url=os.getenv("EMBEDDINGS_BASE_URL"),
#             model="text-embedding-3-small")
    

# Singleton instance
 

def process_image(image_base64: str) -> str:
    """Extract text description from image using multimodal LLM"""
    try:
        # Decode base64 image
        image_data = base64.b64decode(image_base64)
        image = Image.open(BytesIO(image_data))
        
        # Resize if needed (to reduce token usage)
        if image.size[0] > 1024 or image.size[1] > 1024:
            image = image.resize((1024, 1024))
        
        # Convert back to base64
        buffered = BytesIO()
        image.save(buffered, format="JPEG")
        processed_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        
        # Get description from multimodal LLM
        message = HumanMessage(
            content=[
                {"type": "text", "text": "Describe this image in detail focusing on technical content relevant to data science."},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{processed_base64}"}},
            ]
        )
        response = multimodal_llm.invoke([message])
        return response.content
    except Exception as e:
        print(f"Error processing image: {e}")
        
@app.get("/")
def root():
    return {"message": "Virtual TA API is live. Try /api."}
    

@app.post("/api/")
async def answer_question( 
    
    request: QuestionRequest
#     
): 
    try:
        question = request.question
        image_base64 = request.image

        if not question and not image_base64:
            raise HTTPException(status_code=400, detail="Either question or image must be provided.")

        # If image is present, process it and append to question context
        if image_base64:
            image_desc = process_image(image_base64)
            if question:
                question = f"{question}\n\nImage context: {image_desc}"
            else:
                question = image_desc

        # Get the answer and source documents from RAG chain
        result = qa_chain({"query": question})

        # Collect links from source docs without duplicates
        seen_urls = set()
        links = []
        for doc in result.get("source_documents", []):
            url = doc.metadata.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                snippet = doc.page_content[:200].replace("\n", " ") + "..."
                links.append(LinkResponse(url=url, text=snippet))
                if len(links) >= 5:  # limit to top 2 links
                    break

        return AnswerResponse(answer=result["result"], links=links)

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    
    
    