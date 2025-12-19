import re
from typing import Dict, Optional
from pathlib import Path
from backend.doc_insighter.core.ai_agent import DataExtractor
from backend.doc_insighter.core.llama_parsing import LlamaCloudDocumentParser
from backend.doc_insighter.tools.app_logger import Logger
log = Logger()


class ImportProcessProjectDocument:
    name = "SOW"
    def __init__(self, doc_specific_prompt) -> None:
        self.parser = LlamaCloudDocumentParser()
        self.extractor = DataExtractor(verbose=False)
        self.prompt = doc_specific_prompt

    def clean_text(self, text):
        if not text:
            return ""
        else:
            text = re.sub(r'[ \t]+', ' ', text)  
            text = re.sub(r'\n+', '\n', text)   
            return text.strip()
    
    def read_data(self, file_path:Path) ->Dict[str,str]:
        if not file_path.exists():
            log.log_error(f"File not found at: {file_path}")
            return {
                'status':"Failed",
                'message':"incorrect file path",
                'data': ""
            }
        else:
            base_name = file_path.stem
            log.log_info(f"Running parser for : {file_path} with base_name: {base_name}")
            extracted_text = self.parser.extract_all_text(modified_name=base_name, file_path=str(file_path))
            clean_text = self.clean_text(extracted_text)
            return {
                'status':"success",
                'message':"file parsed successfully",
                'data':clean_text}
    
    def extract_insights(self, text):
        try:
            response = self.extractor.extract_data(
                input_file=text, 
                user_requirement=self.prompt,
                file_type='text')
            log.log_info(f"{self.name} Document processed successfully")
            return {
                "status":"success",
                "message": f"{self.name}Document processed successfully",
                "data":response}
        except Exception as e:
            log.log_error(f"Failed to process {self.name} document-{e}")
            return {
                "status": "error",
                "message": str(e),
                "data": None
            }
    
    def run_doc_processor(self, file_path: Path):
        try:
            parsed_data = self.read_data(Path(file_path))
            
            if parsed_data['status'] == 'success':
                parsed_text = parsed_data['data']
                insights = self.extract_insights(parsed_text)
                
                if insights['status'] == 'success':
                    return insights['data']  
                else:
                    log.log_error(f"Insight extraction failed: {insights['message']}")
                    return None
            else:
                log.log_error(f"Document parsing failed: {parsed_data['message']}")
                return None
        
        except Exception as e:
            log.log_error(f"Error in run_doc_processor: {str(e)}")
            return None
    
# doc_processor = ImportProcessProjectDocument()
# file_path = "test_data/sample sow.pdf"
# print(doc_processor.run_doc_processor(Path(file_path)))