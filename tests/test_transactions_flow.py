import pytest

async def setup_base(client):
    # create admin
    await client.post('/auth/register', json={'email':'admin_tx@example.com','password':'secret123'})
    r = await client.post('/auth/login', json={'email':'admin_tx@example.com','password':'secret123'})
    admin_token = r.json()['access_token']
    # promote admin (id may be 1) best-effort
    await client.post('/auth/promote/1/admin', headers={'Authorization':f'Bearer {admin_token}'})
    # operator
    await client.post('/auth/register', json={'email':'op_tx@example.com','password':'secret123'})
    r2 = await client.post('/auth/login', json={'email':'op_tx@example.com','password':'secret123'})
    op_token = r2.json()['access_token']
    await client.post('/auth/promote/2/operator', headers={'Authorization':f'Bearer {admin_token}'})
    # create currencies
    for code in ('BTC','USDT'):
        await client.post('/currencies', json={'code':code,'name':code,'reserve':100000}, headers={'Authorization':f'Bearer {op_token}'})
    return admin_token, op_token

async def test_transaction_creation_and_completion(client):
    admin_token, op_token = await setup_base(client)
    # user
    await client.post('/auth/register', json={'email':'txuser@example.com','password':'secret123'})
    r = await client.post('/auth/login', json={'email':'txuser@example.com','password':'secret123'})
    user_token = r.json()['access_token']
    # KYC quick verify
    await client.post('/auth/kyc/submit', json={'full_name':'Tx User','document_id':'DOC123'}, headers={'Authorization':f'Bearer {user_token}'})
    await client.post('/auth/kyc/3/status', json={'status':'verified'}, headers={'Authorization':f'Bearer {op_token}'})
    # create order
    order_r = await client.post('/orders', json={'from_currency':1,'to_currency':2,'amount_from':0.02,'payout_details':'addr'}, headers={'Authorization':f'Bearer {user_token}'})
    assert order_r.status_code in (200,201)
    order_id = order_r.json()['id']
    # add transaction below amount
    tx_r1 = await client.post(f'/orders/{order_id}/transactions', json={'tx_hash':'abc','amount':0.01}, headers={'Authorization':f'Bearer {user_token}'})
    assert tx_r1.status_code == 200
    # add transaction meeting amount to flip status to paid
    tx_r2 = await client.post(f'/orders/{order_id}/transactions', json={'tx_hash':'def','amount':0.01}, headers={'Authorization':f'Bearer {user_token}'})
    assert tx_r2.status_code == 200
    # fetch order
    order_after = await client.get(f'/orders/{order_id}', headers={'Authorization':f'Bearer {user_token}'})
    assert order_after.status_code == 200
    assert order_after.json()['status'] in ('paid','processing','completed')
