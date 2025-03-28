import numpy as np
import pandas as pd

class BitcoinTradingStrategy:
    def __init__(self, prediction_model, risk_tolerance=0.05):
        """
        Inizializzazione strategia di trading
        Args:
        - prediction_model: Modello ML per predizioni
        - risk_tolerance: Percentuale massima di rischio (default 5%)
        """
        self.prediction_model = prediction_model
        self.risk_tolerance = risk_tolerance
        
    def calculate_trade_signals(self, predictions, current_price):
        """
        Calcola segnali di trading basati su predizioni
        """
        price_changes = np.diff(predictions)
        trend_direction = np.mean(price_changes)
        trend_volatility = np.std(price_changes)
        positive_moves = np.sum(price_changes > 0) / len(price_changes)
        negative_moves = np.sum(price_changes < 0) / len(price_changes)
        upper_threshold = current_price * (1 + self.risk_tolerance)
        lower_threshold = current_price * (1 - self.risk_tolerance)

        trade_signals = {
            'buy_signal': False,
            'sell_signal': False,
            'hold_signal': True,
            'confidence_score': 0.0,
            'predicted_price_change': trend_direction,
            'volatility': trend_volatility
        }

        if trend_direction > 0 and positive_moves > 0.6:
            if predictions[-1] > upper_threshold:
                trade_signals['buy_signal'] = True
                trade_signals['hold_signal'] = False
                trade_signals['confidence_score'] = positive_moves

        elif trend_direction < 0 and negative_moves > 0.6:
            if predictions[-1] < lower_threshold:
                trade_signals['sell_signal'] = True
                trade_signals['hold_signal'] = False
                trade_signals['confidence_score'] = negative_moves

        return trade_signals

    def risk_management(self, trade_signals, portfolio):
        """
        Gestione del rischio e dimensionamento della posizione
        """
        recommendations = {
            'action': 'HOLD',
            'position_size': 0,
            'stop_loss': None,
            'take_profit': None
        }

        if trade_signals['buy_signal']:
            position_size = portfolio['total_value'] * self.risk_tolerance
            recommendations.update({
                'action': 'BUY',
                'position_size': position_size,
                'stop_loss': portfolio['current_price'] * 0.95,
                'take_profit': portfolio['current_price'] * 1.1
            })

        elif trade_signals['sell_signal']:
            recommendations.update({
                'action': 'SELL',
                'position_size': portfolio['bitcoin_balance']
            })

        return recommendations

