import tensorflow as tf
import numpy as np
import json
from kafka import KafkaConsumer, KafkaProducer
import logging

# Configurazione del logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class PredictorService:
    def __init__(self):
        logging.info("Inizializzazione di PredictorService")
        
        # Consumer Kafka per dati e modello
        try:
            self.kafka_consumer = KafkaConsumer(
                'preprocessed_bitcoin_data',
                'model_training_results',
                bootstrap_servers=['kafka:9092'],
                value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                auto_offset_reset='earliest',
                group_id='prediction-group'
            )
            logging.info("KafkaConsumer inizializzato con successo")
        except Exception as e:
            logging.error(f"Errore durante l'inizializzazione di KafkaConsumer: {e}")
        
        # Producer Kafka per predizioni
        try:
            self.kafka_producer = KafkaProducer(
                bootstrap_servers=['kafka:9092'],
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
            logging.info("KafkaProducer inizializzato con successo")
        except Exception as e:
            logging.error(f"Errore durante l'inizializzazione di KafkaProducer: {e}")
        
        # Caricamento modello
        try:
            self.model = tf.keras.models.load_model('/models/bitcoin_prediction_model.keras')
            logging.info("Modello caricato correttamente da /models/bitcoin_prediction_model.keras")
        except Exception as e:
            logging.error(f"Errore durante il caricamento del modello: {e}")

    def predict_next_hours(self, last_sequence, hours=2):
        """
        Predizione prezzi per le prossime ore
        """
        logging.info("Inizio della predizione per le prossime ore")
        predictions = []
        current_sequence = last_sequence
        
        for hour in range(hours):
            logging.info(f"Predizione per ora {hour+1}")
            try:
                # Predizione del prossimo prezzo
                next_pred = self.model.predict(current_sequence)[0]
                logging.info(f"Predizione per ora {hour+1}: {next_pred}")
                predictions.append(float(next_pred))
                
                # Aggiornamento della sequenza:
                # Si scarta il primo timestep e si aggiunge la nuova predizione
                current_sequence = np.append(current_sequence[:, 1:, :], 
                                             next_pred.reshape(1, 1, 1), 
                                             axis=1)
                logging.info(f"Aggiornamento della sequenza completato per ora {hour+1}")
            except Exception as e:
                logging.error(f"Errore durante la predizione per ora {hour+1}: {e}")
                break
        
        # Pubblica le predizioni su Kafka
        try:
            self.kafka_producer.send('bitcoin_predictions', {
                'predictions': predictions
            })
            logging.info(f"Predizioni pubblicate su 'bitcoin_predictions': {predictions}")
        except Exception as e:
            logging.error(f"Errore durante l'invio delle predizioni a Kafka: {e}")
        
        return predictions

    def run(self):
        """
        Ricezione dati e generazione predizioni
        """
        logging.info("PredictorService in esecuzione. In attesa di messaggi Kafka...")
        for message in self.kafka_consumer:
            logging.info(f"Messaggio ricevuto dal topic: {message.topic}")
            if 'X' in message.value:  # Verifica presenza dei dati preprocessati
                try:
                    # Estrae l'ultima sequenza dai dati preprocessati
                    last_sequence = np.array(message.value['X'])[-1]
                    logging.info("Estrazione dell'ultima sequenza completata")
                    # Riformatta la sequenza per adattarla all'input del modello
                    reshaped_sequence = last_sequence.reshape(1, *last_sequence.shape)
                    logging.info(f"Sequenza riformattata: {reshaped_sequence.shape}")
                    self.predict_next_hours(reshaped_sequence)
                except Exception as e:
                    logging.error(f"Errore durante l'elaborazione del messaggio: {e}")
            else:
                logging.info("Messaggio ricevuto non contiene la chiave 'X' - ignorato.")

if __name__ == "__main__":
    predictor = PredictorService()
    predictor.run()
