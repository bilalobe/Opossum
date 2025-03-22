# app/models/availability.py
import logging
import asyncio
import requests
from datetime import datetime, timedelta
from app.config import Config

logger = logging.getLogger(__name__)

class ServiceAvailability:
 """Monitors and tracks service availability for model backends"""

 def __init__(self):
     self.service_status = {
         "ollama": {"available": False, "last_checked": None},
         "gemini": {"available": False, "last_checked": None},
         "transformers": {"available": True, "last_checked": None},  # Local, assumed available
     }

     # Track Gemini API usage for rate limiting
     self.gemini_usage = {
         "daily_count": 0,
         "minute_count": 0,
         "day_reset": datetime.now(),
         "minute_reset": datetime.now()
     }

     # Minimum interval between availability checks
     self.check_interval = timedelta(seconds=30)
     logger.info("ServiceAvailability initialized with 30s check interval")

 async def check_all_services(self):
     """Check availability of all configured services"""
     logger.debug("Beginning availability check for all services")

     # Run all checks concurrently
     await asyncio.gather(
         self.check_ollama_availability(),
         self.check_gemini_availability(),
         self.check_transformers_availability()
     )

     # Log overall availability status
     available_services = [s for s, status in self.service_status.items()
                          if status["available"]]
     logger.info(f"Service availability: {len(available_services)}/3 services available")

 async def check_ollama_availability(self):
     """Check the availability of the Ollama service"""
     now = datetime.now()
     if (self.service_status["ollama"]["last_checked"] and
         (now - self.service_status["ollama"]["last_checked"]) < self.check_interval):
         logger.debug("Skipping Ollama check - checked recently")
         return

     self.service_status["ollama"]["last_checked"] = now
     previous_status = self.service_status["ollama"]["available"]

     try:
         response = requests.get(Config.OLLAMA_HEALTH_URL, timeout=2)
         if response.status_code == 200:
             self.service_status["ollama"]["available"] = True
             if not previous_status:
                 logger.info("Ollama service is now available")
         else:
             self.service_status["ollama"]["available"] = False
             if previous_status:
                 logger.warning(f"Ollama service unavailable: HTTP {response.status_code}")
     except requests.RequestException as e:
         self.service_status["ollama"]["available"] = False
         if previous_status:
             logger.error(f"Ollama service check failed: {e}")

 async def check_gemini_availability(self):
     """Check the availability of the Gemini service"""
     # Reset usage counters if needed
     self._reset_gemini_usage_counters()

     now = datetime.now()
     if (self.service_status["gemini"]["last_checked"] and
         (now - self.service_status["gemini"]["last_checked"]) < self.check_interval):
         logger.debug("Skipping Gemini check - checked recently")
         return

     self.service_status["gemini"]["last_checked"] = now
     previous_status = self.service_status["gemini"]["available"]

     # Check for API key
     if not Config.GEMINI_API_KEY:
         if previous_status:
             logger.warning("Gemini service unavailable: No API key configured")
         self.service_status["gemini"]["available"] = False
         return

     # Check rate limits
     if (self.gemini_usage["daily_count"] >= Config.GEMINI_DAILY_LIMIT or
         self.gemini_usage["minute_count"] >= Config.GEMINI_RPM_LIMIT):
         self.service_status["gemini"]["available"] = False
         if previous_status:
             logger.warning(f"Gemini service rate limited: {self.gemini_usage['minute_count']}/min, {self.gemini_usage['daily_count']}/day")
         return

     # If we reach here, Gemini is available
     self.service_status["gemini"]["available"] = True
     if not previous_status:
         logger.info("Gemini service is now available")
     logger.debug(f"Gemini usage stats: {self.gemini_usage['daily_count']}/day, {self.gemini_usage['minute_count']}/min")

 async def check_transformers_availability(self):
     """Check the availability of the Transformers service"""
     now = datetime.now()
     if (self.service_status["transformers"]["last_checked"] and
         (now - self.service_status["transformers"]["last_checked"]) < self.check_interval):
         logger.debug("Skipping Transformers check - checked recently")
         return

     self.service_status["transformers"]["last_checked"] = now

     # For now we assume transformers is always available since it's local
     # In a real implementation, we might check if the model is loaded
     self.service_status["transformers"]["available"] = True
     logger.debug("Transformers service assumed available (local)")

 def record_gemini_usage(self):
     """Record Gemini API usage and update availability based on limits"""
     self._reset_gemini_usage_counters()

     self.gemini_usage["daily_count"] += 1
     self.gemini_usage["minute_count"] += 1

     # Update availability if we've hit limits
     if (self.gemini_usage["daily_count"] >= Config.GEMINI_DAILY_LIMIT or
         self.gemini_usage["minute_count"] >= Config.GEMINI_RPM_LIMIT):
         self.service_status["gemini"]["available"] = False
         logger.warning(f"Gemini service now rate limited: {self.gemini_usage['minute_count']}/min, {self.gemini_usage['daily_count']}/day")

     logger.debug(f"Gemini usage: {self.gemini_usage['daily_count']}/day, {self.gemini_usage['minute_count']}/min")

 def _reset_gemini_usage_counters(self):
     """Reset usage counters when their time periods have elapsed"""
     now = datetime.now()

     # Reset daily counter if day has changed
     if (now - self.gemini_usage["day_reset"]).days > 0:
         if self.gemini_usage["daily_count"] > 0:
             logger.info(f"Resetting Gemini daily counter from {self.gemini_usage['daily_count']} to 0")
         self.gemini_usage["daily_count"] = 0
         self.gemini_usage["day_reset"] = now

     # Reset minute counter if minute has elapsed
     if (now - self.gemini_usage["minute_reset"]).seconds >= 60:
         if self.gemini_usage["minute_count"] > 0:
             logger.debug(f"Resetting Gemini minute counter from {self.gemini_usage['minute_count']} to 0")
         self.gemini_usage["minute_count"] = 0
         self.gemini_usage["minute_reset"] = now