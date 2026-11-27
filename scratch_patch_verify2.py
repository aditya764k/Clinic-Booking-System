import re

with open("backend/app/api/billing.py", "r") as f:
    content = f.read()

# Replace the hmac verification with payment API fetch
new_verify_logic = """    try:
        rzp_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        payment = rzp_client.payment.fetch(body.razorpay_payment_id)
        
        if payment["status"] != "captured":
            raise ValueError(f"Payment status is {payment['status']}, not captured")
            
        if payment.get("order_id") != invoice.razorpay_order_id and payment.get("invoice_id") != invoice.receipt_number:
            raise ValueError("Payment does not belong to this invoice's order")
            
    except Exception as exc:
        if settings.RAZORPAY_KEY_SECRET == "test":
            logger.warning("Bypassing Razorpay validation for local testing due to error: %s", exc)
        else:
            logger.error("Razorpay verification failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid payment verification",
            )
"""

# We need to replace the hmac block.
# Let's find it.
old_hmac_block = """    secret = settings.RAZORPAY_KEY_SECRET.encode("utf-8")
    
    if getattr(body, 'razorpay_invoice_id', '') and getattr(body, 'razorpay_invoice_receipt', ''):
        message = f"{body.razorpay_invoice_id}|{body.razorpay_invoice_receipt}|{body.razorpay_payment_id}"
    else:
        message = f"{body.razorpay_order_id}|{body.razorpay_payment_id}"
        
    expected_sig = hmac.new(secret, message.encode("utf-8"), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected_sig, body.razorpay_signature):
        if settings.RAZORPAY_KEY_SECRET == "test" or not body.razorpay_signature:
            logger.warning("Bypassing Razorpay signature validation for local testing")
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid payment signature",
            )"""

if old_hmac_block in content:
    content = content.replace(old_hmac_block, new_verify_logic)
    with open("backend/app/api/billing.py", "w") as f:
        f.write(content)
    print("Patched successfully!")
else:
    print("Could not find the hmac block.")
