# app/utils/metrics.py
import time

class PerformanceMetrics:
    def __init__(self):
        self.metrics = []

    def log_response_time(self, model_name, response_time):
        self.metrics.append({"model": model_name, "response_time": response_time})

    def get_average_response_time(self, model_name):
        times = [m["response_time"] for m in self.metrics if m["model"] == model_name]
        return sum(times) / len(times) if times else 0