"""Quick API test script"""
import asyncio
import httpx


async def test_api():
    """Test the API endpoints"""
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient() as client:
        print("Testing API endpoints...\n")
        
        # Test root endpoint
        print("1. Testing root endpoint...")
        response = await client.get(f"{base_url}/")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}\n")
        
        # Test health endpoint
        print("2. Testing health endpoint...")
        response = await client.get(f"{base_url}/health")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}\n")
        
        # Test supported languages
        print("3. Testing voice languages endpoint...")
        response = await client.get(f"{base_url}/api/v1/voice/languages")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Supported languages: {len(data['languages'])}")
            for lang in data['languages'][:5]:  # Show first 5
                print(f"     - {lang['name']} ({lang['code']}) - Offline: {lang['offline_supported']}")
        print()
        
        # Test start screening
        print("4. Testing start screening endpoint...")
        response = await client.post(
            f"{base_url}/api/v1/voice/screening/start",
            json={
                "screening_type": "EPDS",
                "language": "hi",
                "user_id": 1
            }
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Session ID: {data['session_id']}")
            print(f"   Total questions: {data['total_questions']}")
            print(f"   First question: {data['current_question']['text'][:60]}...")
        print()
        
        print("✅ API is working!")


if __name__ == "__main__":
    asyncio.run(test_api())
