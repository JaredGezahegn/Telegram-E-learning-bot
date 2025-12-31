"""System status and reporting service for comprehensive monitoring."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import json
from pathlib import Path

from src.config import get_config
from .logging_service import get_logging_service, LogLevel, LogCategory
from .monitoring_service import get_monitoring_service, HealthStatus
from .posting_history_repository import PostingHistoryRepository


logger = logging.getLogger(__name__)


class SystemStatusService:
    """Comprehensive system status and reporting service."""
    
    def __init__(self):
        """Initialize system status service."""
        self.config = get_config()
        self.logging_service = get_logging_service()
        self.monitoring_service = get_monitoring_service()
        self.posting_history_repo = PostingHistoryRepository()
        
        # Status tracking
        self.service_start_time = datetime.utcnow()
        self.last_status_check = None
        
        # Component status cache
        self._component_status_cache = {}
        self._cache_expiry = timedelta(minutes=5)
        self._last_cache_update = None
    
    async def get_comprehensive_status(self, include_history: bool = True,
                                     include_metrics: bool = True) -> Dict[str, Any]:
        """
        Get comprehensive system status report.
        
        Args:
            include_history: Whether to include posting history
            include_metrics: Whether to include performance metrics
            
        Returns:
            Comprehensive status dictionary
        """
        try:
            self.last_status_check = datetime.utcnow()
            
            # Get basic system information
            status_report = {
                'timestamp': self.last_status_check.isoformat(),
                'service_uptime_hours': (self.last_status_check - self.service_start_time).total_seconds() / 3600,
                'system_info': await self._get_system_info(),
                'component_status': await self._get_component_status(),
                'overall_health': await self._assess_overall_health()
            }
            
            # Add posting history if requested
            if include_history:
                status_report['posting_history'] = self._get_posting_status()
            
            # Add performance metrics if requested
            if include_metrics:
                status_report['performance_metrics'] = self._get_performance_metrics()
            
            # Add configuration status
            status_report['configuration'] = self._get_configuration_status()
            
            # Add recent logs summary
            status_report['recent_activity'] = self._get_recent_activity_summary()
            
            # Log the status check
            self.logging_service.log_structured(
                LogLevel.INFO,
                LogCategory.MONITORING,
                "system_status",
                "Comprehensive status check completed",
                {
                    'overall_health': status_report['overall_health']['status'],
                    'components_checked': len(status_report['component_status']),
                    'include_history': include_history,
                    'include_metrics': include_metrics
                }
            )
            
            return status_report
            
        except Exception as e:
            logger.error(f"Error getting comprehensive status: {e}")
            self.logging_service.log_error_with_context(
                e, {'operation': 'get_comprehensive_status'}, 'system_status'
            )
            
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'error': str(e),
                'overall_health': {'status': 'error', 'message': 'Status check failed'}
            }
    
    async def _get_system_info(self) -> Dict[str, Any]:
        """Get basic system information."""
        try:
            import sys
            import platform
            
            return {
                'python_version': sys.version,
                'platform': platform.platform(),
                'architecture': platform.architecture(),
                'processor': platform.processor(),
                'hostname': platform.node(),
                'service_start_time': self.service_start_time.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting system info: {e}")
            return {'error': str(e)}
    
    async def _get_component_status(self) -> Dict[str, Any]:
        """Get status of all system components."""
        # Check if cache is still valid
        if (self._last_cache_update and 
            datetime.utcnow() - self._last_cache_update < self._cache_expiry):
            return self._component_status_cache
        
        try:
            component_status = {}
            
            # Check database connectivity
            component_status['database'] = await self._check_database_status()
            
            # Check logging service
            component_status['logging'] = self._check_logging_status()
            
            # Check monitoring service
            component_status['monitoring'] = self._check_monitoring_status()
            
            # Check configuration
            component_status['configuration'] = self._check_configuration_status()
            
            # Check posting history
            component_status['posting_history'] = self._check_posting_history_status()
            
            # Update cache
            self._component_status_cache = component_status
            self._last_cache_update = datetime.utcnow()
            
            return component_status
            
        except Exception as e:
            logger.error(f"Error getting component status: {e}")
            return {'error': str(e)}
    
    async def _check_database_status(self) -> Dict[str, Any]:
        """Check database connectivity and health."""
        try:
            # Test database connection
            health_metrics = self.posting_history_repo.get_health_metrics()
            
            if health_metrics.get('database_healthy', False):
                return {
                    'status': 'healthy',
                    'total_records': health_metrics.get('total_records', 0),
                    'oldest_record': health_metrics.get('oldest_record'),
                    'last_check': datetime.utcnow().isoformat()
                }
            else:
                return {
                    'status': 'unhealthy',
                    'error': health_metrics.get('error', 'Unknown database error'),
                    'last_check': datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'last_check': datetime.utcnow().isoformat()
            }
    
    def _check_logging_status(self) -> Dict[str, Any]:
        """Check logging service status."""
        try:
            log_stats = self.logging_service.get_log_statistics()
            
            return {
                'status': 'healthy',
                'total_logs': log_stats.get('total_logs', 0),
                'session_start': log_stats.get('session_start'),
                'uptime_seconds': log_stats.get('uptime_seconds', 0),
                'log_files_count': len(log_stats.get('log_files', [])),
                'last_check': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'last_check': datetime.utcnow().isoformat()
            }
    
    def _check_monitoring_status(self) -> Dict[str, Any]:
        """Check monitoring service status."""
        try:
            monitoring_status = self.monitoring_service.get_system_status()
            
            return {
                'status': 'healthy' if monitoring_status.get('service_running', False) else 'stopped',
                'service_running': monitoring_status.get('service_running', False),
                'current_health_status': monitoring_status.get('current_health_status'),
                'uptime_hours': monitoring_status.get('uptime_hours', 0),
                'metrics_count': monitoring_status.get('metrics_history_count', 0),
                'last_check': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'last_check': datetime.utcnow().isoformat()
            }
    
    def _check_configuration_status(self) -> Dict[str, Any]:
        """Check configuration validity."""
        try:
            # Validate configuration
            self.config.validate()
            
            return {
                'status': 'valid',
                'bot_token_configured': bool(self.config.bot_token),
                'channel_id_configured': bool(self.config.channel_id),
                'posting_time': self.config.posting_time,
                'timezone': self.config.timezone,
                'log_level': self.config.log_level,
                'last_check': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'invalid',
                'error': str(e),
                'last_check': datetime.utcnow().isoformat()
            }
    
    def _check_posting_history_status(self) -> Dict[str, Any]:
        """Check posting history system status."""
        try:
            # Get recent posting statistics
            stats = self.posting_history_repo.get_posting_statistics(days=7)
            
            return {
                'status': 'healthy',
                'total_attempts_7d': stats.get('total_attempts', 0),
                'success_rate_7d': stats.get('success_rate', 0.0),
                'last_post_time': stats.get('last_post_time'),
                'common_errors_count': len(stats.get('common_errors', [])),
                'last_check': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'last_check': datetime.utcnow().isoformat()
            }
    
    async def _assess_overall_health(self) -> Dict[str, Any]:
        """Assess overall system health based on component status."""
        try:
            component_status = await self._get_component_status()
            
            # Count healthy vs unhealthy components
            healthy_components = 0
            total_components = 0
            issues = []
            warnings = []
            
            for component_name, status in component_status.items():
                if isinstance(status, dict):
                    total_components += 1
                    component_health = status.get('status', 'unknown')
                    
                    if component_health in ['healthy', 'valid']:
                        healthy_components += 1
                    elif component_health in ['unhealthy', 'invalid', 'error']:
                        issues.append(f"{component_name}: {status.get('error', 'unhealthy')}")
                    elif component_health in ['degraded', 'stopped']:
                        warnings.append(f"{component_name}: {component_health}")
            
            # Determine overall health
            if issues:
                overall_status = HealthStatus.UNHEALTHY.value
                message = f"{len(issues)} critical issues detected"
            elif warnings:
                overall_status = HealthStatus.ATTENTION_NEEDED.value
                message = f"{len(warnings)} components need attention"
            elif healthy_components == total_components:
                overall_status = HealthStatus.HEALTHY.value
                message = "All systems operational"
            else:
                overall_status = HealthStatus.DEGRADED.value
                message = "Some components have unknown status"
            
            # Add monitoring service health if available
            try:
                monitoring_health = await self.monitoring_service.perform_health_check()
                if monitoring_health.get('issues'):
                    issues.extend(monitoring_health['issues'])
                if monitoring_health.get('warnings'):
                    warnings.extend(monitoring_health['warnings'])
            except Exception as e:
                warnings.append(f"Monitoring health check failed: {e}")
            
            return {
                'status': overall_status,
                'message': message,
                'healthy_components': healthy_components,
                'total_components': total_components,
                'issues': issues,
                'warnings': warnings,
                'assessment_time': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error assessing overall health: {e}")
            return {
                'status': HealthStatus.CRITICAL.value,
                'message': f"Health assessment failed: {e}",
                'issues': [str(e)],
                'warnings': [],
                'assessment_time': datetime.utcnow().isoformat()
            }
    
    def _get_posting_status(self) -> Dict[str, Any]:
        """Get posting history and statistics."""
        try:
            # Get recent posting statistics
            stats_7d = self.posting_history_repo.get_posting_statistics(days=7)
            stats_30d = self.posting_history_repo.get_posting_statistics(days=30)
            
            # Get recent posting history
            recent_history = self.posting_history_repo.get_posting_history(limit=10)
            
            return {
                'statistics_7d': stats_7d,
                'statistics_30d': stats_30d,
                'recent_attempts': [
                    {
                        'timestamp': h.posted_at.isoformat() if h.posted_at else None,
                        'lesson_id': h.lesson_id,
                        'success': h.success,
                        'retry_count': h.retry_count,
                        'error_message': h.error_message
                    }
                    for h in recent_history
                ],
                'last_updated': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting posting status: {e}")
            return {'error': str(e)}
    
    def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics summary."""
        try:
            # Get metrics from monitoring service
            metrics_summary = self.monitoring_service.get_metrics_summary(hours=24)
            current_status = self.monitoring_service.get_system_status()
            
            return {
                'current_metrics': current_status.get('current_metrics', {}),
                'average_metrics_24h': current_status.get('average_metrics_last_hour', {}),
                'metrics_summary_24h': metrics_summary,
                'last_updated': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {'error': str(e)}
    
    def _get_configuration_status(self) -> Dict[str, Any]:
        """Get configuration status and settings."""
        try:
            return {
                'bot_token_set': bool(self.config.bot_token),
                'channel_id': self.config.channel_id,
                'posting_time': self.config.posting_time,
                'timezone': self.config.timezone,
                'retry_attempts': self.config.retry_attempts,
                'retry_delay': self.config.retry_delay,
                'database_path': self.config.database_path,
                'log_level': self.config.log_level,
                'configuration_valid': True
            }
            
        except Exception as e:
            return {
                'configuration_valid': False,
                'error': str(e)
            }
    
    def _get_recent_activity_summary(self) -> Dict[str, Any]:
        """Get summary of recent system activity."""
        try:
            # Get recent logs summary
            recent_logs = self.logging_service.export_logs(
                start_date=datetime.utcnow() - timedelta(hours=1)
            )
            
            # Categorize recent logs
            log_summary = {
                'total_logs_1h': len(recent_logs),
                'errors_1h': len([log for log in recent_logs if log.get('level') == 'ERROR']),
                'warnings_1h': len([log for log in recent_logs if log.get('level') == 'WARNING']),
                'info_logs_1h': len([log for log in recent_logs if log.get('level') == 'INFO'])
            }
            
            # Get recent posting activity
            recent_posts = self.posting_history_repo.get_posting_history(
                limit=5,
                since=datetime.utcnow() - timedelta(hours=24)
            )
            
            posting_summary = {
                'posts_24h': len(recent_posts),
                'successful_posts_24h': len([p for p in recent_posts if p.success]),
                'failed_posts_24h': len([p for p in recent_posts if not p.success])
            }
            
            return {
                'log_activity': log_summary,
                'posting_activity': posting_summary,
                'last_updated': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting recent activity summary: {e}")
            return {'error': str(e)}
    
    async def generate_health_report(self, detailed: bool = True) -> Dict[str, Any]:
        """
        Generate a comprehensive health report.
        
        Args:
            detailed: Whether to include detailed metrics and history
            
        Returns:
            Health report dictionary
        """
        try:
            report = {
                'report_timestamp': datetime.utcnow().isoformat(),
                'report_type': 'detailed' if detailed else 'summary',
                'system_status': await self.get_comprehensive_status(
                    include_history=detailed,
                    include_metrics=detailed
                )
            }
            
            if detailed:
                # Add additional detailed information
                report['recommendations'] = self._generate_recommendations(
                    report['system_status']
                )
                
                report['trend_analysis'] = self._analyze_trends()
            
            # Log report generation
            self.logging_service.log_structured(
                LogLevel.INFO,
                LogCategory.MONITORING,
                "health_report",
                f"Health report generated ({'detailed' if detailed else 'summary'})",
                {
                    'overall_health': report['system_status']['overall_health']['status'],
                    'detailed': detailed
                }
            )
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating health report: {e}")
            self.logging_service.log_error_with_context(
                e, {'operation': 'generate_health_report', 'detailed': detailed}, 'health_report'
            )
            
            return {
                'report_timestamp': datetime.utcnow().isoformat(),
                'error': str(e),
                'system_status': {'overall_health': {'status': 'error'}}
            }
    
    def _generate_recommendations(self, system_status: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate recommendations based on system status."""
        recommendations = []
        
        try:
            overall_health = system_status.get('overall_health', {})
            
            # Check for critical issues
            if overall_health.get('issues'):
                recommendations.append({
                    'priority': 'high',
                    'category': 'critical_issues',
                    'message': 'Address critical system issues immediately',
                    'details': overall_health['issues']
                })
            
            # Check posting success rate
            posting_history = system_status.get('posting_history', {})
            stats_7d = posting_history.get('statistics_7d', {})
            
            if stats_7d.get('success_rate', 1.0) < 0.8:
                recommendations.append({
                    'priority': 'medium',
                    'category': 'posting_reliability',
                    'message': 'Posting success rate is below 80%',
                    'details': f"Current 7-day success rate: {stats_7d.get('success_rate', 0):.1%}"
                })
            
            # Check resource usage
            performance_metrics = system_status.get('performance_metrics', {})
            current_metrics = performance_metrics.get('current_metrics', {})
            
            if current_metrics.get('memory_percent', 0) > 85:
                recommendations.append({
                    'priority': 'medium',
                    'category': 'resource_usage',
                    'message': 'High memory usage detected',
                    'details': f"Current memory usage: {current_metrics.get('memory_percent', 0):.1f}%"
                })
            
            # Check log file sizes
            if not recommendations:
                recommendations.append({
                    'priority': 'low',
                    'category': 'maintenance',
                    'message': 'System is operating normally',
                    'details': 'Consider regular maintenance tasks like log cleanup'
                })
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            recommendations.append({
                'priority': 'high',
                'category': 'system_error',
                'message': 'Error generating recommendations',
                'details': str(e)
            })
        
        return recommendations
    
    def _analyze_trends(self) -> Dict[str, Any]:
        """Analyze system trends over time."""
        try:
            # Get posting statistics for trend analysis
            stats_7d = self.posting_history_repo.get_posting_statistics(days=7)
            stats_30d = self.posting_history_repo.get_posting_statistics(days=30)
            
            # Calculate trends
            trends = {}
            
            # Success rate trend
            success_rate_7d = stats_7d.get('success_rate', 0)
            success_rate_30d = stats_30d.get('success_rate', 0)
            
            if success_rate_30d > 0:
                success_rate_change = ((success_rate_7d - success_rate_30d) / success_rate_30d) * 100
                trends['success_rate_trend'] = {
                    'direction': 'improving' if success_rate_change > 5 else 'declining' if success_rate_change < -5 else 'stable',
                    'change_percent': success_rate_change,
                    'current_7d': success_rate_7d,
                    'baseline_30d': success_rate_30d
                }
            
            # Posting frequency trend
            attempts_7d = stats_7d.get('total_attempts', 0)
            attempts_30d = stats_30d.get('total_attempts', 0)
            
            # Calculate daily averages
            daily_avg_7d = attempts_7d / 7 if attempts_7d > 0 else 0
            daily_avg_30d = attempts_30d / 30 if attempts_30d > 0 else 0
            
            if daily_avg_30d > 0:
                frequency_change = ((daily_avg_7d - daily_avg_30d) / daily_avg_30d) * 100
                trends['posting_frequency_trend'] = {
                    'direction': 'increasing' if frequency_change > 10 else 'decreasing' if frequency_change < -10 else 'stable',
                    'change_percent': frequency_change,
                    'daily_avg_7d': daily_avg_7d,
                    'daily_avg_30d': daily_avg_30d
                }
            
            return {
                'analysis_timestamp': datetime.utcnow().isoformat(),
                'trends': trends,
                'data_quality': 'good' if attempts_30d > 10 else 'limited'
            }
            
        except Exception as e:
            logger.error(f"Error analyzing trends: {e}")
            return {
                'analysis_timestamp': datetime.utcnow().isoformat(),
                'error': str(e)
            }
    
    async def export_status_report(self, format_type: str = 'json',
                                  include_detailed: bool = True) -> str:
        """
        Export system status report in specified format.
        
        Args:
            format_type: Export format ('json' or 'text')
            include_detailed: Whether to include detailed information
            
        Returns:
            Formatted status report string
        """
        try:
            report = await self.generate_health_report(detailed=include_detailed)
            
            if format_type.lower() == 'json':
                return json.dumps(report, indent=2, default=str)
            
            elif format_type.lower() == 'text':
                return self._format_text_report(report)
            
            else:
                raise ValueError(f"Unsupported format type: {format_type}")
                
        except Exception as e:
            logger.error(f"Error exporting status report: {e}")
            return f"Error generating report: {e}"
    
    def _format_text_report(self, report: Dict[str, Any]) -> str:
        """Format report as human-readable text."""
        try:
            lines = []
            lines.append("=" * 60)
            lines.append("TELEGRAM ENGLISH BOT - SYSTEM STATUS REPORT")
            lines.append("=" * 60)
            lines.append(f"Generated: {report['report_timestamp']}")
            lines.append("")
            
            # Overall health
            system_status = report.get('system_status', {})
            overall_health = system_status.get('overall_health', {})
            
            lines.append(f"OVERALL HEALTH: {overall_health.get('status', 'unknown').upper()}")
            lines.append(f"Message: {overall_health.get('message', 'No message')}")
            lines.append("")
            
            # Component status
            component_status = system_status.get('component_status', {})
            if component_status:
                lines.append("COMPONENT STATUS:")
                for component, status in component_status.items():
                    if isinstance(status, dict):
                        component_health = status.get('status', 'unknown')
                        lines.append(f"  {component.title()}: {component_health.upper()}")
                        if status.get('error'):
                            lines.append(f"    Error: {status['error']}")
                lines.append("")
            
            # Issues and warnings
            if overall_health.get('issues'):
                lines.append("CRITICAL ISSUES:")
                for issue in overall_health['issues']:
                    lines.append(f"  - {issue}")
                lines.append("")
            
            if overall_health.get('warnings'):
                lines.append("WARNINGS:")
                for warning in overall_health['warnings']:
                    lines.append(f"  - {warning}")
                lines.append("")
            
            # Posting statistics
            posting_history = system_status.get('posting_history', {})
            stats_7d = posting_history.get('statistics_7d', {})
            
            if stats_7d:
                lines.append("POSTING STATISTICS (Last 7 days):")
                lines.append(f"  Total Attempts: {stats_7d.get('total_attempts', 0)}")
                lines.append(f"  Successful Posts: {stats_7d.get('successful_posts', 0)}")
                lines.append(f"  Success Rate: {stats_7d.get('success_rate', 0):.1%}")
                lines.append(f"  Average Retries: {stats_7d.get('average_retry_count', 0):.1f}")
                lines.append("")
            
            # Recommendations
            recommendations = report.get('recommendations', [])
            if recommendations:
                lines.append("RECOMMENDATIONS:")
                for rec in recommendations:
                    priority = rec.get('priority', 'unknown').upper()
                    message = rec.get('message', 'No message')
                    lines.append(f"  [{priority}] {message}")
                lines.append("")
            
            lines.append("=" * 60)
            
            return "\n".join(lines)
            
        except Exception as e:
            logger.error(f"Error formatting text report: {e}")
            return f"Error formatting report: {e}"


# Global system status service instance
_system_status_service = None

def get_system_status_service() -> SystemStatusService:
    """Get the global system status service instance."""
    global _system_status_service
    if _system_status_service is None:
        _system_status_service = SystemStatusService()
    return _system_status_service