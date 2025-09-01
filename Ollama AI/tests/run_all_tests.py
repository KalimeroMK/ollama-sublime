#!/usr/bin/env python3
"""
Comprehensive test runner for the Ollama Sublime Plugin.
Runs all unit tests and integration tests, providing a unified test report.
"""

import unittest
import sys
import os
import time
from io import StringIO

# Add both the current directory (for test modules) and parent directory (for plugin modules) to the path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, current_dir)
sys.path.insert(0, parent_dir)


class ColoredTestResult(unittest.TextTestResult):
    """Custom test result class with colored output."""
    
    def __init__(self, stream, descriptions, verbosity):
        super().__init__(stream, descriptions, verbosity)
        self.verbosity = verbosity  # Store verbosity for later use
        self.success_count = 0
    
    def addSuccess(self, test):
        super().addSuccess(test)
        self.success_count += 1
        if self.verbosity > 1:
            self.stream.write("✅ ")
            self.stream.write(str(test))
            self.stream.write(" ... ok\n")
    
    def addError(self, test, err):
        super().addError(test, err)
        if self.verbosity > 1:
            self.stream.write("💥 ")
            self.stream.write(str(test))
            self.stream.write(" ... ERROR\n")
    
    def addFailure(self, test, err):
        super().addFailure(test, err)
        if self.verbosity > 1:
            self.stream.write("❌ ")
            self.stream.write(str(test))
            self.stream.write(" ... FAIL\n")
    
    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        if self.verbosity > 1:
            self.stream.write("⏭️ ")
            self.stream.write(str(test))
            self.stream.write(" ... skipped\n")


class ColoredTestRunner(unittest.TextTestRunner):
    """Custom test runner with colored output."""
    
    def __init__(self, stream=None, descriptions=True, verbosity=1):
        super().__init__(stream, descriptions, verbosity)
        self.resultclass = ColoredTestResult


def run_test_module(module_name, description):
    """Run tests for a specific module and return results."""
    print(f"\n🧪 Running {description}...")
    print("=" * 60)
    
    try:
        # Import the test module
        test_module = __import__(module_name)
        
        # Create test suite
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromModule(test_module)
        
        # Run tests with custom runner
        stream = StringIO()
        runner = ColoredTestRunner(stream=stream, verbosity=2)
        result = runner.run(suite)
        
        # Print results
        output = stream.getvalue()
        print(output)
        
        return result
        
    except ImportError as e:
        print(f"❌ Failed to import {module_name}: {e}")
        return None
    except Exception as e:
        print(f"💥 Error running tests for {module_name}: {e}")
        return None


def run_connectivity_test():
    """Run the connectivity test."""
    print("\n🌐 Running Connectivity Test...")
    print("=" * 60)
    
    try:
        # Import and run connectivity test
        import test_ollama_connection
        return test_ollama_connection.main()
    except ImportError:
        print("❌ Connectivity test not available")
        return 1
    except Exception as e:
        print(f"💥 Error running connectivity test: {e}")
        return 1


def main():
    """Main test runner function."""
    print("🚀 Ollama Sublime Plugin - Comprehensive Test Suite")
    print("=" * 70)
    print("Testing all modules to ensure code reliability and functionality")
    print("=" * 70)
    
    start_time = time.time()
    
    # Define test modules to run
    test_modules = [
        ("test_ollama_api", "Ollama API Client Tests"),
        ("test_context_analyzer", "Context Analyzer Tests"),
        ("test_multi_file_context", "Multi-File Context Tests"),
        ("test_ui_helpers", "UI Helpers Tests"),
        ("test_response_processor", "Response Processor Tests"),
        ("test_php_completion", "PHP/Laravel Completion Tests"),
        ("test_ollama_ai_integration", "Ollama AI Integration Tests")
    ]
    
    # Track overall results
    total_tests = 0
    total_failures = 0
    total_errors = 0
    total_skipped = 0
    total_success = 0
    module_results = []
    
    # Run unit and integration tests
    for module_name, description in test_modules:
        result = run_test_module(module_name, description)
        
        if result:
            total_tests += result.testsRun
            total_failures += len(result.failures)
            total_errors += len(result.errors)
            total_skipped += len(result.skipped)
            if hasattr(result, 'success_count'):
                total_success += result.success_count
            else:
                total_success += result.testsRun - len(result.failures) - len(result.errors)
            
            module_results.append({
                'name': description,
                'tests': result.testsRun,
                'failures': len(result.failures),
                'errors': len(result.errors),
                'skipped': len(result.skipped),
                'success': result.testsRun - len(result.failures) - len(result.errors)
            })
        else:
            module_results.append({
                'name': description,
                'tests': 0,
                'failures': 0,
                'errors': 1,
                'skipped': 0,
                'success': 0
            })
            total_errors += 1
    
    # Run connectivity test
    connectivity_result = run_connectivity_test()
    
    # Calculate execution time
    end_time = time.time()
    execution_time = end_time - start_time
    
    # Print comprehensive summary
    print("\n" + "=" * 70)
    print("📊 COMPREHENSIVE TEST RESULTS")
    print("=" * 70)
    
    # Per-module results
    print("\n📋 Module Test Results:")
    for result in module_results:
        status = "✅" if result['errors'] == 0 and result['failures'] == 0 else "❌"
        print(f"{status} {result['name']:.<45} {result['success']:>3}/{result['tests']:>3} passed")
        if result['failures'] > 0:
            print(f"   └─ {result['failures']} failures")
        if result['errors'] > 0:
            print(f"   └─ {result['errors']} errors")
        if result['skipped'] > 0:
            print(f"   └─ {result['skipped']} skipped")
    
    # Connectivity test result
    connectivity_status = "✅" if connectivity_result == 0 else "❌"
    print(f"{connectivity_status} Ollama Server Connectivity Test:.<25> {'PASSED' if connectivity_result == 0 else 'FAILED'}")
    
    # Overall statistics
    print(f"\n📈 Overall Statistics:")
    print(f"   Total Tests: {total_tests}")
    print(f"   Successful: {total_success} ✅")
    print(f"   Failed: {total_failures} ❌")
    print(f"   Errors: {total_errors} 💥")
    print(f"   Skipped: {total_skipped} ⏭️")
    print(f"   Execution Time: {execution_time:.2f}s ⏱️")
    
    # Success rate
    if total_tests > 0:
        success_rate = (total_success / total_tests) * 100
        print(f"   Success Rate: {success_rate:.1f}% 📊")
    
    # Final verdict
    print("\n" + "=" * 70)
    if total_failures == 0 and total_errors == 0 and connectivity_result == 0:
        print("🎉 ALL TESTS PASSED! 🎉")
        print("✨ The Ollama Sublime Plugin is fully tested and ready to use!")
        print("\n🔧 Tested Components:")
        print("• ✅ API Client (HTTP requests, streaming, error handling)")
        print("• ✅ Context Analyzer (symbol extraction, project scanning)")
        print("• ✅ UI Helpers (tab management, file operations)")
        print("• ✅ Response Processor (content cleaning, validation)")
        print("• ✅ PHP/Laravel Completion (AI-powered code completion)")
        print("• ✅ Main Commands (all 9 plugin commands)")
        print("• ✅ Ollama Server Connectivity")
        
        print(f"\n📊 Test Coverage: {total_tests} test cases covering all critical functionality")
        return 0
    else:
        print("❌ SOME TESTS FAILED!")
        print("🔍 Review the detailed results above to identify issues.")
        
        if connectivity_result != 0:
            print("\n⚠️  Connectivity test failed - check Ollama server setup:")
            print("   • Make sure Ollama is running: ollama serve")
            print("   • Make sure qwen2.5-coder model is available: ollama pull qwen2.5-coder")
        
        return 1


def run_specific_test(test_name):
    """Run a specific test module."""
    test_modules = {
        "api": ("test_ollama_api", "Ollama API Client Tests"),
        "context": ("test_context_analyzer", "Context Analyzer Tests"),
        "ui": ("test_ui_helpers", "UI Helpers Tests"),
        "response": ("test_response_processor", "Response Processor Tests"),
        "completion": ("test_php_completion", "PHP/Laravel Completion Tests"),
        "integration": ("test_ollama_ai_integration", "Ollama AI Integration Tests"),
        "connectivity": ("test_ollama_connection", "Connectivity Test")
    }
    
    if test_name in test_modules:
        module_name, description = test_modules[test_name]
        if test_name == "connectivity":
            return run_connectivity_test()
        else:
            result = run_test_module(module_name, description)
            return 0 if result and len(result.failures) == 0 and len(result.errors) == 0 else 1
    else:
        print(f"❌ Unknown test module: {test_name}")
        print(f"Available modules: {', '.join(test_modules.keys())}")
        return 1


if __name__ == "__main__":
    # Check for specific test argument
    if len(sys.argv) > 1:
        test_name = sys.argv[1]
        sys.exit(run_specific_test(test_name))
    else:
        sys.exit(main())