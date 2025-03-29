from flask import Flask, jsonify, request
from flask_cors import CORS
from kafka import KafkaConsumer, KafkaProducer
import json
import threading
import time
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('APIGateway')

# Inizializzazione Flask
app = Flask(__name__)
CORS(app)  # Abilita CORS per consentire richieste da frontend

# Variabili globali
latest_signals = {}  # Dizionario per memorizzare l'ultimo segnale per ogni timeframe
historical_prices = []  # Storico prezzi per grafici
signal_history = []  # Storico segnali
max_history_items = int(os.getenv("MAX_HISTORY_ITEMS", "100"))  # Numero massimo di elementi da tenere in memoria

# Configurazione Kafka
bootstrap_servers = os.getenv("KAFKA_SERVERS", "kafka:9092").split(",")
trading_signals_topic = os.getenv("TRADING_SIGNALS_TOPIC", "bitcoin_trading_signals")
api_key = os.getenv("API_KEY", "")  # API key per proteggere gli endpoint sensibili

# Consumer per i segnali di trading
def consume_trading_signals():
    global latest_signals, signal_history
    
    consumer = KafkaConsumer(
        trading_signals_topic,
        bootstrap_servers=bootstrap_servers,
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        auto_offset_reset='latest',
        group_id='gateway-group'
    )
    
    try:
        logger.info(f"🔄 Avvio consumer per il topic {trading_signals_topic}")
        
        for msg in consumer:
            signal = msg.value
            
            # Aggiungi timestamp se non presente
            if 'timestamp' not in signal:
                signal['timestamp'] = datetime.now().isoformat()
            
            # Estrai il timeframe (default: 4h)
            timeframe = signal.get('timeframe', '4h')
            
            # Aggiorna l'ultimo segnale per questo timeframe
            latest_signals[timeframe] = signal
            
            # Aggiungi alla cronologia, mantenendo la dimensione limitata
            signal_history.append(signal)
            if len(signal_history) > max_history_items:
                signal_history = signal_history[-max_history_items:]
            
            # Aggiorna anche lo storico prezzi se disponibile
            if 'price_now' in signal:
                price_entry = {
                    'price': signal['price_now'],
                    'timestamp': signal['timestamp'],
                    'timeframe': timeframe
                }
                historical_prices.append(price_entry)
                if len(historical_prices) > max_history_items:
                    historical_prices = historical_prices[-max_history_items:]
            
            logger.info(f"✅ Ricevuto nuovo segnale di trading ({timeframe}): {signal['action']} con confidenza {signal.get('confidence', 0)}")
            
    except Exception as e:
        logger.error(f"❌ Errore nel consumer Kafka: {str(e)}")
    finally:
        consumer.close()

# Funzione per verificare l'API key
def api_key_required(func):
    def wrapper(*args, **kwargs):
        if not api_key:
            # Se non è configurata un'API key, consenti l'accesso
            return func(*args, **kwargs)
        
        # Verifica l'API key
        request_key = request.headers.get('X-API-Key')
        if request_key and request_key == api_key:
            return func(*args, **kwargs)
        else:
            return jsonify({"error": "Unauthorized - Invalid API key"}), 401
    
    # Rinomina il wrapper per mantenere il nome della funzione originale
    wrapper.__name__ = func.__name__
    return wrapper

# Endpoints API
@app.route('/api/status')
def status():
    """Endpoint per verificare lo stato del servizio"""
    return jsonify({
        "status": "online",
        "service": "Bitcoin Trading System",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/signals/latest')
@api_key_required
def get_latest_signals():
    """Endpoint per ottenere gli ultimi segnali di trading per tutti i timeframe"""
    # Filtra per timeframe se specificato
    timeframe = request.args.get('timeframe')
    
    if timeframe and timeframe in latest_signals:
        return jsonify(latest_signals[timeframe])
    elif timeframe:
        return jsonify({"message": f"Nessun segnale disponibile per il timeframe {timeframe}"}), 404
    else:
        if latest_signals:
            return jsonify(latest_signals)
        else:
            return jsonify({"message": "Nessun segnale disponibile"}), 404

@app.route('/api/signals/history')
@api_key_required
def get_signal_history():
    """Endpoint per ottenere la cronologia dei segnali di trading"""
    # Parametri opzionali
    timeframe = request.args.get('timeframe')
    limit = request.args.get('limit', default=20, type=int)
    action = request.args.get('action')  # Filtra per BUY, SELL, HOLD
    
    # Limita il numero massimo di risultati
    limit = min(limit, max_history_items)
    
    # Filtra i risultati
    filtered_history = signal_history
    
    if timeframe:
        filtered_history = [s for s in filtered_history if s.get('timeframe') == timeframe]
    
    if action:
        filtered_history = [s for s in filtered_history if s.get('action') == action.upper()]
    
    # Prendi gli ultimi 'limit' elementi
    result = filtered_history[-limit:] if filtered_history else []
    
    return jsonify(result)

@app.route('/api/prices/history')
@api_key_required
def get_price_history():
    """Endpoint per ottenere la cronologia dei prezzi"""
    # Parametri opzionali
    timeframe = request.args.get('timeframe')
    limit = request.args.get('limit', default=100, type=int)
    
    # Limita il numero massimo di risultati
    limit = min(limit, max_history_items)
    
    # Filtra i risultati
    filtered_prices = historical_prices
    
    if timeframe:
        filtered_prices = [p for p in filtered_prices if p.get('timeframe') == timeframe]
    
    # Prendi gli ultimi 'limit' elementi
    result = filtered_prices[-limit:] if filtered_prices else []
    
    return jsonify(result)

@app.route('/api/dashboard')
@api_key_required
def get_dashboard_data():
    """Endpoint per ottenere tutti i dati necessari per la dashboard"""
    timeframe = request.args.get('timeframe', '4h')
    
    # Raccogli tutti i dati rilevanti
    dashboard_data = {
        "latest_signal": latest_signals.get(timeframe, {}),
        "recent_signals": [s for s in signal_history[-5:] if s.get('timeframe') == timeframe],
        "price_history": [p for p in historical_prices[-50:] if p.get('timeframe') == timeframe],
        "last_updated": datetime.now().isoformat()
    }
    
    return jsonify(dashboard_data)

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint non trovato"}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Errore interno del server"}), 500

if __name__ == '__main__':
    # Avvia il consumer Kafka in un thread separato
    threading.Thread(target=consume_trading_signals, daemon=True).start()
    
    # Configura porta e host
    port = int(os.getenv("API_PORT", "5001"))
    host = os.getenv("API_HOST", "0.0.0.0")
    
    logger.info(f"🚀 Avvio API Gateway su {host}:{port}")
    app.run(host=host, port=port)