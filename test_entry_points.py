#!/usr/bin/env python3
"""
Test Entry Points
================

Quick test to verify admin and operator entry points work correctly.
"""

import subprocess
import sys
from pathlib import Path

def test_entry_point(entry_point: str, description: str) -> bool:
    """Test an entry point by importing it."""
    print(f"🔍 Testing {description} ({entry_point})...")
    
    try:
        result = subprocess.run(
            [sys.executable, "-c", f"import {entry_point}; print('[OK] {description} import successful')"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print(f"✅ {description} entry point working")
            return True
        else:
            print(f"❌ {description} failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ {description} error: {e}")
        return False

def test_poetry_scripts() -> bool:
    """Test that poetry scripts are available."""
    print("🔍 Testing poetry script commands...")
    
    scripts = [
        ("jcselect-admin", "Admin App"),
        ("jcselect-operator", "Operator App"),
    ]
    
    success = True
    for script, description in scripts:
        try:
            result = subprocess.run(
                [script, "--help"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 or "usage:" in result.stdout.lower() or "help" in result.stdout.lower():
                print(f"✅ {description} command ({script}) available")
            else:
                print(f"❌ {description} command ({script}) not working")
                success = False
                
        except FileNotFoundError:
            print(f"⚠️  {description} command ({script}) not found in PATH")
            print(f"   Try: poetry run {script}")
            success = False
        except Exception as e:
            print(f"❌ {description} command error: {e}")
            success = False
    
    return success

def test_poetry_run_scripts() -> bool:
    """Test poetry run commands."""
    print("🔍 Testing poetry run commands...")
    
    scripts = [
        ("jcselect-admin", "Admin App"),
        ("jcselect-operator", "Operator App"),
    ]
    
    success = True
    for script, description in scripts:
        try:
            result = subprocess.run(
                ["poetry", "run", script, "--help"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 or "usage:" in result.stdout.lower() or "help" in result.stdout.lower():
                print(f"✅ {description} via poetry run working")
            else:
                print(f"❌ {description} via poetry run not working")
                success = False
                
        except Exception as e:
            print(f"❌ {description} poetry run error: {e}")
            success = False
    
    return success

def main() -> int:
    """Main test function."""
    print("🧪 Testing JCSELECT Entry Points")
    print("=" * 35)
    
    # Check if we're in the right directory
    if not Path("pyproject.toml").exists():
        print("❌ Please run this script from the jcselect project root directory")
        return 1
    
    success = True
    
    # Test import-based entry points
    print("\n📦 Testing Import-Based Entry Points:")
    if not test_entry_point("jcselect.admin", "Admin Entry Point"):
        success = False
    if not test_entry_point("jcselect.operator", "Operator Entry Point"):
        success = False
    if not test_entry_point("jcselect.main", "Main Entry Point"):
        success = False
    
    # Test poetry script commands
    print("\n🎯 Testing Poetry Script Commands:")
    if not test_poetry_scripts():
        print("\n🔄 Trying poetry run commands:")
        if not test_poetry_run_scripts():
            success = False
    
    # Summary
    print("\n" + "=" * 35)
    if success:
        print("✅ All entry points working correctly!")
        print("\nReady to launch:")
        print("  poetry run jcselect-admin    (admin interface)")
        print("  poetry run jcselect-operator (operator interface)")
        return 0
    else:
        print("❌ Some entry points have issues")
        print("\nTroubleshooting:")
        print("  1. Run: poetry install")
        print("  2. Check dependencies in pyproject.toml")
        print("  3. Verify Python path includes src/")
        print("\nAlternative launch methods:")
        print("  poetry run jcselect-admin")
        print("  poetry run jcselect-operator")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 