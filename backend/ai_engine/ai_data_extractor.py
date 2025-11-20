import pandas as pd
import pymupdf4llm
import os
from crewai import Agent, Task, Crew, Process
from backend.ai_engine.tools.file_reader_tool import CustomFileReaderTool
from pathlib import Path
from backend.ai_engine.tools.llm_models import llm
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv
load_dotenv()

from backend.ai_engine.tools.app_logger import Logger
log = Logger()

class ResponseModel(BaseModel):
    message :  str

class PDFToMarkdown:
    def __init__(self, ) -> None:
        pass

    def convert(self,pdf_path):
        log.log_info(f"Converting pdf file:{pdf_path}")
        return pymupdf4llm.to_markdown(pdf_path)

class DataExtractor:
    def __init__(self, verbose: bool = True) -> None:
        self.verbose = verbose
        self.converter = PDFToMarkdown()
        self.file_reader_tool = CustomFileReaderTool()

    def summarizer_assistant(self, requirements: str, input_text: str, output_schema: Optional[ResponseModel] = None):
        summary_agent = Agent(
            role="Document Analyst",
            goal="Analyze input document or text and generate response as per user requriements.",
            backstory="""You are expert document analyzer , reader and parser.
            You are expirenced project manager who is haveing very good understanding about documnets used for IT related projects.
            You know how to handle Markdown documents or text. 
            You know how use input document or text to generate response which satisfies user requirements.""",
            llm=llm,
            tools=[self.file_reader_tool],
            verbose= self.verbose
        )
            
        summary_task = Task(
            description="""
            Task is to analyze input document or text and extract useful information as per user requirements.

            USER REQUIRMENTS:{user_requirement}
            INPUT Document/TEXT :{input_text} (input can be file or markdown text directly)

            Follow below give guidelines:
            1. Read 100 lines from input text/document. Repeat untill no more lines are left to read.
            2. Use file reader tool. 
            3. Understand the user requirements.
            4. Generate response relevant to these requirements.

            """,
            expected_output="""Response as per user requirements.""",
            output_json= output_schema,
            agent=summary_agent,
        )

        crew = Crew(
            agents=[summary_agent],
            tasks = [summary_task],
            process= Process.sequential,
            # memory=True,
            verbose=self.verbose,
        )

        result = crew.kickoff(inputs={'user_requirement':requirements,
                                      'input_text':input_text})

        return result.raw
    
    def invoke(self,user_requirement, input_content):
        if input_content:
            log.log_info("File Converted, Starting Summarizer")
        response = self.summarizer_assistant(user_requirement, input_content)
        if response:
            log.log_info(f"Process Completed, Response generated")
            return response
        else:
            log.log_debug(f"Failed to Generate response")

    def extract_data(self, input_file , user_requirement, file_type:str = 'pdf'):
        if file_type == "pdf":
            input_content = self.converter.convert(input_file)
        else:
            input_content = input_file

        response = self.invoke(user_requirement, input_content)
        return response


# if __name__ == '__main__':
#     # user_requirement = """summarize provided text in 2-3 line and generate 5 questions on text with expected answers in json format. design question such that will requrie descriptive answers"""
#     user_requirement = """Summarize provided text up to 2-3 lines."""
#     input_dir = "sample_data/New folder"
#     file_path = "test_data/Health Companion-Health Insurance Plan_GEN617.pdf"
#     pdf_path = "sample_data/Urban Mixed-Use Tower Development.pdf"
#     extractor = DataExtractor(verbose=False)
#     ans = extractor.extract_data(file_path, user_requirement)
#     print(ans)


    
        
