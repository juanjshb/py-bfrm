from typing import Set

class RiskConfig:
    def __init__(self):
        self.weights = {}
        self.critical = set()
        self.rules = []

risk_config = RiskConfig()