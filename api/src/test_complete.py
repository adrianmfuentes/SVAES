import asyncio
import httpx
import logging

logging.basicConfig(level=logging.DEBUG)

async def test():
    async with httpx.AsyncClient() as client:
        import uuid
        email = f'test{uuid.uuid4().hex[:8]}@svaes.com'
        print(f'\n=== Testing with email: {email} ===')

        reg = await client.post(
            'http://localhost:8000/api/v1/auth/register',
            json={'email': email, 'password': 'Test1234!', 'display_name': 'Test', 'role': 'U2'},
            timeout=30.0
        )
        print(f'Register: {reg.status_code} - {reg.text}')

        login = await client.post(
            'http://localhost:8000/api/v1/auth/login',
            json={'email': email, 'password': 'Test1234!'},
            timeout=30.0
        )
        print(f'Login: {login.status_code} - {login.text}')

asyncio.run(test())