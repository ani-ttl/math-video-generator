"""
Video Generator using Manim for Math Problems
"""

import os
import sys
import tempfile
import subprocess
import time
import hashlib
import logging
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import json
import shutil

import streamlit as st
from sarvamai import SarvamAI
from sarvamai.play import save

logger = logging.getLogger(__name__)

class MathVideoGenerator:
    """Generates educational math videos using Manim and Sarvam AI"""
    
    def __init__(self, sarvam_api_key: str):
        """
        Initialize video generator
        
        Args:
            sarvam_api_key: Sarvam AI API key for Hindi TTS
        """
        self.sarvam_api_key = sarvam_api_key
        self.client = SarvamAI(api_subscription_key=sarvam_api_key) if sarvam_api_key else None
        
        # Template configurations
        self.templates_dir = Path(__file__).parent.parent / "templates"
        self.color_scheme = {
            'TEXT_COLOR': 'BLACK',
            'HIGHLIGHT_COLOR': 'BLUE',
            'STEP_COLOR': 'BLUE_D',
            'POINT_COLOR': 'RED',
            'LINE_COLOR': 'GREEN',
            'ANSWER_COLOR': 'GREEN_D',
            'FORMULA_COLOR': 'PURPLE',
            'DATA_COLOR': 'ORANGE'
        }
        
        # Audio settings
        self.audio_config = {
            'target_language_code': 'hi-IN',
            'speaker': 'anushka',
            'pitch': 0.1,
            'pace': 0.95,
            'loudness': 1.2,
            'speech_sample_rate': 22050,
            'enable_preprocessing': True,
            'model': 'bulbul:v1'
        }
    
    def test_sarvam_connection(self) -> bool:
        """Test Sarvam AI connection"""
        if not self.client:
            return False
        
        try:
            # Test with a simple phrase
            test_text = "नमस्ते, यह एक test है।"
            response = self.client.text_to_speech(
                text=test_text,
                **self.audio_config
            )
            return len(response.audios) > 0
        except Exception as e:
            logger.error(f"Sarvam connection test failed: {str(e)}")
            return False
    
    def generate_audio_content(self, problem_data: Dict) -> Dict[str, str]:
        """
        Generate Hindi-English mixed narration content
        
        Args:
            problem_data: Dictionary containing problem details
            
        Returns:
            Dictionary mapping audio keys to narration text
        """
        timestamp = str(int(time.time()))
        topic = problem_data.get('topic', 'Math')
        grade = problem_data.get('grade', 8)
        problem_statement = problem_data.get('statement', '')
        answer = problem_data.get('answer', '')
        
        # Generate natural Hindi-English mixed content
        audio_content = {
            f"intro_{timestamp}": f"नमस्ते बच्चों! चलिए Grade {grade} का {topic} का एक प्रश्न हल करें।",
            f"title_{timestamp}": f"आज का topic है - {topic}। इसमें हम step by step solution देखेंगे।",
            f"problem_{timestamp}": f"हमारा problem statement है: {problem_statement}",
            f"solution_start_{timestamp}": "अब इसका solution देखते हैं step by step। ध्यान से follow करें।",
            f"answer_{timestamp}": f"तो हमारा final answer है {answer}। यह correct answer है।",
            f"conclusion_{timestamp}": f"बहुत अच्छे बच्चों! आज आपने सीखा कि {topic} के problems कैसे solve करते हैं। Practice करते रहें!"
        }
        
        # Add step-specific narrations
        solution_steps = problem_data.get('solution_steps', [])
        for i, step in enumerate(solution_steps):
            step_key = f"step_{i+1}_{timestamp}"
            if topic.lower() in ['algebra', 'linear equations']:
                audio_content[step_key] = f"Step {i+1}: {step}। यहाँ हमने equation को simplify किया।"
            elif topic.lower() in ['geometry', 'triangles']:
                audio_content[step_key] = f"Step {i+1}: {step}। geometric properties का use करके।"
            elif topic.lower() == 'trigonometry':
                audio_content[step_key] = f"Step {i+1}: {step}। trigonometric ratio use करके।"
            else:
                audio_content[step_key] = f"Step {i+1}: {step}। carefully observe करें।"
        
        return audio_content
    
    def create_audio_files(self, audio_content: Dict[str, str], audio_dir: str) -> Dict[str, float]:
        """
        Create all audio files using Sarvam AI
        
        Args:
            audio_content: Dictionary of audio content
            audio_dir: Directory to save audio files
            
        Returns:
            Dictionary mapping audio keys to durations
        """
        if not self.client:
            logger.warning("Sarvam AI client not initialized")
            # Return estimated durations for testing
            return {key: max(2.0, len(text.split()) * 0.4) for key, text in audio_content.items()}
        
        audio_durations = {}
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, (audio_key, text) in enumerate(audio_content.items()):
            try:
                status_text.text(f"Generating audio: {audio_key}")
                
                # Generate TTS audio
                audio_data = self.client.text_to_speech(
                    text=text,
                    **self.audio_config
                )
                
                # Save audio file
                audio_path = os.path.join(audio_dir, f"{audio_key}.wav")
                save(audio_data.audios[0], audio_path)
                
                # Estimate duration (rough calculation based on word count and pace)
                word_count = len(text.split())
                estimated_duration = max(2.0, word_count * 0.4)  # ~0.4 seconds per word
                audio_durations[audio_key] = estimated_duration
                
                logger.info(f"Created audio {audio_key}: {estimated_duration:.1f}s")
                
            except Exception as e:
                logger.error(f"Error creating audio {audio_key}: {str(e)}")
                # Use fallback duration
                audio_durations[audio_key] = 3.0
            
            # Update progress
            progress = (i + 1) / len(audio_content)
            progress_bar.progress(progress)
        
        progress_bar.empty()
        status_text.empty()
        
        return audio_durations
    
    def generate_script_content(self, problem_data: Dict, audio_content: Dict[str, str], class_name: str) -> str:
        """
        Generate complete Manim script based on problem type
        
        Args:
            problem_data: Problem details
            audio_content: Audio narration content
            class_name: Manim scene class name
            
        Returns:
            Complete Python script content
        """
        topic = problem_data.get('topic', '').lower()
        
        # Choose appropriate template based on topic
        if any(keyword in topic for keyword in ['algebra', 'equation', 'linear', 'quadratic']):
            return self._generate_algebra_script(problem_data, audio_content, class_name)
        elif any(keyword in topic for keyword in ['geometry', 'triangle', 'circle', 'polygon']):
            return self._generate_geometry_script(problem_data, audio_content, class_name)
        elif 'coordinate' in topic:
            return self._generate_coordinate_geometry_script(problem_data, audio_content, class_name)
        elif any(keyword in topic for keyword in ['trigonometry', 'sin', 'cos', 'tan']):
            return self._generate_trigonometry_script(problem_data, audio_content, class_name)
        elif any(keyword in topic for keyword in ['probability', 'statistics', 'data']):
            return self._generate_stats_script(problem_data, audio_content, class_name)
        else:
            return self._generate_generic_script(problem_data, audio_content, class_name)
    
    def _generate_algebra_script(self, problem_data: Dict, audio_content: Dict, class_name: str) -> str:
        """Generate Manim script for algebra problems"""
        
        script_template = f'''from manim import *
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
        self.TEXT_COLOR = {self.color_scheme['TEXT_COLOR']}
        self.HIGHLIGHT_COLOR = {self.color_scheme['HIGHLIGHT_COLOR']}
        self.STEP_COLOR = {self.color_scheme['STEP_COLOR']}
        self.ANSWER_COLOR = {self.color_scheme['ANSWER_COLOR']}
        self.FORMULA_COLOR = {self.color_scheme['FORMULA_COLOR']}
        
        # Session management
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
            print("Sarvam AI client not available")
            return
            
        audio_content = {json.dumps(audio_content, indent=8)}
        
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
                
                # Estimate duration
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
        # Set white background
        self.camera.background_color = WHITE
        
        # Grid background for title
        grid_lines = VGroup()
        for i in range(-8, 9):
            h_line = Line([-8, i, 0], [8, i, 0], stroke_width=0.5, color=GRAY, stroke_opacity=0.2)
            v_line = Line([i, -4, 0], [i, 4, 0], stroke_width=0.5, color=GRAY, stroke_opacity=0.2)
            grid_lines.add(h_line, v_line)
        
        # Introduction
        title = Text(
            "{problem_data.get('topic', 'Math')} Problem - Grade {problem_data.get('grade', 8)}",
            font="Arial Unicode MS",
            color=self.TEXT_COLOR,
            font_size=32
        )
        
        self.add(grid_lines)
        self.play(Write(title), run_time=1)
        self.wait(0.5)
        
        # Play intro audio
        intro_key = [k for k in self.audio_durations.keys() if 'intro' in k][0]
        self.play_audio_and_wait(intro_key, self.audio_durations[intro_key])
        
        # Problem statement
        self.play(FadeOut(grid_lines))
        
        problem_text = Text(
            "{problem_data.get('statement', '')}",
            font="Arial Unicode MS",
            color=self.TEXT_COLOR,
            font_size=24
        ).scale(0.8)
        
        # Add green underline for Hindi problem statements
        problem_underline = Line(
            problem_text.get_left() + DOWN * 0.15,
            problem_text.get_right() + DOWN * 0.15,
            color=GREEN,
            stroke_width=3
        )
        
        self.play(Transform(title, problem_text), run_time=1)
        self.play(Create(problem_underline), run_time=0.5)
        self.wait(0.5)
        
        # Problem audio
        problem_key = [k for k in self.audio_durations.keys() if 'problem' in k][0]
        self.play_audio_and_wait(problem_key, self.audio_durations[problem_key])
        
        # Calculation area
        calc_box = Rectangle(
            width=6.2, 
            height=7.2, 
            fill_color=WHITE, 
            fill_opacity=0.15,
            stroke_color=self.STEP_COLOR,
            stroke_width=2
        )
        calc_box.to_edge(RIGHT, buff=0.1)
        
        self.play(FadeOut(title, problem_underline))
        self.play(Create(calc_box), run_time=1)
        
        # Solution steps
        solution_start_key = [k for k in self.audio_durations.keys() if 'solution_start' in k][0]
        self.play_audio_and_wait(solution_start_key, self.audio_durations[solution_start_key])
        
        # Display each step
        step_equations = VGroup()
        solution_steps = {json.dumps(problem_data.get('solution_steps', []))}
        
        for i, step in enumerate(solution_steps):
            if step.strip():
                # Try to render as math equation, fallback to text
                try:
                    step_eq = MathTex(step, font_size=24, color=self.STEP_COLOR)
                except:
                    step_eq = Text(step, font="Arial Unicode MS", font_size=20, color=self.STEP_COLOR)
                
                step_equations.add(step_eq)
        
        if step_equations:
            step_equations.arrange(DOWN, aligned_edge=LEFT, buff=0.3)
            step_equations.move_to(calc_box.get_center())
            
            for i, step_eq in enumerate(step_equations):
                self.play(Write(step_eq), run_time=1)
                self.wait(0.5)
                
                # Play step audio if available
                step_keys = [k for k in self.audio_durations.keys() if f'step_{{{i+1}}}' in k]
                if step_keys:
                    self.play_audio_and_wait(step_keys[0], self.audio_durations[step_keys[0]])
                else:
                    self.wait(2.0)
        
        # Final answer
        try:
            answer_text = MathTex(
                f"\\text{{Answer: }} {problem_data.get('answer', '')}",
                font_size=28,
                color=self.ANSWER_COLOR
            )
        except:
            answer_text = Text(
                f"Answer: {problem_data.get('answer', '')}",
                font="Arial Unicode MS",
                font_size=28,
                color=self.ANSWER_COLOR
            )
        
        answer_box = SurroundingRectangle(answer_text, color=self.ANSWER_COLOR, buff=0.1)
        
        self.play(FadeOut(step_equations, calc_box))
        self.play(Write(answer_text), run_time=1)
        self.play(Create(answer_box), run_time=0.5)
        
        # Answer highlight animation
        for _ in range(3):
            self.play(answer_box.animate.set_stroke(opacity=1, width=4), run_time=0.3)
            self.play(answer_box.animate.set_stroke(opacity=0.5, width=2), run_time=0.3)
        
        # Answer audio
        answer_key = [k for k in self.audio_durations.keys() if 'answer' in k][0]
        self.play_audio_and_wait(answer_key, self.audio_durations[answer_key])
        
        # Conclusion
        conclusion_key = [k for k in self.audio_durations.keys() if 'conclusion' in k][0]
        self.play_audio_and_wait(conclusion_key, self.audio_durations[conclusion_key])
        
        self.wait(2.0)  # Final buffer
'''
        
        return script_template
    
    def _generate_geometry_script(self, problem_data: Dict, audio_content: Dict, class_name: str) -> str:
        """Generate Manim script for geometry problems"""
        # Similar structure but with geometric shapes
        return self._generate_algebra_script(problem_data, audio_content, class_name)  # Simplified for now
    
    def _generate_coordinate_geometry_script(self, problem_data: Dict, audio_content: Dict, class_name: str) -> str:
        """Generate script for coordinate geometry with axes and points"""
        return self._generate_algebra_script(problem_data, audio_content, class_name)  # Simplified for now
    
    def _generate_trigonometry_script(self, problem_data: Dict, audio_content: Dict, class_name: str) -> str:
        """Generate script for trigonometry with triangles and ratios"""
        return self._generate_algebra_script(problem_data, audio_content, class_name)  # Simplified for now
    
    def _generate_stats_script(self, problem_data: Dict, audio_content: Dict, class_name: str) -> str:
        """Generate script for statistics/probability with charts"""
        return self._generate_algebra_script(problem_data, audio_content, class_name)  # Simplified for now
    
    def _generate_generic_script(self, problem_data: Dict, audio_content: Dict, class_name: str) -> str:
        """Generate generic script for other topics"""
        return self._generate_algebra_script(problem_data, audio_content, class_name)
    
    def render_video(self, script_content: str, class_name: str, problem_data: Dict) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Render the Manim video
        
        Args:
            script_content: Python script content
            class_name: Manim scene class name
            problem_data: Problem data for metadata
            
        Returns:
            Tuple of (video_path, script_path, error_message)
        """
        temp_dir = tempfile.mkdtemp(prefix="manim_render_")
        
        try:
            # Write script to file
            script_path = os.path.join(temp_dir, f"{class_name}.py")
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script_content)
            
            # Set up Manim command
            media_dir = os.path.join(temp_dir, "media")
            cmd = [
                sys.executable, "-m", "manim",
                "-pqh",  # High quality, preview
                script_path,
                class_name,
                "--flush_cache",
                f"--media_dir={media_dir}"
            ]
            
            # Show rendering progress
            progress_placeholder = st.empty()
            
            with progress_placeholder.container():
                st.info("🎬 Rendering video... This may take 2-5 minutes.")
                progress_bar = st.progress(0)
                
                # Start rendering process
                process = subprocess.Popen(
                    cmd,
                    cwd=temp_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    universal_newlines=True
                )
                
                # Monitor progress (simple timer-based)
                start_time = time.time()
                timeout = 300  # 5 minute timeout
                
                while process.poll() is None:
                    elapsed = time.time() - start_time
                    progress = min(elapsed / timeout, 0.95)
                    progress_bar.progress(progress)
                    
                    if elapsed > timeout:
                        process.kill()
                        return None, script_path, "Rendering timed out after 5 minutes"
                    
                    time.sleep(1)
                
                progress_bar.progress(1.0)
            
            progress_placeholder.empty()
            
            # Get process result
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                error_msg = f"Manim rendering failed:\\nSTDOUT: {stdout}\\nSTDERR: {stderr}"
                logger.error(error_msg)
                return None, script_path, error_msg
            
            # Find the generated video file
            video_dir = os.path.join(media_dir, "videos", class_name, "1080p60")
            
            if os.path.exists(video_dir):
                for file in os.listdir(video_dir):
                    if file.endswith('.mp4'):
                        video_path = os.path.join(video_dir, file)
                        logger.info(f"Video rendered successfully: {video_path}")
                        
                        # Copy to a permanent location
                        permanent_video_path = os.path.join(temp_dir, f"{class_name}_final.mp4")
                        shutil.copy2(video_path, permanent_video_path)
                        
                        return permanent_video_path, script_path, None
            
            return None, script_path, "Video file not found after rendering"
            
        except Exception as e:
            error_msg = f"Rendering error: {str(e)}"
            logger.error(error_msg)
            return None, None, error_msg
    
    def create_video_metadata(self, problem_data: Dict, render_info: Dict = None) -> Dict:
        """Create metadata for the generated video"""
        metadata = {
            'problem_data': problem_data,
            'generation_info': {
                'timestamp': datetime.now().isoformat(),
                'generator_version': '1.0.0',
                'manim_version': 'community-v0.18.0',
                'sarvam_ai_used': bool(self.client),
                'render_settings': {
                    'quality': 'high',
                    'resolution': '1080p60',
                    'format': 'mp4'
                }
            }
        }
        
        if render_info:
            metadata['generation_info'].update(render_info)
        
        return metadata
    
    def generate_video_complete(self, problem_data: Dict) -> Tuple[Optional[str], Optional[str], Dict, Optional[str]]:
        """
        Complete video generation pipeline
        
        Args:
            problem_data: Complete problem information
            
        Returns:
            Tuple of (video_path, script_path, metadata, error_message)
        """
        try:
            # Generate unique class name
            timestamp = int(time.time())
            topic_clean = problem_data.get('topic', 'Math').replace(' ', '').replace('-', '')
            class_name = f"{topic_clean}Problem{timestamp}"
            
            # Generate audio content
            st.info("📝 Generating narration content...")
            audio_content = self.generate_audio_content(problem_data)
            
            # Generate script
            st.info("🐍 Creating Manim script...")
            script_content = self.generate_script_content(problem_data, audio_content, class_name)
            
            # Create temporary directory for audio
            temp_audio_dir = tempfile.mkdtemp(prefix="audio_")
            
            # Generate audio files
            st.info("🎵 Generating audio files...")
            audio_durations = self.create_audio_files(audio_content, temp_audio_dir)
            
            # Render video
            st.info("🎬 Rendering video...")
            video_path, script_path, error = self.render_video(script_content, class_name, problem_data)
            
            if error:
                return None, script_path, {}, error
            
            # Create metadata
            metadata = self.create_video_metadata(
                problem_data, 
                {'audio_durations': audio_durations, 'class_name': class_name}
            )
            
            return video_path, script_path, metadata, None
            
        except Exception as e:
            error_msg = f"Video generation failed: {str(e)}"
            logger.error(error_msg)
            return None, None, {}, error_msg

# Utility functions
def validate_problem_data(problem_data: Dict) -> Tuple[bool, str]:
    """Validate problem data structure"""
    required_fields = ['statement', 'grade', 'topic', 'solution_steps', 'answer']
    
    for field in required_fields:
        if field not in problem_data or not problem_data[field]:
            return False, f"Missing or empty field: {field}"
    
    # Validate grade
    if not isinstance(problem_data['grade'], int) or problem_data['grade'] < 6 or problem_data['grade'] > 10:
        return False, "Grade must be between 6 and 10"
    
    # Validate solution steps
    if isinstance(problem_data['solution_steps'], str):
        problem_data['solution_steps'] = problem_data['solution_steps'].strip().split('\\n')
    
    if not isinstance(problem_data['solution_steps'], list) or len(problem_data['solution_steps']) == 0:
        return False, "Solution steps must be a non-empty list"
    
    return True, "Valid"

def estimate_video_duration(problem_data: Dict) -> float:
    """Estimate video duration in seconds"""
    base_duration = 30  # Introduction, conclusion, etc.
    
    # Add time for problem statement
    problem_words = len(problem_data.get('statement', '').split())
    base_duration += max(5, problem_words * 0.3)
    
    # Add time for solution steps
    solution_steps = problem_data.get('solution_steps', [])
    for step in solution_steps:
        step_words = len(str(step).split())
        base_duration += max(3, step_words * 0.4)
    
    # Add buffer time
    base_duration += len(solution_steps) * 2  # 2 seconds per step for visualization
    
    return base_duration

@st.cache_resource
def get_video_generator(api_key: str):
    """Get cached video generator instance"""
    if not api_key:
        return None
    
    try:
        generator = MathVideoGenerator(api_key)
        if generator.test_sarvam_connection():
            return generator
        else:
            st.error("Failed to connect to Sarvam AI. Please check your API key.")
            return None
    except Exception as e:
        st.error(f"Error initializing video generator: {str(e)}")
        return None
