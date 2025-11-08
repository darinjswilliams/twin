import requests

response = requests.post(
    'http://localhost:8000/send-resume-request-secure',
    json={
        'name': 'Script Test',
        'email': 'script@test.com',
        'message': 'Testing from script',
        'captcha_token': 'test-token-will-be-mocked'
    }
)

print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")