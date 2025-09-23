import streamlit as st
import os
import tempfile
import subprocess
import time
from pathlib import Path
import requests
import json

# Page config
st.set_page_config(
    page_title="Math Video Generator",
    page_icon="📐",
    layout="wide"
)

st.title("📐 Math Video Generator")
st.markdown("Generate animated math videos using AI and Manim")

# Sidebar for API keys
with st.sidebar:
    st.header("🔑 API Configuration")
    claude_api_key = st.text_input("Claude API Key", type="password", help="Your Anthropic Claude API key")
    sarvam_api_key = st.text_input("Sarvam AI API Key", type="password", help="Your Sarvam AI API key (for voice)")

# Main interface
col1, col2 = st.columns([1, 1])

with col1:
    st.header("📝 Problem Details")
    
    problem_text = st.text_area(
        "Math Problem",
        placeholder="Enter the math problem to solve...",
        height=100
    )
    
    grade_level = st.selectbox(
        "Grade Level",
        ["Elementary (K-5)", "Middle School (6-8)", "High School (9-12)", "College"]
    )
    
    solution = st.text_area(
        "Solution Steps",
        placeholder="Enter the step-by-step solution...",
        height=150
    )
    
    additional_notes = st.text_area(
        "Additional Notes (Optional)",
        placeholder="Any specific animation requests or emphasis...",
        height=80
    )

with col2:
    st.header("🎬 Video Settings")
    
    video_length = st.slider("Target Video Length (minutes)", 1, 5, 2)
    video_quality = st.selectbox("Video Quality", ["low", "medium", "high"])
    include_voice = st.checkbox("Include AI Voiceover", value=True)

# Generate button
if st.button("🚀 Generate Video", type="primary", use_container_width=True):
    if not claude_api_key:
        st.error("Please enter your Claude API key in the sidebar")
    elif not problem_text or not solution:
        st.error("Please enter both the problem and solution")
    else:
        # Create progress indicators
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # Step 1: Generate Manim script using Claude
            status_text.text("🤖 Generating animation script with Claude AI...")
            progress_bar.progress(20)
            
            # Claude API call
            claude_prompt = f"""
You are an expert at creating educational math animations using the Manim library. 

Create a complete Python script that:
1. Uses Manim to animate the solution to this math problem
2. Includes clear step-by-step visual explanations
3. Is appropriate for {grade_level} level
4. Takes approximately {video_length} minutes to watch
5. Includes narration text as comments

Problem: {problem_text}

Solution: {solution}

Additional requirements: {additional_notes}

Generate ONLY the Python code with proper Manim syntax. Include detailed comments for narration.
The class should be named 'MathAnimation' and inherit from Scene.
"""
            
            manim_script = call_claude_api(claude_prompt, claude_api_key)
            
            if manim_script:
                progress_bar.progress(40)
                status_text.text("💾 Saving animation script...")
                
                # Step 2: Save script to temporary file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                    f.write(manim_script)
                    script_path = f.name
                
                progress_bar.progress(60)
                status_text.text("🎬 Rendering video with Manim...")
                
                # Step 3: Run Manim to generate video
                output_dir = tempfile.mkdtemp()
                cmd = [
                    "manim",
                    "-pql" if video_quality == "low" else "-pqm" if video_quality == "medium" else "-pqh",
                    script_path,
                    "MathAnimation",
                    "-o", output_dir
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    progress_bar.progress(80)
                    status_text.text("🎵 Adding voiceover (if enabled)...")
                    
                    # Step 4: Add voiceover if requested
                    video_path = find_video_file(output_dir)
                    
                    if include_voice and sarvam_api_key and video_path:
                        video_path = add_voiceover(video_path, manim_script, sarvam_api_key)
                    
                    progress_bar.progress(100)
                    status_text.text("✅ Video generated successfully!")
                    
                    # Step 5: Display results
                    if video_path and os.path.exists(video_path):
                        st.success("🎉 Your math video is ready!")
                        
                        # Display video
                        with open(video_path, 'rb') as video_file:
                            video_bytes = video_file.read()
                            st.video(video_bytes)
                        
                        # Download button
                        st.download_button(
                            label="📥 Download Video",
                            data=video_bytes,
                            file_name=f"math_video_{int(time.time())}.mp4",
                            mime="video/mp4"
                        )
                        
                        # Show generated script
                        with st.expander("View Generated Script"):
                            st.code(manim_script, language="python")
                    
                    else:
                        st.error("Video file not found after rendering")
                        
                else:
                    st.error(f"Manim rendering failed: {result.stderr}")
                    
                # Cleanup
                try:
                    os.unlink(script_path)
                except:
                    pass
                    
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            progress_bar.progress(0)
            status_text.text("")

# Fix video section
st.header("🔧 Fix Generated Video")
st.markdown("If the generated video needs adjustments, describe what needs to be fixed:")

fix_description = st.text_area(
    "What needs to be fixed?",
    placeholder="e.g., 'The animation is too fast', 'Add more explanation for step 2', 'Change the color scheme'...",
    height=100
)

if st.button("🔄 Regenerate with Fixes", type="secondary"):
    if fix_description:
        st.info("Feature coming soon: Video will be regenerated with your requested fixes")
    else:
        st.warning("Please describe what needs to be fixed")

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
            "max_tokens": 4000,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=data,
            timeout=60
        )
        
        if response.status_code == 200:
            return response.json()["content"][0]["text"]
        else:
            st.error(f"Claude API error: {response.status_code}")
            return None
            
    except Exception as e:
        st.error(f"Error calling Claude API: {str(e)}")
        return None

def find_video_file(output_dir):
    """Find the generated video file"""
    for file in Path(output_dir).rglob("*.mp4"):
        return str(file)
    return None

def add_voiceover(video_path, script_content, sarvam_api_key):
    """Add AI-generated voiceover (placeholder - implement based on Sarvam API)"""
    # This would integrate with Sarvam AI's text-to-speech API
    # For now, return the original video path
    return video_path

# Installation instructions
with st.expander("📋 Installation Instructions"):
    st.markdown("""
    To run this app locally:
    
    1. **Install Python dependencies:**
    ```bash
    pip install streamlit manim requests
    ```
    
    2. **Install system dependencies (Ubuntu/Debian):**
    ```bash
    sudo apt update
    sudo apt install -y cairo-dev libcairo2-dev
    ```
    
    3. **Run the app:**
    ```bash
    streamlit run app.py
    ```
    
    4. **Get API Keys:**
    - Claude: https://console.anthropic.com/
    - Sarvam AI: https://www.sarvam.ai/
    """)

# Footer
st.markdown("---")
st.markdown("Built with ❤️ using Streamlit, Manim, and AI")
