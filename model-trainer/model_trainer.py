import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from kafka import KafkaConsumer, KafkaProducer
import json
import numpy as np

class ModelTrainerService:
    def __init__(self):
        # Consumer Kafka per dati preprocessati
        self.kafka_consumer = KafkaConsumer(
            'preprocessed_bitcoin_data',
            bootstrap_servers=['kafka:9092'],
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
        )
        
        # Producer Kafka per modelli addestrati
        self.kafka_producer = KafkaProducer(
            bootstrap_servers=['kafka:9092'],
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )

    def build_lstm_model(self, input_shape):
        """
        Costruzione modello LSTM
        """
        model = Sequential([
            LSTM(50, return_sequences=True, input_shape=input_shape),
            LSTM(50, return_sequences=False),
            Dense(25, activation='relu'),
            Dense(1)
        ])
        model.compile(optimizer='adam', loss='mse')
        return model

    def train_model(self, X, y):
        """
        Addestramento modello LSTM
        """
        # Conversione a numpy array
        X = np.array(X)
        y = np.array(y)
        
        # Costruzione modello
        model = self.build_lstm_model((X.shape[1], X.shape[2]))
        
        # Addestramento
        history = model.fit(
            X, y, 
            epochs=50, 
            batch_size=32, 
            validation_split=0.2,
            verbose=0
        )
        
        # Salvataggio modello
        model.save('/models/bitcoin_prediction_model')
        
        # Publish training results
        self.kafka_producer.send('model_training_results', {
            'loss': history.history['loss'][-1],
            'val_loss': history.history['val_loss'][-1]
        })

    def run(self):
        """
        Ricezione e addestramento continuo
        """
        for message in self.kafka_consumer:
            X = message.value['X']
            y = message.value['y']
            self.train_model(X, y)

