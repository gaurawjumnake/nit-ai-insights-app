import os
import urllib.parse
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

class AbstractDocScanner(ABC):
    """
    Abstract Base Class. 
    Enforces that any scanner must accept a directory/mount_point 
    and implement a 'scan' method.
    """
    def __init__(self, directory: Path, mount_point: str):
        self.directory = directory
        self.mount_point = mount_point

    @abstractmethod
    def scan(self) -> List[Dict[str, Any]]:
        """Abstract method that must be implemented by child classes."""
        pass

    def _format_file_stats(self, path: Path) -> Dict[str, Any]:
        """
        A shared helper method to format dates, sizes, and URLs.
        This makes the code dynamic and DRY (Don't Repeat Yourself).
        """
        stats = path.stat()
        
        # Format Size
        size_kb = stats.st_size / 1024
        size_str = f"{size_kb:.2f} KB"
        
        # Format Date
        upload_time = datetime.fromtimestamp(stats.st_mtime)
        date_str = upload_time.strftime("%Y-%m-%d %H:%M:%S")
        
        # Format URL (Handle spaces safely)
        safe_filename = urllib.parse.quote(path.name)
        clean_mount = self.mount_point.rstrip("/")
        download_url = f"{clean_mount}/{safe_filename}"

        return {
            "file_name": path.name,
            "file_type": path.suffix.lower(),
            "file_size": size_str,
            "upload_date": date_str,
            "download_url": download_url
        }

class ProjectFileScanner(AbstractDocScanner):
    """
    Specific implementation that filters for Excel and CSV files.
    """
    def scan(self) -> List[Dict[str, Any]]:
        files_data = []

        # Safety check: Create directory if missing
        if not self.directory.exists():
            try:
                self.directory.mkdir(parents=True, exist_ok=True)
            except OSError:
                return []

        # Define allowed extensions
        ALLOWED_EXTENSIONS = {'.xlsx', '.xls', '.csv'}

        # Iterate through the dynamic directory
        for path in self.directory.iterdir():
            if path.is_file() and path.suffix.lower() in ALLOWED_EXTENSIONS:
                
                # Use the helper from the Abstract Parent
                file_info = self._format_file_stats(path)
                files_data.append(file_info)

        # Sort: Newest files first
        files_data.sort(key=lambda x: x['upload_date'], reverse=True)
        
        return files_data
    
