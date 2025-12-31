"""System monitoring and health tracking service."""

import asyncio
import logging
import psutil
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import json
from pathlib import Path

from src.config import get_config
from .logging_service import get_logging_service, LogLevel, LogCategory


class HealthStatus(Enum):
    """System health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    ATTENTION_NEEDED = "attention_needed"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


@dataclass
class SystemMetrics:
    """System performance metrics."""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    disk_free_gb: float
    uptime_seconds: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'cpu_percent': self.cpu_percent,
            'memory_percent': self.memory_percent,
            'memory_used_mb': self.memory_used_mb,
            'memory_available_mb': self.memory_available_mb,
            'disk_usage_percent': self.disk_usage_percent,
            'disk_free_gb': self.disk_free_gb,
            'uptime_seconds': self.uptime_seconds
        }


@dataclass
class PostingStatistics:
    """Statistics for lesson posting operations."""
    total_attempts: int = 0
    successful_posts: int = 0
    failed_posts: int = 0
    total_retries: int = 0
    average_retry_count: float = 0.0
    last_successful_post: Optional[datetime] = None
    last_failed_post: Optional[datetime] = None
    success_rate: float = 0.0
    
    def update_success(self, retry_count: int = 0) -> None:
        """Update statistics for successful post."""
        self.total_attempts += 1
        self.successful_posts += 1
        self.total_retries += retry_count
        self.last_successful_post = datetime.utcnow()
        self._recalculate_rates()
    
    def update_failure(self, retry_count: int = 0) -> None:
        """Update statistics for failed post."""
        self.total_attempts += 1
        self.failed_posts += 1
        self.total_retries += retry_count
        self.last_failed_post = datetime.utcnow()
        self._recalculate_rates()
    
    def _recalculate_rates(self) -> None:
        """Recalculate derived statistics."""
        if self.total_attempts > 0:
            self.success_rate = self.successful_posts / self.total_attempts
            self.average_retry_count = self.total_retries / self.total_attempts
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert statistics to dictionary."""
        return {
            'total_attempts': self.total_attempts,
            'successful_posts': self.successful_posts,
            'failed_posts': self.failed_posts,
            'total_retries': self.total_retries,
            'average_retry_count': self.average_retry_count,
            'last_successful_post': self.last_successful_post.isoformat() if self.last_successful_post else None,
            'last_failed_post': self.last_failed_post.isoformat() if self.last_failed_post else None,
            'success_rate': self.success_rate
        }


class MonitoringService:
    """Comprehensive system monitoring and health tracking service."""
    
    def __init__(self, metrics_retention_hours: int = 24):
        """
        Initialize monitoring service.
        
        Args:
            metrics_retention_hours: How long to retain metrics history
        """
        self.config = get_config()
        self.logging_service = get_logging_service()
        self.logger = logging.getLogger(__name__)
        
        # Monitoring configuration
        self.metrics_retention_hours = metrics_retention_hours
        self.metrics_collection_interval = 60  # seconds
        self.health_check_interval = 300  # 5 minutes
        
        # System state tracking
        self.start_time = datetime.utcnow()
        self.last_health_check = None
        self.current_health_status = HealthStatus.HEALTHY
        
        # Metrics storage
        self.metrics_history: List[SystemMetrics] = []
        self.posting_stats = PostingStatistics()
        
        # Health check callbacks
        self.health_check_callbacks: List[Callable[[], Dict[str, Any]]] = []
        
        # Monitoring tasks
        self._monitoring_tasks: List[asyncio.Task] = []
        self._running = False
        
        # Resource thresholds for health assessment
        self.thresholds = {
            'cpu_warning': 70.0,
            'cpu_critical': 90.0,
            'memory_warning': 80.0,
            'memory_critical': 95.0,
            'disk_warning': 85.0,
            'disk_critical': 95.0,
            'max_failed_posts': 5,
            'min_success_rate': 0.8
        }
    
    async def start(self) -> bool:
        """
        Start monitoring service.
        
        Returns:
            True if started successfully, False otherwise.
        """
        try:
            if self._running:
                self.logger.warning("Monitoring service is already running")
                return True
            
            self.logger.info("Starting monitoring service")
            
            # Start monitoring tasks
            self._monitoring_tasks = [
                asyncio.create_task(self._metrics_collection_loop()),
                asyncio.create_task(self._health_check_loop()),
                asyncio.create_task(self._cleanup_loop())
            ]
            
            self._running = True
            
            # Log startup
            self.logging_service.log_structured(
                LogLevel.INFO,
                LogCategory.MONITORING,
                "monitoring_service",
                "Monitoring service started",
                {
                    'metrics_retention_hours': self.metrics_retention_hours,
                    'collection_interval': self.metrics_collection_interval,
                    'health_check_interval': self.health_check_interval
                }
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start monitoring service: {e}")
            self.logging_service.log_error_with_context(
                e, {'operation': 'start_monitoring'}, 'monitoring_service'
            )
            return False
    
    async def stop(self) -> None:
        """Stop monitoring service."""
        try:
            if not self._running:
                self.logger.warning("Monitoring service is not running")
                return
            
            self.logger.info("Stopping monitoring service")
            
            # Cancel monitoring tasks
            for task in self._monitoring_tasks:
                task.cancel()
            
            # Wait for tasks to complete
            await asyncio.gather(*self._monitoring_tasks, return_exceptions=True)
            
            self._running = False
            self._monitoring_tasks.clear()
            
            # Log shutdown
            self.logging_service.log_structured(
                LogLevel.INFO,
                LogCategory.MONITORING,
                "monitoring_service",
                "Monitoring service stopped",
                self.get_system_status()
            )
            
        except Exception as e:
            self.logger.error(f"Error stopping monitoring service: {e}")
    
    async def _metrics_collection_loop(self) -> None:
        """Background task for collecting system metrics."""
        while self._running:
            try:
                metrics = self._collect_system_metrics()
                self.metrics_history.append(metrics)
                
                # Log metrics periodically (every 10 minutes)
                if len(self.metrics_history) % 10 == 0:
                    self.logging_service.log_structured(
                        LogLevel.DEBUG,
                        LogCategory.MONITORING,
                        "metrics_collector",
                        "System metrics collected",
                        metrics.to_dict()
                    )
                
                await asyncio.sleep(self.metrics_collection_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in metrics collection: {e}")
                await asyncio.sleep(self.metrics_collection_interval)
    
    async def _health_check_loop(self) -> None:
        """Background task for performing health checks."""
        while self._running:
            try:
                await self.perform_health_check()
                await asyncio.sleep(self.health_check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in health check: {e}")
                await asyncio.sleep(self.health_check_interval)
    
    async def _cleanup_loop(self) -> None:
        """Background task for cleaning up old metrics."""
        while self._running:
            try:
                self._cleanup_old_metrics()
                # Run cleanup every hour
                await asyncio.sleep(3600)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cleanup: {e}")
                await asyncio.sleep(3600)
    
    def _collect_system_metrics(self) -> SystemMetrics:
        """Collect current system metrics."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_mb = memory.used / (1024 * 1024)
            memory_available_mb = memory.available / (1024 * 1024)
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_usage_percent = (disk.used / disk.total) * 100
            disk_free_gb = disk.free / (1024 * 1024 * 1024)
            
            # Uptime
            uptime_seconds = (datetime.utcnow() - self.start_time).total_seconds()
            
            return SystemMetrics(
                timestamp=datetime.utcnow(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_used_mb=memory_used_mb,
                memory_available_mb=memory_available_mb,
                disk_usage_percent=disk_usage_percent,
                disk_free_gb=disk_free_gb,
                uptime_seconds=uptime_seconds
            )
            
        except Exception as e:
            self.logger.error(f"Error collecting system metrics: {e}")
            # Return default metrics on error
            return SystemMetrics(
                timestamp=datetime.utcnow(),
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_used_mb=0.0,
                memory_available_mb=0.0,
                disk_usage_percent=0.0,
                disk_free_gb=0.0,
                uptime_seconds=0.0
            )
    
    def _cleanup_old_metrics(self) -> None:
        """Remove old metrics beyond retention period."""
        cutoff_time = datetime.utcnow() - timedelta(hours=self.metrics_retention_hours)
        
        original_count = len(self.metrics_history)
        self.metrics_history = [
            m for m in self.metrics_history 
            if m.timestamp > cutoff_time
        ]
        
        removed_count = original_count - len(self.metrics_history)
        if removed_count > 0:
            self.logger.debug(f"Cleaned up {removed_count} old metrics entries")
    
    async def perform_health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive system health check.
        
        Returns:
            Health check results
        """
        self.last_health_check = datetime.utcnow()
        
        try:
            # Get latest metrics
            current_metrics = self._collect_system_metrics()
            
            # Assess system health
            health_issues = []
            health_warnings = []
            
            # Check CPU usage
            if current_metrics.cpu_percent > self.thresholds['cpu_critical']:
                health_issues.append(f"Critical CPU usage: {current_metrics.cpu_percent:.1f}%")
            elif current_metrics.cpu_percent > self.thresholds['cpu_warning']:
                health_warnings.append(f"High CPU usage: {current_metrics.cpu_percent:.1f}%")
            
            # Check memory usage
            if current_metrics.memory_percent > self.thresholds['memory_critical']:
                health_issues.append(f"Critical memory usage: {current_metrics.memory_percent:.1f}%")
            elif current_metrics.memory_percent > self.thresholds['memory_warning']:
                health_warnings.append(f"High memory usage: {current_metrics.memory_percent:.1f}%")
            
            # Check disk usage
            if current_metrics.disk_usage_percent > self.thresholds['disk_critical']:
                health_issues.append(f"Critical disk usage: {current_metrics.disk_usage_percent:.1f}%")
            elif current_metrics.disk_usage_percent > self.thresholds['disk_warning']:
                health_warnings.append(f"High disk usage: {current_metrics.disk_usage_percent:.1f}%")
            
            # Check posting statistics
            if self.posting_stats.failed_posts > self.thresholds['max_failed_posts']:
                health_issues.append(f"Too many failed posts: {self.posting_stats.failed_posts}")
            
            if (self.posting_stats.total_attempts > 0 and 
                self.posting_stats.success_rate < self.thresholds['min_success_rate']):
                health_warnings.append(f"Low success rate: {self.posting_stats.success_rate:.2%}")
            
            # Run custom health checks
            for callback in self.health_check_callbacks:
                try:
                    callback_result = callback()
                    if callback_result.get('issues'):
                        health_issues.extend(callback_result['issues'])
                    if callback_result.get('warnings'):
                        health_warnings.extend(callback_result['warnings'])
                except Exception as e:
                    health_warnings.append(f"Health check callback error: {e}")
            
            # Determine overall health status
            if health_issues:
                self.current_health_status = HealthStatus.UNHEALTHY
            elif health_warnings:
                self.current_health_status = HealthStatus.ATTENTION_NEEDED
            else:
                self.current_health_status = HealthStatus.HEALTHY
            
            health_result = {
                'status': self.current_health_status.value,
                'timestamp': self.last_health_check.isoformat(),
                'issues': health_issues,
                'warnings': health_warnings,
                'metrics': current_metrics.to_dict(),
                'posting_stats': self.posting_stats.to_dict(),
                'uptime_hours': current_metrics.uptime_seconds / 3600
            }
            
            # Log health status
            log_level = LogLevel.ERROR if health_issues else (
                LogLevel.WARNING if health_warnings else LogLevel.INFO
            )
            
            self.logging_service.log_system_health(
                self.current_health_status.value,
                health_result
            )
            
            return health_result
            
        except Exception as e:
            self.logger.error(f"Error performing health check: {e}")
            self.logging_service.log_error_with_context(
                e, {'operation': 'health_check'}, 'monitoring_service'
            )
            
            return {
                'status': HealthStatus.CRITICAL.value,
                'timestamp': datetime.utcnow().isoformat(),
                'issues': [f"Health check failed: {e}"],
                'warnings': [],
                'metrics': {},
                'posting_stats': {}
            }
    
    def record_posting_attempt(self, success: bool, retry_count: int = 0) -> None:
        """
        Record a lesson posting attempt.
        
        Args:
            success: Whether posting was successful
            retry_count: Number of retries made
        """
        if success:
            self.posting_stats.update_success(retry_count)
        else:
            self.posting_stats.update_failure(retry_count)
        
        # Log the posting statistics update
        self.logging_service.log_structured(
            LogLevel.DEBUG,
            LogCategory.MONITORING,
            "posting_tracker",
            f"Posting attempt recorded: {'success' if success else 'failure'}",
            {
                'success': success,
                'retry_count': retry_count,
                'total_attempts': self.posting_stats.total_attempts,
                'success_rate': self.posting_stats.success_rate
            }
        )
    
    def add_health_check_callback(self, callback: Callable[[], Dict[str, Any]]) -> None:
        """
        Add a custom health check callback.
        
        Args:
            callback: Function that returns health check results
        """
        self.health_check_callbacks.append(callback)
        self.logger.info(f"Added health check callback: {callback.__name__}")
    
    def setup_resilience_integration(self) -> None:
        """Set up integration with resilience service."""
        try:
            # Import here to avoid circular imports
            from .resilience_service import get_resilience_service
            
            resilience_service = get_resilience_service()
            
            # Add resilience health check callback
            def resilience_health_check() -> Dict[str, Any]:
                """Health check callback for resilience service."""
                try:
                    resilience_status = resilience_service.get_resilience_status()
                    
                    issues = []
                    warnings = []
                    
                    # Check system mode
                    current_mode = resilience_status.get('current_mode', 'normal')
                    if current_mode == 'emergency':
                        issues.append(f"System in emergency mode")
                    elif current_mode == 'minimal':
                        warnings.append(f"System in minimal operation mode")
                    elif current_mode == 'degraded':
                        warnings.append(f"System in degraded operation mode")
                    
                    # Check consecutive failures
                    consecutive_failures = resilience_status.get('consecutive_failures', 0)
                    if consecutive_failures >= 5:
                        issues.append(f"High consecutive failures: {consecutive_failures}")
                    elif consecutive_failures >= 3:
                        warnings.append(f"Elevated consecutive failures: {consecutive_failures}")
                    
                    # Check circuit breakers
                    circuit_breakers = resilience_status.get('circuit_breakers', {})
                    for service, breaker in circuit_breakers.items():
                        if breaker.get('state') == 'open':
                            issues.append(f"Circuit breaker open for {service}")
                        elif breaker.get('failure_count', 0) >= 3:
                            warnings.append(f"High failure count for {service}: {breaker['failure_count']}")
                    
                    return {
                        'issues': issues,
                        'warnings': warnings,
                        'resilience_status': resilience_status
                    }
                    
                except Exception as e:
                    return {
                        'issues': [f"Resilience health check failed: {e}"],
                        'warnings': []
                    }
            
            self.add_health_check_callback(resilience_health_check)
            self.logger.info("Resilience integration set up successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to set up resilience integration: {e}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        Get comprehensive system status.
        
        Returns:
            System status dictionary
        """
        try:
            current_metrics = self._collect_system_metrics() if self.metrics_history else None
            
            # Calculate average metrics over last hour
            hour_ago = datetime.utcnow() - timedelta(hours=1)
            recent_metrics = [m for m in self.metrics_history if m.timestamp > hour_ago]
            
            avg_metrics = {}
            if recent_metrics:
                avg_metrics = {
                    'avg_cpu_percent': sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics),
                    'avg_memory_percent': sum(m.memory_percent for m in recent_metrics) / len(recent_metrics),
                    'avg_disk_usage_percent': sum(m.disk_usage_percent for m in recent_metrics) / len(recent_metrics)
                }
            
            return {
                'service_running': self._running,
                'start_time': self.start_time.isoformat(),
                'uptime_hours': (datetime.utcnow() - self.start_time).total_seconds() / 3600,
                'current_health_status': self.current_health_status.value,
                'last_health_check': self.last_health_check.isoformat() if self.last_health_check else None,
                'current_metrics': current_metrics.to_dict() if current_metrics else {},
                'average_metrics_last_hour': avg_metrics,
                'posting_statistics': self.posting_stats.to_dict(),
                'metrics_history_count': len(self.metrics_history),
                'health_check_callbacks_count': len(self.health_check_callbacks),
                'thresholds': self.thresholds.copy()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting system status: {e}")
            return {
                'service_running': self._running,
                'error': str(e)
            }
    
    def get_metrics_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get metrics summary for specified time period.
        
        Args:
            hours: Number of hours to include in summary
            
        Returns:
            Metrics summary
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            relevant_metrics = [m for m in self.metrics_history if m.timestamp > cutoff_time]
            
            if not relevant_metrics:
                return {'error': 'No metrics available for specified period'}
            
            # Calculate statistics
            cpu_values = [m.cpu_percent for m in relevant_metrics]
            memory_values = [m.memory_percent for m in relevant_metrics]
            disk_values = [m.disk_usage_percent for m in relevant_metrics]
            
            return {
                'period_hours': hours,
                'data_points': len(relevant_metrics),
                'cpu_stats': {
                    'min': min(cpu_values),
                    'max': max(cpu_values),
                    'avg': sum(cpu_values) / len(cpu_values)
                },
                'memory_stats': {
                    'min': min(memory_values),
                    'max': max(memory_values),
                    'avg': sum(memory_values) / len(memory_values)
                },
                'disk_stats': {
                    'min': min(disk_values),
                    'max': max(disk_values),
                    'avg': sum(disk_values) / len(disk_values)
                },
                'start_time': relevant_metrics[0].timestamp.isoformat(),
                'end_time': relevant_metrics[-1].timestamp.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting metrics summary: {e}")
            return {'error': str(e)}
    
    def export_metrics(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Export metrics data for specified time period.
        
        Args:
            hours: Number of hours to export
            
        Returns:
            List of metrics dictionaries
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            relevant_metrics = [m for m in self.metrics_history if m.timestamp > cutoff_time]
            
            return [m.to_dict() for m in relevant_metrics]
            
        except Exception as e:
            self.logger.error(f"Error exporting metrics: {e}")
            return []


# Global monitoring service instance
_monitoring_service = None

def get_monitoring_service() -> MonitoringService:
    """Get the global monitoring service instance."""
    global _monitoring_service
    if _monitoring_service is None:
        _monitoring_service = MonitoringService()
    return _monitoring_service

async def setup_monitoring(metrics_retention_hours: int = 24) -> MonitoringService:
    """Set up and start monitoring service."""
    global _monitoring_service
    _monitoring_service = MonitoringService(metrics_retention_hours)
    await _monitoring_service.start()
    return _monitoring_service