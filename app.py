import streamlit as st
import requests
import json
import tempfile
import subprocess
import os
import time
from pathlib import Path
import sys
import hashlib

# Page config
st.set_page_config(
    page_title="NCERT Math Video Generator",
    page_icon="📐",
    layout="wide"
)

st.title("📐 NCERT Math Video Generator")
st.markdown("Generate educational math videos for grades 6-10 with Hindi-English narration using Manim and Sarvam AI")

# Check Manim installation
@st.cache_data
def check_dependencies():
    """Check if required libraries are available"""
    results = {}
    
    # Check Manim
    try:
        import manim
        results['manim'] = f"✅ Available (v{manim.__version__})"
    except ImportError:
        results['manim'] = "❌ Not installed"
    
    # Check other dependencies
    try:
        import numpy
        results['numpy'] = "✅ Available"
    except ImportError:
        results['numpy'] = "❌ Not installed"
    
    return results

# Display dependency status
deps = check_dependencies()
with st.sidebar:
    st.header("📦 Dependencies")
    for dep, status in deps.items():
        st.text(f"{dep}: {status}")
    
    if "❌" in str(deps.values()):
        st.warning("Some dependencies are missing. Video generation may not work.")
    else:
        st.success("All dependencies available!")

# API Configuration
with st.sidebar:
    st.header("🔑 API Keys")
    claude_api_key = st.text_input("Claude API Key", type="password", help="For generating Manim scripts")
    sarvam_api_key = st.text_input("Sarvam AI API Key", type="password", help="For Hindi TTS narration")
    
    if claude_api_key and sarvam_api_key:
        st.success("✅ API keys configured")

# Main interface
col1, col2 = st.columns([1, 1])

with col1:
    st.header("📝 Problem Details")
    
    problem_statement = st.text_area(
        "Problem Statement (exact wording):",
        placeholder="e.g., Solve the equation: 2x + 5 = 13",
        height=100
    )
    
    grade_level = st.selectbox(
        "Grade Level:",
        ["Grade 6", "Grade 7", "Grade 8", "Grade 9", "Grade 10"]
    )
    
    topic_area = st.selectbox(
        "Topic Area:",
        ["Algebra", "Geometry", "Arithmetic", "Coordinate Geometry", "Trigonometry", "Statistics"]
    )
    
    solution_steps = st.text_area(
        "Complete Step-by-Step Solution:",
        placeholder="Provide detailed solution steps...",
        height=150
    )

with col2:
    st.header("🎬 Video Settings")
    
    language_mix = st.selectbox(
        "Narration Style:",
        ["Hindi-English Mix (Recommended)", "Primarily Hindi", "Primarily English"]
    )
    
    video_duration = st.slider(
        "Target Duration (minutes):",
        1, 5, 2
    )
    
    visual_style = st.selectbox(
        "Visual Style:",
        ["Clean & Minimal", "Colorful & Engaging", "Traditional Textbook"]
    )
    
    st.subheader("🎨 Customization (Optional)")
    custom_hindi_phrases = st.text_area(
        "Specific Hindi phrases to use:",
        placeholder="Any specific Hindi terms you want included...",
        height=80
    )
    
    custom_colors = st.checkbox("Use custom color scheme", value=False)

# Advanced settings
with st.expander("⚙️ Advanced Settings"):
    col3, col4 = st.columns(2)
    
    with col3:
        animation_speed = st.slider("Animation Speed", 0.5, 2.0, 1.0, 0.1)
        highlight_important = st.checkbox("Extra highlighting for key steps", value=True)
    
    with col4:
        include_grid = st.checkbox("Include background grid", value=True)
        voice_pace = st.slider("Voice Pace", 0.7, 1.3, 0.95, 0.05)

# Generate Video Button
if st.button("🚀 Generate NCERT Math Video", type="primary", use_container_width=True):
    if not claude_api_key or not sarvam_api_key:
        st.error("Please provide both Claude API key and Sarvam AI API key")
    elif not problem_statement or not solution_steps:
        st.error("Please provide both problem statement and solution steps")
    else:
        # Check if Manim is available
        if "❌" in deps.get('manim', ''):
            st.error("Manim is not installed. Please install dependencies first.")
            st.code("pip install manim sarvamai", language="bash")
            st.stop()
        
        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # Step 1: Generate Manim script with Claude
            status_text.text("🤖 Generating NCERT-compliant Manim script...")
            progress_bar.progress(20)
            
            # Build comprehensive prompt
            manim_prompt = build_manim_prompt(
                problem_statement, grade_level, topic_area, solution_steps,
                language_mix, custom_hindi_phrases, sarvam_api_key,
                animation_speed, highlight_important, include_grid, voice_pace
            )
            
            manim_script = call_claude_api(manim_prompt, claude_api_key)
            
            if not manim_script:
                st.error("Failed to generate Manim script")
                st.stop()
            
            progress_bar.progress(40)
            status_text.text("💾 Creating video script file...")
            
            # Step 2: Save script to file
            timestamp = int(time.time())
            script_filename = f"math_video_{timestamp}.py"
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(manim_script)
                script_path = f.name
            
            # Display generated script
            with st.expander("📄 View Generated Manim Script"):
                st.code(manim_script, language="python")
            
            progress_bar.progress(60)
            status_text.text("🎬 Rendering video with Manim...")
            
            # Step 3: Run Manim to generate video
            output_dir = tempfile.mkdtemp()
            
            # Extract class name from script
            class_name = extract_class_name(manim_script)
            
            # Manim command
            cmd = [
                "manim",
                "-pqh",  # High quality
                script_path,
                class_name,
                "--flush_cache"
            ]
            
            st.info(f"Running: {' '.join(cmd)}")
            
            # Execute Manim with timeout
            try:
                result = subprocess.run(
                    cmd,
                    cwd=output_dir,
                    capture_output=True,
                    text=True,
                    timeout=600  # 10 minutes timeout
                )
                
                if result.returncode == 0:
                    progress_bar.progress(90)
                    status_text.text("🎵 Processing audio and finalizing...")
                    
                    # Find generated video
                    video_files = list(Path(output_dir).rglob("*.mp4"))
                    
                    if video_files:
                        video_path = str(video_files[0])
                        
                        # Display success
                        progress_bar.progress(100)
                        status_text.text("✅ NCERT Math video generated successfully!")
                        
                        # Show video
                        with open(video_path, 'rb') as video_file:
                            video_bytes = video_file.read()
                        
                        st.success("🎉 Your NCERT Math video is ready!")
                        st.video(video_bytes)
                        
                        # Download options
                        col5, col6 = st.columns(2)
                        
                        with col5:
                            st.download_button(
                                "📥 Download Video (MP4)",
                                video_bytes,
                                f"ncert_math_{timestamp}.mp4",
                                mime="video/mp4"
                            )
                        
                        with col6:
                            st.download_button(
                                "📄 Download Script",
                                manim_script,
                                f"script_{timestamp}.py",
                                mime="text/plain"
                            )
                        
                        # Video info
                        st.info(f"""
                        **Video Details:**
                        - Grade: {grade_level}
                        - Topic: {topic_area}
                        - Duration: ~{video_duration} minutes
                        - Language: {language_mix}
                        - Quality: High (1080p)
                        """)
                        
                    else:
                        st.error("Video file not found after rendering")
                        st.text("Available files:")
                        for item in Path(output_dir).rglob("*"):
                            st.text(str(item))
                
                else:
                    st.error("❌ Manim rendering failed!")
                    st.text("**Error Output:**")
                    st.code(result.stderr, language="text")
                    st.text("**Standard Output:**")
                    st.code(result.stdout, language="text")
                    
                    # Debugging info
                    st.text("**Debug Info:**")
                    st.text(f"Script path: {script_path}")
                    st.text(f"Class name: {class_name}")
                    st.text(f"Working directory: {output_dir}")
            
            except subprocess.TimeoutExpired:
                st.error("⏰ Video generation timed out (10 minutes). Try a simpler problem.")
            except Exception as e:
                st.error(f"❌ Error running Manim: {str(e)}")
            
            finally:
                # Cleanup
                try:
                    os.unlink(script_path)
                except:
                    pass
        
        except Exception as e:
            st.error(f"❌ Unexpected error: {str(e)}")
            import traceback
            st.code(traceback.format_exc(), language="text")

def build_manim_prompt(problem, grade, topic, solution, lang_mix, custom_phrases, sarvam_key, anim_speed, highlight, grid, voice_pace):
    """Build comprehensive prompt for Claude to generate NCERT-compliant Manim script"""
    
    return f"""
You are an expert at creating educational math animations for NCERT curriculum using Manim Community Edition and Sarvam AI TTS. 

Generate a complete Python script following these EXACT specifications:

## Problem Details:
- **Problem**: {problem}
- **Grade Level**: {grade} 
- **Topic Area**: {topic}
- **Solution Steps**: {solution}
- **Language Style**: {lang_mix}
- **Custom Hindi Phrases**: {custom_phrases}

## Technical Requirements:

### 1. Required Imports:
```python
from manim import *
import os
import shutil
import time
import hashlib
import requests
import json
```

### 2. Class Structure:
Create a class called `NCERTMathProblem` that inherits from `Scene`.

### 3. Visual Requirements (MANDATORY):
- Background: `self.camera.background_color = WHITE`
- Color palette:
  ```python
  TEXT_COLOR = BLACK
  HIGHLIGHT_COLOR = BLUE
  STEP_COLOR = BLUE_D
  POINT_COLOR = RED
  LINE_COLOR = GREEN
  ANSWER_COLOR = GREEN_D
  ```
- Include grid background if specified: {grid}
- Animation speed factor: {anim_speed}
- Extra highlighting: {highlight}

### 4. Audio Integration:
- Use Sarvam AI API key: "{sarvam_key}"
- Voice pace: {voice_pace}
- Create audio files in `__init__` method with unique timestamps
- Hindi-English mix appropriate for {grade}
- Use this audio creation pattern:
```python
def create_audio_file(self, text, filename):
    headers = {{
        'Content-Type': 'application/json',
        'api-subscription-key': self.SARVAM_API_KEY
    }}
    
    data = {{
        'inputs': [text],
        'target_language_code': 'hi-IN',
        'speaker': 'anushka',
        'pitch': 0.1,
        'pace': {voice_pace},
        'loudness': 1.2,
        'speech_sample_rate': 22050,
        'enable_preprocessing': True,
        'model': 'bulbul:v1'
    }}
    
    response = requests.post('https://api.sarvam.ai/text-to-speech', headers=headers, json=data)
    if response.status_code == 200:
        with open(filename, 'wb') as f:
            f.write(response.content)
        return True
    return False
```

### 5. Timing Pattern (CRITICAL):
For every audio segment, use this exact pattern:
```python
self.play(Write(element), run_time=1)
self.wait(0.5)
audio_duration = self.play_audio_and_wait("audio_file", duration)
self.wait(1.2)  # Mandatory buffer
```

### 6. Scene Structure (~2 minutes total):
1. Introduction (3 seconds)
2. Title with problem (5 seconds) 
3. Problem setup (4 seconds)
4. Solution steps (3-4 seconds each)
5. Answer highlight (4 seconds)
6. Conclusion (4 seconds)

### 7. Audio Content (Hindi-English Mix):
Create natural bilingual narration appropriate for {grade} students:
- Introduction: "नमस्ते बच्चों! आज हम {topic} का एक problem solve करेंगे।"
- Problem reading with Hindi explanations
- Step explanations in mixed language
- Conclusion: "बहुत अच्छे! आज आपने सीखा..."

### 8. Problem-Specific Requirements:
For {topic} problems:
- Use appropriate mathematical objects
- Show step-by-step transformations
- Include visual aids and diagrams
- Highlight key insights

Generate the COMPLETE Python script with all methods implemented, proper error handling, and following all timing requirements. The script should run without any modifications.

Make sure to:
- Include unique timestamp-based audio filenames
- Handle audio file creation errors gracefully  
- Use proper Manim syntax for latest version
- Follow NCERT teaching methodology
- Include comments explaining key sections

The script should be production-ready and render a professional educational video.
"""

def call_claude_api(prompt, api_key):
    """Call Claude API to generate Manim script"""
    try:
        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        }
        
        data = {
            "model": "claude-3-sonnet-20240229",
            "max_tokens": 8000,  # Increased for complex scripts
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=data,
            timeout=120
        )
        
        if response.status_code == 200:
            return response.json()["content"][0]["text"]
        else:
            st.error(f"Claude API error: {response.status_code}")
            st.code(response.text, language="text")
            return None
            
    except Exception as e:
        st.error(f"Error calling Claude API: {str(e)}")
        return None

def extract_class_name(script_content):
    """Extract the class name from the generated script"""
    lines = script_content.split('\n')
    for line in lines:
        if line.strip().startswith('class ') and 'Scene' in line:
            # Extract class name
            class_def = line.strip().split('class ')[1].split('(')[0]
            return class_def.strip()
    return "NCERTMathProblem"  # Default fallback

# Sample Problems Section
st.header("📚 Sample NCERT Problems")

sample_problems = {
    "Grade 6 - Algebra": {
        "problem": "Find the value of x if 3x + 7 = 19",
        "solution": "Step 1: Subtract 7 from both sides\n3x + 7 - 7 = 19 - 7\n3x = 12\n\nStep 2: Divide both sides by 3\n3x ÷ 3 = 12 ÷ 3\nx = 4"
    },
    "Grade 8 - Geometry": {
        "problem": "Find the area of a triangle with base 8 cm and height 6 cm",
        "solution": "Step 1: Use the formula Area = ½ × base × height\nArea = ½ × 8 × 6\n\nStep 2: Calculate\nArea = ½ × 48\nArea = 24 cm²"
    },
    "Grade 10 - Coordinate Geometry": {
        "problem": "Find the distance between points A(2, 3) and B(5, 7)",
        "solution": "Step 1: Use distance formula\nd = √[(x₂-x₁)² + (y₂-y₁)²]\n\nStep 2: Substitute values\nd = √[(5-2)² + (7-3)²]\nd = √[3² + 4²]\nd = √[9 + 16]\nd = √25 = 5 units"
    }
}

col7, col8, col9 = st.columns(3)

for i, (grade_topic, data) in enumerate(sample_problems.items()):
    col = [col7, col8, col9][i]
    with col:
        st.subheader(grade_topic)
        st.text(data["problem"])
        if st.button(f"Use {grade_topic} Example", key=f"sample_{i}"):
            st.session_state.update({
                'problem_statement': data["problem"],
                'solution_steps': data["solution"]
            })
            st.experimental_rerun()

# Installation Guide
with st.expander("📦 Installation Guide"):
    st.markdown("""
    ### For Streamlit Cloud Deployment:
    
    **requirements.txt:**
    ```
    streamlit>=1.28.0
    requests>=2.31.0
    manim>=0.17.3
    sarvamai>=1.0.0
    numpy>=1.24.0
    Pillow>=9.5.0
    ```
    
    **packages.txt:**
    ```
    python3-dev
    libcairo2-dev
    libpango1.0-dev
    ffmpeg
    cmake
    pkg-config
    ```
    
    ### For Local Development:
    ```bash
    # Install system dependencies (Ubuntu/Debian)
    sudo apt update
    sudo apt install python3-dev libcairo2-dev libpango1.0-dev ffmpeg cmake pkg-config
    
    # Install Python packages
    pip install manim sarvamai streamlit requests numpy Pillow
    ```
    
    ### Get API Keys:
    - **Claude**: https://console.anthropic.com/
    - **Sarvam AI**: https://www.sarvam.ai/
    """)

# Footer
st.markdown("---")
st.markdown("🇮🇳 **Built for NCERT Curriculum** | Supports Hindi-English bilingual education")

if st.button("🧪 Test Dependencies"):
    st.info("Testing all dependencies...")
    
    test_results = []
    
    # Test imports
    try:
        import manim
        test_results.append("✅ Manim imported successfully")
    except ImportError as e:
        test_results.append(f"❌ Manim import failed: {e}")
    
    try:
        import numpy
        test_results.append("✅ NumPy available")
    except ImportError:
        test_results.append("❌ NumPy not available")
    
    # Test API connectivity
    if claude_api_key:
        test_prompt = "Reply with just 'API working'"
        result = call_claude_api(test_prompt, claude_api_key)
        if result:
            test_results.append("✅ Claude API working")
        else:
            test_results.append("❌ Claude API failed")
    else:
        test_results.append("⚠️ Claude API key not provided")
    
    for result in test_results:
        st.text(result)
