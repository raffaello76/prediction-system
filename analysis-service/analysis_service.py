import json
import numpy as np
import logging
from kafka import KafkaConsumer
from strategy import BitcoinTradingStrategy  # il file strategy.py sarà incluso sotto

# Configurazione logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('AnalysisService')

class AnalysisService:
    def __init__(self):
        logger.info("Inizializzazione di AnalysisService")
        try:
            self.prediction_consumer = KafkaConsumer(
                'bitcoin_predictions',
                bootstrap_servers=['kafka:9092'],
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='latest',
                group_id='analysis-group'
            )
            logger.info("Prediction consumer inizializzato con successo")
        except Exception as e:
            logger.error(f"Errore nell'inizializzazione del prediction consumer: {e}")

        try:
            self.price_consumer = KafkaConsumer(
                'bitcoin_data',
                bootstrap_servers=['kafka:9092'],
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='latest',
                consumer_timeout_ms=5000
            )
            logger.info("Price consumer inizializzato con successo")
        except Exception as e:
            logger.error(f"Errore nell'inizializzazione del price consumer: {e}")

        # Inizializza la strategia
        self.strategy = BitcoinTradingStrategy(prediction_model=None)
        logger.info("BitcoinTradingStrategy inizializzata")
        self.last_price = 0

    def get_latest_price(self):
        logger.info("Recupero dell'ultimo prezzo da 'bitcoin_data'")
        for msg in self.price_consumer:
            try:
                data = msg.value['data']
                if isinstance(data, list) and len(data) > 0:
                    last_close = data[-1]['close']
                    self.last_price = last_close
                    logger.info(f"Ultimo prezzo aggiornato: {self.last_price}")
            except Exception as e:
                logger.error(f"Errore durante l'elaborazione del messaggio di prezzo: {e}")
                continue

    def run(self):
        logger.info("Avvio di AnalysisService: recupero dell'ultimo prezzo")
        self.get_latest_price()
        logger.info("Inizio a consumare le predizioni da 'bitcoin_predictions'")
        for msg in self.prediction_consumer:
            try:
                predictions = msg.value['predictions']
                logger.info(f"Predizioni ricevute: {predictions}")
            except Exception as e:
                logger.error(f"Errore nell'estrazione delle predizioni dal messaggio: {e}")
                continue

            if not self.last_price:
                logger.info("Prezzo corrente non disponibile, aggiornamento...")
                self.get_latest_price()

            portfolio = {
                'total_value': 100000,
                'bitcoin_balance': 2,
                'current_price': self.last_price
            }
            logger.info(f"Portfolio simulato: {portfolio}")

            try:
                trade_signals = self.strategy.calculate_trade_signals(predictions, self.last_price)
                recommendations = self.strategy.risk_management(trade_signals, portfolio)
                logger.info(f"Segnali di trading calcolati: {trade_signals}")
                logger.info(f"Raccomandazioni ottenute: {recommendations}")
            except Exception as e:
                logger.error(f"Errore durante il calcolo dei segnali di trading: {e}")
                continue

            print("📈 Predizioni:", predictions)
            print("💰 Prezzo corrente:", self.last_price)
            print("🧠 Segnali:", trade_signals)
            print("📊 Raccomandazioni:", recommendations)
            logger.info("Ciclo di elaborazione del messaggio completato")

if __name__ == "__main__":
    service = AnalysisService()
    service.run()
