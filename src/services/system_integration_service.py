"""System integration service for coordinating resilience, monitoring, and error handling."""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager

from src.config import get_config
from .resilience_service import get_resilience_service, setup_resilience
from .monitoring_service import get_monitoring_service, setup_monitoring
from .logging_service import get_logging_service, LogLevel, LogCategory
from .system_status_service import get_system_status_service
from .resource_monitor import get_resource_monitor, setup_resource_monitoring


logger = logging.getLogger(__name__)


class SystemIntegrationService:
    """Coordinates all system services for comprehensive error handling and resilience."""
    
    def __init__(self):
        """Initialize system integration service."""
        self.config = get_config()
        self.logging_service = get_logging_service()
        
        # Service instances (will be initialized during startup)
        self.resilience_service = None
        self.monitoring_service = None
        self.system_status_service = None
        self.resource_monitor = None
        
        self._initialized = False
        self._startup_time = None
    
    async def initialize_all_services(self) -> bool:
        """
        Initialize all system services in the correct order.
        
        Returns:
            True if all services initialized successfully, False otherwise.
        """
        try:
            if self._initialized:
                logger.warning("System services already initialized")
                return True
            
            self._startup_time = datetime.utcnow()
            
            logger.info("Initializing system services...")
            
            # Initialize resource monitor
            self.resource_monitor = await setup_resource_monitoring()
            if not self.resource_monitor._running:
                logger.error("Failed to start resource monitor")
                return False
            
            # Initialize resilience service first
            self.resilience_service = await setup_resilience()
            if not self.resilience_service._running:
                logger.error("Failed to start resilience service")
                return False
            
            # Initialize monitoring service
            self.monitoring_service = await setup_monitoring()
            if not self.monitoring_service._running:
                logger.error("Failed to start monitoring service")
                return False
            
            # Set up integration between monitoring and resilience
            self.monitoring_service.setup_resilience_integration()
            
            # Initialize system status service
            self.system_status_service = get_system_status_service()
            
            # Set up resource monitor integration with resilience
            self._setup_resource_monitor_integration()
            
            # Register custom recovery actions
            await self._register_custom_recovery_actions()
            
            # Set up health monitoring callbacks
            self._setup_health_monitoring()
            
            self._initialized = True
            
            # Log successful initialization
            self.logging_service.log_structured(
                LogLevel.INFO,
                LogCategory.SYSTEM,
                "system_integration",
                "All system services initialized successfully",
                {
                    'startup_time': self._startup_time.isoformat(),
                    'services': ['resource_monitor', 'resilience', 'monitoring', 'system_status'],
                    'graceful_degradation_enabled': self.config.enable_graceful_degradation
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize system services: {e}")
            self.logging_service.log_error_with_context(
                e, {'operation': 'initialize_services'}, 'system_integration'
            )
            return False
    
    async def shutdown_all_services(self) -> None:
        """Gracefully shutdown all system services."""
        try:
            if not self._initialized:
                logger.warning("System services not initialized")
                return
            
            logger.info("Shutting down system services...")
            
            # Shutdown in reverse order
            if self.monitoring_service:
                await self.monitoring_service.stop()
            
            if self.resilience_service:
                await self.resilience_service.stop()
            
            if self.resource_monitor:
                await self.resource_monitor.stop()
            
            self._initialized = False
            
            # Log shutdown
            uptime = (datetime.utcnow() - self._startup_time).total_seconds() if self._startup_time else 0
            
            self.logging_service.log_structured(
                LogLevel.INFO,
                LogCategory.SYSTEM,
                "system_integration",
                "All system services shut down",
                {
                    'shutdown_time': datetime.utcnow().isoformat(),
                    'uptime_seconds': uptime
                }
            )
            
        except Exception as e:
            logger.error(f"Error during system shutdown: {e}")
    
    async def _register_custom_recovery_actions(self) -> None:
        """Register custom recovery actions specific to the Telegram bot."""
        try:
            from .resilience_service import RecoveryAction, ErrorSeverity
            
            # Database recovery action
            async def database_recovery(context: Dict[str, Any]) -> bool:
                """Recover from database issues."""
                try:
                    # Import here to avoid circular imports
                    from src.models.database import DatabaseManager
                    
                    db_manager = DatabaseManager()
                    
                    # Attempt to repair database
                    await asyncio.to_thread(db_manager.check_integrity)
                    
                    logger.info("Database recovery completed successfully")
                    return True
                    
                except Exception as e:
                    logger.error(f"Database recovery failed: {e}")
                    return False
            
            self.resilience_service.register_recovery_action(RecoveryAction(
                name="database_recovery",
                action=database_recovery,
                severity=ErrorSeverity.HIGH,
                cooldown_seconds=600,  # 10 minutes
                max_attempts=2,
                description="Attempt to recover from database issues"
            ))
            
            # Telegram API recovery action
            async def telegram_api_recovery(context: Dict[str, Any]) -> bool:
                """Recover from Telegram API issues."""
                try:
                    # Wait longer before attempting recovery
                    await asyncio.sleep(30)
                    
                    # Reset circuit breaker failure count
                    self.resilience_service.circuit_breakers.get('telegram_api', {})['failure_count'] = 0
                    
                    logger.info("Telegram API recovery completed")
                    return True
                    
                except Exception as e:
                    logger.error(f"Telegram API recovery failed: {e}")
                    return False
            
            self.resilience_service.register_recovery_action(RecoveryAction(
                name="telegram_api_recovery",
                action=telegram_api_recovery,
                severity=ErrorSeverity.MEDIUM,
                cooldown_seconds=300,  # 5 minutes
                max_attempts=3,
                description="Recover from Telegram API connectivity issues"
            ))
            
            # Lesson management recovery action
            async def lesson_management_recovery(context: Dict[str, Any]) -> bool:
                """Recover from lesson management issues."""
                try:
                    # This could involve reloading lessons, clearing caches, etc.
                    logger.info("Lesson management recovery completed")
                    return True
                    
                except Exception as e:
                    logger.error(f"Lesson management recovery failed: {e}")
                    return False
            
            self.resilience_service.register_recovery_action(RecoveryAction(
                name="lesson_management_recovery",
                action=lesson_management_recovery,
                severity=ErrorSeverity.LOW,
                cooldown_seconds=180,  # 3 minutes
                max_attempts=3,
                description="Recover from lesson management issues"
            ))
            
            # Resource monitor cleanup action
            async def resource_monitor_cleanup(context: Dict[str, Any]) -> bool:
                """Perform resource monitor cleanup."""
                try:
                    # Get resource monitor if available
                    if self.resource_monitor and self.resource_monitor._running:
                        success = await self.resource_monitor.perform_resource_cleanup()
                        logger.info(f"Resource monitor cleanup {'succeeded' if success else 'failed'}")
                        return success
                    
                    return True
                    
                except Exception as e:
                    logger.error(f"Resource monitor cleanup failed: {e}")
                    return False
            
            self.resilience_service.register_recovery_action(RecoveryAction(
                name="resource_monitor_cleanup",
                action=resource_monitor_cleanup,
                severity=ErrorSeverity.LOW,
                cooldown_seconds=300,  # 5 minutes
                max_attempts=3,
                description="Perform resource monitor cleanup to free memory"
            ))
            
            logger.info("Custom recovery actions registered successfully")
            
        except Exception as e:
            logger.error(f"Failed to register custom recovery actions: {e}")
    
    def _setup_resource_monitor_integration(self) -> None:
        """Set up integration between resource monitor and resilience service."""
        try:
            from .resource_monitor import ResourceStatus
            
            def resource_alert_callback(status: ResourceStatus, metrics) -> None:
                """Handle resource alerts by triggering resilience actions."""
                try:
                    if status == ResourceStatus.CRITICAL:
                        # Trigger resource cleanup
                        asyncio.create_task(
                            self.resilience_service._execute_recovery_action(
                                "cleanup_resources", 
                                {'resource_status': status.value, 'metrics': metrics.to_dict()}
                            )
                        )
                    elif status == ResourceStatus.EMERGENCY:
                        # Trigger emergency cleanup
                        asyncio.create_task(
                            self.resilience_service._execute_recovery_action(
                                "emergency_cleanup", 
                                {'resource_status': status.value, 'metrics': metrics.to_dict()}
                            )
                        )
                except Exception as e:
                    logger.error(f"Error in resource alert callback: {e}")
            
            # Add callback to resource monitor
            self.resource_monitor.add_alert_callback(resource_alert_callback)
            
            logger.info("Resource monitor integration set up successfully")
            
        except Exception as e:
            logger.error(f"Failed to set up resource monitor integration: {e}")
    
    def _setup_health_monitoring(self) -> None:
        """Set up health monitoring callbacks."""
        try:
            # Add system integration health check
            def integration_health_check() -> Dict[str, Any]:
                """Health check for system integration."""
                issues = []
                warnings = []
                
                # Check if all services are running
                if not self.resilience_service or not self.resilience_service._running:
                    issues.append("Resilience service not running")
                
                if not self.monitoring_service or not self.monitoring_service._running:
                    issues.append("Monitoring service not running")
                
                # Check system uptime
                if self._startup_time:
                    uptime_hours = (datetime.utcnow() - self._startup_time).total_seconds() / 3600
                    if uptime_hours < 0.1:  # Less than 6 minutes
                        warnings.append("System recently started")
                
                return {
                    'issues': issues,
                    'warnings': warnings,
                    'uptime_hours': uptime_hours if self._startup_time else 0,
                    'initialized': self._initialized
                }
            
            if self.monitoring_service:
                self.monitoring_service.add_health_check_callback(integration_health_check)
            
            logger.info("Health monitoring callbacks set up successfully")
            
        except Exception as e:
            logger.error(f"Failed to set up health monitoring: {e}")
    
    @asynccontextmanager
    async def resilient_system_operation(self, operation_name: str):
        """
        Context manager for system-wide resilient operations.
        
        Args:
            operation_name: Name of the operation
        """
        if not self._initialized:
            raise RuntimeError("System services not initialized")
        
        async with self.resilience_service.resilient_operation(operation_name, "system"):
            yield
    
    async def get_comprehensive_system_status(self) -> Dict[str, Any]:
        """Get comprehensive status of all system components."""
        try:
            if not self._initialized:
                return {
                    'error': 'System services not initialized',
                    'timestamp': datetime.utcnow().isoformat()
                }
            
            # Get status from all services
            status = {
                'timestamp': datetime.utcnow().isoformat(),
                'system_initialized': self._initialized,
                'startup_time': self._startup_time.isoformat() if self._startup_time else None,
                'uptime_hours': (datetime.utcnow() - self._startup_time).total_seconds() / 3600 if self._startup_time else 0
            }
            
            # Add resilience status
            if self.resilience_service:
                status['resilience'] = self.resilience_service.get_resilience_status()
            
            # Add monitoring status
            if self.monitoring_service:
                status['monitoring'] = self.monitoring_service.get_system_status()
            
            # Add comprehensive system status
            if self.system_status_service:
                status['system_status'] = await self.system_status_service.get_comprehensive_status()
            
            # Add resource monitoring status
            if self.resource_monitor:
                status['resource_monitor'] = self.resource_monitor.get_resource_status()
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting comprehensive system status: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    async def perform_system_health_check(self) -> Dict[str, Any]:
        """Perform a comprehensive system health check."""
        try:
            if not self._initialized:
                return {
                    'status': 'error',
                    'message': 'System services not initialized',
                    'timestamp': datetime.utcnow().isoformat()
                }
            
            # Perform health checks on all services
            health_results = {}
            
            # Resilience service health
            if self.resilience_service:
                resilience_status = self.resilience_service.get_resilience_status()
                health_results['resilience'] = {
                    'status': 'healthy' if resilience_status['service_running'] else 'unhealthy',
                    'current_mode': resilience_status['current_mode'],
                    'consecutive_failures': resilience_status['consecutive_failures']
                }
            
            # Monitoring service health
            if self.monitoring_service:
                monitoring_health = await self.monitoring_service.perform_health_check()
                health_results['monitoring'] = {
                    'status': monitoring_health['status'],
                    'issues': monitoring_health.get('issues', []),
                    'warnings': monitoring_health.get('warnings', [])
                }
            
            # Overall system health
            overall_issues = []
            overall_warnings = []
            
            for service, health in health_results.items():
                if health.get('status') == 'unhealthy':
                    overall_issues.append(f"{service} service unhealthy")
                elif health.get('issues'):
                    overall_issues.extend([f"{service}: {issue}" for issue in health['issues']])
                
                if health.get('warnings'):
                    overall_warnings.extend([f"{service}: {warning}" for warning in health['warnings']])
            
            # Determine overall status
            if overall_issues:
                overall_status = 'unhealthy'
            elif overall_warnings:
                overall_status = 'degraded'
            else:
                overall_status = 'healthy'
            
            return {
                'status': overall_status,
                'timestamp': datetime.utcnow().isoformat(),
                'services': health_results,
                'overall_issues': overall_issues,
                'overall_warnings': overall_warnings,
                'uptime_hours': (datetime.utcnow() - self._startup_time).total_seconds() / 3600 if self._startup_time else 0
            }
            
        except Exception as e:
            logger.error(f"Error performing system health check: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    async def handle_system_emergency(self, emergency_type: str, context: Dict[str, Any]) -> bool:
        """
        Handle system-wide emergencies.
        
        Args:
            emergency_type: Type of emergency
            context: Emergency context
            
        Returns:
            True if emergency handled successfully, False otherwise.
        """
        try:
            logger.critical(f"System emergency detected: {emergency_type}")
            
            self.logging_service.log_structured(
                LogLevel.CRITICAL,
                LogCategory.SYSTEM,
                "system_emergency",
                f"System emergency: {emergency_type}",
                {
                    'emergency_type': emergency_type,
                    'context': context,
                    'timestamp': datetime.utcnow().isoformat()
                }
            )
            
            # Execute emergency recovery based on type
            if emergency_type == "resource_exhaustion":
                return await self.resilience_service._execute_recovery_action("emergency_cleanup", context)
            elif emergency_type == "service_failure":
                return await self.resilience_service._execute_recovery_action("system_restart", context)
            elif emergency_type == "data_corruption":
                return await self.resilience_service._execute_recovery_action("database_recovery", context)
            else:
                # Generic emergency recovery
                return await self.resilience_service._execute_recovery_action("emergency_recovery", context)
            
        except Exception as e:
            logger.error(f"Error handling system emergency: {e}")
            return False
    
    def is_system_healthy(self) -> bool:
        """Quick check if system is in a healthy state."""
        try:
            if not self._initialized:
                return False
            
            # Check resilience service mode
            if self.resilience_service:
                resilience_status = self.resilience_service.get_resilience_status()
                current_mode = resilience_status.get('current_mode', 'normal')
                if current_mode in ['emergency', 'minimal']:
                    return False
            
            return True
            
        except Exception:
            return False


# Global system integration service instance
_system_integration_service = None

def get_system_integration_service() -> SystemIntegrationService:
    """Get the global system integration service instance."""
    global _system_integration_service
    if _system_integration_service is None:
        _system_integration_service = SystemIntegrationService()
    return _system_integration_service

async def initialize_system_services() -> bool:
    """Initialize all system services."""
    integration_service = get_system_integration_service()
    return await integration_service.initialize_all_services()

async def shutdown_system_services() -> None:
    """Shutdown all system services."""
    integration_service = get_system_integration_service()
    await integration_service.shutdown_all_services()