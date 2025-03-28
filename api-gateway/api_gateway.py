from flask import Flask, jsonify
from kafka import KafkaConsumer
import json
import threading
import time

app = Flask(__name__)
latest_prediction = None

def consume_predictions():
    global latest_prediction
    consumer = KafkaConsumer(
        'bitcoin_predictions',
        bootstrap_servers=['kafka:9092'],
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        auto_offset_reset='latest',
        group_id='gateway-group'
    )
    for msg in consumer:
        latest_prediction = msg.value
        # Per evitare loop troppo intensi
        time.sleep(1)

@app.route('/status')
def status():
    return jsonify({"status": "Bitcoin Prediction System is running."})

@app.route('/latest-prediction')
def get_latest_prediction():
    if latest_prediction:
        return jsonify(latest_prediction)
    else:
        return jsonify({"message": "No prediction available yet."}), 404

if __name__ == '__main__':
    # Avvia il consumer di Kafka in un thread separato
    threading.Thread(target=consume_predictions, daemon=True).start()
    app.run(host='0.0.0.0', port=5001)

