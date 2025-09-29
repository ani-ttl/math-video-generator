#!/usr/bin/env python3
"""
Quick Start Script for Math Video Creator
Run this to set up and test your installation
"""

import os
import sys
import subprocess
import json
import tempfile
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3.8, 0):
        print("❌ Python 3.8 or higher is required")
        return False
    print(f"✅ Python {sys.version.split()[0]} detected")
    return True

def check_system_dependencies():
    """Check system dependencies"""
    dependencies = {
        'ffmpeg': 'ffmpeg -version',
        'latex': 'pdflatex --version'
    }
    
    missing = []
    for name, cmd in dependencies.items():
        try:
            result = subprocess.run(cmd.split(), capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ {name} is installed")
            else:
                missing.append(name)
        except FileNotFoundError:
            missing.append(name)
    
    if missing:
        print(f"❌ Missing dependencies: {', '.join(missing)}")
        print("\n📝 Installation commands:")
        if 'ffmpeg' in missing:
            print("  Ubuntu/Debian: sudo apt-get install ffmpeg")
            print("  macOS: brew install ffmpeg")
            print("  Windows: Download from https://ffmpeg.org/download.html")
        
        if 'latex' in missing:
            print("  Ubuntu/Debian: sudo apt-get install texlive-full")
            print("  macOS: brew install --cask mactex")
            print("  Windows: Install MiKTeX from https://miktex.org/")
        
        return False
    
    return True

def install_python_dependencies():
    """Install Python packages"""
    print("📦 Installing Python dependencies...")
    
    requirements = [
        "streamlit>=1.28.0",
        "manim>=0.18.0",
        "google-api-python-client>=2.0.0",
        "google-auth>=2.0.0",
        "numpy>=1.21.0",
        "Pillow>=8.3.0"
    ]
    
    # Install sarvamai if available
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "sarvamai"], 
                      check=True, capture_output=True)
        print("✅ Sarvam AI installed")
    except subprocess.CalledProcessError:
        print("⚠️  Sarvam AI not installed (will use text-only mode)")
        requirements.append("gtts>=2.2.0")  # Fallback TTS
    
    for package in requirements:
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", package], 
                          check=True, capture_output=True)
            print(f"✅ {package.split('>=')[0]} installed")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install {package}: {e}")
            return False
    
    return True

def test_manim_installation():
    """Test Manim by creating a simple animation"""
    print("🧪 Testing Manim installation...")
    
    test_script = '''
from manim import *

class TestScene(Scene):
    def construct(self):
        text = Text("Manim Test", color=BLUE)
        self.add(text)
        self.wait(1)
'''
    
    with tempfile.TemporaryDirectory() as temp_dir:
        script_path = os.path.join(temp_dir, "test_manim.py")
        with open(script_path, 'w') as f:
            f.write(test_script)
        
        try:
            cmd = [sys.executable, "-m", "manim", "-pql", script_path, "TestScene", "--flush_cache"]
            result = subprocess.run(cmd, cwd=temp_dir, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                print("✅ Manim is working correctly")
                return True
            else:
                print(f"❌ Manim test failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("❌ Manim test timed out")
            return False
        except Exception as e:
            print(f"❌ Manim test error: {e}")
            return False

def create_project_structure():
    """Create necessary directories and files"""
    print("📁 Creating project structure...")
    
    dirs_to_create = [
        "utils",
        "templates", 
        "assets",
        ".streamlit",
        "data",
        "output"
    ]
    
    for dir_name in dirs_to_create:
        os.makedirs(dir_name, exist_ok=True)
        print(f"✅ Created directory: {dir_name}")
    
    # Create sample secrets template
    secrets_template = '''# Streamlit Secrets Template
# Copy this to .streamlit/secrets.toml and fill in your values

[google_drive]
credentials = """
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "your-private-key-id",
  "private_key": "-----BEGIN PRIVATE KEY-----\\nYOUR_PRIVATE_KEY\\n-----END PRIVATE KEY-----\\n",
  "client_email": "your-service-account@your-project.iam.gserviceaccount.com",
  "client_id": "your-client-id",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs"
}
"""

[google_drive.ncert_folders]
grade_6 = "your_grade_6_folder_id"
grade_7 = "your_grade_7_folder_id" 
grade_8 = "your_grade_8_folder_id"
grade_9 = "your_grade_9_folder_id"
grade_10 = "your_grade_10_folder_id"

output_folder = "your_output_folder_id"

[sarvam]
default_api_key = "your_sarvam_api_key_optional"
'''
    
    with open(".streamlit/secrets.template.toml", 'w') as f:
        f.write(secrets_template)
    print("✅ Created secrets template")
    
    # Create sample problem data
    sample_problems = {
        "algebra": {
            "statement": "Solve for x: 2x + 5 = 13",
            "grade": 8,
            "topic": "Algebra",
            "solution_steps": [
                "2x + 5 = 13",
                "2x = 13 - 5", 
                "2x = 8",
                "x = 4"
            ],
            "answer": "x = 4"
        },
        "geometry": {
            "statement": "Find the area of a triangle with base 6 cm and height 8 cm",
            "grade": 7,
            "topic": "Geometry", 
            "solution_steps": [
                "Area of triangle = (1/2) × base × height",
                "Area = (1/2) × 6 × 8",
                "Area = (1/2) × 48",
                "Area = 24 cm²"
            ],
            "answer": "24 cm²"
        }
    }
    
    with open("assets/sample_problems.json", 'w') as f:
        json.dump(sample_problems, f, indent=2)
    print("✅ Created sample problems")

def test_sample_generation():
    """Test video generation with sample problem"""
    print("🎬 Testing sample video generation...")
    
    try:
        # Import after installation
        from utils.video_generator import MathVideoGenerator, validate_problem_data
        
        # Load sample problem
        with open("assets/sample_problems.json", 'r') as f:
            sample_problems = json.load(f)
        
        problem_data = sample_problems["algebra"]
        
        # Validate problem data
        is_valid, message = validate_problem_data(problem_data)
        if not is_valid:
            print(f"❌ Invalid problem data: {message}")
            return False
        
        # Test without Sarvam AI (text-only mode)
        generator = MathVideoGenerator("")  # Empty API key
        
        # Generate script only
        audio_content = generator.generate_audio_content(problem_data)
        script_content = generator.generate_script_content(
            problem_data, audio_content, "TestAlgebraProblem"
        )
        
        # Save test script
        with open("output/test_script.py", 'w') as f:
            f.write(script_content)
        
        print("✅ Sample script generated successfully")
        print("📝 Check output/test_script.py for the generated Manim script")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Please ensure all dependencies are installed")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def setup_git_hooks():
    """Setup git hooks for development"""
    if os.path.exists(".git"):
        print("🔧 Setting up git hooks...")
        
        pre_commit_hook = '''#!/bin/sh
# Pre-commit hook to check code quality

echo "Running pre-commit checks..."

# Check Python syntax
python -m py_compile app.py utils/*.py
if [ $? -ne 0 ]; then
    echo "❌ Python syntax errors found"
    exit 1
fi

# Check for secrets in commits
if git diff --cached --name-only | grep -E "secrets\\.toml$|api_key|private_key"; then
    echo "❌ Potential secrets detected. Please review your commit."
    exit 1
fi

echo "✅ Pre-commit checks passed"
'''
        
        hook_path = ".git/hooks/pre-commit"
        with open(hook_path, 'w') as f:
            f.write(pre_commit_hook)
        os.chmod(hook_path, 0o755)
        print("✅ Git pre-commit hook installed")

def print_next_steps():
    """Print next steps for the user"""
    print("\n" + "="*60)
    print("🎉 SETUP COMPLETE!")
    print("="*60)
    
    print("\n📋 Next Steps:")
    print("1. Set up Google Drive API:")
    print("   - Go to https://console.cloud.google.com/")
    print("   - Create a new project or select existing")
    print("   - Enable Google Drive API")
    print("   - Create Service Account credentials")
    print("   - Download JSON key file")
    
    print("\n2. Configure secrets:")
    print("   - Copy .streamlit/secrets.template.toml to .streamlit/secrets.toml")
    print("   - Fill in your Google Drive credentials")
    print("   - Add your Sarvam AI API key (optional)")
    
    print("\n3. Set up Google Drive folders:")
    print("   - Create folder structure for NCERT books")
    print("   - Share folders with your service account email")
    print("   - Note down folder IDs and update secrets.toml")
    
    print("\n4. Test the application:")
    print("   - Run: streamlit run app.py")
    print("   - Try generating a video with sample problems")
    
    print("\n5. Deploy to Streamlit Cloud:")
    print("   - Push code to GitHub")
    print("   - Connect repository to Streamlit Cloud")
    print("   - Add secrets through web interface")
    
    print("\n📚 Documentation:")
    print("   - Check README.md for detailed instructions")
    print("   - See templates/ directory for example Manim scripts")
    print("   - Review utils/ modules for customization")
    
    print("\n🆘 Need help?")
    print("   - Check logs in output/ directory")
    print("   - Review troubleshooting guide")
    print("   - Open GitHub issue for support")

def main():
    """Main setup function"""
    print("🚀 Math Video Creator - Quick Start Setup")
    print("="*50)
    
    # Check prerequisites
    if not check_python_version():
        sys.exit(1)
    
    if not check_system_dependencies():
        print("\n⚠️  Please install missing system dependencies and run again")
        sys.exit(1)
    
    # Install Python packages
    if not install_python_dependencies():
        print("\n❌ Failed to install Python dependencies")
        sys.exit(1)
    
    # Test Manim
    if not test_manim_installation():
        print("\n❌ Manim installation test failed")
        print("Please check the error messages above and try again")
        sys.exit(1)
    
    # Create project structure
    create_project_structure()
    
    # Test sample generation
    if not test_sample_generation():
        print("\n⚠️  Sample generation test failed, but setup can continue")
    
    # Setup git hooks if in git repository
    setup_git_hooks()
    
    # Print next steps
    print_next_steps()
    
    print(f"\n✨ Setup completed successfully!")
    print(f"📁 Project directory: {os.getcwd()}")

if __name__ == "__main__":
    main()
