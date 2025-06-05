#!/usr/bin/env python3
"""Script to generate .qm translation files from .ts files."""

import subprocess
import sys
from pathlib import Path


def find_lrelease():
    """Find the lrelease executable."""
    # Try to find lrelease in PySide6 installation
    try:
        import PySide6
        pyside_path = Path(PySide6.__file__).parent
        lrelease_path = pyside_path / "lrelease.exe"
        if lrelease_path.exists():
            return str(lrelease_path)
    except ImportError:
        pass
    
    # Try system PATH
    try:
        result = subprocess.run(["where", "lrelease"], capture_output=True, text=True, shell=True)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split('\n')[0]
    except:
        pass
    
    return None


def generate_qm_files():
    """Generate .qm files from all .ts files in i18n directory."""
    project_root = Path(__file__).parent.parent
    i18n_path = project_root / "src" / "jcselect" / "i18n"
    
    if not i18n_path.exists():
        print(f"Error: i18n directory not found: {i18n_path}")
        return False
    
    lrelease = find_lrelease()
    if not lrelease:
        print("Error: lrelease tool not found")
        print("Please ensure Qt tools are installed or PySide6 is available")
        return False
    
    print(f"Using lrelease: {lrelease}")
    
    # Find all .ts files
    ts_files = list(i18n_path.glob("*.ts"))
    if not ts_files:
        print(f"No .ts files found in {i18n_path}")
        return False
    
    success = True
    for ts_file in ts_files:
        qm_file = ts_file.with_suffix(".qm")
        
        print(f"Generating {qm_file.name} from {ts_file.name}...")
        
        try:
            result = subprocess.run(
                [lrelease, str(ts_file), "-qm", str(qm_file)],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print(f"  ✅ Successfully generated {qm_file.name}")
            else:
                print(f"  ❌ Failed to generate {qm_file.name}")
                print(f"     Error: {result.stderr}")
                success = False
                
        except Exception as e:
            print(f"  ❌ Error running lrelease: {e}")
            success = False
    
    return success


def main():
    """Main function."""
    print("🌐 Generating translation files...")
    
    if generate_qm_files():
        print("✅ Translation files generated successfully!")
        return 0
    else:
        print("❌ Failed to generate some translation files")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 