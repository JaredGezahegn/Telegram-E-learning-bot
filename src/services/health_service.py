"""
Health check service for deployment platforms.
Provides HTTP endpoint for health monitoring.
"""

import sqlite3
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any
import json
import logging

logger = logging.getLogger(__name__)


class HealthCheckHandler(BaseHTTPRequestHandler):
    """HTTP handler for health check requests."""
    
    def do_GET(self):
        """Handle GET requests for health checks."""
        if self.path == '/health':
            try:
                health_status = self.get_health_status()
                self.send_response(200 if health_status['healthy'] else 503)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(health_status).encode())
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                self.send_response(503)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                error_response = {
                    'healthy': False,
                    'error': str(e),
                    'timestamp': time.time()
                }
                self.wfile.write(json.dumps(error_response).encode())
        elif self.path == '/debug':
            try:
                debug_info = self.get_debug_info()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(debug_info).encode())
            except Exception as e:
                logger.error(f"Debug info failed: {e}")
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                error_response = {
                    'error': str(e),
                    'timestamp': time.time()
                }
                self.wfile.write(json.dumps(error_response).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status of the application."""
        try:
            # Import here to avoid circular imports
            import sys
            import os
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
            
            from services.database_factory import create_lesson_repository
            
            # Use the configured database (SQLite or Supabase)
            repo = create_lesson_repository()
            
            # Test connection and get lesson count
            if hasattr(repo, 'get_all_lessons'):
                lessons = repo.get_all_lessons()
                lesson_count = len(lessons)
                database_type = "supabase" if "Supabase" in str(type(repo)) else "sqlite"
            else:
                # Fallback for older repository interface
                lesson_count = 0
                database_type = "unknown"
            
            return {
                'healthy': True,
                'database': 'connected',
                'database_type': database_type,
                'lesson_count': lesson_count,
                'timestamp': time.time(),
                'status': 'operational'
            }
        except Exception as e:
            return {
                'healthy': False,
                'database': 'error',
                'error': str(e),
                'timestamp': time.time(),
                'status': 'degraded'
            }
    
    def get_debug_info(self) -> Dict[str, Any]:
        """Get debug information about configuration and environment."""
        import os
        
        try:
            # Import here to avoid circular imports
            import sys
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
            
            from config import get_config
            
            config = get_config()
            
            return {
                'environment_variables': {
                    'DATABASE_TYPE': os.getenv('DATABASE_TYPE'),
                    'SUPABASE_URL': os.getenv('SUPABASE_URL'),
                    'SUPABASE_ANON_KEY': os.getenv('SUPABASE_ANON_KEY')[:20] + '...' if os.getenv('SUPABASE_ANON_KEY') else None,
                    'TELEGRAM_BOT_TOKEN': os.getenv('TELEGRAM_BOT_TOKEN')[:20] + '...' if os.getenv('TELEGRAM_BOT_TOKEN') else None,
                    'CHANNEL_ID': os.getenv('CHANNEL_ID'),
                },
                'config_values': {
                    'database_type': config.database_type,
                    'database_path': config.database_path,
                    'supabase_url': config.supabase_url,
                    'channel_id': config.channel_id,
                    'posting_time': config.posting_time,
                    'timezone': config.timezone,
                },
                'timestamp': time.time()
            }
        except Exception as e:
            return {
                'error': str(e),
                'timestamp': time.time()
            }
    
    def log_message(self, format, *args):
        """Override to reduce log noise from health checks."""
        # Only log non-health check requests
        # Check if args[0] is a string and contains '/health'
        if args and isinstance(args[0], str) and '/health' not in args[0]:
            super().log_message(format, *args)
        elif args and not isinstance(args[0], str):
            # For non-string args (like HTTPStatus), always log
            super().log_message(format, *args)


class HealthService:
    """Service to provide health check HTTP endpoint."""
    
    def __init__(self, port: int = 8000):
        self.port = port
        self.server = None
        self.thread = None
        self.running = False
    
    def start(self):
        """Start the health check HTTP server."""
        try:
            self.server = HTTPServer(('0.0.0.0', self.port), HealthCheckHandler)
            self.thread = threading.Thread(target=self._run_server, daemon=True)
            self.running = True
            self.thread.start()
            logger.info(f"Health check service started on port {self.port}")
        except Exception as e:
            logger.error(f"Failed to start health service: {e}")
    
    def stop(self):
        """Stop the health check HTTP server."""
        if self.server and self.running:
            self.running = False
            self.server.shutdown()
            self.server.server_close()
            if self.thread:
                self.thread.join(timeout=5)
            logger.info("Health check service stopped")
    
    def _run_server(self):
        """Run the HTTP server in a separate thread."""
        try:
            self.server.serve_forever()
        except Exception as e:
            if self.running:  # Only log if we're supposed to be running
                logger.error(f"Health service error: {e}")


# Global health service instance
_health_service = None


def start_health_service(port: int = 8000):
    """Start the global health service."""
    global _health_service
    if _health_service is None:
        _health_service = HealthService(port)
        _health_service.start()


def stop_health_service():
    """Stop the global health service."""
    global _health_service
    if _health_service:
        _health_service.stop()
        _health_service = None