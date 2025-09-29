import streamlit as st
import os
import tempfile
import subprocess
import sys
from pathlib import Path
import json
import time
import hashlib
from datetime import datetime
import zipfile
import io

# Google Drive integration
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

# Sarvam AI
from sarvamai import SarvamAI
from sarvamai.play import save

# Additional imports for math processing
import re
import numpy as np

class GoogleDriveManager:
    """Handles Google Drive operations for NCERT textbooks and video storage"""
    
    def __init__(self, credentials_path=None, credentials_json=None):
        """Initialize with service account credentials"""
        if credentials_json:
            # Use credentials from Streamlit secrets
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
    
    def list_ncert_books(self, grade_folder_id):
        """List NCERT textbooks from a specific grade folder"""
        try:
            results = self.service.files().list(
                q=f"'{grade_folder_id}' in parents and mimeType='application/pdf'",
                fields="files(id, name, modifiedTime)"
            ).execute()
            
            return results.get('files', [])
        except Exception as e:
            st.error(f"Error accessing NCERT books: {str(e)}")
            return []
    
    def search_topics_in_textbook(self, textbook_content, topic_query):
        """Search for specific topics in textbook content"""
        # This is a simplified search - you might want to use more sophisticated NLP
        matches = []
        lines = textbook_content.split('\n')
        
        for i, line in enumerate(lines):
            if topic_query.lower() in line.lower():
                # Get context (3 lines before and after)
                start = max(0, i-3)
                end = min(len(lines), i+4)
                context = '\n'.join(lines[start:end])
                matches.append({
                    'line_number': i,
                    'content': line,
                    'context': context
                })
        
        return matches
    
    def upload_video(self, video_path, script_path, output_folder_id, problem_name):
        """Upload generated video and script to Google Drive"""
        try:
            # Create folder for this problem
            folder_name = f"{problem_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            folder_metadata = {
                'name': folder_name,
                'parents': [output_folder_id],
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            folder = self.service.files().create(body=folder_metadata).execute()
            folder_id = folder.get('id')
            
            # Upload video
            video_metadata = {'name': f"{problem_name}_video.mp4", 'parents': [folder_id]}
            video_media = MediaIoBaseUpload(
                io.BytesIO(open(video_path, 'rb').read()),
                mimetype='video/mp4'
            )
            video_file = self.service.files().create(
                body=video_metadata,
                media_body=video_media
            ).execute()
            
            # Upload script
            script_metadata = {'name': f"{problem_name}_script.py", 'parents': [folder_id]}
            script_media = MediaIoBaseUpload(
                io.BytesIO(open(script_path, 'rb').read()),
                mimetype='text/plain'
            )
            script_file = self.service.files().create(
                body=script_metadata,
                media_body=script_media
            ).execute()
            
            return {
                'folder_id': folder_id,
                'video_id': video_file.get('id'),
                'script_id': script_file.get('id')
            }
            
        except Exception as e:
            st.error(f"Error uploading to Google Drive: {str(e)}")
            return None

class MathVideoGenerator:
    """Core video generation logic"""
    
    def __init__(self, sarvam_api_key):
        self.sarvam_api_key = sarvam_api_key
        self.client = SarvamAI(api_subscription_key=sarvam_api_key) if sarvam_api_key else None
        
    def create_manim_script(self, problem_data):
        """Generate Manim script based on problem data"""
        
        # Extract problem details
        problem_statement = problem_data['statement']
        grade = problem_data['grade']
        topic = problem_data['topic']
        solution_steps = problem_data['solution_steps']
        answer = problem_data['answer']
        
        # Generate unique class name
        class_name = f"{topic.replace(' ', '')}Problem{int(time.time())}"
        
        # Create audio content
        audio_content = self.generate_audio_content(problem_data)
        
        # Generate script based on topic
        if topic.lower() in ['algebra', 'linear equations', 'quadratic equations']:
            script = self.generate_algebra_script(class_name, problem_data, audio_content)
        elif topic.lower() in ['geometry', 'triangles', 'circles']:
            script = self.generate_geometry_script(class_name, problem_data, audio_content)
        elif topic.lower() in ['coordinate geometry']:
            script = self.generate_coordinate_geometry_script(class_name, problem_data, audio_content)
        elif topic.lower() in ['trigonometry']:
            script = self.generate_trigonometry_script(class_name, problem_data, audio_content)
        elif topic.lower() in ['probability']:
            script = self.generate_probability_script(class_name, problem_data, audio_content)
        elif topic.lower() in ['statistics']:
            script = self.generate_statistics_script(class_name, problem_data, audio_content)
        else:
            script = self.generate_generic_script(class_name, problem_data, audio_content)
        
        return script, class_name
    
    def generate_audio_content(self, problem_data):
        """Generate Hindi-English mixed audio content"""
        timestamp = str(int(time.time()))
        topic = problem_data['topic']
        
        return {
            f"intro_{timestamp}": f"नमस्ते बच्चों! चलिए {topic} का एक प्रश्न हल करें।",
            f"title_{timestamp}": f"आज का topic है - {topic}। इसमें हम step by step solution देखेंगे।",
            f"problem_{timestamp}": f"Problem statement है: {problem_data['statement']}",
            f"solution_start_{timestamp}": "अब इसका solution देखते हैं step by step।",
            f"answer_{timestamp}": f"तो final answer है {problem_data['answer']}।",
            f"conclusion_{timestamp}": f"बहुत अच्छे बच्चों! आज आपने सीखा कि {topic} के problems कैसे solve करते हैं।"
        }
    
    def generate_algebra_script(self, class_name, problem_data, audio_content):
        """Generate Manim script for algebra problems"""
        
        script = f'''from manim import *
from sarvamai import SarvamAI
from sarvamai.play import save
import os
import shutil
import time
import hashlib

class {class_name}(Scene):
    def __init__(self):
        super().__init__()
        self.SARVAM_API_KEY = "{self.sarvam_api_key}"
        self.client = SarvamAI(api_subscription_key=self.SARVAM_API_KEY) if self.SARVAM_API_KEY else None
        
        # Color scheme
        self.TEXT_COLOR = BLACK
        self.HIGHLIGHT_COLOR = BLUE
        self.STEP_COLOR = BLUE_D
        self.ANSWER_COLOR = GREEN_D
        self.FORMULA_COLOR = PURPLE
        
        # Unique session ID
        self.session_id = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
        self.audio_dir = f"audio_{{self.session_id}}"
        
        self.clean_audio_cache()
        self.create_all_audio_files()
    
    def clean_audio_cache(self):
        """Clean old audio files"""
        if os.path.exists(self.audio_dir):
            shutil.rmtree(self.audio_dir)
        os.makedirs(self.audio_dir, exist_ok=True)
    
    def create_all_audio_files(self):
        """Create all audio files using Sarvam AI"""
        if not self.client:
            return
            
        audio_content = {audio_content}
        
        self.audio_durations = {{}}
        
        for audio_name, text in audio_content.items():
            try:
                audio_data = self.client.text_to_speech(
                    text=text,
                    target_language_code="hi-IN",
                    speaker="anushka",
                    pitch=0.1,
                    pace=0.95,
                    loudness=1.2,
                    speech_sample_rate=22050,
                    enable_preprocessing=True,
                    model="bulbul:v1"
                )
                
                audio_path = os.path.join(self.audio_dir, f"{{audio_name}}.wav")
                save(audio_data.audios[0], audio_path)
                
                # Estimate duration (rough calculation)
                word_count = len(text.split())
                self.audio_durations[audio_name] = max(2.0, word_count * 0.4)
                
            except Exception as e:
                print(f"Error creating audio {{audio_name}}: {{e}}")
                self.audio_durations[audio_name] = 3.0
    
    def play_audio_and_wait(self, audio_name, duration):
        """Play audio and wait for specified duration"""
        audio_path = os.path.join(self.audio_dir, f"{{audio_name}}.wav")
        if os.path.exists(audio_path):
            self.add_sound(audio_path, gain=0)
        self.wait(duration)
        self.wait(0.8)  # Buffer time
    
    def construct(self):
        # Set background
        self.camera.background_color = WHITE
        
        # Introduction
        intro_text = Text("Math Problem Solver", font="Arial Unicode MS", color=self.TEXT_COLOR, font_size=36)
        self.play(Write(intro_text), run_time=1)
        self.wait(0.5)
        
        # Get first audio key
        intro_key = list(self.audio_durations.keys())[0]
        self.play_audio_and_wait(intro_key, self.audio_durations[intro_key])
        
        # Problem statement
        problem_text = Text(
            "{problem_data['statement']}", 
            font="Arial Unicode MS", 
            color=self.TEXT_COLOR, 
            font_size=24
        ).scale(0.8)
        
        self.play(Transform(intro_text, problem_text), run_time=1)
        self.wait(0.5)
        
        # Play problem audio
        problem_key = [k for k in self.audio_durations.keys() if 'problem' in k][0]
        self.play_audio_and_wait(problem_key, self.audio_durations[problem_key])
        
        # Solution steps
        steps_group = VGroup()
        for i, step in enumerate([{step.replace('"', '\\"') for step in problem_data['solution_steps']}]):
            step_text = Text(
                f"Step {{i+1}}: {{step}}", 
                font="Arial Unicode MS", 
                color=self.STEP_COLOR, 
                font_size=20
            )
            steps_group.add(step_text)
        
        steps_group.arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        steps_group.move_to(ORIGIN)
        
        self.play(FadeOut(intro_text))
        
        for step in steps_group:
            self.play(Write(step), run_time=1)
            self.wait(0.5)
            self.wait(2.0)  # Time for explanation
        
        # Final answer
        answer_text = Text(
            f"Answer: {problem_data['answer']}", 
            font="Arial Unicode MS", 
            color=self.ANSWER_COLOR, 
            font_size=28
        )
        answer_box = SurroundingRectangle(answer_text, color=self.ANSWER_COLOR, buff=0.1)
        
        self.play(FadeOut(steps_group))
        self.play(Write(answer_text), run_time=1)
        self.play(Create(answer_box), run_time=0.5)
        
        # Answer audio
        answer_key = [k for k in self.audio_durations.keys() if 'answer' in k][0]
        self.play_audio_and_wait(answer_key, self.audio_durations[answer_key])
        
        # Conclusion
        conclusion_key = [k for k in self.audio_durations.keys() if 'conclusion' in k][0]
        self.play_audio_and_wait(conclusion_key, self.audio_durations[conclusion_key])
        
        self.wait(2.0)  # Final buffer
'''
        
        return script
    
    def generate_geometry_script(self, class_name, problem_data, audio_content):
        """Generate Manim script for geometry problems"""
        # Similar structure but with geometric shapes and visual elements
        # Implementation would be similar to algebra but with Polygon, Circle, etc.
        return self.generate_algebra_script(class_name, problem_data, audio_content)  # Placeholder
    
    def generate_coordinate_geometry_script(self, class_name, problem_data, audio_content):
        """Generate script for coordinate geometry with axes and points"""
        return self.generate_algebra_script(class_name, problem_data, audio_content)  # Placeholder
    
    def generate_trigonometry_script(self, class_name, problem_data, audio_content):
        """Generate script for trigonometry with triangles and ratios"""
        return self.generate_algebra_script(class_name, problem_data, audio_content)  # Placeholder
    
    def generate_probability_script(self, class_name, problem_data, audio_content):
        """Generate script for probability with visual representations"""
        return self.generate_algebra_script(class_name, problem_data, audio_content)  # Placeholder
    
    def generate_statistics_script(self, class_name, problem_data, audio_content):
        """Generate script for statistics with charts and graphs"""
        return self.generate_algebra_script(class_name, problem_data, audio_content)  # Placeholder
    
    def generate_generic_script(self, class_name, problem_data, audio_content):
        """Generate generic script for other topics"""
        return self.generate_algebra_script(class_name, problem_data, audio_content)
    
    def render_video(self, script_content, class_name):
        """Render the Manim video"""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Write script to file
            script_path = os.path.join(temp_dir, f"{class_name}.py")
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script_content)
            
            try:
                # Run Manim
                cmd = [
                    sys.executable, "-m", "manim",
                    "-pqh", script_path, class_name,
                    "--flush_cache",
                    f"--media_dir={temp_dir}/media"
                ]
                
                result = subprocess.run(
                    cmd,
                    cwd=temp_dir,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout
                )
                
                if result.returncode != 0:
                    return None, f"Manim error: {result.stderr}"
                
                # Find the generated video
                video_dir = os.path.join(temp_dir, "media", "videos", class_name, "1080p60")
                if os.path.exists(video_dir):
                    for file in os.listdir(video_dir):
                        if file.endswith('.mp4'):
                            video_path = os.path.join(video_dir, file)
                            return video_path, script_path
                
                return None, "Video file not found"
                
            except subprocess.TimeoutExpired:
                return None, "Video rendering timed out"
            except Exception as e:
                return None, f"Rendering error: {str(e)}"

def main():
    st.set_page_config(
        page_title="Math Video Creator",
        page_icon="🎬",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("🎬 Math Video Creator")
    st.markdown("Create educational math videos using Manim and Sarvam AI")
    
    # Sidebar for configuration
    st.sidebar.header("Configuration")
    
    # API Keys
    sarvam_api_key = st.sidebar.text_input(
        "Sarvam AI API Key", 
        type="password",
        help="Enter your Sarvam AI API key for Hindi narration"
    )
    
    # Google Drive configuration
    st.sidebar.subheader("Google Drive Setup")
    
    use_secrets = st.sidebar.checkbox("Use Streamlit Secrets for Google Drive", value=True)
    
    if use_secrets:
        try:
            drive_credentials = st.secrets["google_drive"]["credentials"]
            ncert_folder_ids = st.secrets["google_drive"]["ncert_folders"]
            output_folder_id = st.secrets["google_drive"]["output_folder"]
            
            drive_manager = GoogleDriveManager(credentials_json=drive_credentials)
            st.sidebar.success("✅ Google Drive connected via secrets")
        except Exception as e:
            st.sidebar.error(f"❌ Error with Streamlit secrets: {str(e)}")
            drive_manager = None
    else:
        credentials_file = st.sidebar.file_uploader(
            "Upload Google Drive Service Account JSON",
            type=['json']
        )
        
        if credentials_file:
            try:
                credentials_content = credentials_file.read().decode('utf-8')
                drive_manager = GoogleDriveManager(credentials_json=credentials_content)
                st.sidebar.success("✅ Google Drive connected")
            except Exception as e:
                st.sidebar.error(f"❌ Error connecting to Google Drive: {str(e)}")
                drive_manager = None
        else:
            drive_manager = None
    
    # Main interface
    tab1, tab2, tab3 = st.tabs(["📝 Create Problem", "📚 Browse NCERT", "🎥 Generated Videos"])
    
    with tab1:
        st.header("Create Math Problem Video")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Problem input form
            with st.form("problem_form"):
                grade = st.selectbox("Grade", options=list(range(6, 11)), index=2)
                
                topic = st.selectbox(
                    "Topic",
                    options=[
                        "Algebra", "Linear Equations", "Quadratic Equations",
                        "Geometry", "Triangles", "Circles",
                        "Coordinate Geometry", "Trigonometry",
                        "Probability", "Statistics", "Arithmetic"
                    ]
                )
                
                problem_statement = st.text_area(
                    "Problem Statement",
                    placeholder="Enter the math problem here...",
                    height=100
                )
                
                solution_steps = st.text_area(
                    "Solution Steps (one per line)",
                    placeholder="Step 1: ...\nStep 2: ...\nStep 3: ...",
                    height=150
                )
                
                answer = st.text_input("Final Answer")
                
                submit_button = st.form_submit_button("Generate Video", type="primary")
        
        with col2:
            st.subheader("Video Preview")
            if st.session_state.get('generated_video'):
                st.video(st.session_state.generated_video)
            else:
                st.info("Video will appear here after generation")
        
        if submit_button and sarvam_api_key:
            if not all([problem_statement, solution_steps, answer]):
                st.error("Please fill in all fields")
            else:
                # Prepare problem data
                problem_data = {
                    'statement': problem_statement,
                    'grade': grade,
                    'topic': topic,
                    'solution_steps': solution_steps.strip().split('\n'),
                    'answer': answer
                }
                
                # Generate video
                with st.spinner("Generating video... This may take a few minutes."):
                    generator = MathVideoGenerator(sarvam_api_key)
                    
                    # Create script
                    script_content, class_name = generator.create_manim_script(problem_data)
                    
                    # Show script preview
                    with st.expander("Generated Python Script"):
                        st.code(script_content, language='python')
                    
                    # Render video
                    video_path, script_path = generator.render_video(script_content, class_name)
                    
                    if video_path and os.path.exists(video_path):
                        # Read video file
                        with open(video_path, 'rb') as video_file:
                            video_bytes = video_file.read()
                        
                        st.session_state.generated_video = video_bytes
                        
                        # Display video
                        st.success("✅ Video generated successfully!")
                        st.video(video_bytes)
                        
                        # Download buttons
                        col1, col2 = st.columns(2)
                        with col1:
                            st.download_button(
                                "📥 Download Video",
                                data=video_bytes,
                                file_name=f"{class_name}.mp4",
                                mime="video/mp4"
                            )
                        
                        with col2:
                            if script_path and os.path.exists(script_path):
                                with open(script_path, 'r', encoding='utf-8') as f:
                                    script_bytes = f.read().encode('utf-8')
                                
                                st.download_button(
                                    "📥 Download Script",
                                    data=script_bytes,
                                    file_name=f"{class_name}.py",
                                    mime="text/plain"
                                )
                        
                        # Upload to Google Drive
                        if drive_manager and st.button("📤 Upload to Google Drive"):
                            with st.spinner("Uploading to Google Drive..."):
                                result = drive_manager.upload_video(
                                    video_path, script_path, output_folder_id, class_name
                                )
                                
                                if result:
                                    st.success("✅ Uploaded to Google Drive successfully!")
                                    st.json(result)
                    else:
                        st.error("❌ Failed to generate video. Please check your inputs and try again.")
        
        elif submit_button and not sarvam_api_key:
            st.error("Please enter your Sarvam AI API key")
    
    with tab2:
        st.header("Browse NCERT Textbooks")
        
        if drive_manager:
            grade_selection = st.selectbox("Select Grade", options=list(range(6, 11)))
            
            # This would require folder IDs for each grade in your Google Drive
            if st.button("Load Textbooks"):
                st.info("NCERT textbook browsing feature - implementation depends on your Drive structure")
        else:
            st.warning("Please configure Google Drive access first")
    
    with tab3:
        st.header("Generated Videos")
        st.info("Video history and management - to be implemented based on your Drive structure")

if __name__ == "__main__":
    main()
