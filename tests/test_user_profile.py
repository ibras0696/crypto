import pytest

async def test_me_endpoint(client):
    # register and login
    await client.post('/auth/register', json={'email':'profile@example.com','password':'secret123'})
    r = await client.post('/auth/login', json={'email':'profile@example.com','password':'secret123'})
    token = r.json()['access_token']
    me = await client.get('/auth/me', headers={'Authorization':f'Bearer {token}'})
    assert me.status_code == 200
    data = me.json()
    assert data['email'] == 'profile@example.com'
    assert data['kyc_status'] == 'unverified'
