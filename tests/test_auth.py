import pytest

async def test_register_and_login(client):
    r = await client.post('/auth/register', json={'email':'u1@example.com','password':'secret123'})
    assert r.status_code == 200, r.text
    r = await client.post('/auth/login', json={'email':'u1@example.com','password':'secret123'})
    assert r.status_code == 200
    token = r.json()['access_token']
    assert token
