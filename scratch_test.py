import requests

session = requests.Session()
res = session.post("http://localhost:8000/auth/login", json={"email": "jdnyasa@gmail.com", "password": "password123"})
print(res.status_code, res.text)

res2 = session.post("http://localhost:8000/invoices/6/verify-razorpay", json={
    "razorpay_payment_id": "test",
    "razorpay_order_id": "test",
    "razorpay_signature": "test"
})
print(res2.status_code, res2.text)
