from fastapi.testclient import TestClient
from app.main import app

from app.core.dependencies import get_current_user
from app.models.identity import User, UserRole

client = TestClient(app)

def override_get_current_user():
    return User(id=1, role=UserRole.receptionist, email="rec@test.com")

app.dependency_overrides[get_current_user] = override_get_current_user

res = client.post("/invoices/6/verify-razorpay", json={
    "razorpay_payment_id": "pay_test",
    "razorpay_order_id": "order_test",
    "razorpay_signature": "sig_test"
})
print(res.status_code, res.json())
