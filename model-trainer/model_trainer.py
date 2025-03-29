import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, BatchNormalization
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from kafka import KafkaConsumer, KafkaProducer
import json
import numpy as np
import logging
import os  # Per la gestione dei path del modello

# Configura il logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ModelTrainerService:
    def __init__(self, model_save_path='/models/bitcoin_prediction_model.keras'):  # Aggiunta l'estensione .keras
        # Consumer Kafka per dati preprocessati
        self.kafka_consumer = KafkaConsumer(
            'preprocessed_bitcoin_data',
            bootstrap_servers=['kafka:9092'],
            value_deserializer=lambda x: json.loads(x.decode('utf-8')),
            auto_offset_reset='earliest',  
            group_id='model-trainer-group',
            enable_auto_commit=True  
        )

        # Producer Kafka per risultati dell'addestramento
        self.kafka_producer = KafkaProducer(
            bootstrap_servers=['kafka:9092'],
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )

        # Path per salvare il modello.  Lo rendiamo configurabile.
        self.model_save_path = model_save_path
        os.makedirs(os.path.dirname(self.model_save_path), exist_ok=True) #Crea la directory se non esiste

    def build_lstm_model(self, input_shape):
        """
        Costruisce un modello LSTM più robusto.
        """
        model = Sequential()

        # Primo layer LSTM
        model.add(LSTM(64, return_sequences=True, input_shape=input_shape))
        model.add(BatchNormalization()) #Normalizzazione
        model.add(Dropout(0.2))  # Dropout per prevenire l'overfitting

        # Secondo layer LSTM
        model.add(LSTM(64, return_sequences=False)) # returns single output
        model.add(BatchNormalization())
        model.add(Dropout(0.2))

        # Layers Dense
        model.add(Dense(32, activation='relu')) #Hidden Layer
        model.add(BatchNormalization())
        model.add(Dropout(0.2))
        model.add(Dense(1))  # Layer di output

        # Ottimizzatore Adam con learning rate modificabile
        optimizer = Adam(learning_rate=0.001) #Learning Rate configurabile

        model.compile(optimizer=optimizer, loss='mse')
        return model

    def train_model(self, X, y):
        """
        Addestra il modello LSTM con callback per migliorare le prestazioni.
        """
        # Conversione a numpy array (fondamentale)
        X = np.array(X)
        y = np.array(y)

        # Costruisci il modello
        model = self.build_lstm_model((X.shape[1], X.shape[2]))

        # Callbacks
        early_stopping = EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True) #early stopping
        reduce_lr = ReduceLROnPlateau(monitor='val_loss', factor=0.2, patience=5, min_lr=0.00001) #riduzione learning rate

        # Addestramento del modello
        history = model.fit(
            X, y,
            epochs=100, # Numero di epoche aumentato
            batch_size=32,
            validation_split=0.2,
            verbose=0, #Imposta verbose a 1 per vedere l'output di training
            callbacks=[early_stopping, reduce_lr]
        )

        # Salvataggio del modello
        model.save(self.model_save_path) # Nessuna modifica qui
        logging.info(f"Modello salvato in: {self.model_save_path}")

        # Pubblica i risultati dell'addestramento
        training_results = {
            'loss': history.history['loss'][-1],
            'val_loss': history.history['val_loss'][-1]
        }
        self.kafka_producer.send('model_training_results', training_results)
        logging.info(f"Risultati dell'addestramento pubblicati su Kafka: {training_results}")

    def run(self):
        """
        Ciclo principale per ricevere dati da Kafka e addestrare il modello.
        """
        logging.info("Servizio Model Trainer avviato. In attesa di dati...")
        try:
            for message in self.kafka_consumer:
                X = message.value['X']
                y = message.value['y']
                logging.info("Dati ricevuti da Kafka. Avvio dell'addestramento...")
                self.train_model(X, y)
                logging.info("Addestramento completato.")
        except Exception as e:
            logging.error(f"Errore durante l'esecuzione: {e}", exc_info=True) #Logga l'errore completo
        finally:
            self.kafka_consumer.close()
            self.kafka_producer.close()
            logging.info("Consumer e Producer Kafka chiusi.")

if __name__ == '__main__':
    trainer = ModelTrainerService()
    trainer.run()