"""Resource monitoring service for tracking system resource usage within hosting limits."""

import asyncio
import logging
import psutil
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from enum import Enum

from src.config import get_config
from .logging_service import get_logging_service, LogLevel, LogCategory


logger = logging.getLogger(__name__)


class ResourceStatus(Enum):
    """Resource usage status levels."""
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class ResourceLimits:
    """Resource limits for free hosting tiers."""
    # Memory limits (MB)
    memory_warning_mb: float = 200.0  # Warning at 200MB
    memory_critical_mb: float = 300.0  # Critical at 300MB
    memory_emergency_mb: float = 400.0  # Emergency at 400MB
    
    # CPU limits (percentage over time window)
    cpu_warning_percent: float = 70.0
    cpu_critical_percent: float = 85.0
    cpu_emergency_percent: float = 95.0
    
    # Disk limits (percentage)
    disk_warning_percent: float = 80.0
    disk_critical_percent: float = 90.0
    disk_emergency_percent: float = 95.0
    
    # Network limits
    network_connections_warning: int = 50
    network_connections_critical: int = 80
    network_connections_emergency: int = 100


@dataclass
class ResourceMetrics:
    """Current resource usage metrics."""
    timestamp: datetime
    memory_mb: float
    memory_percent: float
    cpu_percent: float
    disk_percent: float
    network_connections: int
    process_count: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'memory_mb': self.memory_mb,
            'memory_percent': self.memory_percent,
            'cpu_percent': self.cpu_percent,
            'disk_percent': self.disk_percent,
            'network_connections': self.network_connections,
            'process_count': self.process_count
        }


class ResourceMonitor:
    """Monitor system resources and enforce hosting limits."""
    
    def __init__(self):
        """Initialize resource monitor."""
        self.config = get_config()
        self.logging_service = get_logging_service()
        self.limits = ResourceLimits()
        
        # Monitoring state
        self._running = False
        self._monitoring_task: Optional[asyncio.Task] = None
        self._metrics_history: List[ResourceMetrics] = []
        self._max_history_size = 100  # Keep last 100 measurements
        
        # Alert callbacks
        self._alert_callbacks: List[Callable[[ResourceStatus, ResourceMetrics], None]] = []
        
        # Current status
        self._current_status = ResourceStatus.NORMAL
        self._last_alert_time: Optional[datetime] = None
        self._alert_cooldown_seconds = 300  # 5 minutes between alerts
    
    async def start(self) -> bool:
        """Start resource monitoring."""
        try:
            if self._running:
                logger.warning("Resource monitor is already running")
                return True
            
            logger.info("Starting resource monitor")
            
            # Start monitoring task
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
            self._running = True
            
            # Log startup
            self.logging_service.log_structured(
                LogLevel.INFO,
                LogCategory.SYSTEM,
                "resource_monitor",
                "Resource monitor started",
                {
                    'limits': {
                        'memory_warning_mb': self.limits.memory_warning_mb,
                        'memory_critical_mb': self.limits.memory_critical_mb,
                        'cpu_warning_percent': self.limits.cpu_warning_percent,
                        'cpu_critical_percent': self.limits.cpu_critical_percent
                    }
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start resource monitor: {e}")
            return False
    
    async def stop(self) -> None:
        """Stop resource monitoring."""
        try:
            if not self._running:
                logger.warning("Resource monitor is not running")
                return
            
            logger.info("Stopping resource monitor")
            
            # Cancel monitoring task
            if self._monitoring_task:
                self._monitoring_task.cancel()
                try:
                    await self._monitoring_task
                except asyncio.CancelledError:
                    pass
            
            self._running = False
            
            # Log shutdown
            self.logging_service.log_structured(
                LogLevel.INFO,
                LogCategory.SYSTEM,
                "resource_monitor",
                "Resource monitor stopped",
                {
                    'final_status': self._current_status.value,
                    'metrics_collected': len(self._metrics_history)
                }
            )
            
        except Exception as e:
            logger.error(f"Error stopping resource monitor: {e}")
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while self._running:
            try:
                # Collect current metrics
                metrics = await self._collect_metrics()
                
                # Store metrics
                self._store_metrics(metrics)
                
                # Analyze resource status
                status = self._analyze_resource_status(metrics)
                
                # Handle status changes
                if status != self._current_status:
                    await self._handle_status_change(status, metrics)
                
                # Check for alerts
                await self._check_alerts(status, metrics)
                
                # Wait before next check
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in resource monitoring loop: {e}")
                await asyncio.sleep(30)
    
    async def _collect_metrics(self) -> ResourceMetrics:
        """Collect current system resource metrics."""
        try:
            # Get process info
            process = psutil.Process()
            
            # Memory usage
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            
            # System memory
            system_memory = psutil.virtual_memory()
            memory_percent = system_memory.percent
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Disk usage
            disk_usage = psutil.disk_usage('/')
            disk_percent = (disk_usage.used / disk_usage.total) * 100
            
            # Network connections
            try:
                connections = psutil.net_connections()
                network_connections = len(connections)
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                network_connections = 0
            
            # Process count
            try:
                process_count = len(psutil.pids())
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                process_count = 0
            
            return ResourceMetrics(
                timestamp=datetime.utcnow(),
                memory_mb=memory_mb,
                memory_percent=memory_percent,
                cpu_percent=cpu_percent,
                disk_percent=disk_percent,
                network_connections=network_connections,
                process_count=process_count
            )
            
        except Exception as e:
            logger.error(f"Error collecting resource metrics: {e}")
            # Return default metrics on error
            return ResourceMetrics(
                timestamp=datetime.utcnow(),
                memory_mb=0.0,
                memory_percent=0.0,
                cpu_percent=0.0,
                disk_percent=0.0,
                network_connections=0,
                process_count=0
            )
    
    def _store_metrics(self, metrics: ResourceMetrics) -> None:
        """Store metrics in history."""
        self._metrics_history.append(metrics)
        
        # Limit history size
        if len(self._metrics_history) > self._max_history_size:
            self._metrics_history = self._metrics_history[-self._max_history_size:]
    
    def _analyze_resource_status(self, metrics: ResourceMetrics) -> ResourceStatus:
        """Analyze current resource status based on metrics."""
        # Check memory status
        if metrics.memory_mb >= self.limits.memory_emergency_mb:
            return ResourceStatus.EMERGENCY
        elif metrics.memory_mb >= self.limits.memory_critical_mb:
            return ResourceStatus.CRITICAL
        elif metrics.memory_mb >= self.limits.memory_warning_mb:
            return ResourceStatus.WARNING
        
        # Check CPU status
        if metrics.cpu_percent >= self.limits.cpu_emergency_percent:
            return ResourceStatus.EMERGENCY
        elif metrics.cpu_percent >= self.limits.cpu_critical_percent:
            return ResourceStatus.CRITICAL
        elif metrics.cpu_percent >= self.limits.cpu_warning_percent:
            return ResourceStatus.WARNING
        
        # Check disk status
        if metrics.disk_percent >= self.limits.disk_emergency_percent:
            return ResourceStatus.EMERGENCY
        elif metrics.disk_percent >= self.limits.disk_critical_percent:
            return ResourceStatus.CRITICAL
        elif metrics.disk_percent >= self.limits.disk_warning_percent:
            return ResourceStatus.WARNING
        
        # Check network connections
        if metrics.network_connections >= self.limits.network_connections_emergency:
            return ResourceStatus.EMERGENCY
        elif metrics.network_connections >= self.limits.network_connections_critical:
            return ResourceStatus.CRITICAL
        elif metrics.network_connections >= self.limits.network_connections_warning:
            return ResourceStatus.WARNING
        
        return ResourceStatus.NORMAL
    
    async def _handle_status_change(self, new_status: ResourceStatus, metrics: ResourceMetrics) -> None:
        """Handle resource status changes."""
        old_status = self._current_status
        self._current_status = new_status
        
        # Log status change
        self.logging_service.log_structured(
            LogLevel.WARNING if new_status != ResourceStatus.NORMAL else LogLevel.INFO,
            LogCategory.SYSTEM,
            "resource_status_change",
            f"Resource status changed from {old_status.value} to {new_status.value}",
            {
                'old_status': old_status.value,
                'new_status': new_status.value,
                'metrics': metrics.to_dict(),
                'change_time': datetime.utcnow().isoformat()
            }
        )
        
        # Trigger callbacks
        for callback in self._alert_callbacks:
            try:
                callback(new_status, metrics)
            except Exception as e:
                logger.error(f"Error in resource alert callback: {e}")
    
    async def _check_alerts(self, status: ResourceStatus, metrics: ResourceMetrics) -> None:
        """Check if alerts should be sent."""
        # Only alert on warning or higher
        if status == ResourceStatus.NORMAL:
            return
        
        # Check cooldown
        if self._last_alert_time:
            time_since_last = (datetime.utcnow() - self._last_alert_time).total_seconds()
            if time_since_last < self._alert_cooldown_seconds:
                return
        
        # Send alert
        await self._send_alert(status, metrics)
        self._last_alert_time = datetime.utcnow()
    
    async def _send_alert(self, status: ResourceStatus, metrics: ResourceMetrics) -> None:
        """Send resource usage alert."""
        alert_level = LogLevel.WARNING
        if status == ResourceStatus.CRITICAL:
            alert_level = LogLevel.ERROR
        elif status == ResourceStatus.EMERGENCY:
            alert_level = LogLevel.CRITICAL
        
        self.logging_service.log_structured(
            alert_level,
            LogCategory.SYSTEM,
            "resource_alert",
            f"Resource usage alert: {status.value}",
            {
                'status': status.value,
                'metrics': metrics.to_dict(),
                'limits': {
                    'memory_warning_mb': self.limits.memory_warning_mb,
                    'memory_critical_mb': self.limits.memory_critical_mb,
                    'cpu_warning_percent': self.limits.cpu_warning_percent,
                    'cpu_critical_percent': self.limits.cpu_critical_percent
                },
                'alert_time': datetime.utcnow().isoformat()
            }
        )
    
    def add_alert_callback(self, callback: Callable[[ResourceStatus, ResourceMetrics], None]) -> None:
        """Add callback for resource alerts."""
        self._alert_callbacks.append(callback)
    
    def remove_alert_callback(self, callback: Callable[[ResourceStatus, ResourceMetrics], None]) -> None:
        """Remove alert callback."""
        if callback in self._alert_callbacks:
            self._alert_callbacks.remove(callback)
    
    def get_current_metrics(self) -> Optional[ResourceMetrics]:
        """Get the most recent resource metrics."""
        if self._metrics_history:
            return self._metrics_history[-1]
        return None
    
    def get_metrics_history(self, minutes: int = 60) -> List[ResourceMetrics]:
        """Get resource metrics history for the specified time period."""
        if not self._metrics_history:
            return []
        
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        return [
            metrics for metrics in self._metrics_history
            if metrics.timestamp > cutoff_time
        ]
    
    def get_resource_status(self) -> Dict[str, Any]:
        """Get current resource monitoring status."""
        current_metrics = self.get_current_metrics()
        
        return {
            'running': self._running,
            'current_status': self._current_status.value,
            'last_alert_time': self._last_alert_time.isoformat() if self._last_alert_time else None,
            'metrics_count': len(self._metrics_history),
            'current_metrics': current_metrics.to_dict() if current_metrics else None,
            'limits': {
                'memory_warning_mb': self.limits.memory_warning_mb,
                'memory_critical_mb': self.limits.memory_critical_mb,
                'memory_emergency_mb': self.limits.memory_emergency_mb,
                'cpu_warning_percent': self.limits.cpu_warning_percent,
                'cpu_critical_percent': self.limits.cpu_critical_percent,
                'cpu_emergency_percent': self.limits.cpu_emergency_percent
            }
        }
    
    async def perform_resource_cleanup(self) -> bool:
        """Perform resource cleanup to free memory and reduce usage."""
        try:
            logger.info("Performing resource cleanup")
            
            # Force garbage collection
            import gc
            collected = gc.collect()
            
            # Clear old metrics history (keep only last 50)
            if len(self._metrics_history) > 50:
                self._metrics_history = self._metrics_history[-50:]
            
            # Log cleanup results
            self.logging_service.log_structured(
                LogLevel.INFO,
                LogCategory.SYSTEM,
                "resource_cleanup",
                "Resource cleanup completed",
                {
                    'garbage_collected': collected,
                    'metrics_history_size': len(self._metrics_history),
                    'cleanup_time': datetime.utcnow().isoformat()
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error during resource cleanup: {e}")
            return False
    
    def is_within_hosting_limits(self) -> bool:
        """Check if current resource usage is within free hosting limits."""
        current_metrics = self.get_current_metrics()
        if not current_metrics:
            return True
        
        # Check against emergency thresholds (should never exceed these on free hosting)
        if (current_metrics.memory_mb >= self.limits.memory_emergency_mb or
            current_metrics.cpu_percent >= self.limits.cpu_emergency_percent or
            current_metrics.disk_percent >= self.limits.disk_emergency_percent):
            return False
        
        return True


# Global resource monitor instance
_resource_monitor = None

def get_resource_monitor() -> ResourceMonitor:
    """Get the global resource monitor instance."""
    global _resource_monitor
    if _resource_monitor is None:
        _resource_monitor = ResourceMonitor()
    return _resource_monitor

async def setup_resource_monitoring() -> ResourceMonitor:
    """Set up and start resource monitoring."""
    global _resource_monitor
    _resource_monitor = ResourceMonitor()
    await _resource_monitor.start()
    return _resource_monitor