import qrcode
from io import BytesIO
from config import SOLANA_ADDRESS

def generate_payment_qr(order_id, amount):
    # Generate QR code for Solana payment
    payment_string = f"solana:{SOLANA_ADDRESS}?amount={amount}&label=Order_{order_id}"
    qr = qrcode.make(payment_string)
    bio = BytesIO()
    qr.save(bio, format='PNG')
    bio.seek(0)
    return bio