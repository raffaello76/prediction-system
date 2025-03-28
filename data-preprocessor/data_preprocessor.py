import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from kafka import KafkaConsumer, KafkaProducer
import json

class DataPreprocessorService:
    def __init__(self):
        # Consumer Kafka per ricevere dati grezzi
        self.kafka_consumer = KafkaConsumer(
            'bitcoin_data',
            bootstrap_servers=['kafka:9092'],
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
        )
        
        # Producer Kafka per dati preprocessati
        self.kafka_producer = KafkaProducer(
            bootstrap_servers=['kafka:9092'],
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        
        self.scaler = MinMaxScaler()

    def preprocess_data(self, raw_data):
        """
        Preprocessing dei dati per machine learning
        """
        # Conversione in DataFrame
        df = pd.DataFrame(raw_data)
        
        # Selezione e scalatura delle features
        features = ['open', 'high', 'low', 'close', 'volume']
        scaled_data = self.scaler.fit_transform(df[features])
        
        # Preparazione sequenze per LSTM
        def create_sequences(data, lookback=60):
            X, y = [], []
            for i in range(lookback, len(data)):
                X.append(data[i-lookback:i])
                y.append(data[i])
            return np.array(X), np.array(y)
        
        X, y = create_sequences(scaled_data)
        
        # Publish preprocessed data to Kafka
        self.kafka_producer.send('preprocessed_bitcoin_data', {
            'X': X.tolist(),
            'y': y.tolist(),
            'scaler_params': {
                'scale_': self.scaler.scale_.tolist(),
                'min_': self.scaler.min_.tolist()
            }
        })
        
        return X, y

    def run(self):
        """
        Elaborazione continua dei dati in arrivo
        """
        for message in self.kafka_consumer:
            raw_data = message.value['data']
            self.preprocess_data(raw_data)

