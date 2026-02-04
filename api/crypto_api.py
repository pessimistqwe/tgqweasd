import requests
import os

CRYPTO_BOT_TOKEN = os.getenv("CRYPTO_BOT_TOKEN")
API_URL = "https://pay.crypt.bot/api/"

class CryptoBotAPI:
    def __init__(self):
        self.token = CRYPTO_BOT_TOKEN
        self.headers = {"Crypto-Pay-API-Token": self.token}
    
    def create_invoice(self, amount: float, asset: str, description: str, 
                      user_id: int, payload: str = None) -> dict:
        """Создать счет для пополнения"""
        try:
            response = requests.post(
                f"{API_URL}createInvoice",
                headers=self.headers,
                json={
                    "asset": asset,
                    "amount": str(amount),
                    "description": description,
                    "hidden_message": f"Пополнение баланса пользователя {user_id}",
                    "paid_btn_name": "openBot",
                    "paid_btn_url": f"https://t.me/YOUR_BOT_USERNAME?start=deposit_{user_id}",
                    "payload": payload or f"deposit_{user_id}_{amount}_{asset}"
                }
            )
            return response.json()["result"]
        except Exception as e:
            print(f"Error creating invoice: {e}")
            return None
    
    def check_invoice(self, invoice_id: str) -> dict:
        """Проверить статус платежа"""
        try:
            response = requests.post(
                f"{API_URL}getInvoices",
                headers=self.headers,
                json={"invoice_ids": [invoice_id]}
            )
            items = response.json()["result"]["items"]
            return items[0] if items else None
        except Exception as e:
            print(f"Error checking invoice: {e}")
            return None
    
    def get_balance(self) -> dict:
        """Получить баланс вашего кошелька в Crypto Bot"""
        try:
            response = requests.post(
                f"{API_URL}getBalance",
                headers=self.headers
            )
            return response.json()["result"]
        except Exception as e:
            print(f"Error getting balance: {e}")
            return None
    
    def transfer(self, user_id: int, amount: float, asset: str, 
                 address: str, comment: str = None) -> dict:
        """Вывод средств (требует ручного подтверждения в Crypto Bot!)"""
        try:
            response = requests.post(
                f"{API_URL}transfer",
                headers=self.headers,
                json={
                    "user_id": user_id,  # Telegram ID получателя (если в Crypto Bot)
                    "asset": asset,
                    "amount": str(amount),
                    "spend_id": f"withdrawal_{user_id}_{datetime.now().timestamp()}",
                    "comment": comment or "Вывод средств",
                    "disable_send_notification": False
                }
            )
            return response.json()["result"]
        except Exception as e:
            print(f"Error transfer: {e}")
            return None

crypto_api = CryptoBotAPI()