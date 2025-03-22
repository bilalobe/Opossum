# app/models/availability.py
import asyncio
import logging
import time
from datetime import datetime, timedelta

import requests

from app.config import Config

logger = logging.getLogger(__name__)


class ServiceAvailability:
    """Monitors and tracks service availability for model backends"""

    def __init__(self):
        self.service_status = {
            "ollama": {
                "available": False,
                "last_checked": None,
                "status": "offline",  # Human-readable status: online, degraded, offline
                "response_time": 0,  # Response time in ms
                "availability": 0,  # Availability percentage
                "check_history": []  # List of timestamps of successful checks
            },
            "gemini": {
                "available": False,
                "last_checked": None,
                "status": "offline",
                "response_time": 0,
                "availability": 0,
                "check_history": []
            },
            "transformers": {
                "available": True,
                "last_checked": None,
                "status": "online",
                "response_time": 100,  # Default low response time for local service
                "availability": 100.0,  # Assuming local transformers is always available
                "check_history": []
            },
            "redis": {
                "available": False,
                "last_checked": None,
                "status": "offline",
                "response_time": 0,
                "availability": 0,
                "check_history": []
            }
        }

        # Track Gemini API usage for rate limiting
        self.gemini_usage = {
            "daily_count": 0,
            "minute_count": 0,
            "tokens_used": 0,
            "day_reset": datetime.now(),
            "minute_reset": datetime.now()
        }
        
        self.max_history_items = Config.SERVICE_HISTORY_MAX_ITEMS

        # Minimum interval between availability checks
        self.check_interval = timedelta(seconds=30)

        # Initialize check history with a timestamp to avoid empty history
        now = datetime.now()
        for service in self.service_status:
            self.service_status[service]["check_history"] = [now.timestamp()]

        logger.info("ServiceAvailability initialized with 30s check interval and metrics tracking")

    async def check_all_services(self):
        """Check availability of all services in parallel."""
        tasks = [
            self.check_gemini_availability(),
            self.check_ollama_availability(),
            self.check_transformers_availability()
        ]
        await asyncio.gather(*tasks)

    def _update_availability_metrics(self):
        """Update availability metrics based on check history"""
        now = datetime.now()
        # Use a fixed timestamp instead of repeatedly calculating it
        window_start_timestamp = (now - timedelta(hours=24)).timestamp()
        
        for service_name, service_data in self.service_status.items():
            # Use list comprehension only once and store the result
            recent_history = [ts for ts in service_data["check_history"] if ts > window_start_timestamp]
            self.service_status[service_name]["check_history"] = recent_history
            
            # Early return if no history
            if not recent_history:
                self.service_status[service_name]["availability"] = 0
                self.service_status[service_name]["status"] = "offline"
                continue
            
            # Calculate availability percentage
            successful_checks = len(recent_history)
            expected_checks = int(timedelta(hours=24).total_seconds() / self.check_interval.total_seconds())
            availability = min(100.0, (successful_checks / max(1, expected_checks)) * 100)
            self.service_status[service_name]["availability"] = round(availability, 2)
            
            # Update status based on availability and response time
            if self.service_status[service_name]["available"]:
                if availability >= 99.0 and self.service_status[service_name]["response_time"] <= 1000:
                    self.service_status[service_name]["status"] = "online"
                else:
                    self.service_status[service_name]["status"] = "degraded"
            else:
                self.service_status[service_name]["status"] = "offline"
                
            # Enforce history limit
            if len(self.service_status[service_name]["check_history"]) > self.max_history_items:
                self.service_status[service_name]["check_history"] = self.service_status[service_name]["check_history"][-self.max_history_items:]

    async def check_ollama_availability(self):
        """Check the availability of the Ollama service"""
        now = datetime.now()
        if (self.service_status["ollama"]["last_checked"] and
                (now - self.service_status["ollama"]["last_checked"]) < self.check_interval):
            logger.debug("Skipping Ollama check - checked recently")
            return

        self.service_status["ollama"]["last_checked"] = now
        previous_status = self.service_status["ollama"]["available"]
        start_time = time.time()

        try:
            response = requests.get(Config.OLLAMA_HEALTH_URL, timeout=2)
            # Calculate response time in milliseconds
            response_time = int((time.time() - start_time) * 1000)

            if response.status_code == 200:
                self.service_status["ollama"]["available"] = True
                self.service_status["ollama"]["response_time"] = response_time
                # Add successful check to history
                self.service_status["ollama"]["check_history"].append(now.timestamp())

                if not previous_status:
                    logger.info("Ollama service is now available")
            else:
                self.service_status["ollama"]["available"] = False
                self.service_status["ollama"]["response_time"] = 0
                if previous_status:
                    logger.warning(f"Ollama service unavailable: HTTP {response.status_code}")
        except requests.RequestException as e:
            self.service_status["ollama"]["available"] = False
            self.service_status["ollama"]["response_time"] = 0
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
        start_time = time.time()

        # Check for API key
        if not Config.GEMINI_API_KEY:
            if previous_status:
                logger.warning("Gemini service unavailable: No API key configured")
            self.service_status["gemini"]["available"] = False
            self.service_status["gemini"]["response_time"] = 0
            return

        # Check rate limits
        if (self.gemini_usage["daily_count"] >= Config.GEMINI_DAILY_LIMIT or
                self.gemini_usage["minute_count"] >= Config.GEMINI_RPM_LIMIT):
            self.service_status["gemini"]["available"] = False
            self.service_status["gemini"]["response_time"] = 0
            if previous_status:
                logger.warning(
                    f"Gemini service rate limited: {self.gemini_usage['minute_count']}/min, {self.gemini_usage['daily_count']}/day")
            return

        # Simulate a lightweight API check - in production, you'd make an actual API call
        try:
            # Simulate network delay
            await asyncio.sleep(0.1)
            response_time = int((time.time() - start_time) * 1000)

            # If we reach here, Gemini is available
            self.service_status["gemini"]["available"] = True
            self.service_status["gemini"]["response_time"] = response_time
            # Add successful check to history
            self.service_status["gemini"]["check_history"].append(now.timestamp())

            if not previous_status:
                logger.info("Gemini service is now available")
            logger.debug(
                f"Gemini usage stats: {self.gemini_usage['daily_count']}/day, {self.gemini_usage['minute_count']}/min")
        except Exception as e:
            self.service_status["gemini"]["available"] = False
            self.service_status["gemini"]["response_time"] = 0
            logger.error(f"Gemini check failed: {e}")

    async def check_transformers_availability(self):
        """Check the availability of the Transformers service"""
        now = datetime.now()
        if (self.service_status["transformers"]["last_checked"] and
                (now - self.service_status["transformers"]["last_checked"]) < self.check_interval):
            logger.debug("Skipping Transformers check - checked recently")
            return

        self.service_status["transformers"]["last_checked"] = now
        start_time = time.time()

        # For now we assume transformers is always available since it's local
        # Simulate a response time check
        await asyncio.sleep(0.05)
        response_time = int((time.time() - start_time) * 1000)

        # In a real implementation, we might check if the model is loaded
        self.service_status["transformers"]["available"] = True
        self.service_status["transformers"]["response_time"] = response_time
        # Add successful check to history
        self.service_status["transformers"]["check_history"].append(now.timestamp())

        logger.debug("Transformers service assumed available (local)")

    async def _check_redis_availability(self):
        """Check Redis service availability"""
        start_time = time.time()
        try:
            from app.utils.infrastructure.redis_config import check_redis_health
            is_available = check_redis_health()
            
            response_time = int((time.time() - start_time) * 1000)
            self._update_service_status("redis", is_available, response_time)
            
        except Exception as e:
            logger.error(f"Error checking Redis availability: {str(e)}")
            self._update_service_status("redis", False, 0)

    def _update_service_status(self, service_name, is_available, response_time):
        """Update service status with availability check results"""
        now = datetime.now()
        
        # Update service status
        self.service_status[service_name]["available"] = is_available
        self.service_status[service_name]["last_checked"] = now
        self.service_status[service_name]["response_time"] = response_time
        
        # Update check history
        self.service_status[service_name]["check_history"].append(now)
        
        # Keep only last 100 checks
        if len(self.service_status[service_name]["check_history"]) > 100:
            self.service_status[service_name]["check_history"].pop(0)
        
        # Calculate availability percentage
        total_checks = len(self.service_status[service_name]["check_history"])
        if total_checks > 0:
            availability = (sum(1 for _ in self.service_status[service_name]["check_history"]) / total_checks) * 100
            self.service_status[service_name]["availability"] = round(availability, 2)
        
        # Update status string
        if is_available:
            if response_time > 1000:  # If response time > 1 second
                self.service_status[service_name]["status"] = "degraded"
            else:
                self.service_status[service_name]["status"] = "online"
        else:
            self.service_status[service_name]["status"] = "offline"
        
        # Update Prometheus metrics
        self._update_prometheus_metrics(service_name)

    async def start_background_checks(self, app):
        """Start background availability checks"""
        async def background_checker():
            while True:
                try:
                    await self.check_all_services()
                    # Update cache with latest status
                    from app.utils.infrastructure.redis_config import add_to_cache
                    add_to_cache("service_status", self.get_services_for_visualization(), 
                               ttl=Config.AVAILABILITY_CACHE_TTL*2)
                except Exception as e:
                    logger.error(f"Error in background service check: {e}")
                await asyncio.sleep(Config.AVAILABILITY_CHECK_INTERVAL)
        
        # Create task and store in app context
        app.background_tasks = app.background_tasks if hasattr(app, 'background_tasks') else []
        app.background_tasks.append(asyncio.create_task(background_checker()))
        logger.info("Started background service availability checks")

    def record_gemini_usage(self, tokens_used=0):
        """Record Gemini API usage with token awareness"""
        self._reset_gemini_usage_counters()
        
        self.gemini_usage["daily_count"] += 1
        self.gemini_usage["minute_count"] += 1
        self.gemini_usage["tokens_used"] += tokens_used
        
        # Use both request count and token count for limits
        rate_limited = (
            self.gemini_usage["daily_count"] >= Config.GEMINI_DAILY_LIMIT or
            self.gemini_usage["minute_count"] >= Config.GEMINI_RPM_LIMIT or
            self.gemini_usage["tokens_used"] >= Config.GEMINI_DAILY_TOKEN_LIMIT
        )
        
        if rate_limited:
            self.service_status["gemini"]["available"] = False
            self.service_status["gemini"]["status"] = "rate_limited"
            logger.warning(
                f"Gemini service now rate limited: {self.gemini_usage['minute_count']}/min, "
                f"{self.gemini_usage['daily_count']}/day, {self.gemini_usage['tokens_used']} tokens"
            )
        
        logger.debug(
            f"Gemini usage: {self.gemini_usage['daily_count']}/day, "
            f"{self.gemini_usage['minute_count']}/min, {self.gemini_usage['tokens_used']} tokens"
        )
        
        # Update Prometheus metrics
        self._update_gemini_metrics(tokens_used)

    def _reset_gemini_usage_counters(self):
        """Reset usage counters when their time periods have elapsed"""
        now = datetime.now()

        # Reset daily counters if day has changed
        if (now - self.gemini_usage["day_reset"]).days > 0:
            if self.gemini_usage["daily_count"] > 0 or self.gemini_usage["tokens_used"] > 0:
                logger.info(
                    f"Resetting Gemini daily counters from {self.gemini_usage['daily_count']} "
                    f"requests and {self.gemini_usage['tokens_used']} tokens to 0"
                )
            self.gemini_usage["daily_count"] = 0
            self.gemini_usage["tokens_used"] = 0
            self.gemini_usage["day_reset"] = now

        # Reset minute counter if minute has elapsed
        if (now - self.gemini_usage["minute_reset"]).seconds >= 60:
            if self.gemini_usage["minute_count"] > 0:
                logger.debug(f"Resetting Gemini minute counter from {self.gemini_usage['minute_count']} to 0")
            self.gemini_usage["minute_count"] = 0
            self.gemini_usage["minute_reset"] = now

    def get_services_for_visualization(self):
        """Format service data for visualization"""
        visualization_data = {}

        for service_name, service_data in self.service_status.items():
            # Convert available flag to status string if not set
            status = service_data.get("status", "online" if service_data["available"] else "offline")

            visualization_data[service_name] = {
                "status": status,
                "response_time": service_data["response_time"],
                "availability": service_data["availability"]
            }

        return visualization_data

    def setup_prometheus_metrics(self):
        """Configure Prometheus metrics for monitoring"""
        try:
            from prometheus_client import Gauge, Counter
            
            # Create metrics
            self.metrics = {
                "availability": {
                    s: Gauge(f"service_availability_{s}", f"Availability percentage of {s} service")
                    for s in self.service_status
                },
                "response_time": {
                    s: Gauge(f"service_response_time_{s}", f"Response time in ms for {s} service")
                    for s in self.service_status
                },
                "api_calls": Counter("gemini_api_calls_total", "Total Gemini API calls"),
                "tokens_used": Counter("gemini_tokens_used_total", "Total Gemini API tokens used"),
                "model_selection": {
                    model: Counter(f"model_selection_{model}", f"Number of times {model} was selected")
                    for model in ["gemini", "ollama", "transformers"]
                }
            }
            logger.info("Prometheus metrics initialized")
        except ImportError:
            logger.warning("prometheus_client not installed, metrics disabled")
            self.metrics = None

    def _update_prometheus_metrics(self, service_name=None):
        """Update Prometheus metrics"""
        if not self.metrics:
            return
            
        if service_name:
            # Update single service metrics
            self.metrics["availability"][service_name].set(
                self.service_status[service_name]["availability"]
            )
            self.metrics["response_time"][service_name].set(
                self.service_status[service_name]["response_time"]
            )
        else:
            # Update all service metrics
            for svc in self.service_status:
                self.metrics["availability"][svc].set(
                    self.service_status[svc]["availability"]
                )
                self.metrics["response_time"][svc].set(
                    self.service_status[svc]["response_time"]
                )
                
    def _increment_model_selection(self, model_name):
        """Increment model selection counter"""
        if self.metrics and model_name in self.metrics["model_selection"]:
            self.metrics["model_selection"][model_name].inc()

    def _update_gemini_metrics(self, tokens_used=0):
        """Update Gemini-specific metrics"""
        if self.metrics:
            self.metrics["api_calls"].inc()
            if tokens_used > 0:
                self.metrics["tokens_used"].inc(tokens_used)
