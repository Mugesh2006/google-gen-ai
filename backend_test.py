import requests
import sys
import json
from datetime import datetime
import os

class LegalDocAPITester:
    def __init__(self, base_url="https://legaldoc-ai-1.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.analysis_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, files=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}" if endpoint else self.api_url
        headers = {}
        if data and not files:
            headers['Content-Type'] = 'application/json'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                if files:
                    response = requests.post(url, files=files, timeout=60)
                else:
                    response = requests.post(url, json=data, headers=headers, timeout=60)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=30)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    if method == 'GET' and endpoint == '':
                        print(f"   Response: {response_data}")
                    elif 'analyze-document' in endpoint and method == 'POST':
                        print(f"   Analysis ID: {response_data.get('id', 'N/A')}")
                        print(f"   Overall Risk Score: {response_data.get('overall_risk_score', 'N/A')}/10")
                        print(f"   Clauses Found: {len(response_data.get('clauses', []))}")
                        self.analysis_id = response_data.get('id')
                    return True, response_data
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"   Error: {error_detail}")
                except:
                    print(f"   Error: {response.text}")
                return False, {}

        except requests.exceptions.Timeout:
            print(f"❌ Failed - Request timed out")
            return False, {}
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test the root API endpoint"""
        return self.run_test(
            "Root API Endpoint",
            "GET",
            "",
            200
        )

    def test_document_analysis(self):
        """Test document analysis with the test contract"""
        test_file_path = "/app/test_contract.txt"
        
        if not os.path.exists(test_file_path):
            print(f"❌ Test file not found: {test_file_path}")
            return False, {}
        
        with open(test_file_path, 'rb') as f:
            files = {'file': ('test_contract.txt', f, 'text/plain')}
            return self.run_test(
                "Document Analysis",
                "POST",
                "analyze-document",
                200,
                files=files
            )

    def test_get_analyses(self):
        """Test getting all analyses"""
        return self.run_test(
            "Get All Analyses",
            "GET",
            "analyses",
            200
        )

    def test_get_specific_analysis(self):
        """Test getting a specific analysis"""
        if not self.analysis_id:
            print("⚠️  Skipping specific analysis test - no analysis ID available")
            return True, {}
        
        return self.run_test(
            "Get Specific Analysis",
            "GET",
            f"analysis/{self.analysis_id}",
            200
        )

    def test_delete_analysis(self):
        """Test deleting an analysis"""
        if not self.analysis_id:
            print("⚠️  Skipping delete test - no analysis ID available")
            return True, {}
        
        return self.run_test(
            "Delete Analysis",
            "DELETE",
            f"analysis/{self.analysis_id}",
            200
        )

    def validate_analysis_structure(self, analysis_data):
        """Validate the structure of analysis response"""
        print("\n🔍 Validating Analysis Structure...")
        
        required_fields = ['id', 'document_id', 'filename', 'document_type', 'clauses', 
                          'summary', 'recommendations', 'overall_risk_score', 'created_at']
        
        missing_fields = []
        for field in required_fields:
            if field not in analysis_data:
                missing_fields.append(field)
        
        if missing_fields:
            print(f"❌ Missing required fields: {missing_fields}")
            return False
        
        # Validate clauses structure
        clauses = analysis_data.get('clauses', [])
        if not clauses:
            print("❌ No clauses found in analysis")
            return False
        
        print(f"✅ Found {len(clauses)} clauses")
        
        # Check clause structure
        clause_fields = ['id', 'clause_text', 'risk_level', 'risk_score', 'explanation']
        for i, clause in enumerate(clauses[:3]):  # Check first 3 clauses
            for field in clause_fields:
                if field not in clause:
                    print(f"❌ Clause {i+1} missing field: {field}")
                    return False
        
        # Validate risk levels
        risk_levels = [clause.get('risk_level') for clause in clauses]
        valid_levels = ['low', 'medium', 'high']
        invalid_levels = [level for level in risk_levels if level not in valid_levels]
        
        if invalid_levels:
            print(f"❌ Invalid risk levels found: {set(invalid_levels)}")
            return False
        
        print("✅ Analysis structure is valid")
        return True

def main():
    print("🚀 Starting AI Legal Document Assistant API Tests")
    print("=" * 60)
    
    tester = LegalDocAPITester()
    
    # Test 1: Root endpoint
    success, _ = tester.test_root_endpoint()
    if not success:
        print("❌ Root endpoint failed - stopping tests")
        return 1
    
    # Test 2: Document analysis (most important test)
    print("\n" + "=" * 60)
    print("🧠 Testing AI Document Analysis (This may take 30-60 seconds)")
    print("=" * 60)
    
    success, analysis_data = tester.test_document_analysis()
    if not success:
        print("❌ Document analysis failed - this is critical!")
        return 1
    
    # Validate analysis structure
    if analysis_data:
        if not tester.validate_analysis_structure(analysis_data):
            print("❌ Analysis structure validation failed")
            return 1
    
    # Test 3: Get all analyses
    tester.test_get_analyses()
    
    # Test 4: Get specific analysis
    tester.test_get_specific_analysis()
    
    # Test 5: Delete analysis (optional)
    # tester.test_delete_analysis()
    
    # Print final results
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS")
    print("=" * 60)
    print(f"Tests Run: {tester.tests_run}")
    print(f"Tests Passed: {tester.tests_passed}")
    print(f"Success Rate: {(tester.tests_passed/tester.tests_run)*100:.1f}%")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed! Backend API is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())