#!/usr/bin/env python3
"""
FocusGuard Build Script
Builds client and server executables using PyInstaller
"""

import os
import sys
import subprocess
import shutil

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(PROJECT_ROOT, 'dist')
BUILD_DIR = os.path.join(PROJECT_ROOT, 'build')


def check_pyinstaller():
    """Check if PyInstaller is installed"""
    try:
        import PyInstaller
        print(f"✅ PyInstaller {PyInstaller.__version__} found")
        return True
    except ImportError:
        print("❌ PyInstaller not found")
        print("Install with: pip install pyinstaller")
        return False


def clean_build():
    """Clean previous build artifacts"""
    print("\n🧹 Cleaning previous builds...")
    
    for dir_path in [DIST_DIR, BUILD_DIR]:
        if os.path.exists(dir_path):
            shutil.rmtree(dir_path)
            print(f"  Removed: {dir_path}")


def build_client():
    """Build client executable"""
    print("\n📦 Building FocusGuard Client...")
    
    spec_file = os.path.join(PROJECT_ROOT, 'focusguard_client.spec')
    
    if not os.path.exists(spec_file):
        print(f"❌ Spec file not found: {spec_file}")
        return False
    
    result = subprocess.run(
        [sys.executable, '-m', 'PyInstaller', spec_file, '--clean'],
        cwd=PROJECT_ROOT
    )
    
    if result.returncode == 0:
        print("✅ Client build successful!")
        return True
    else:
        print("❌ Client build failed!")
        return False


def build_server():
    """Build server executable"""
    print("\n📦 Building FocusGuard Server...")
    
    spec_file = os.path.join(PROJECT_ROOT, 'focusguard_server.spec')
    
    if not os.path.exists(spec_file):
        print(f"❌ Spec file not found: {spec_file}")
        return False
    
    result = subprocess.run(
        [sys.executable, '-m', 'PyInstaller', spec_file, '--clean'],
        cwd=PROJECT_ROOT
    )
    
    if result.returncode == 0:
        print("✅ Server build successful!")
        return True
    else:
        print("❌ Server build failed!")
        return False


def show_results():
    """Show build results"""
    print("\n" + "=" * 60)
    print("BUILD RESULTS")
    print("=" * 60)
    
    if os.path.exists(DIST_DIR):
        for item in os.listdir(DIST_DIR):
            item_path = os.path.join(DIST_DIR, item)
            if os.path.isfile(item_path):
                size = os.path.getsize(item_path) / (1024 * 1024)
                print(f"  📄 {item} ({size:.1f} MB)")
    else:
        print("  No output files found")


def main():
    print("=" * 60)
    print("FocusGuard Build System")
    print("=" * 60)
    
    if not check_pyinstaller():
        sys.exit(1)
    
    # Parse arguments
    build_client_flag = '--client' in sys.argv or '--all' in sys.argv or len(sys.argv) == 1
    build_server_flag = '--server' in sys.argv or '--all' in sys.argv or len(sys.argv) == 1
    clean_flag = '--clean' in sys.argv
    
    if clean_flag:
        clean_build()
    
    success = True
    
    if build_client_flag:
        if not build_client():
            success = False
    
    if build_server_flag:
        if not build_server():
            success = False
    
    show_results()
    
    if success:
        print("\n✅ Build completed successfully!")
    else:
        print("\n⚠️ Build completed with errors")
        sys.exit(1)


if __name__ == "__main__":
    main()
