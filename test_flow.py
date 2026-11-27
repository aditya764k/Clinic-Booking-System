import requests
s = requests.Session()
r1 = s.get("http://localhost:8000/auth/google/login", allow_redirects=False)
print("r1 headers:", r1.headers)
print("r1 cookies:", s.cookies.get_dict())
print("redirect url:", r1.headers.get("Location"))
from urllib.parse import urlparse, parse_qs
parsed = urlparse(r1.headers["Location"])
qs = parse_qs(parsed.query)
state = qs["state"][0]
print("state:", state)
# now simulate the callback
r2 = s.get(f"http://localhost:8000/auth/google/callback?state={state}&code=dummy", allow_redirects=False)
print("r2 status:", r2.status_code)
print("r2 text:", r2.text)
