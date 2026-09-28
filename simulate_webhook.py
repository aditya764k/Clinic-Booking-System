import requests
import hmac
import hashlib
import json
import sys

# This must exactly match the RAZORPAY_WEBHOOK_SECRET in your .env file
SECRET = "aditya@1906" 

def simulate_webhook(order_id: str):
    # This is the exact shape Razorpay sends when a payment succeeds
    payload = {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_test_random123", # Fake payment ID
                    "order_id": order_id,       # The order ID you got from Swagger
                    "amount": 50000             # 500.00 INR in paise (Must match invoice)
                }
            }
        }
    }
    
    # 1. Convert payload to JSON bytes (this is what the raw body looks like)
    body = json.dumps(payload).encode('utf-8')
    
    # 2. Compute the HMAC SHA-256 signature just like Razorpay does
    signature = hmac.new(SECRET.encode('utf-8'), body, hashlib.sha256).hexdigest()
    
    print(f"Sending webhook for Order ID: {order_id}...")
    
    # 3. Send the POST request to your local FastAPI server
    try:
        resp = requests.post(
            "http://localhost:8000/webhooks/razorpay", 
            data=body, 
            headers={
                "X-Razorpay-Signature": signature, 
                "Content-Type": "application/json"
            }
        )
        print(f"Response Status: {resp.status_code}")
        print(f"Response Body: {resp.text}")
    except requests.exceptions.ConnectionError:
        print("Failed to connect to http://localhost:8000. Is the backend running?")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python simulate_webhook.py <YOUR_ORDER_ID>")
        print("Example: python simulate_webhook.py order_Oa3aL942000000")
        sys.exit(1)
        
    simulate_webhook(sys.argv[1])
