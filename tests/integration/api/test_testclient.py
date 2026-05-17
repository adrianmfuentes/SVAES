import asyncio
from fastapi.testclient import TestClient
from main import app

def test_endpoints():
    with TestClient(app) as client:
        import uuid
        email = f'test{uuid.uuid4().hex[:8]}@svaes.com'

        # Register
        reg = client.post(
            '/api/v1/auth/register',
            json={
                'email': email, 
                'password': 'Test1234!', # NOSONAR - This is a test password, not used in production
                'display_name': 'Test', 
                'role': 'U2'
            },
        )
        print(f'Register: {reg.status_code} - {reg.text}')

        # Login
        login = client.post(
            '/api/v1/auth/login',
            json={
                'email': email, 
                'password': 'Test1234!' # NOSONAR - This is a test password, not used in production
            },
        )
        print(f'Login: {login.status_code} - {login.text}')

if __name__ == '__main__':
    test_endpoints()