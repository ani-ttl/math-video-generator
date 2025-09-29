"""
Google Drive Manager for NCERT textbooks and video storage
"""

import io
import json
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import streamlit as st

from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

class GoogleDriveManager:
    """Handles all Google Drive operations for the Math Video Creator"""
    
    def __init__(self, credentials_path: Optional[str] = None, credentials_json: Optional[str] = None):
        """
        Initialize Google Drive connection
        
        Args:
            credentials_path: Path to service account JSON file
            credentials_json: JSON string of service account credentials
        """
        self.service = None
        self.credentials = None
        
        try:
            if credentials_json:
                credentials_info = json.loads(credentials_json)
                self.credentials = Credentials.from_service_account_info(
                    credentials_info,
                    scopes=['https://www.googleapis.com/auth/drive']
                )
            elif credentials_path:
                self.credentials = Credentials.from_service_account_file(
                    credentials_path,
                    scopes=['https://www.googleapis.com/auth/drive']
                )
            else:
                raise ValueError("Either credentials_path or credentials_json must be provided")
            
            self.service = build('drive', 'v3', credentials=self.credentials)
            logger.info("Google Drive connection established successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Google Drive: {str(e)}")
            raise
    
    def test_connection(self) -> bool:
        """Test Google Drive connection"""
        try:
            # Try to list some files
            results = self.service.files().list(pageSize=1).execute()
            return True
        except Exception as e:
            logger.error(f"Drive connection test failed: {str(e)}")
            return False
    
    def list_ncert_books(self, grade_folder_id: str) -> List[Dict]:
        """
        List NCERT textbooks from a specific grade folder
        
        Args:
            grade_folder_id: Google Drive folder ID for the grade
            
        Returns:
            List of dictionaries containing file information
        """
        try:
            results = self.service.files().list(
                q=f"'{grade_folder_id}' in parents and mimeType='application/pdf'",
                fields="files(id, name, modifiedTime, size, webViewLink)",
                orderBy="name"
            ).execute()
            
            files = results.get('files', [])
            logger.info(f"Found {len(files)} NCERT books in folder {grade_folder_id}")
            return files
            
        except HttpError as e:
            logger.error(f"Error accessing NCERT books: {str(e)}")
            if e.resp.status == 404:
                st.error("Folder not found. Please check the folder ID.")
            elif e.resp.status == 403:
                st.error("Access denied. Please check folder permissions.")
            return []
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return []
    
    def download_file_content(self, file_id: str, max_size_mb: int = 50) -> Optional[bytes]:
        """
        Download file content from Google Drive
        
        Args:
            file_id: Google Drive file ID
            max_size_mb: Maximum file size to download in MB
            
        Returns:
            File content as bytes or None if failed
        """
        try:
            # Get file metadata first
            file_metadata = self.service.files().get(fileId=file_id, fields="size,name").execute()
            
            file_size = int(file_metadata.get('size', 0))
            file_name = file_metadata.get('name', 'unknown')
            
            # Check file size
            max_size_bytes = max_size_mb * 1024 * 1024
            if file_size > max_size_bytes:
                logger.warning(f"File {file_name} too large: {file_size} bytes")
                st.warning(f"File {file_name} is too large to download ({file_size / (1024*1024):.1f} MB)")
                return None
            
            # Download file
            request = self.service.files().get_media(fileId=file_id)
            file_io = io.BytesIO()
            downloader = MediaIoBaseDownload(file_io, request)
            
            done = False
            progress_bar = st.progress(0)
            
            while done is False:
                status, done = downloader.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    progress_bar.progress(progress)
            
            progress_bar.empty()
            logger.info(f"Successfully downloaded {file_name}")
            return file_io.getvalue()
            
        except HttpError as e:
            logger.error(f"Error downloading file {file_id}: {str(e)}")
            st.error(f"Failed to download file: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error downloading file: {str(e)}")
            return None
    
    def search_in_textbook(self, content: str, search_terms: List[str]) -> List[Dict]:
        """
        Search for specific terms in textbook content
        
        Args:
            content: Text content to search in
            search_terms: List of terms to search for
            
        Returns:
            List of search results with context
        """
        results = []
        lines = content.split('\n')
        
        for term in search_terms:
            for i, line in enumerate(lines):
                if term.lower() in line.lower():
                    # Get context (3 lines before and after)
                    start = max(0, i-3)
                    end = min(len(lines), i+4)
                    context = '\n'.join(lines[start:end])
                    
                    results.append({
                        'term': term,
                        'line_number': i + 1,
                        'content': line.strip(),
                        'context': context,
                        'relevance_score': self._calculate_relevance(line, term)
                    })
        
        # Sort by relevance
        results.sort(key=lambda x: x['relevance_score'], reverse=True)
        return results
    
    def _calculate_relevance(self, text: str, term: str) -> float:
        """Calculate relevance score for search results"""
        text_lower = text.lower()
        term_lower = term.lower()
        
        # Basic scoring
        score = 0.0
        
        # Exact match gets highest score
        if term_lower == text_lower.strip():
            score += 10.0
        
        # Term at beginning of line
        if text_lower.startswith(term_lower):
            score += 5.0
        
        # Multiple occurrences
        count = text_lower.count(term_lower)
        score += count * 2.0
        
        # Mathematical keywords boost
        math_keywords = ['formula', 'theorem', 'proof', 'example', 'solution', 'answer']
        for keyword in math_keywords:
            if keyword in text_lower:
                score += 1.0
        
        return score
    
    def create_output_folder(self, parent_folder_id: str, folder_name: str) -> Optional[str]:
        """
        Create a new folder for storing generated videos
        
        Args:
            parent_folder_id: Parent folder ID
            folder_name: Name for the new folder
            
        Returns:
            New folder ID or None if failed
        """
        try:
            folder_metadata = {
                'name': folder_name,
                'parents': [parent_folder_id],
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            folder = self.service.files().create(body=folder_metadata).execute()
            folder_id = folder.get('id')
            logger.info(f"Created folder {folder_name} with ID {folder_id}")
            return folder_id
            
        except HttpError as e:
            logger.error(f"Error creating folder: {str(e)}")
            return None
    
    def upload_video_package(self, 
                           video_path: str, 
                           script_path: str, 
                           output_folder_id: str, 
                           problem_name: str,
                           metadata: Dict = None) -> Optional[Dict]:
        """
        Upload generated video and script to Google Drive
        
        Args:
            video_path: Path to the generated video file
            script_path: Path to the Python script
            output_folder_id: Google Drive folder ID for outputs
            problem_name: Name identifier for the problem
            metadata: Additional metadata to store
            
        Returns:
            Dictionary with upload results or None if failed
        """
        try:
            # Create timestamped folder for this problem
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            folder_name = f"{problem_name}_{timestamp}"
            
            folder_id = self.create_output_folder(output_folder_id, folder_name)
            if not folder_id:
                return None
            
            upload_results = {'folder_id': folder_id, 'files': []}
            
            # Upload video file
            if video_path:
                video_result = self._upload_file(
                    video_path, 
                    f"{problem_name}_video.mp4", 
                    folder_id, 
                    'video/mp4'
                )
                if video_result:
                    upload_results['files'].append({
                        'type': 'video',
                        'id': video_result['id'],
                        'name': video_result['name'],
                        'webViewLink': video_result.get('webViewLink')
                    })
            
            # Upload script file
            if script_path:
                script_result = self._upload_file(
                    script_path, 
                    f"{problem_name}_script.py", 
                    folder_id, 
                    'text/plain'
                )
                if script_result:
                    upload_results['files'].append({
                        'type': 'script',
                        'id': script_result['id'],
                        'name': script_result['name'],
                        'webViewLink': script_result.get('webViewLink')
                    })
            
            # Upload metadata file
            if metadata:
                metadata_content = json.dumps(metadata, indent=2)
                metadata_io = io.BytesIO(metadata_content.encode('utf-8'))
                
                metadata_media = MediaIoBaseUpload(
                    metadata_io,
                    mimetype='application/json'
                )
                
                metadata_file_metadata = {
                    'name': f"{problem_name}_metadata.json",
                    'parents': [folder_id]
                }
                
                metadata_result = self.service.files().create(
                    body=metadata_file_metadata,
                    media_body=metadata_media,
                    fields='id,name,webViewLink'
                ).execute()
                
                upload_results['files'].append({
                    'type': 'metadata',
                    'id': metadata_result['id'],
                    'name': metadata_result['name'],
                    'webViewLink': metadata_result.get('webViewLink')
                })
            
            logger.info(f"Successfully uploaded video package to folder {folder_id}")
            return upload_results
            
        except Exception as e:
            logger.error(f"Error uploading video package: {str(e)}")
            st.error(f"Failed to upload to Google Drive: {str(e)}")
            return None
    
    def _upload_file(self, file_path: str, drive_name: str, folder_id: str, mime_type: str) -> Optional[Dict]:
        """Helper method to upload a single file"""
        try:
            with open(file_path, 'rb') as file:
                file_content = file.read()
            
            media = MediaIoBaseUpload(
                io.BytesIO(file_content),
                mimetype=mime_type
            )
            
            file_metadata = {
                'name': drive_name,
                'parents': [folder_id]
            }
            
            result = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,name,webViewLink'
            ).execute()
            
            return result
            
        except Exception as e:
            logger.error(f"Error uploading file {file_path}: {str(e)}")
            return None
    
    def list_generated_videos(self, output_folder_id: str, limit: int = 20) -> List[Dict]:
        """
        List recently generated videos
        
        Args:
            output_folder_id: Folder containing generated videos
            limit: Maximum number of videos to return
            
        Returns:
            List of video information
        """
        try:
            # Get all subfolders (each video is in its own folder)
            results = self.service.files().list(
                q=f"'{output_folder_id}' in parents and mimeType='application/vnd.google-apps.folder'",
                fields="files(id, name, modifiedTime)",
                orderBy="modifiedTime desc",
                pageSize=limit
            ).execute()
            
            folders = results.get('files', [])
            videos = []
            
            for folder in folders:
                # Get video file from each folder
                video_files = self.service.files().list(
                    q=f"'{folder['id']}' in parents and mimeType='video/mp4'",
                    fields="files(id, name, webViewLink, modifiedTime, size)"
                ).execute()
                
                if video_files.get('files'):
                    video_file = video_files['files'][0]  # Should be only one video per folder
                    videos.append({
                        'folder_name': folder['name'],
                        'video_id': video_file['id'],
                        'video_name': video_file['name'],
                        'created_time': folder['modifiedTime'],
                        'size': video_file.get('size', 0),
                        'webViewLink': video_file.get('webViewLink')
                    })
            
            return videos
            
        except Exception as e:
            logger.error(f"Error listing generated videos: {str(e)}")
            return []
    
    def get_folder_stats(self, folder_id: str) -> Dict:
        """Get statistics about a folder"""
        try:
            results = self.service.files().list(
                q=f"'{folder_id}' in parents",
                fields="files(mimeType, size)"
            ).execute()
            
            files = results.get('files', [])
            stats = {
                'total_files': len(files),
                'total_size': 0,
                'file_types': {}
            }
            
            for file in files:
                mime_type = file.get('mimeType', 'unknown')
                size = int(file.get('size', 0))
                
                stats['total_size'] += size
                
                if mime_type in stats['file_types']:
                    stats['file_types'][mime_type] += 1
                else:
                    stats['file_types'][mime_type] = 1
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting folder stats: {str(e)}")
            return {'error': str(e)}

# Utility functions for Streamlit integration
@st.cache_resource
def get_drive_manager():
    """Get cached Google Drive manager instance"""
    try:
        # Try to get credentials from Streamlit secrets first
        if hasattr(st, 'secrets') and 'google_drive' in st.secrets:
            credentials_json = st.secrets['google_drive']['credentials']
            return GoogleDriveManager(credentials_json=credentials_json)
        else:
            return None
    except Exception as e:
        logger.error(f"Error initializing drive manager: {str(e)}")
        return None

@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_ncert_books(_drive_manager, grade: int):
    """Load and cache NCERT books for a grade"""
    if not _drive_manager:
        return []
    
    try:
        folder_ids = st.secrets['google_drive']['ncert_folders']
        grade_folder_id = folder_ids.get(f'grade_{grade}')
        
        if grade_folder_id:
            return _drive_manager.list_ncert_books(grade_folder_id)
        else:
            st.warning(f"No folder ID configured for Grade {grade}")
            return []
    except Exception as e:
        st.error(f"Error loading NCERT books: {str(e)}")
        return []
