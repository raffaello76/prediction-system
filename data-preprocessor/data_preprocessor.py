import json
import pandas as pd
import numpy as np
from datetime import datetime
import time
from kafka import KafkaConsumer, KafkaProducer
import logging
from sklearn.preprocessing import MinMaxScaler

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('data-preprocessor')

class DataPreprocessor:
    def __init__(self):
        # Attesa per Kafka
        self._wait_for_kafka()
        
        # Consumer per il topic di dati grezzi
        self.consumer = KafkaConsumer(
            'bitcoin_data',
            bootstrap_servers=['kafka:9092'],
            value_deserializer=lambda x: json.loads(x.decode('utf-8')),
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            group_id='data-preprocessor-group'
        )
        
        # Producer per i dati preprocessati
        self.producer = KafkaProducer(
            bootstrap_servers=['kafka:9092'],
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            max_request_size=5242880  # Aumentato a 5MB
        )
        
        # Scaler per normalizzare i dati
        self.scaler = MinMaxScaler(feature_range=(0, 1))
        
        # Buffer per accumulare dati
        self.data_buffer = []
        
        # Parametri per la preparazione delle sequenze
        self.sequence_length = 10  # Numero di timeframes per ogni sequenza
        self.min_buffer_size = 30  # Minimo numero di candles prima di iniziare il preprocessing
        
        logger.info("DataPreprocessor inizializzato")

    def _wait_for_kafka(self, max_retries=30, retry_interval=10):
        """Attende che Kafka sia disponibile"""
        retries = 0
        while retries < max_retries:
            try:
                # Prova a connettersi a Kafka
                temp_consumer = KafkaConsumer(
                    bootstrap_servers=['kafka:9092'],
                    request_timeout_ms=5000
                )
                temp_consumer.close()
                logger.info("Connessione a Kafka riuscita!")
                return
            except Exception as e:
                logger.warning(f"Attesa per Kafka, riprovo in {retry_interval} secondi... ({e})")
                retries += 1
                time.sleep(retry_interval)
        
        raise Exception("Impossibile connettersi a Kafka dopo i tentativi massimi")

    def preprocess_candles(self, raw_data):
        """
        Converte i dati grezzi in un DataFrame e aggiunge indicatori tecnici
        """
        logger.info(f"Preprocessing di {len(raw_data)} candele")
        
        # Converte in DataFrame
        df = pd.DataFrame(raw_data)
        
        # Converti open_time in datetime
        df['open_time'] = pd.to_datetime(df['open_time'])
        
        # Ordina per tempo
        df = df.sort_values('open_time')
        
        # Calcola indicatori tecnici
        # 1. Returns
        df['returns'] = df['close'].pct_change()
        
        # 2. Moving Averages
        df['ma7'] = df['close'].rolling(window=7).mean()
        df['ma14'] = df['close'].rolling(window=14).mean()
        
        # 3. Price relative to MA
        df['price_ma7_ratio'] = df['close'] / df['ma7']
        
        # 4. Volatility (standard deviation of returns)
        df['volatility_7'] = df['returns'].rolling(window=7).std()
        
        # 5. Price range as percentage
        df['price_range'] = (df['high'] - df['low']) / df['close']
        
        # 6. Volume change
        df['volume_change'] = df['volume'].pct_change()
        
        # Riempi i valori NaN che derivano dal calcolo
        df = df.bfill()
        
        # Drop any remaining NaN values
        df = df.dropna()
        
        logger.info(f"DataFrame dopo preprocessing: {df.shape} righe")
        return df

    def prepare_sequences(self, df):
        """
        Prepara sequenze X e y per l'addestramento LSTM
        X: sequence_length timesteps di features
        y: il prezzo di chiusura del timestep successivo
        """
        logger.info("Preparazione sequenze per LSTM")
        
        # Features da utilizzare per la predizione
        features = ['open', 'high', 'low', 'close', 'volume', 
                   'returns', 'ma7', 'ma14', 'price_ma7_ratio', 
                   'volatility_7', 'price_range', 'volume_change']
        
        # Normalizza le feature (potrebbe essere necessario salvare lo scaler per future previsioni)
        df_scaled = pd.DataFrame(
            self.scaler.fit_transform(df[features]),
            columns=features
        )
        
        X = []
        y = []
        
        # Crea sequenze
        for i in range(len(df_scaled) - self.sequence_length):
            X.append(df_scaled.iloc[i:i+self.sequence_length].values)
            
            # Target: prezzo di chiusura normalizzato del timestep successivo
            close_index = features.index('close')
            y.append(df_scaled.iloc[i+self.sequence_length, close_index])
        
        logger.info(f"Sequenze create: X={len(X)}, y={len(y)}")
        return X, y

    def process_data(self):
        """
        Elabora i dati nel buffer e prepara sequenze per training
        """
        if len(self.data_buffer) < self.min_buffer_size:
            logger.info(f"Buffer insufficiente: {len(self.data_buffer)}/{self.min_buffer_size}")
            return
        
        try:
            # Preprocessing
            df = self.preprocess_candles(self.data_buffer)
            
            # Crea sequenze
            X, y = self.prepare_sequences(df)
            
            if len(X) > 0:
                # Definisci dimensione massima del batch
                batch_size = 50  # Puoi regolare questo valore in base alle tue esigenze
                
                # Numero di batch
                num_batches = (len(X) + batch_size - 1) // batch_size
                
                logger.info(f"Invio dati in {num_batches} batch di massimo {batch_size} sequenze ciascuno")
                
                # Invia i dati in batch
                for i in range(num_batches):
                    start_idx = i * batch_size
                    end_idx = min((i + 1) * batch_size, len(X))
                    
                    batch_X = X[start_idx:end_idx]
                    batch_y = y[start_idx:end_idx]
                    
                    data_to_send = {
                        'X': [x.tolist() for x in batch_X],
                        'y': batch_y,
                        'timestamp': datetime.now().isoformat(),
                        'batch_info': f"{i+1}/{num_batches}",
                        'features_used': ['open', 'high', 'low', 'close', 'volume', 
                                        'returns', 'ma7', 'ma14', 'price_ma7_ratio', 
                                        'volatility_7', 'price_range', 'volume_change']
                    }
                    
                    # Invia al topic per il training
                    self.producer.send('preprocessed_bitcoin_data', data_to_send)
                    self.producer.flush()
                    
                    logger.info(f"Inviato batch {i+1}/{num_batches} con {len(batch_X)} sequenze")
                
                # Mantieni solo gli ultimi 50% dei dati per l'overlap tra batch
                half_size = len(self.data_buffer) // 2
                self.data_buffer = self.data_buffer[-half_size:]
                
                logger.info(f"Completato invio di tutti i batch: {len(X)} sequenze totali")
            else:
                logger.warning("Nessuna sequenza generata dopo il preprocessing")
        except Exception as e:
            logger.error(f"Errore durante l'elaborazione dei dati: {e}")

    def run(self):
        """
        Avvia il servizio di preprocessing
        """
        logger.info("Avvio del servizio di preprocessing")
        try:
            for message in self.consumer:
                try:
                    # Estrai dati dal messaggio
                    data = message.value
                    logger.info(f"Ricevuto messaggio da topic {message.topic}, partition {message.partition}")
                    
                    # Aggiungi le candele al buffer
                    candles = data.get('data', [])
                    if not candles:
                        logger.warning("Nessuna candela nel messaggio")
                        continue
                    
                    self.data_buffer.extend(candles)
                    logger.info(f"Aggiunto al buffer, ora contiene {len(self.data_buffer)} candele")
                    
                    # Processa i dati
                    self.process_data()
                    
                except json.JSONDecodeError:
                    logger.error("Errore nella decodifica JSON del messaggio")
                except Exception as e:
                    logger.error(f"Errore nell'elaborazione del messaggio: {e}")
        except KeyboardInterrupt:
            logger.info("Servizio interrotto dall'utente")
        except Exception as e:
            logger.error(f"Errore generale nel servizio: {e}")
        finally:
            logger.info("Chiusura del servizio di preprocessing")
            self.consumer.close()
            self.producer.close()

if __name__ == "__main__":
    preprocessor = DataPreprocessor()
    preprocessor.run()