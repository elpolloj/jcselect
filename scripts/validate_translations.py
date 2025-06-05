#!/usr/bin/env python3
"""Script to validate translation loading."""

import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QTranslator
from PySide6.QtGui import QGuiApplication


def validate_translations():
    """Validate that translations load correctly."""
    app = QGuiApplication(sys.argv)
    
    # Load translations
    translator = QTranslator(app)
    i18n_path = Path(__file__).parent.parent / "src" / "jcselect" / "i18n"
    
    print(f"Checking translation files in: {i18n_path}")
    
    # Check if .ts file exists
    ts_file = i18n_path / "ar_LB.ts"
    print(f"Arabic .ts file exists: {ts_file.exists()}")
    
    # Check if .qm file exists
    qm_file = i18n_path / "ar_LB.qm"
    print(f"Arabic .qm file exists: {qm_file.exists()}")
    
    if qm_file.exists():
        # Try to load the translation
        if translator.load(str(qm_file)):
            app.installTranslator(translator)
            print("✅ Arabic translation loaded successfully!")
            
            # Test some basic translations
            test_strings = [
                "Search voters...",
                "Vote recorded successfully", 
                "Error",
                "No search results found"
            ]
            
            print("\nTesting translations:")
            for string in test_strings:
                translated = app.translate("VoterSearchWindow", string)
                print(f"  '{string}' -> '{translated}'")
            
            return True
        else:
            print("❌ Failed to load Arabic translation")
            return False
    else:
        print("❌ Arabic .qm file not found")
        return False


def main():
    """Main function."""
    print("🌐 Validating translations...")
    
    if validate_translations():
        print("\n✅ Translation validation successful!")
        return 0
    else:
        print("\n❌ Translation validation failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 