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
        Recupera dati da multipli exchange
        """
        all_data = {}
        for exchange_name in exchanges:
            try:
                exchange_class = getattr(ccxt, exchange_name)
                exchange = exchange_class()
                
                # Recupero dati OHLCV
                ohlcv = exchange.fetch_ohlcv('BTC/USDT', '4h')
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                
                # Conversione timestamp
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                
                all_data[exchange_name] = df.to_dict(orient='records')
                
                # Publish to Kafka
                self.kafka_producer.send('bitcoin_data', {
                    'exchange': exchange_name,
                    'data': df.to_dict(orient='records')
                })
            
            except Exception as e:
                print(f"Errore nel recupero dati da {exchange_name}: {e}")
        
        return all_data

    def fetch_additional_data(self):
        """
        Recupero dati aggiuntivi da API esterne
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
                
                # Publish to Kafka
                self.kafka_producer.send('bitcoin_additional_data', {
                    'source': source,
                    'data': data
                })
                
                additional_data[source] = data
            
            except Exception as e:
                print(f"Errore nel recupero dati da {source}: {e}")
        
        return additional_data

    def run(self):
        """
        Esecuzione continua del servizio di fetch
        """
        while True:
            # Recupero dati ogni ora
            self.fetch_from_exchanges()
            self.fetch_additional_data()
            time.sleep(3600)  # Attesa 1 ora

