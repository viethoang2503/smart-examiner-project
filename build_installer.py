import os
import sys
import subprocess
import shutil

def find_inno_setup():
    """Look for Inno Setup Compiler in default Windows paths"""
    paths = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
        r"D:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    ]
    
    for path in paths:
        if os.path.exists(path):
            return path
            
    return None

def main():
    print("="*60)
    print("FocusGuard Smart Examiner - Installer Builder")
    print("="*60)
    
    if sys.platform != "win32":
        print("❌ ERROR: This script can only be run on Windows!")
        print("Please run this on the target Windows machine.")
        sys.exit(1)
        
    # Check if 'dist' folder exists (meaning PyInstaller was already run)
    if not os.path.exists("dist") or not os.path.exists(r"dist\FocusGuard_Client") or not os.path.exists(r"dist\FocusGuard_Server"):
        print("⚠️ Warning: PyInstaller 'dist' directories not found or incomplete.")
        print("⏳ Running build_windows.bat first to generate executables...")
        
        try:
            subprocess.run(["build_windows.bat"], check=True, shell=True)
        except Exception as e:
            print(f"❌ Failed to build executables: {e}")
            sys.exit(1)
            
    print("✅ Found PyInstaller 'dist' distributions.")
    
    # Locate Inno Setup
    iscc_path = find_inno_setup()
    if not iscc_path:
        print("\n❌ ERROR: Inno Setup Compiler (ISCC.exe) not found!")
        print("Please download and install Inno Setup 6 from:")
        print("https://jrsoftware.org/isdl.php")
        sys.exit(1)
        
    print(f"✅ Found Inno Setup at: {iscc_path}")
    
    # Check if installer.iss exists
    if not os.path.exists("installer.iss"):
        print("❌ ERROR: installer.iss not found in current directory!")
        sys.exit(1)
        
    # Run Inno Setup Compiler
    print("\n📦 Compiling Setup_SmartExaminer.exe...")
    try:
        # Use subprocess to call ISCC
        subprocess.run([iscc_path, "installer.iss"], check=True)
        
        print("\n" + "="*60)
        print("🎉 SUCCESS! Installer compilation complete.")
        print("📍 Check the 'Output' folder for your Setup_SmartExaminer.exe file.")
        print("="*60)
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Inno Setup compilation failed with error code: {e.returncode}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
