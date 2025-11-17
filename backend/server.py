import os
import base64
import io
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from ag_ui_langgraph import add_langgraph_fastapi_endpoint 
from agent import graph, CustomLangGraphAGUIAgent

from dotenv import load_dotenv
load_dotenv()

# Ensure OpenAI API key is loaded from environment
# The ChatOpenAI in agent.py will automatically use OPENAI_API_KEY from environment
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY environment variable is required. Please set it in your .env file.")

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for processed PDFs (in production, use a database)
file_storage = {}

class FileUploadRequest(BaseModel):
    filename: str
    content: str  # base64 encoded
    thread_id: str


# add new route for health check (must be defined before langgraph endpoint)
@app.get("/health")
def health():
    """Health check."""
    return {"status": "ok"}

@app.post("/process-file")
async def process_file_endpoint(request: FileUploadRequest):
    """Process a file (PDF or Excel) and store the extracted content."""
    file_extension = os.path.splitext(request.filename)[1].lower()
    if file_extension == '.pdf':
        return await process_pdf(request)
    elif file_extension in ['.xlsx', '.xls']:
        return await process_excel(request)
    else:
        raise HTTPException(status_code=400, detail="Unsupported file type")

async def process_pdf(request: FileUploadRequest):
    """Process a PDF file and store the extracted text."""
    try:
        from pypdf import PdfReader
        from pypdf.errors import PdfReadError

        # Decode base64 content
        pdf_bytes = base64.b64decode(request.content)
        pdf_file = io.BytesIO(pdf_bytes)
        
        try:
            reader = PdfReader(pdf_file)
            
            if reader.is_encrypted:
                raise HTTPException(status_code=400, detail=f"File '{request.filename}' is encrypted and cannot be processed.")

            text_content = []
            
            for page_num, page in enumerate(reader.pages, 1):
                page_text = page.extract_text()
                if page_text:
                    text_content.append(f"--- Page {page_num} ---\n{page_text}")
            
            full_text = "\n\n".join(text_content)
            
            if not full_text.strip():
                # This could be an image-only PDF
                full_text = "The PDF contains no extractable text. It might be an image-based file."

        except PdfReadError:
            raise HTTPException(status_code=400, detail=f"File '{request.filename}' is corrupted or not a valid PDF.")
        
        # Generate a unique ID for this PDF
        file_id = str(uuid.uuid4())

        # Get thread_id from request
        thread_id = request.thread_id
        if thread_id not in file_storage:
            file_storage[thread_id] = {}
        
        # Store the extracted text
        file_storage[thread_id][file_id] = {
            "filename": request.filename,
            "text": full_text,
            "page_count": len(reader.pages),
            "file_type": "pdf"
        }
        
        return {
            "success": True,
            "file_id": file_id,
            "filename": request.filename,
            "extracted_text": full_text[:1000] + "..." if len(full_text) > 1000 else full_text,
            "page_count": len(reader.pages),
            "text_length": len(full_text),
            "file_type": "pdf"
        }
        
    except HTTPException as http_exc:
        # Re-raise HTTPException to be handled by FastAPI
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while processing '{request.filename}': {str(e)}")

async def process_excel(request: FileUploadRequest):
    """Process an Excel file and store the extracted content."""
    try:
        import pandas as pd
        
        # Decode base64 content
        excel_bytes = base64.b64decode(request.content)
        excel_file = io.BytesIO(excel_bytes)
        
        # Read Excel file - try to read all sheets
        excel_data = pd.ExcelFile(excel_file)
        sheet_names = excel_data.sheet_names
        
        text_content = []
        total_rows = 0
        
        for sheet_name in sheet_names:
            df = pd.read_excel(excel_file, sheet_name=sheet_name)
            total_rows += len(df)
            
            text_content.append(f"=== Sheet: {sheet_name} ===")
            text_content.append(f"Rows: {len(df)}, Columns: {len(df.columns)}")
            text_content.append(f"Column Names: {', '.join(df.columns.tolist())}")
            text_content.append("\nData Preview (first 10 rows):")
            text_content.append(df.head(10).to_string(index=False))
            text_content.append("\n")
        
        full_text = "\n\n".join(text_content)
        
        if not full_text.strip():
            full_text = "The Excel file appears to be empty."
        
        # Generate a unique ID for this file
        file_id = str(uuid.uuid4())
        
        # Get thread_id from request
        thread_id = request.thread_id
        if thread_id not in file_storage:
            file_storage[thread_id] = {}

        # Store the extracted text
        file_storage[thread_id][file_id] = {
            "filename": request.filename,
            "text": full_text,
            "sheet_count": len(sheet_names),
            "total_rows": total_rows,
            "file_type": "excel"
        }
        
        return {
            "success": True,
            "file_id": file_id,
            "filename": request.filename,
            "extracted_text": full_text[:1000] + "..." if len(full_text) > 1000 else full_text,
            "sheet_count": len(sheet_names),
            "total_rows": total_rows,
            "text_length": len(full_text),
            "file_type": "excel"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing Excel: {str(e)}")

@app.get("/files/{thread_id}")
async def get_files(thread_id: str):
    """Retrieve metadata for all uploaded files."""
    if thread_id not in file_storage:
        return []
        
    files_metadata = []
    for file_id, data in file_storage[thread_id].items():
        files_metadata.append({
            "fileId": file_id,
            "name": data["filename"],
            "fileType": data["file_type"],
            "pageCount": data.get("page_count"),
            "sheetCount": data.get("sheet_count"),
            "totalRows": data.get("total_rows"),
        })
    return files_metadata

@app.delete("/file/{thread_id}/{file_id}")
async def delete_file(thread_id: str, file_id: str):
    """Delete an uploaded file."""
    if thread_id not in file_storage or file_id not in file_storage[thread_id]:
        raise HTTPException(status_code=404, detail="File not found")
    del file_storage[thread_id][file_id]
    return {"status": "ok", "file_id": file_id}

@app.get("/file/{thread_id}/{file_id}")
async def get_file_content(thread_id: str, file_id: str):
    """Retrieve the extracted text for a given file ID (PDF or Excel)."""
    if thread_id not in file_storage or file_id not in file_storage[thread_id]:
        raise HTTPException(status_code=404, detail="File not found")
    
    return file_storage[thread_id][file_id]

add_langgraph_fastapi_endpoint(
  app=app,
  agent=CustomLangGraphAGUIAgent(
    name="agent_with_auth", # the name of your agent defined in langgraph.json
    description="Describe your agent here, will be used for multi-agent orchestration",
    graph=graph, # the graph object from your langgraph import
  )
)

def main():
    """Run the uvicorn server."""
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "server:app", # the path to your FastAPI file
        host="0.0.0.0",
        port=port,
        reload=True,
    )

if __name__ == "__main__":
    main()
