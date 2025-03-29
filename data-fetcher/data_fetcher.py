import os
import logging
import time
import json
import pandas as pd
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException
from kafka import KafkaProducer
from typing import List, Dict

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

class BinanceDataFetcherService:
    def __init__(self):
        # Initialize Binance client
        api_key = os.environ.get('BINANCE_API_KEY', '').strip()
        api_secret = os.environ.get('BINANCE_API_SECRET', '').strip()
        
        try:
            if api_key and api_secret:
                logging.info(f"Initializing Binance client with API Key: {api_key[:4]}***")
                self.client = Client(api_key, api_secret)
            else:
                logging.info("No API Key provided, initializing public Binance client")
                self.client = Client()
        except Exception as e:
            logging.error(f"Error initializing Binance client: {e}")
            raise

        # Initialize Kafka Producer
        self.kafka_producer = KafkaProducer(
            bootstrap_servers=['kafka:9092'],
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )

    def fetch_btcusdt_data(self, interval: str = '4h') -> List[Dict]:
        """
        Fetch BTCUSDT kline (candlestick) data from Binance
        
        :param interval: Kline interval (default is 4 hours)
        :return: List of dictionaries containing OHLCV data
        """
        try:
            # Fetch last 500 candles 
            klines = self.client.get_klines(symbol='BTCUSDT', interval=interval, limit=500)
            
            # Convert to DataFrame for easier processing
            df = pd.DataFrame(klines, columns=[
                'open_time', 'open', 'high', 'low', 'close', 'volume', 
                'close_time', 'quote_asset_volume', 'number_of_trades', 
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # Select and convert necessary columns
            df = df[['open_time', 'open', 'high', 'low', 'close', 'volume']]
            
            # Convert columns to appropriate types
            df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
            df = df.astype({
                'open': float, 
                'high': float, 
                'low': float, 
                'close': float, 
                'volume': float
            })
            
            # Convert timestamps to ISO format strings for JSON serialization
            df['open_time'] = df['open_time'].apply(lambda x: x.isoformat())
            
            # Convert to list of dictionaries
            data_records = df.to_dict(orient='records')
            
            # Log and send to Kafka
            logging.info(f"Fetched {len(data_records)} BTCUSDT klines")
            self.kafka_producer.send('bitcoin_data', {
                'exchange': 'binance',
                'symbol': 'BTCUSDT',
                'interval': interval,
                'data': data_records
            })
            
            return data_records
        
        except BinanceAPIException as e:
            logging.error(f"Binance API Exception: {e}")
            return []
        except Exception as e:
            logging.error(f"Error fetching BTCUSDT data: {e}")
            return []

    def run(self, interval: int = 1800):
        """
        Continuously run the data fetcher
        
        :param interval: Sleep time between fetch cycles (default 30 minutes)
        """
        while True:
            try:
                logging.info("Starting BTCUSDT data fetch cycle")
                self.fetch_btcusdt_data()
                logging.info(f"Waiting {interval} seconds before next fetch")
                time.sleep(interval)
            except Exception as e:
                logging.error(f"Error in run cycle: {e}")
                # Wait a bit before retrying to prevent rapid error loops
                time.sleep(60)

def main():
    service = BinanceDataFetcherService()
    service.run()

if __name__ == "__main__":
    main()
