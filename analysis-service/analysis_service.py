import json
import numpy as np
from kafka import KafkaConsumer
from strategy import BitcoinTradingStrategy  # il file strategy.py sarà incluso sotto

class AnalysisService:
    def __init__(self):
        self.prediction_consumer = KafkaConsumer(
            'bitcoin_predictions',
            bootstrap_servers=['kafka:9092'],
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='latest',
            group_id='analysis-group'
        )
        self.price_consumer = KafkaConsumer(
            'bitcoin_data',
            bootstrap_servers=['kafka:9092'],
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='latest',
            consumer_timeout_ms=5000
        )
        self.strategy = BitcoinTradingStrategy(prediction_model=None)
        self.last_price = 0

    def get_latest_price(self):
        for msg in self.price_consumer:
            try:
                data = msg.value['data']
                if isinstance(data, list) and len(data) > 0:
                    last_close = data[-1]['close']
                    self.last_price = last_close
            except:
                continue

    def run(self):
        self.get_latest_price()
        for msg in self.prediction_consumer:
            predictions = msg.value['predictions']
            if not self.last_price:
                self.get_latest_price()
            portfolio = {
                'total_value': 100000,
                'bitcoin_balance': 2,
                'current_price': self.last_price
            }
            trade_signals = self.strategy.calculate_trade_signals(predictions, self.last_price)
            recommendations = self.strategy.risk_management(trade_signals, portfolio)

            print("📈 Predizioni:", predictions)
            print("💰 Prezzo corrente:", self.last_price)
            print("🧠 Segnali:", trade_signals)
            print("📊 Raccomandazioni:", recommendations)

if __name__ == "__main__":
    service = AnalysisService()
    service.run()

