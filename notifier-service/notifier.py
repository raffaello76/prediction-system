import json
import requests
import os
from kafka import KafkaConsumer

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_IDS = os.getenv("TELEGRAM_CHAT_IDS", "")

class TelegramNotifier:
    def __init__(self):
        if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_IDS:
            raise ValueError("❌ TELEGRAM_TOKEN o TELEGRAM_CHAT_IDS non impostati.")

        # Trasforma la stringa in una lista di ID
        self.chat_ids = [chat_id.strip() for chat_id in TELEGRAM_CHAT_IDS.split(",")]
        
        self.consumer = KafkaConsumer(
            'bitcoin_predictions',
            bootstrap_servers=['kafka:9092'],
            value_deserializer=lambda x: json.loads(x.decode('utf-8')),
            auto_offset_reset='latest',
            group_id='telegram-notifier-group'
        )

    def send_telegram_message(self, message):
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        for chat_id in self.chat_ids:
            payload = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            try:
                response = requests.post(url, json=payload)
                if response.status_code != 200:
                    print(f"❌ Errore Telegram [{chat_id}]:", response.text)
            except Exception as e:
                print(f"❌ Errore Telegram [{chat_id}]:", e)

    def run(self):
        for msg in self.consumer:
            predictions = msg.value['predictions']
            trend = "📈 In rialzo" if predictions[-1] > predictions[0] else "📉 In calo"
            message = (
                f"*📊 Nuova Predizione Bitcoin*\n"
                f"{trend}\n"
                f"Prezzi stimati: {predictions}\n"
                f"_Segnale generato automaticamente_"
            )
            self.send_telegram_message(message)

if __name__ == "__main__":
    TelegramNotifier().run()

