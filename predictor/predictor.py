import tensorflow as tf
import numpy as np
import json
from kafka import KafkaConsumer, KafkaProducer

class PredictorService:
    def __init__(self):
        # Consumer Kafka per dati e modello
        self.kafka_consumer = KafkaConsumer(
            'preprocessed_bitcoin_data',
            'model_training_results',
            bootstrap_servers=['kafka:9092'],
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
        )
        
        # Producer Kafka per predizioni
        self.kafka_producer = KafkaProducer(
            bootstrap_servers=['kafka:9092'],
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        
        # Caricamento modello
        self.model = tf.keras.models.load_model('/models/bitcoin_prediction_model')

    def predict_next_hours(self, last_sequence, hours=6):
        """
        Predizione prezzi per le prossime ore
        """
        predictions = []
        current_sequence = last_sequence
        
        for _ in range(hours):
            # Predizione prossimo prezzo
            next_pred = self.model.predict(current_sequence)[0]
            predictions.append(float(next_pred))
            
            # Aggiornamento sequenza
            current_sequence = np.append(current_sequence[:,1:,:], 
                                         next_pred.reshape(1, 1, 1), 
                                         axis=1)
        
        # Publish predictions
        self.kafka_producer.send('bitcoin_predictions', {
            'predictions': predictions
        })
        
        return predictions

    def run(self):
        """
        Ricezione dati e generazione predizioni
        """
        for message in self.kafka_consumer:
            if 'X' in message.value:  # Dati preprocessati
                last_sequence = np.array(message.value['X'])[-1]
                self.predict_next_hours(last_sequence.reshape(1, *last_sequence.shape))

