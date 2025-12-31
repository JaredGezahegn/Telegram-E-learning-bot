"""System resilience and error recovery service."""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, List, Tuple
from enum import Enum
from dataclasses import dataclass
import psutil
from contextlib import asynccontextmanager

from src.config import get_config
from .logging_service import get_logging_service, LogLevel, LogCategory
from .monitoring_service import get_monitoring_service


logger = logging.getLogger(__name__)


class SystemMode(Enum):
    """System operation modes for graceful degradation."""
    NORMAL = "normal"
    DEGRADED = "degraded"
    MINIMAL = "minimal"
    EMERGENCY = "emergency"


class ErrorSeverity(Enum):
    """Error severity levels for recovery decisions."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ResourceThresholds:
    """Resource usage thresholds for different system modes."""
    # CPU thresholds (percentage)
    cpu_normal_max: float = 70.0
    cpu_degraded_max: float = 85.0
    cpu_minimal_max: float = 95.0
    
    # Memory thresholds (percentage)
    memory_normal_max: float = 75.0
    memory_degraded_max: float = 85.0
    memory_minimal_max: float = 95.0
    
    # Disk thresholds (percentage)
    disk_normal_max: float = 80.0
    disk_degraded_max: float = 90.0
    disk_minimal_max: float = 95.0
    
    # Network error thresholds
    network_error_threshold: int = 3
    consecutive_failure_threshold: int = 5


@dataclass
class RecoveryAction:
    """Represents a recovery action to be taken."""
    name: str
    action: Callable
    severity: ErrorSeverity
    cooldown_seconds: int = 300  # 5 minutes default cooldown
    max_attempts: int = 3
    description: str = ""


class ResilienceService:
    """Comprehensive system resilience and error recovery service."""
    
    def __init__(self):
        """Initialize resilience service."""
        self.config = get_config()
        self.logging_service = get_logging_service()
        self.monitoring_service = get_monitoring_service()
        
        # System state
        self.current_mode = SystemMode.NORMAL
        self.mode_change_time = datetime.utcnow()
        self.consecutive_failures = 0
        self.last_network_error = None
        self.network_error_count = 0
        
        # Resource thresholds
        self.thresholds = ResourceThresholds()
        
        # Recovery actions registry
        self.recovery_actions: Dict[str, RecoveryAction] = {}
        self.action_history: Dict[str, List[datetime]] = {}
        
        # Circuit breaker state
        self.circuit_breakers: Dict[str, Dict[str, Any]] = {}
        
        # Background tasks
        self._monitoring_tasks: List[asyncio.Task] = []
        self._running = False
        
        # Register default recovery actions
        self._register_default_recovery_actions()
    
    async def start(self) -> bool:
        """Start resilience service."""
        try:
            if self._running:
                logger.warning("Resilience service is already running")
                return True
            
            logger.info("Starting resilience service")
            
            # Start monitoring tasks
            self._monitoring_tasks = [
                asyncio.create_task(self._resource_monitoring_loop()),
                asyncio.create_task(self._recovery_monitoring_loop()),
                asyncio.create_task(self._circuit_breaker_monitoring_loop())
            ]
            
            self._running = True
            
            # Log startup
            self.logging_service.log_structured(
                LogLevel.INFO,
                LogCategory.SYSTEM,
                "resilience_service",
                "Resilience service started",
                {
                    'current_mode': self.current_mode.value,
                    'thresholds': {
                        'cpu_normal_max': self.thresholds.cpu_normal_max,
                        'memory_normal_max': self.thresholds.memory_normal_max,
                        'disk_normal_max': self.thresholds.disk_normal_max
                    }
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start resilience service: {e}")
            self.logging_service.log_error_with_context(
                e, {'operation': 'start_resilience'}, 'resilience_service'
            )
            return False
    
    async def stop(self) -> None:
        """Stop resilience service."""
        try:
            if not self._running:
                logger.warning("Resilience service is not running")
                return
            
            logger.info("Stopping resilience service")
            
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
                LogCategory.SYSTEM,
                "resilience_service",
                "Resilience service stopped",
                {
                    'final_mode': self.current_mode.value,
                    'uptime_minutes': (datetime.utcnow() - self.mode_change_time).total_seconds() / 60
                }
            )
            
        except Exception as e:
            logger.error(f"Error stopping resilience service: {e}")
    
    async def _resource_monitoring_loop(self) -> None:
        """Monitor system resources and adjust operation mode."""
        while self._running:
            try:
                await self._check_resource_constraints()
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in resource monitoring: {e}")
                await asyncio.sleep(30)
    
    async def _recovery_monitoring_loop(self) -> None:
        """Monitor for recovery opportunities and execute actions."""
        while self._running:
            try:
                await self._check_recovery_opportunities()
                await asyncio.sleep(60)  # Check every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in recovery monitoring: {e}")
                await asyncio.sleep(60)
    
    async def _circuit_breaker_monitoring_loop(self) -> None:
        """Monitor circuit breakers and reset when appropriate."""
        while self._running:
            try:
                await self._update_circuit_breakers()
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in circuit breaker monitoring: {e}")
                await asyncio.sleep(30)
    
    async def _check_resource_constraints(self) -> None:
        """Check system resources and adjust operation mode if needed."""
        try:
            # Get current resource usage
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_percent = psutil.virtual_memory().percent
            disk_percent = psutil.disk_usage('/').used / psutil.disk_usage('/').total * 100
            
            # Determine appropriate system mode based on resource usage
            new_mode = self._determine_system_mode(cpu_percent, memory_percent, disk_percent)
            
            # Change mode if needed
            if new_mode != self.current_mode:
                await self._change_system_mode(new_mode, {
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory_percent,
                    'disk_percent': disk_percent,
                    'trigger': 'resource_constraint'
                })
            
        except Exception as e:
            logger.error(f"Error checking resource constraints: {e}")
    
    def _determine_system_mode(self, cpu_percent: float, memory_percent: float, 
                              disk_percent: float) -> SystemMode:
        """Determine appropriate system mode based on resource usage."""
        # Check for emergency conditions (any resource above minimal threshold)
        if (cpu_percent > self.thresholds.cpu_minimal_max or 
            memory_percent > self.thresholds.memory_minimal_max or 
            disk_percent > self.thresholds.disk_minimal_max):
            return SystemMode.EMERGENCY
        
        # Check for minimal mode conditions
        if (cpu_percent > self.thresholds.cpu_degraded_max or 
            memory_percent > self.thresholds.memory_degraded_max or 
            disk_percent > self.thresholds.disk_degraded_max):
            return SystemMode.MINIMAL
        
        # Check for degraded mode conditions
        if (cpu_percent > self.thresholds.cpu_normal_max or 
            memory_percent > self.thresholds.memory_normal_max or 
            disk_percent > self.thresholds.disk_normal_max):
            return SystemMode.DEGRADED
        
        # Normal operation
        return SystemMode.NORMAL
    
    async def _change_system_mode(self, new_mode: SystemMode, context: Dict[str, Any]) -> None:
        """Change system operation mode and apply appropriate measures."""
        old_mode = self.current_mode
        self.current_mode = new_mode
        self.mode_change_time = datetime.utcnow()
        
        # Log mode change
        self.logging_service.log_structured(
            LogLevel.WARNING if new_mode != SystemMode.NORMAL else LogLevel.INFO,
            LogCategory.SYSTEM,
            "mode_change",
            f"System mode changed from {old_mode.value} to {new_mode.value}",
            {
                'old_mode': old_mode.value,
                'new_mode': new_mode.value,
                'context': context,
                'change_time': self.mode_change_time.isoformat()
            }
        )
        
        # Apply mode-specific measures
        await self._apply_mode_measures(new_mode, context)
    
    async def _apply_mode_measures(self, mode: SystemMode, context: Dict[str, Any]) -> None:
        """Apply measures appropriate for the given system mode."""
        try:
            if mode == SystemMode.DEGRADED:
                await self._apply_degraded_measures(context)
            elif mode == SystemMode.MINIMAL:
                await self._apply_minimal_measures(context)
            elif mode == SystemMode.EMERGENCY:
                await self._apply_emergency_measures(context)
            elif mode == SystemMode.NORMAL:
                await self._apply_normal_measures(context)
                
        except Exception as e:
            logger.error(f"Error applying mode measures for {mode.value}: {e}")
    
    async def _apply_degraded_measures(self, context: Dict[str, Any]) -> None:
        """Apply measures for degraded operation mode."""
        measures = [
            "Reduce monitoring frequency",
            "Disable non-essential logging",
            "Increase retry delays",
            "Reduce concurrent operations"
        ]
        
        self.logging_service.log_structured(
            LogLevel.WARNING,
            LogCategory.SYSTEM,
            "degraded_mode",
            "Applying degraded operation measures",
            {'measures': measures, 'context': context}
        )
        
        # Trigger resource cleanup recovery action
        await self._execute_recovery_action("cleanup_resources", context)
    
    async def _apply_minimal_measures(self, context: Dict[str, Any]) -> None:
        """Apply measures for minimal operation mode."""
        measures = [
            "Disable all non-critical features",
            "Minimal logging only",
            "Extended retry delays",
            "Single-threaded operation"
        ]
        
        self.logging_service.log_structured(
            LogLevel.ERROR,
            LogCategory.SYSTEM,
            "minimal_mode",
            "Applying minimal operation measures",
            {'measures': measures, 'context': context}
        )
        
        # Trigger aggressive cleanup
        await self._execute_recovery_action("aggressive_cleanup", context)
    
    async def _apply_emergency_measures(self, context: Dict[str, Any]) -> None:
        """Apply measures for emergency operation mode."""
        measures = [
            "Emergency resource cleanup",
            "Suspend all non-essential operations",
            "Critical error logging only",
            "Prepare for graceful shutdown"
        ]
        
        self.logging_service.log_structured(
            LogLevel.CRITICAL,
            LogCategory.SYSTEM,
            "emergency_mode",
            "Applying emergency operation measures",
            {'measures': measures, 'context': context}
        )
        
        # Trigger emergency cleanup
        await self._execute_recovery_action("emergency_cleanup", context)
    
    async def _apply_normal_measures(self, context: Dict[str, Any]) -> None:
        """Apply measures for normal operation mode."""
        self.logging_service.log_structured(
            LogLevel.INFO,
            LogCategory.SYSTEM,
            "normal_mode",
            "Restored normal operation mode",
            {'context': context}
        )
        
        # Reset error counters
        self.consecutive_failures = 0
        self.network_error_count = 0
    
    async def handle_network_error(self, error: Exception, operation: str, 
                                 context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Handle network errors with automatic reconnection logic.
        
        Args:
            error: The network error that occurred
            operation: Description of the operation that failed
            context: Additional context about the error
            
        Returns:
            True if recovery was attempted, False if giving up
        """
        self.network_error_count += 1
        self.last_network_error = datetime.utcnow()
        
        # Log the network error
        self.logging_service.log_structured(
            LogLevel.WARNING,
            LogCategory.NETWORK,
            "network_error",
            f"Network error in {operation}",
            {
                'error': str(error),
                'error_type': type(error).__name__,
                'operation': operation,
                'error_count': self.network_error_count,
                'context': context or {}
            }
        )
        
        # Check if we should attempt recovery
        if self.network_error_count >= self.thresholds.network_error_threshold:
            # Trigger network recovery
            recovery_context = {
                'error': str(error),
                'operation': operation,
                'error_count': self.network_error_count,
                'original_context': context
            }
            
            return await self._execute_recovery_action("network_reconnection", recovery_context)
        
        return True  # Continue with normal retry logic
    
    async def handle_operation_failure(self, operation: str, error: Exception,
                                     severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                                     context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Handle general operation failures with appropriate recovery.
        
        Args:
            operation: Name of the failed operation
            error: The error that occurred
            severity: Severity level of the error
            context: Additional context
            
        Returns:
            True if recovery was attempted, False if giving up
        """
        self.consecutive_failures += 1
        
        # Log the operation failure
        self.logging_service.log_structured(
            LogLevel.ERROR if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL] else LogLevel.WARNING,
            LogCategory.SYSTEM,
            "operation_failure",
            f"Operation {operation} failed",
            {
                'operation': operation,
                'error': str(error),
                'error_type': type(error).__name__,
                'severity': severity.value,
                'consecutive_failures': self.consecutive_failures,
                'context': context or {}
            }
        )
        
        # Check if we need to trigger recovery based on consecutive failures
        if self.consecutive_failures >= self.thresholds.consecutive_failure_threshold:
            recovery_context = {
                'operation': operation,
                'error': str(error),
                'severity': severity.value,
                'consecutive_failures': self.consecutive_failures,
                'original_context': context
            }
            
            # Choose recovery action based on severity
            if severity == ErrorSeverity.CRITICAL:
                return await self._execute_recovery_action("emergency_recovery", recovery_context)
            elif severity == ErrorSeverity.HIGH:
                return await self._execute_recovery_action("system_restart", recovery_context)
            else:
                return await self._execute_recovery_action("service_restart", recovery_context)
        
        return True
    
    def register_recovery_action(self, action: RecoveryAction) -> None:
        """Register a custom recovery action."""
        self.recovery_actions[action.name] = action
        self.action_history[action.name] = []
        
        logger.info(f"Registered recovery action: {action.name}")
    
    async def _execute_recovery_action(self, action_name: str, 
                                     context: Dict[str, Any]) -> bool:
        """Execute a recovery action with cooldown and attempt limits."""
        if action_name not in self.recovery_actions:
            logger.error(f"Unknown recovery action: {action_name}")
            return False
        
        action = self.recovery_actions[action_name]
        now = datetime.utcnow()
        
        # Check cooldown
        if action_name in self.action_history:
            recent_attempts = [
                attempt for attempt in self.action_history[action_name]
                if (now - attempt).total_seconds() < action.cooldown_seconds
            ]
            
            if len(recent_attempts) >= action.max_attempts:
                logger.warning(f"Recovery action {action_name} is in cooldown")
                return False
        
        try:
            # Record attempt
            self.action_history[action_name].append(now)
            
            # Log recovery attempt
            self.logging_service.log_structured(
                LogLevel.INFO,
                LogCategory.RECOVERY,
                "recovery_action",
                f"Executing recovery action: {action_name}",
                {
                    'action_name': action_name,
                    'description': action.description,
                    'severity': action.severity.value,
                    'context': context
                }
            )
            
            # Execute the action
            result = await action.action(context)
            
            # Log result
            self.logging_service.log_structured(
                LogLevel.INFO if result else LogLevel.ERROR,
                LogCategory.RECOVERY,
                "recovery_result",
                f"Recovery action {action_name} {'succeeded' if result else 'failed'}",
                {
                    'action_name': action_name,
                    'success': result,
                    'context': context
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing recovery action {action_name}: {e}")
            self.logging_service.log_error_with_context(
                e, {'action_name': action_name, 'context': context}, 'recovery_action'
            )
            return False
    
    def _register_default_recovery_actions(self) -> None:
        """Register default recovery actions."""
        
        # Network reconnection action
        async def network_reconnection(context: Dict[str, Any]) -> bool:
            """Attempt to recover from network errors."""
            try:
                # Wait before attempting reconnection
                await asyncio.sleep(5)
                
                # Reset network error counter on successful recovery attempt
                self.network_error_count = max(0, self.network_error_count - 1)
                
                logger.info("Network reconnection recovery completed")
                return True
                
            except Exception as e:
                logger.error(f"Network reconnection failed: {e}")
                return False
        
        self.register_recovery_action(RecoveryAction(
            name="network_reconnection",
            action=network_reconnection,
            severity=ErrorSeverity.MEDIUM,
            cooldown_seconds=60,
            max_attempts=5,
            description="Attempt network reconnection after errors"
        ))
        
        # Resource cleanup action
        async def cleanup_resources(context: Dict[str, Any]) -> bool:
            """Clean up system resources."""
            try:
                # Force garbage collection
                import gc
                gc.collect()
                
                # Clear any cached data if applicable
                logger.info("Resource cleanup completed")
                return True
                
            except Exception as e:
                logger.error(f"Resource cleanup failed: {e}")
                return False
        
        self.register_recovery_action(RecoveryAction(
            name="cleanup_resources",
            action=cleanup_resources,
            severity=ErrorSeverity.LOW,
            cooldown_seconds=300,
            max_attempts=3,
            description="Clean up system resources to free memory"
        ))
        
        # Aggressive cleanup action
        async def aggressive_cleanup(context: Dict[str, Any]) -> bool:
            """Perform aggressive resource cleanup."""
            try:
                # Force garbage collection multiple times
                import gc
                for _ in range(3):
                    gc.collect()
                
                # Clear monitoring history to free memory
                if hasattr(self.monitoring_service, 'metrics_history'):
                    # Keep only last hour of metrics
                    cutoff = datetime.utcnow() - timedelta(hours=1)
                    self.monitoring_service.metrics_history = [
                        m for m in self.monitoring_service.metrics_history
                        if m.timestamp > cutoff
                    ]
                
                logger.info("Aggressive cleanup completed")
                return True
                
            except Exception as e:
                logger.error(f"Aggressive cleanup failed: {e}")
                return False
        
        self.register_recovery_action(RecoveryAction(
            name="aggressive_cleanup",
            action=aggressive_cleanup,
            severity=ErrorSeverity.MEDIUM,
            cooldown_seconds=600,
            max_attempts=2,
            description="Perform aggressive resource cleanup"
        ))
        
        # Emergency cleanup action
        async def emergency_cleanup(context: Dict[str, Any]) -> bool:
            """Perform emergency resource cleanup."""
            try:
                # Aggressive garbage collection
                import gc
                gc.collect()
                
                # Clear all non-essential caches and histories
                if hasattr(self.monitoring_service, 'metrics_history'):
                    self.monitoring_service.metrics_history.clear()
                
                # Reset error counters
                self.consecutive_failures = 0
                self.network_error_count = 0
                
                logger.info("Emergency cleanup completed")
                return True
                
            except Exception as e:
                logger.error(f"Emergency cleanup failed: {e}")
                return False
        
        self.register_recovery_action(RecoveryAction(
            name="emergency_cleanup",
            action=emergency_cleanup,
            severity=ErrorSeverity.HIGH,
            cooldown_seconds=1800,  # 30 minutes
            max_attempts=1,
            description="Perform emergency resource cleanup"
        ))
    
    async def _check_recovery_opportunities(self) -> None:
        """Check for opportunities to recover from degraded states."""
        try:
            # If we're in a degraded state, check if we can recover
            if self.current_mode != SystemMode.NORMAL:
                # Get current resource usage
                cpu_percent = psutil.cpu_percent(interval=1)
                memory_percent = psutil.virtual_memory().percent
                disk_percent = psutil.disk_usage('/').used / psutil.disk_usage('/').total * 100
                
                # Check if resources have improved enough to upgrade mode
                target_mode = self._determine_system_mode(cpu_percent, memory_percent, disk_percent)
                
                if target_mode.value < self.current_mode.value:  # Better mode (lower enum value)
                    await self._change_system_mode(target_mode, {
                        'cpu_percent': cpu_percent,
                        'memory_percent': memory_percent,
                        'disk_percent': disk_percent,
                        'trigger': 'recovery_opportunity'
                    })
            
        except Exception as e:
            logger.error(f"Error checking recovery opportunities: {e}")
    
    async def _update_circuit_breakers(self) -> None:
        """Update circuit breaker states."""
        try:
            current_time = datetime.utcnow()
            
            for service_name, breaker in self.circuit_breakers.items():
                if breaker['state'] == 'open':
                    # Check if we should try to close the circuit breaker
                    if (current_time - breaker['last_failure']).total_seconds() > breaker['timeout']:
                        breaker['state'] = 'half_open'
                        breaker['failure_count'] = 0
                        
                        logger.info(f"Circuit breaker for {service_name} moved to half-open state")
                        
                        self.logging_service.log_structured(
                            LogLevel.INFO,
                            LogCategory.SYSTEM,
                            "circuit_breaker",
                            f"Circuit breaker {service_name} moved to half-open",
                            {'service': service_name, 'state': 'half_open'}
                        )
            
        except Exception as e:
            logger.error(f"Error updating circuit breakers: {e}")
    
    def get_circuit_breaker_state(self, service_name: str) -> str:
        """Get the current state of a circuit breaker."""
        if service_name not in self.circuit_breakers:
            # Initialize circuit breaker
            self.circuit_breakers[service_name] = {
                'state': 'closed',
                'failure_count': 0,
                'last_failure': None,
                'timeout': 300,  # 5 minutes
                'failure_threshold': 5
            }
        
        return self.circuit_breakers[service_name]['state']
    
    def record_circuit_breaker_success(self, service_name: str) -> None:
        """Record a successful operation for a circuit breaker."""
        if service_name in self.circuit_breakers:
            breaker = self.circuit_breakers[service_name]
            
            if breaker['state'] == 'half_open':
                # Success in half-open state closes the circuit
                breaker['state'] = 'closed'
                breaker['failure_count'] = 0
                
                logger.info(f"Circuit breaker for {service_name} closed after successful operation")
            elif breaker['state'] == 'closed':
                # Reset failure count on success
                breaker['failure_count'] = 0
    
    def record_circuit_breaker_failure(self, service_name: str) -> None:
        """Record a failed operation for a circuit breaker."""
        if service_name not in self.circuit_breakers:
            self.get_circuit_breaker_state(service_name)  # Initialize
        
        breaker = self.circuit_breakers[service_name]
        breaker['failure_count'] += 1
        breaker['last_failure'] = datetime.utcnow()
        
        if breaker['failure_count'] >= breaker['failure_threshold']:
            breaker['state'] = 'open'
            
            logger.warning(f"Circuit breaker for {service_name} opened due to failures")
            
            self.logging_service.log_structured(
                LogLevel.WARNING,
                LogCategory.SYSTEM,
                "circuit_breaker",
                f"Circuit breaker {service_name} opened",
                {
                    'service': service_name,
                    'failure_count': breaker['failure_count'],
                    'state': 'open'
                }
            )
    
    @asynccontextmanager
    async def resilient_operation(self, operation_name: str, 
                                service_name: Optional[str] = None):
        """
        Context manager for resilient operations with circuit breaker support.
        
        Args:
            operation_name: Name of the operation
            service_name: Optional service name for circuit breaker
        """
        # Check circuit breaker if service specified
        if service_name:
            breaker_state = self.get_circuit_breaker_state(service_name)
            if breaker_state == 'open':
                raise RuntimeError(f"Circuit breaker for {service_name} is open")
        
        start_time = time.time()
        success = False
        
        try:
            yield
            success = True
            
            # Record success for circuit breaker
            if service_name:
                self.record_circuit_breaker_success(service_name)
            
            # Reset consecutive failures on success
            if self.consecutive_failures > 0:
                self.consecutive_failures = 0
                logger.info(f"Reset consecutive failures after successful {operation_name}")
            
        except Exception as e:
            # Record failure for circuit breaker
            if service_name:
                self.record_circuit_breaker_failure(service_name)
            
            # Handle the error through resilience system
            await self.handle_operation_failure(operation_name, e)
            raise
        
        finally:
            # Log operation metrics
            duration = time.time() - start_time
            self.logging_service.log_structured(
                LogLevel.DEBUG,
                LogCategory.PERFORMANCE,
                "operation_metrics",
                f"Operation {operation_name} completed",
                {
                    'operation': operation_name,
                    'success': success,
                    'duration_seconds': duration,
                    'service': service_name
                }
            )
    
    def get_resilience_status(self) -> Dict[str, Any]:
        """Get current resilience service status."""
        try:
            return {
                'service_running': self._running,
                'current_mode': self.current_mode.value,
                'mode_change_time': self.mode_change_time.isoformat(),
                'consecutive_failures': self.consecutive_failures,
                'network_error_count': self.network_error_count,
                'last_network_error': self.last_network_error.isoformat() if self.last_network_error else None,
                'circuit_breakers': {
                    name: {
                        'state': breaker['state'],
                        'failure_count': breaker['failure_count'],
                        'last_failure': breaker['last_failure'].isoformat() if breaker['last_failure'] else None
                    }
                    for name, breaker in self.circuit_breakers.items()
                },
                'recovery_actions': {
                    name: {
                        'description': action.description,
                        'severity': action.severity.value,
                        'recent_attempts': len([
                            attempt for attempt in self.action_history.get(name, [])
                            if (datetime.utcnow() - attempt).total_seconds() < action.cooldown_seconds
                        ])
                    }
                    for name, action in self.recovery_actions.items()
                },
                'thresholds': {
                    'cpu_normal_max': self.thresholds.cpu_normal_max,
                    'memory_normal_max': self.thresholds.memory_normal_max,
                    'disk_normal_max': self.thresholds.disk_normal_max,
                    'network_error_threshold': self.thresholds.network_error_threshold,
                    'consecutive_failure_threshold': self.thresholds.consecutive_failure_threshold
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting resilience status: {e}")
            return {
                'service_running': self._running,
                'error': str(e)
            }


# Global resilience service instance
_resilience_service = None

def get_resilience_service() -> ResilienceService:
    """Get the global resilience service instance."""
    global _resilience_service
    if _resilience_service is None:
        _resilience_service = ResilienceService()
    return _resilience_service

async def setup_resilience() -> ResilienceService:
    """Set up and start resilience service."""
    global _resilience_service
    _resilience_service = ResilienceService()
    await _resilience_service.start()
    return _resilience_service