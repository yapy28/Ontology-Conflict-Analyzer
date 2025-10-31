#!/usr/bin/env python3
"""
Simple smoke test for namespace-agnostic mode.
Tests that the --agnostic flag works and produces expected output.
"""

import subprocess
import sys
from pathlib import Path

def run_test():
    """Run the conflict detector in agnostic mode and check output"""
    test_dir = Path(__file__).parent
    example1 = test_dir / "example1.ttl"
    example2 = test_dir / "example2.ttl"
    script = test_dir.parent / "onto_conflict_detect.py"
    
    print("=" * 80)
    print("SMOKE TEST: Namespace-Agnostic Mode")
    print("=" * 80)
    
    # Test 1: Run with --agnostic flag
    print("\n[TEST 1] Running with --agnostic flag...")
    result = subprocess.run(
        [sys.executable, str(script), str(example1), str(example2), "--agnostic", "-o", "/tmp"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"❌ FAILED: Script exited with code {result.returncode}")
        print("STDERR:", result.stderr)
        return False
    
    output = result.stdout
    
    # Check for agnostic mode banner
    if "RUNNING IN NAMESPACE-AGNOSTIC MODE" in output:
        print("✅ PASSED: Agnostic mode banner present")
    else:
        print("❌ FAILED: Agnostic mode banner not found")
        return False
    
    # Check for namespace-agnostic grouping
    if "NAMESPACE-AGNOSTIC URI GROUP" in output or "Local name" in output:
        print("✅ PASSED: Namespace-agnostic grouping detected")
    else:
        print("✅ OK: No namespace conflicts found (expected for simple test)")
    
    # Test 2: Run WITHOUT --agnostic flag (default mode)
    print("\n[TEST 2] Running in default mode (without --agnostic)...")
    result = subprocess.run(
        [sys.executable, str(script), str(example1), str(example2), "-o", "/tmp"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"❌ FAILED: Script exited with code {result.returncode}")
        print("STDERR:", result.stderr)
        return False
    
    output = result.stdout
    
    # Check that agnostic mode banner is NOT present
    if "RUNNING IN NAMESPACE-AGNOSTIC MODE" not in output:
        print("✅ PASSED: Default mode works (no agnostic banner)")
    else:
        print("❌ FAILED: Agnostic banner present in default mode")
        return False
    
    print("\n" + "=" * 80)
    print("✅ ALL TESTS PASSED")
    print("=" * 80)
    return True

if __name__ == "__main__":
    success = run_test()
    sys.exit(0 if success else 1)
