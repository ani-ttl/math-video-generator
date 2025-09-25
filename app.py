import streamlit as st
import requests
import json

# Page config
st.set_page_config(
    page_title="Math Content Generator",
    page_icon="📐",
    layout="wide"
)

st.title("📐 Math Content Generator")
st.markdown("Generate educational math content using Claude AI")

# Check if we're running successfully
st.success("✅ App is running successfully!")

# Sidebar
with st.sidebar:
    st.header("🔑 API Key")
    claude_api_key = st.text_input("Claude API Key", type="password")
    
    if claude_api_key:
        st.success("API key entered")
    else:
        st.warning("Enter your Claude API key")
        
with st.sidebar:
    sarvam_api_key = st.text_input("Sarvam API Key", type="password")
    
    if sarvam_api_key:
        st.success("API key entered")
    else:
        st.warning("Enter your Sarvam API key")

# Main content
st.header("📝 Generate Math Content")

problem = st.text_area(
    "Enter a math problem:",
    placeholder="e.g., Solve for x: 2x + 5 = 13",
    height=100
)

grade_level = st.selectbox(
    "Grade:",
    ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
)

if st.button("Generate Solution Video", type="primary"):
    if not claude_api_key:
        st.error("Please enter your Claude API key")
    elif not sarvam_api_key:
        st.error("Please enter your Sarvam API key")
    elif not problem:
        st.error("Please enter a math problem")
    else:
        with st.spinner("Generating solution..."):
            # Call Claude API
            try:
                headers = {
                    "Content-Type": "application/json",
                    "x-api-key": claude_api_key,
                    "anthropic-version": "2023-06-01"
                }
                
                prompt = f"""
                Create a detailed step-by-step solution for this math problem appropriate for {grade_level} level:
                
                Problem: {problem}
                
                Please provide:
                1. A clear step-by-step solution
                2. Explanation of each step
                3. The final answer
                """
                
                data = {
                    "model": "claude-3-sonnet-20240229",
                    "max_tokens": 2000,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ]
                }
                
                response = requests.post(
                    "https://api.anthropic.com/v1/messages",
                    headers=headers,
                    json=data,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()["content"][0]["text"]
                    st.success("Solution generated!")
                    st.markdown("### Solution:")
                    st.markdown(result)
                    
                    # Download button
                    st.download_button(
                        "Download Solution",
                        result,
                        f"solution_{hash(problem)}.txt",
                        mime="text/plain"
                    )
                else:
                    st.error(f"API Error: {response.status_code}")
                    st.text(response.text)
                    
            except Exception as e:
                st.error(f"Error: {str(e)}")

# Test section
st.header("🧪 Test Section")
st.info("This section confirms the app is working correctly")

if st.button("Test API Connection"):
    if claude_api_key:
        st.success("✅ Ready to test API")
    else:
        st.warning("Enter API key first")

# Sample problems
with st.expander("📚 Sample Problems"):
    st.markdown("""
    **Grade 2:**
    - What is 15 + 27?
        
    **Grade 7:**
    - Solve: 3x + 7 = 22
    
    **Grade 9:**
    - Factor: x² + 5x + 6
    """)

st.markdown("---")
st.markdown("✨ Created by TicTacLearn")
