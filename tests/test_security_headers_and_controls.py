import pytest
from buddy import app, rate_limiter, get_user_salutation, USER_HONORIFIC, api_token

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_security_headers_present(client):
    res = client.get('/health')
    assert res.status_code == 200
    # Check nosniff
    assert res.headers.get('X-Content-Type-Options') == 'nosniff'
    # Check frame options
    assert res.headers.get('X-Frame-Options') == 'SAMEORIGIN'
    # Check CSP
    assert 'Content-Security-Policy' in res.headers
    assert "default-src 'self'" in res.headers['Content-Security-Policy']
    # Technology banner suppressed
    assert 'Server' not in res.headers
    assert 'X-Powered-By' not in res.headers

def test_hsts_on_https_request(client):
    res = client.get('/health', headers={'X-Forwarded-Proto': 'https'})
    assert res.status_code == 200
    assert 'Strict-Transport-Security' in res.headers
    assert 'max-age=31536000' in res.headers['Strict-Transport-Security']

def test_cookie_security_attributes(client):
    res = client.get('/', headers={'X-Forwarded-Proto': 'https'})
    assert res.status_code == 200
    cookie_header = res.headers.get('Set-Cookie', '')
    assert 'jarvis_token=' in cookie_header
    assert 'HttpOnly' in cookie_header
    assert 'Secure' in cookie_header
    assert 'SameSite=Lax' in cookie_header

def test_rate_limiter_exceeded():
    test_ip = "192.0.2.99"
    test_path = "/api/test_rate_limit_probe"
    
    # Fill up limit
    for _ in range(120):
        limited, retry_after, limit, remaining = rate_limiter.is_rate_limited(test_ip, test_path)
        assert limited is False
    
    # 121st request should be rate limited
    limited, retry_after, limit, remaining = rate_limiter.is_rate_limited(test_ip, test_path)
    assert limited is True
    assert retry_after > 0

def test_user_honorific_endpoint(client):
    headers = {'X-JARVIS-Auth': api_token}
    # Set honorific
    res = client.post('/api/user_honorific', json={'honorific': 'Ma\'am'}, headers=headers)
    assert res.status_code == 200
    assert res.json['honorific'] == 'Ma\'am'
    assert get_user_salutation() == ", Ma'am"
    
    # Clear / reset
    res = client.post('/api/user_honorific', json={'honorific': ''}, headers=headers)
    assert res.status_code == 200
    assert res.json['honorific'] == ''
    assert get_user_salutation() == ""
