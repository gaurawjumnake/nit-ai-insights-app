from fastapi import APIRouter, UploadFile, HTTPException, FastAPI, File
from pydantic import BaseModel
from typing import Optional, Dict
from pathlib import Path
import os
from backend.ai_engine.ai_data_extractor import DataExtractor
from dotenv import load_dotenv
load_dotenv()


router = APIRouter(prefix="/data_extractor", tags=["SOWDataExtractor"])

class InpurRequest(BaseModel):
    file_paht:str

class OutputResponse(BaseModel):
    status: str
    message: str
    data: str = ""

@router.post("/process_sow", response_model=OutputResponse)
async def extract_data_from_sow(file: UploadFile = File(...)):
    if not file.filename.endswith('.pdf'): # type:ignore
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    try:
        # Save uploaded file temporarily
        # with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
        #     content = await file.read()
        #     tmp_file.write(content)
        #     tmp_file_path = tmp_file.name
        upload_dir = os.getenv("DOCUMENT_PATH")
        Path(upload_dir).mkdir(parents=True, exist_ok=True) #type:ignore
        file_path = os.path.join(upload_dir, file.filename) #type:ignore
        content = await file.read()
        with open(file_path, 'wb') as f:
            f.write(content)
    
        Key_points_to_extract = """
        1. Project Scope at a Glance
        2. Objectives
        3. Key Deliverables with Dates
        4. Critical Assumptions & Dependencies
        5. Any other key items which is important form project prespective and project manager should be aware of it.
        """
        extractor = DataExtractor(verbose=False)
        response = extractor.extract_data(
            input_file=file_path, 
            user_requirement=Key_points_to_extract)
        os.unlink(file_path)
        return {
            "status":"success",
            "message": "SOW processed successfully",
            "data":response}
    except Exception as e:
        if 'tmp_file_path' in locals():
            os.unlink(tmp_file_path) # type:ignore
        return {
            "status": "error",
            "message": str(e),
            "data": None
        }



