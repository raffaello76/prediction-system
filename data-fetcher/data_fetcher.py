import os
import ccxt
import requests
import pandas as pd
from typing import List, Dict
import json
import time
from kafka import KafkaProducer

class DataFetcherService:
    def __init__(self):
        # Configurazione Kafka per messaggistica
        self.kafka_producer = KafkaProducer(
            bootstrap_servers=['kafka:9092'],
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )

    def fetch_from_exchanges(self, exchanges: List[str] = ['binance', 'coinbase', 'kucoin']) -> Dict:
        """
        Recupera dati da multipli exchange, gestendo Binance con le proprie API key.
        """
        all_data = {}
        for exchange_name in exchanges:
            try:
                if exchange_name.lower() == 'binance':
                    # Recupera le API key dall'ambiente
                    api_key = os.environ.get('BINANCE_API_KEY')
                    api_secret = os.environ.get('BINANCE_API_SECRET')
                    if not api_key or not api_secret:
                        raise ValueError("Le credenziali per Binance non sono state impostate.")
                    exchange = ccxt.binance({
                        'apiKey': api_key,
                        'secret': api_secret,
                        'enableRateLimit': True,
                    })
                else:
                    exchange_class = getattr(ccxt, exchange_name)
                    exchange = exchange_class()

                # Recupero dati OHLCV per BTC/USDT con timeframe 4h
                ohlcv = exchange.fetch_ohlcv('BTC/USDT', '4h')
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                data_records = df.to_dict(orient='records')
                all_data[exchange_name] = data_records

                # Pubblica i dati su Kafka
                self.kafka_producer.send('bitcoin_data', {
                    'exchange': exchange_name,
                    'data': data_records
                })
            except Exception as e:
                print(f"Errore nel recupero dati da {exchange_name}: {e}")
        return all_data

    def fetch_additional_data(self) -> Dict:
        """
        Recupera dati aggiuntivi da API esterne e li pubblica su Kafka.
        """
        additional_sources = {
            'coingecko': 'https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days=30',
            'cryptocompare': 'https://min-api.cryptocompare.com/data/pricemultifull?fsyms=BTC&tsyms=USD'
        }
        additional_data = {}
        for source, url in additional_sources.items():
            try:
                response = requests.get(url)
                data = response.json()
                additional_data[source] = data
                # Pubblica i dati su Kafka
                self.kafka_producer.send('bitcoin_additional_data', {
                    'source': source,
                    'data': data
                })
            except Exception as e:
                print(f"Errore nel recupero dati da {source}: {e}")
        return additional_data

    def run(self):
        """
        Esecuzione continua del servizio di fetch: recupera i dati ogni 30 minuti.
        """
        while True:
            self.fetch_from_exchanges()
            self.fetch_additional_data()
            time.sleep(1800)  # Attesa 30 minuti

if __name__ == "__main__":
    service = DataFetcherService()
    service.run()

