from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# We can bypass dependencies using app.dependency_overrides
from app.core.dependencies import get_current_user
from app.models.identity import User, UserRole

def override_get_current_user():
    return User(id=1, role=UserRole.receptionist, email="rec@test.com")

app.dependency_overrides[get_current_user] = override_get_current_user

res = client.post("/invoices/6/verify-razorpay", json={
    "razorpay_payment_id": "test",
    "razorpay_order_id": "test",
    "razorpay_signature": "test"
})
print(res.status_code, res.json())
