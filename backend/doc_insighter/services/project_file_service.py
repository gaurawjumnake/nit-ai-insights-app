import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Ensure this matches your env variable loading
PROJECT_DOCUMENT_DIR = Path(os.getenv("PROJECT_DOCUMENT_DIR", "uploaded_docs/project_docs"))

class ProjectFileService:
    
    @staticmethod
    def get_project_files(project_id: str, category: str) -> List[Dict[str, Any]]:
        """
        Scans: PROJECT_DOCUMENT_DIR / project_id
        Filters: Files starting with "{category}_"
        Returns: List sorted by newest first
        """
        # 1. Define the path (ID based only)
        project_dir = PROJECT_DOCUMENT_DIR / str(project_id)

        # 2. Safety Check: If folder doesn't exist, return empty list immediately
        if not project_dir.exists():
            return []

        files_list = []
        
        # 3. Define the prefix to look for (e.g., "wsr_", "sow_")
        # We use lower() to make it case-insensitive
        search_prefix = f"{category.lower()}_"

        try:
            for entry in project_dir.iterdir():
                if entry.is_file():
                    filename = entry.name
                    
                    # 4. Filter: Does this file belong to the requested tab?
                    # We check if "WSR_Report.xlsx" starts with "wsr_"
                    if filename.lower().startswith(search_prefix):
                        
                        # Get Stats
                        stats = entry.stat()
                        upload_time = datetime.fromtimestamp(stats.st_mtime)
                        size_kb = stats.st_size / 1024

                        # 5. Clean up the name for display
                        # If file is "WSR_Week1.xlsx", display_name becomes "Week1.xlsx"
                        display_name = filename[len(search_prefix):]
                        
                        # Handle case where user uploaded "WSR_Week1.xlsx" but logic added prefix again
                        # resulting in WSR_WSR_Week1.xlsx (just a safeguard)
                        if display_name.lower().startswith(search_prefix): 
                             display_name = display_name[len(search_prefix):]

                        files_list.append({
                            "file_name": filename,          # Actual name on disk (needed for download)
                            "display_name": display_name,   # Clean name for UI
                            "size": f"{size_kb:.2f} KB",
                            "upload_date": upload_time,     # Obj for sorting
                            "upload_date_str": upload_time.strftime("%Y-%m-%d %H:%M:%S")
                        })
                        
        except Exception as e:
            # Log error if needed, but return empty list to avoid breaking UI
            print(f"Error scanning directory {project_dir}: {e}")
            return []

        # 6. Sort by Newest First
        files_list.sort(key=lambda x: x['upload_date'], reverse=True)

        return files_list