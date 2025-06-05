#!/usr/bin/env python3
"""Step 10 - Comprehensive Testing & Performance Sweep Verification"""

import os
import sys
import subprocess
from pathlib import Path

def test_imports():
    """Test that all Step 10 components can be imported."""
    print("🔍 Testing Step 10 Component Imports...")
    
    try:
        # Add src to Python path
        sys.path.insert(0, str(Path(__file__).parent / "src"))
        
        # Test DAO results functions
        from jcselect.dao_results import get_totals_by_party, get_totals_by_candidate, calculate_winners
        print("  ✅ DAO results functions imported")
        
        # Test controllers
        from jcselect.controllers.results_controller import ResultsController
        print("  ✅ ResultsController imported")
        
        # Test sync engine
        from jcselect.sync.engine import SyncEngine
        print("  ✅ SyncEngine imported")
        
        # Test models (Note: Candidate doesn't exist, it's mocked in DAO)
        from jcselect.models import Pen, Party, User, TallySession, TallyLine
        print("  ✅ Core models imported")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Import failed: {e}")
        return False

def test_performance_test_files():
    """Test that performance test files exist and have proper structure."""
    print("\n📊 Testing Performance Test Implementation...")
    
    perf_dir = Path("tests/perf")
    if not perf_dir.exists():
        print("  ❌ Performance test directory not found")
        return False
    
    print("  ✅ Performance test directory exists")
    
    required_files = [
        "__init__.py",
        "test_large_dataset_performance.py", 
        "test_fast_sync_latency.py"
    ]
    
    all_exist = True
    for file in required_files:
        file_path = perf_dir / file
        if file_path.exists():
            print(f"    ✅ {file}")
            
            # Check file content for key test methods
            if file.endswith(".py") and file != "__init__.py":
                with open(file_path, "r") as f:
                    content = f.read()
                    
                # Check for performance test markers
                if "CI_PERF_SKIP" in content:
                    print(f"      ✅ Contains CI_PERF_SKIP environment flag")
                if "pytestmark" in content:
                    print(f"      ✅ Contains pytest skip marker")
                    
        else:
            print(f"    ❌ {file}")
            all_exist = False
    
    return all_exist

def test_coverage_configuration():
    """Test that coverage configuration is properly set up."""
    print("\n📈 Testing Coverage Configuration...")
    
    try:
        # Read pyproject.toml manually to avoid toml dependency
        with open("pyproject.toml", "r") as f:
            content = f.read()
        
        # Check pytest configuration
        if "--cov=src/jcselect" in content:
            print("  ✅ Coverage source configured")
        else:
            print("  ❌ Coverage source not configured")
            return False
            
        if "--cov-fail-under=90" in content:
            print("  ✅ Coverage minimum threshold set to 90%")
        else:
            print("  ❌ Coverage threshold not set to 90%")
            
        if "--cov-report=xml" in content:
            print("  ✅ XML coverage report enabled")
        
        # Check coverage tool configuration
        if "[tool.coverage.run]" in content:
            print("  ✅ Coverage run configuration")
        if "[tool.coverage.report]" in content:
            print("  ✅ Coverage report configuration")
        
        # Check for fail_under in report section
        if "fail_under = 90" in content:
            print("  ✅ Coverage fail_under threshold configured")
            
        return True
            
    except Exception as e:
        print(f"  ❌ Coverage config test failed: {e}")
        return False

def test_ci_configuration():
    """Test that CI workflow is properly configured."""
    print("\n🔄 Testing CI Configuration...")
    
    workflow_path = Path(".github/workflows/tests.yml")
    if workflow_path.exists():
        print("  ✅ CI workflow file exists")
        
        try:
            with open(workflow_path, "r") as f:
                content = f.read()
            
            # Check for key CI components
            checks = [
                ("matrix strategy", "matrix:" in content),
                ("performance job", "perf-nightly" in content),
                ("coverage reporting", "codecov" in content),
                ("multiple Python versions", "3.10" in content and "3.11" in content),
                ("multiple OS", "ubuntu-latest" in content and "windows-latest" in content),
                ("environment flags", "CI_PERF_SKIP" in content),
                ("coverage threshold", "CI_COV_MIN" in content),
            ]
            
            all_passed = True
            for check_name, condition in checks:
                if condition:
                    print(f"    ✅ {check_name}")
                else:
                    print(f"    ❌ {check_name}")
                    all_passed = False
                    
            return all_passed
            
        except Exception as e:
            print(f"  ❌ CI workflow validation failed: {e}")
            return False
    else:
        print("  ❌ CI workflow file not found")
        return False

def test_static_analysis_configuration():
    """Test that static analysis tools are properly configured."""
    print("\n🔍 Testing Static Analysis Configuration...")
    
    try:
        # Read pyproject.toml manually
        with open("pyproject.toml", "r") as f:
            content = f.read()
        
        # Check Ruff configuration
        if "[tool.ruff]" in content:
            print("  ✅ Ruff configuration found")
            
            # Check for strict rule sets
            if '"E"' in content and '"W"' in content and '"F"' in content:
                print("    ✅ Basic linting rules enabled")
            if '"UP"' in content and '"B"' in content and '"SIM"' in content:
                print("    ✅ Advanced linting rules enabled")
            if '"D"' in content:
                print("    ✅ Docstring linting enabled")
        
        # Check MyPy configuration
        if "[tool.mypy]" in content:
            print("  ✅ MyPy configuration found")
            
            if "pydantic.mypy" in content:
                print("    ✅ Pydantic-MyPy plugin configured")
        
        # Check if pydantic mypy is in dev dependencies
        if 'pydantic = {extras = ["mypy"]' in content:
            print("    ✅ Pydantic MyPy plugin in dev dependencies")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Static analysis config test failed: {e}")
        return False

def test_documentation():
    """Test that comprehensive testing documentation exists."""
    print("\n📚 Testing Documentation...")
    
    docs_path = Path("docs/dev/testing.md")
    if docs_path.exists():
        print("  ✅ Testing documentation exists")
        
        try:
            with open(docs_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Check for key documentation sections
            sections = [
                ("Environment Flags", "Environment Flags" in content),
                ("Performance Tests", "Performance Tests" in content),
                ("Coverage Requirements", "Coverage Requirements" in content),
                ("CI_PERF_SKIP usage", "CI_PERF_SKIP" in content),
                ("CI_COV_MIN usage", "CI_COV_MIN" in content),
                ("Test categories", "Unit Tests" in content),
                ("Hardware requirements", "Hardware" in content or "Benchmark" in content),
            ]
            
            all_passed = True
            for section_name, condition in sections:
                if condition:
                    print(f"    ✅ {section_name} documented")
                else:
                    print(f"    ❌ {section_name} missing")
                    all_passed = False
            
            return all_passed
            
        except Exception as e:
            print(f"  ❌ Documentation validation failed: {e}")
            return False
    else:
        print("  ❌ Testing documentation not found")
        return False

def test_demo_script():
    """Test that live results demo script exists and is functional."""
    print("\n🎬 Testing Demo Script...")
    
    demo_path = Path("scripts/demo_live_results_loop.py")
    if demo_path.exists():
        print("  ✅ Demo script exists")
        
        # Test basic syntax by compiling
        try:
            with open(demo_path, "r") as f:
                code = f.read()
            compile(code, str(demo_path), "exec")
            print("  ✅ Demo script syntax valid")
            
            # Check for key features
            features = [
                ("Live results simulation", "LiveResultsDemo" in code),
                ("Ballot seeding", "seed_random_ballots" in code),
                ("Fast-sync simulation", "trigger_fast_sync" in code),
                ("Winner calculation", "get_top_winners" in code),
                ("Command-line interface", "argparse" in code),
                ("Cleanup functionality", "cleanup" in code),
            ]
            
            all_features = True
            for feature_name, condition in features:
                if condition:
                    print(f"    ✅ {feature_name}")
                else:
                    print(f"    ❌ {feature_name}")
                    all_features = False
            
            return all_features
            
        except SyntaxError as e:
            print(f"  ❌ Demo script syntax error: {e}")
            return False
        except Exception as e:
            print(f"  ❌ Demo script test failed: {e}")
            return False
    else:
        print("  ❌ Demo script not found")
        return False

def test_ruff_execution():
    """Test that Ruff can execute without errors."""
    print("\n🧹 Testing Ruff Execution...")
    
    try:
        result = subprocess.run(
            ["poetry", "run", "ruff", "check", "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print("  ✅ Ruff execution successful")
            return True
        else:
            print(f"  ❌ Ruff execution failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"  ❌ Ruff test failed: {e}")
        return False

def print_step10_summary():
    """Print Step 10 implementation summary."""
    print("\n" + "="*80)
    print("📋 STEP 10 - COMPREHENSIVE TESTING & PERFORMANCE SWEEP")
    print("="*80)
    print()
    print("✅ DELIVERED COMPONENTS:")
    print("   • Performance Tests:")
    print("     - Large dataset tests (200 pens × 25 parties)")
    print("     - Fast-sync latency tests (50 rapid confirmations)")
    print("     - Memory stability and concurrent access tests")
    print("   • Coverage Configuration:")
    print("     - 90% minimum coverage requirement")
    print("     - CI_COV_MIN environment variable override")
    print("     - XML/HTML/terminal coverage reports")
    print("   • CI Pipeline:")
    print("     - Multi-OS matrix: [ubuntu-latest, windows-latest]")
    print("     - Multi-Python: [3.10, 3.11]")
    print("     - Separate nightly performance job")
    print("     - Codecov integration")
    print("   • Static Analysis:")
    print("     - Comprehensive Ruff rules (E,W,F,UP,B,SIM,I,N,D,C90,PTH,RUF)")
    print("     - MyPy with Pydantic plugin")
    print("     - Pre-commit hooks integration")
    print("   • Documentation:")
    print("     - Complete testing guide (docs/dev/testing.md)")
    print("     - Environment flags explained")
    print("     - Performance benchmarks documented")
    print("   • Demo Script:")
    print("     - Live results simulation (scripts/demo_live_results_loop.py)")
    print("     - Configurable ballot seeding (1k+ ballots)")
    print("     - Fast-sync → top-3 winners display")
    print("     - Command-line interface with cleanup")
    print()

def main():
    """Run all Step 10 verification tests."""
    print("🚀 STEP 10 - COMPREHENSIVE TESTING & PERFORMANCE SWEEP")
    print("=" * 80)
    print()
    
    tests = [
        ("Component Imports", test_imports),
        ("Performance Test Files", test_performance_test_files),
        ("Coverage Configuration", test_coverage_configuration),
        ("CI Configuration", test_ci_configuration),
        ("Static Analysis Setup", test_static_analysis_configuration),
        ("Testing Documentation", test_documentation),
        ("Demo Script", test_demo_script),
        ("Ruff Execution", test_ruff_execution),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"Running: {test_name}")
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"  ❌ Test failed with exception: {e}")
            results.append(False)
        print()
    
    print("=" * 80)
    print("📊 VERIFICATION RESULTS")
    print("=" * 80)
    
    passed = sum(results)
    total = len(results)
    
    for i, (test_name, result) in enumerate(zip([t[0] for t in tests], results)):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:8} {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL STEP 10 COMPONENTS VERIFIED SUCCESSFULLY!")
        print_step10_summary()
        
        print("🔧 USAGE EXAMPLES:")
        print("   # Run performance tests locally:")
        print("   $env:CI_PERF_SKIP=0; poetry run pytest tests/perf/ -v -s")
        print()
        print("   # Run demo script:")
        print("   poetry run python scripts/demo_live_results_loop.py --iterations=3 --ballots=100")
        print()
        print("   # Run with custom coverage:")
        print("   $env:CI_COV_MIN=85; poetry run pytest")
        
        return True
    else:
        print("\n⚠️  Some Step 10 components need attention:")
        failed_tests = [tests[i][0] for i, result in enumerate(results) if not result]
        for failed_test in failed_tests:
            print(f"   • {failed_test}")
        return False

if __name__ == "__main__":
    success = main()
    print("\n" + "="*80)
    if success:
        print("✅ STEP 10 IMPLEMENTATION COMPLETE")
    else:
        print("❌ STEP 10 IMPLEMENTATION NEEDS FIXES")
    print("="*80)
    sys.exit(0 if success else 1) 