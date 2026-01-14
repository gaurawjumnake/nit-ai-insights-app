import os
import re  # <--- Added regex module
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

PROJECT_DOCUMENT_DIR = Path(os.getenv("PROJECT_DOCUMENT_DIR", "uploaded_docs/project_docs"))

class ProjectFileService:
    
    @staticmethod
    def get_project_files(project_id: str, category: str) -> List[Dict[str, Any]]:
        project_dir = PROJECT_DOCUMENT_DIR / str(project_id)

        if not project_dir.exists():
            return []

        files_list = []
        
        # We want to match "WSR_" either at the start OR after a timestamp (underscore)
        # Regex explanation:
        # (?i)  -> Case insensitive flag
        # _?    -> Optional underscore at the start (in case timestamp is missing)
        # category -> The category name (e.g., wsr)
        # _     -> Must be followed by an underscore
        category_pattern = re.compile(f"(?i)(^|_{re.escape(category)})_")

        try:
            for entry in project_dir.iterdir():
                if entry.is_file():
                    filename = entry.name
                    
                    # 1. SEARCH: Check if the category exists in the filename
                    # This finds "WSR_" inside "20260109_170753_WSR_Report.pdf"
                    match = category_pattern.search(filename)
                    
                    if match:
                        # Get Stats
                        stats = entry.stat()
                        upload_time = datetime.fromtimestamp(stats.st_mtime)
                        size_kb = stats.st_size / 1024

                        # 2. CLEAN DISPLAY NAME
                        # We want to remove the Timestamp and the Category prefix
                        # Logic: Find where the category ends and take everything after it
                        
                        # match.end() gives the index where "WSR_" ends.
                        # We slice the string from that point onward.
                        clean_display_name = filename[match.end():]

                        files_list.append({
                            "file_name": filename,          # Original (for download)
                            "display_name": clean_display_name, # Clean (for UI)
                            "size": f"{size_kb:.2f} KB",
                            "upload_date": upload_time,
                            "upload_date_str": upload_time.strftime("%Y-%m-%d %H:%M:%S")
                        })
                        
        except Exception as e:
            print(f"Error scanning directory {project_dir}: {e}")
            return []

        files_list.sort(key=lambda x: x['upload_date'], reverse=True)

        return files_list

    @staticmethod
    def delete_project_file(project_id: str, filename: str) -> bool:
        project_dir = PROJECT_DOCUMENT_DIR / str(project_id)
        if not project_dir.exists():
            return False
            
        file_path = project_dir / filename
        if file_path.exists() and file_path.is_file():
            try:
                os.remove(file_path)
                return True
            except Exception as e:
                print(f"Error deleting file {file_path}: {e}")
                return False
        return False