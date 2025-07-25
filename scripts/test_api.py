"""
Test the Sports Prediction System API endpoints.
Provides comprehensive testing of all function endpoints.
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, Any, List
from datetime import datetime


class SportsPredictionTester:
    """Test harness for the Sports Prediction System."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session = None
        self.test_results = []
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def run_test(self, test_name: str, endpoint: str, method: str = "GET", 
                      params: Dict[str, Any] = None, data: Dict[str, Any] = None,
                      headers: Dict[str, str] = None) -> Dict[str, Any]:
        """Run a single test against an endpoint."""
        print(f"\n🧪 Testing: {test_name}")
        print(f"   Endpoint: {method} {endpoint}")
        
        start_time = time.time()
        
        try:
            url = f"{self.base_url}{endpoint}"
            
            if method.upper() == "GET":
                async with self.session.get(url, params=params, headers=headers) as response:
                    response_data = await response.json()
                    status_code = response.status
            elif method.upper() == "POST":
                async with self.session.post(url, params=params, json=data, headers=headers) as response:
                    response_data = await response.json()
                    status_code = response.status
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            duration = time.time() - start_time
            
            # Evaluate test result
            success = 200 <= status_code < 300
            
            result = {
                "test_name": test_name,
                "endpoint": endpoint,
                "method": method,
                "status_code": status_code,
                "success": success,
                "duration_ms": round(duration * 1000, 2),
                "response_size": len(json.dumps(response_data)),
                "response": response_data,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if success:
                print(f"   ✅ Success ({status_code}) - {result['duration_ms']}ms")
            else:
                print(f"   ❌ Failed ({status_code}) - {result['duration_ms']}ms")
                print(f"   Error: {response_data.get('message', 'Unknown error')}")
            
            self.test_results.append(result)
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            error_result = {
                "test_name": test_name,
                "endpoint": endpoint,
                "method": method,
                "status_code": 0,
                "success": False,
                "duration_ms": round(duration * 1000, 2),
                "response_size": 0,
                "response": {"error": str(e)},
                "timestamp": datetime.utcnow().isoformat()
            }
            
            print(f"   ❌ Exception: {e}")
            self.test_results.append(error_result)
            return error_result
    
    async def test_sports_data_ingestion(self):
        """Test the sports data ingestion endpoint."""
        print("\n📊 Testing Sports Data Ingestion")
        
        # Test NFL data ingestion
        await self.run_test(
            "NFL Data Ingestion", 
            "/api/sports_data_ingestion",
            params={"sport": "nfl", "season": "2024"}
        )
        
        # Test NBA data ingestion
        await self.run_test(
            "NBA Data Ingestion",
            "/api/sports_data_ingestion", 
            params={"sport": "nba", "season": "2023-24"}
        )
        
        # Test invalid sport
        await self.run_test(
            "Invalid Sport Handling",
            "/api/sports_data_ingestion",
            params={"sport": "invalid_sport"}
        )
    
    async def test_game_predictor(self):
        """Test the game prediction endpoint."""
        print("\n🔮 Testing Game Predictor")
        
        # Test upcoming predictions
        await self.run_test(
            "Upcoming NFL Predictions",
            "/api/game_predictor",
            params={"sport": "nfl", "days_ahead": "7"}
        )
        
        await self.run_test(
            "Upcoming NBA Predictions", 
            "/api/game_predictor",
            params={"sport": "nba", "days_ahead": "3"}
        )
        
        # Test specific game prediction (would need a real game ID)
        await self.run_test(
            "Specific Game Prediction",
            "/api/game_predictor",
            params={"game_id": "nfl_game_1"}
        )
    
    async def test_get_predictions(self):
        """Test the get predictions API."""
        print("\n📋 Testing Get Predictions API")
        
        # Test basic predictions retrieval
        await self.run_test(
            "Get All Predictions",
            "/api/get_predictions",
            params={"limit": "10"}
        )
        
        # Test filtering by sport
        await self.run_test(
            "Get NFL Predictions",
            "/api/get_predictions",
            params={"sport": "nfl", "limit": "5"}
        )
        
        # Test filtering by confidence
        await self.run_test(
            "High Confidence Predictions",
            "/api/get_predictions",
            params={"confidence_min": "70", "limit": "5"}
        )
        
        # Test date filtering
        await self.run_test(
            "Recent Predictions",
            "/api/get_predictions",
            params={
                "date_from": "2024-07-20",
                "date_to": "2024-07-30",
                "limit": "10"
            }
        )
    
    async def test_get_team_stats(self):
        """Test the team statistics API."""
        print("\n📈 Testing Team Statistics API")
        
        # Test getting all team stats
        await self.run_test(
            "Get All Team Stats",
            "/api/get_team_stats",
            params={"limit": "10"}
        )
        
        # Test filtering by sport
        await self.run_test(
            "Get NFL Team Stats",
            "/api/get_team_stats",
            params={"sport": "nfl", "limit": "5"}
        )
        
        # Test specific team stats
        await self.run_test(
            "Specific Team Stats",
            "/api/get_team_stats", 
            params={"team_id": "nfl_1", "include_recent_games": "true"}
        )
        
        # Test season filtering
        await self.run_test(
            "Team Stats by Season",
            "/api/get_team_stats",
            params={"sport": "nba", "season": "2023-24", "limit": "5"}
        )
    
    async def test_error_handling(self):
        """Test error handling scenarios."""
        print("\n⚠️  Testing Error Handling")
        
        # Test non-existent endpoint
        await self.run_test(
            "Non-existent Endpoint",
            "/api/non_existent"
        )
        
        # Test malformed parameters
        await self.run_test(
            "Invalid Limit Parameter",
            "/api/get_predictions",
            params={"limit": "invalid"}
        )
        
        # Test empty results
        await self.run_test(
            "Non-existent Team",
            "/api/get_team_stats",
            params={"team_id": "non_existent_team"}
        )
    
    async def test_performance(self):
        """Test performance characteristics."""
        print("\n⚡ Testing Performance")
        
        # Test concurrent requests
        tasks = []
        for i in range(5):
            task = self.run_test(
                f"Concurrent Request {i+1}",
                "/api/get_predictions",
                params={"limit": "5"}
            )
            tasks.append(task)
        
        await asyncio.gather(*tasks)
    
    async def run_all_tests(self):
        """Run the complete test suite."""
        print("🚀 Starting Sports Prediction System Test Suite")
        print(f"📍 Base URL: {self.base_url}")
        print(f"🕐 Start Time: {datetime.utcnow().isoformat()}")
        
        start_time = time.time()
        
        # Run all test categories
        await self.test_sports_data_ingestion()
        await self.test_game_predictor() 
        await self.test_get_predictions()
        await self.test_get_team_stats()
        await self.test_error_handling()
        await self.test_performance()
        
        total_duration = time.time() - start_time
        
        # Generate test report
        self.generate_test_report(total_duration)
    
    def generate_test_report(self, total_duration: float):
        """Generate a comprehensive test report."""
        print("\n" + "="*60)
        print("📊 TEST REPORT SUMMARY")
        print("="*60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        print(f"Total Duration: {total_duration:.2f}s")
        
        # Performance metrics
        durations = [r["duration_ms"] for r in self.test_results if r["success"]]
        if durations:
            print(f"Average Response Time: {sum(durations)/len(durations):.2f}ms")
            print(f"Fastest Response: {min(durations):.2f}ms")
            print(f"Slowest Response: {max(durations):.2f}ms")
        
        # Failed tests details
        if failed_tests > 0:
            print(f"\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test_name']}: {result['response'].get('error', 'Unknown error')}")
        
        # Save detailed results
        report_filename = f"test_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w') as f:
            json.dump({
                "summary": {
                    "total_tests": total_tests,
                    "passed": passed_tests,
                    "failed": failed_tests,
                    "success_rate": (passed_tests/total_tests)*100,
                    "total_duration": total_duration,
                    "average_response_time": sum(durations)/len(durations) if durations else 0
                },
                "detailed_results": self.test_results
            }, f, indent=2)
        
        print(f"\n📄 Detailed report saved to: {report_filename}")


async def main():
    """Main test runner."""
    # Configuration
    # Replace with your actual Function App URL after deployment
    BASE_URL = "https://your-function-app.azurewebsites.net"
    
    # For local testing with Azure Functions Core Tools
    LOCAL_URL = "http://localhost:7071"
    
    # Choose which URL to use
    url = LOCAL_URL  # Change to BASE_URL for deployed testing
    
    print("🏃‍♂️ Sports Prediction System API Tester")
    print(f"🌐 Testing against: {url}")
    
    async with SportsPredictionTester(url) as tester:
        await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
