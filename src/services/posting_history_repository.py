"""Repository for managing posting history and statistics."""

import sqlite3
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path

from src.models.posting_history import PostingHistory
from src.models.database import DatabaseManager
from .logging_service import get_logging_service, LogLevel, LogCategory


logger = logging.getLogger(__name__)


class PostingHistoryRepository:
    """Repository for managing lesson posting history and statistics."""
    
    def __init__(self, db_path: str = "lessons.db"):
        """
        Initialize posting history repository.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_manager = DatabaseManager(db_path)
        self.logging_service = get_logging_service()
        self._ensure_tables()
    
    def _ensure_tables(self) -> None:
        """Ensure posting history tables exist."""
        try:
            with self.db_manager.get_connection() as conn:
                # Create posting_history table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS posting_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        lesson_id INTEGER,
                        posted_at TIMESTAMP NOT NULL,
                        success BOOLEAN NOT NULL,
                        error_message TEXT,
                        retry_count INTEGER DEFAULT 0,
                        message_id INTEGER,
                        correlation_id TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (lesson_id) REFERENCES lessons (id)
                    )
                """)
                
                # Create indexes for better query performance
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_posting_history_posted_at 
                    ON posting_history (posted_at)
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_posting_history_success 
                    ON posting_history (success)
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_posting_history_lesson_id 
                    ON posting_history (lesson_id)
                """)
                
                conn.commit()
                
                self.logging_service.log_database_operation(
                    "create_posting_history_tables", True,
                    {"tables": ["posting_history"], "indexes": 3}
                )
                
        except Exception as e:
            logger.error(f"Error creating posting history tables: {e}")
            self.logging_service.log_database_operation(
                "create_posting_history_tables", False, error=str(e)
            )
            raise
    
    def record_posting_attempt(self, history: PostingHistory) -> Optional[int]:
        """
        Record a posting attempt in the database.
        
        Args:
            history: PostingHistory object to record
            
        Returns:
            ID of the created record or None if failed
        """
        try:
            # Validate the posting history
            history.validate()
            
            with self.db_manager.get_connection() as conn:
                cursor = conn.execute("""
                    INSERT INTO posting_history 
                    (lesson_id, posted_at, success, error_message, retry_count, message_id, correlation_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    history.lesson_id,
                    history.posted_at,
                    history.success,
                    history.error_message,
                    history.retry_count,
                    getattr(history, 'message_id', None),
                    getattr(history, 'correlation_id', None)
                ))
                
                history_id = cursor.lastrowid
                conn.commit()
                
                self.logging_service.log_posting_attempt(
                    history.lesson_id,
                    history.success,
                    history.error_message,
                    history.retry_count,
                    getattr(history, 'message_id', None),
                    getattr(history, 'correlation_id', None)
                )
                
                self.logging_service.log_database_operation(
                    "record_posting_attempt", True,
                    {
                        "history_id": history_id,
                        "lesson_id": history.lesson_id,
                        "success": history.success
                    }
                )
                
                return history_id
                
        except Exception as e:
            logger.error(f"Error recording posting attempt: {e}")
            self.logging_service.log_database_operation(
                "record_posting_attempt", False,
                {"lesson_id": history.lesson_id if history else None},
                str(e)
            )
            return None
    
    def get_posting_history(self, limit: int = 100, 
                           success_only: Optional[bool] = None,
                           since: Optional[datetime] = None) -> List[PostingHistory]:
        """
        Get posting history records.
        
        Args:
            limit: Maximum number of records to return
            success_only: Filter by success status (None for all)
            since: Only return records after this datetime
            
        Returns:
            List of PostingHistory objects
        """
        try:
            query = "SELECT * FROM posting_history WHERE 1=1"
            params = []
            
            if success_only is not None:
                query += " AND success = ?"
                params.append(success_only)
            
            if since:
                query += " AND posted_at >= ?"
                params.append(since)
            
            query += " ORDER BY posted_at DESC LIMIT ?"
            params.append(limit)
            
            with self.db_manager.get_connection() as conn:
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()
                
                histories = []
                for row in rows:
                    history = PostingHistory(
                        id=row[0],
                        lesson_id=row[1],
                        posted_at=datetime.fromisoformat(row[2]) if row[2] else None,
                        success=bool(row[3]),
                        error_message=row[4],
                        retry_count=row[5] or 0
                    )
                    
                    # Add additional fields if they exist
                    if len(row) > 6:
                        history.message_id = row[6]
                    if len(row) > 7:
                        history.correlation_id = row[7]
                    
                    histories.append(history)
                
                self.logging_service.log_database_operation(
                    "get_posting_history", True,
                    {
                        "returned_count": len(histories),
                        "limit": limit,
                        "success_filter": success_only,
                        "since": since.isoformat() if since else None
                    }
                )
                
                return histories
                
        except Exception as e:
            logger.error(f"Error getting posting history: {e}")
            self.logging_service.log_database_operation(
                "get_posting_history", False, error=str(e)
            )
            return []
    
    def get_posting_statistics(self, days: int = 30) -> Dict[str, Any]:
        """
        Get comprehensive posting statistics.
        
        Args:
            days: Number of days to include in statistics
            
        Returns:
            Dictionary with posting statistics
        """
        try:
            since_date = datetime.utcnow() - timedelta(days=days)
            
            with self.db_manager.get_connection() as conn:
                # Get overall statistics
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as total_attempts,
                        SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_posts,
                        SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed_posts,
                        SUM(retry_count) as total_retries,
                        AVG(retry_count) as avg_retry_count,
                        MAX(posted_at) as last_post_time,
                        MIN(posted_at) as first_post_time
                    FROM posting_history 
                    WHERE posted_at >= ?
                """, (since_date,))
                
                stats_row = cursor.fetchone()
                
                # Get success rate by day
                cursor = conn.execute("""
                    SELECT 
                        DATE(posted_at) as post_date,
                        COUNT(*) as daily_attempts,
                        SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as daily_successes
                    FROM posting_history 
                    WHERE posted_at >= ?
                    GROUP BY DATE(posted_at)
                    ORDER BY post_date DESC
                """, (since_date,))
                
                daily_stats = cursor.fetchall()
                
                # Get most recent successful and failed posts
                cursor = conn.execute("""
                    SELECT posted_at, lesson_id FROM posting_history 
                    WHERE success = 1 AND posted_at >= ?
                    ORDER BY posted_at DESC LIMIT 1
                """, (since_date,))
                last_success = cursor.fetchone()
                
                cursor = conn.execute("""
                    SELECT posted_at, lesson_id, error_message FROM posting_history 
                    WHERE success = 0 AND posted_at >= ?
                    ORDER BY posted_at DESC LIMIT 1
                """, (since_date,))
                last_failure = cursor.fetchone()
                
                # Get error frequency
                cursor = conn.execute("""
                    SELECT error_message, COUNT(*) as error_count
                    FROM posting_history 
                    WHERE success = 0 AND posted_at >= ? AND error_message IS NOT NULL
                    GROUP BY error_message
                    ORDER BY error_count DESC
                    LIMIT 10
                """, (since_date,))
                error_frequency = cursor.fetchall()
                
                # Calculate derived statistics
                total_attempts = stats_row[0] or 0
                successful_posts = stats_row[1] or 0
                failed_posts = stats_row[2] or 0
                success_rate = (successful_posts / total_attempts) if total_attempts > 0 else 0.0
                
                statistics = {
                    'period_days': days,
                    'total_attempts': total_attempts,
                    'successful_posts': successful_posts,
                    'failed_posts': failed_posts,
                    'success_rate': success_rate,
                    'total_retries': stats_row[3] or 0,
                    'average_retry_count': float(stats_row[4] or 0.0),
                    'last_post_time': stats_row[5],
                    'first_post_time': stats_row[6],
                    'daily_statistics': [
                        {
                            'date': row[0],
                            'attempts': row[1],
                            'successes': row[2],
                            'success_rate': (row[2] / row[1]) if row[1] > 0 else 0.0
                        }
                        for row in daily_stats
                    ],
                    'last_successful_post': {
                        'timestamp': last_success[0],
                        'lesson_id': last_success[1]
                    } if last_success else None,
                    'last_failed_post': {
                        'timestamp': last_failure[0],
                        'lesson_id': last_failure[1],
                        'error_message': last_failure[2]
                    } if last_failure else None,
                    'common_errors': [
                        {
                            'error_message': row[0],
                            'count': row[1]
                        }
                        for row in error_frequency
                    ]
                }
                
                self.logging_service.log_database_operation(
                    "get_posting_statistics", True,
                    {
                        "period_days": days,
                        "total_attempts": total_attempts,
                        "success_rate": success_rate
                    }
                )
                
                return statistics
                
        except Exception as e:
            logger.error(f"Error getting posting statistics: {e}")
            self.logging_service.log_database_operation(
                "get_posting_statistics", False, {"period_days": days}, str(e)
            )
            return {}
    
    def get_lesson_posting_history(self, lesson_id: int) -> List[PostingHistory]:
        """
        Get posting history for a specific lesson.
        
        Args:
            lesson_id: ID of the lesson
            
        Returns:
            List of PostingHistory objects for the lesson
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT * FROM posting_history 
                    WHERE lesson_id = ?
                    ORDER BY posted_at DESC
                """, (lesson_id,))
                
                rows = cursor.fetchall()
                
                histories = []
                for row in rows:
                    history = PostingHistory(
                        id=row[0],
                        lesson_id=row[1],
                        posted_at=datetime.fromisoformat(row[2]) if row[2] else None,
                        success=bool(row[3]),
                        error_message=row[4],
                        retry_count=row[5] or 0
                    )
                    histories.append(history)
                
                self.logging_service.log_database_operation(
                    "get_lesson_posting_history", True,
                    {"lesson_id": lesson_id, "history_count": len(histories)}
                )
                
                return histories
                
        except Exception as e:
            logger.error(f"Error getting lesson posting history: {e}")
            self.logging_service.log_database_operation(
                "get_lesson_posting_history", False,
                {"lesson_id": lesson_id}, str(e)
            )
            return []
    
    def cleanup_old_history(self, days_to_keep: int = 90) -> Dict[str, Any]:
        """
        Clean up old posting history records.
        
        Args:
            days_to_keep: Number of days of history to retain
            
        Returns:
            Cleanup results
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            
            with self.db_manager.get_connection() as conn:
                # Count records to be deleted
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM posting_history 
                    WHERE posted_at < ?
                """, (cutoff_date,))
                records_to_delete = cursor.fetchone()[0]
                
                # Delete old records
                cursor = conn.execute("""
                    DELETE FROM posting_history 
                    WHERE posted_at < ?
                """, (cutoff_date,))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                result = {
                    'cutoff_date': cutoff_date.isoformat(),
                    'records_deleted': deleted_count,
                    'days_kept': days_to_keep
                }
                
                self.logging_service.log_database_operation(
                    "cleanup_old_history", True, result
                )
                
                return result
                
        except Exception as e:
            logger.error(f"Error cleaning up old history: {e}")
            self.logging_service.log_database_operation(
                "cleanup_old_history", False,
                {"days_to_keep": days_to_keep}, str(e)
            )
            return {
                'error': str(e),
                'records_deleted': 0
            }
    
    def get_health_metrics(self) -> Dict[str, Any]:
        """
        Get health metrics for the posting history system.
        
        Returns:
            Health metrics dictionary
        """
        try:
            with self.db_manager.get_connection() as conn:
                # Get recent posting activity (last 24 hours)
                since_24h = datetime.utcnow() - timedelta(hours=24)
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as total_24h,
                        SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_24h,
                        COUNT(DISTINCT DATE(posted_at)) as active_days_24h
                    FROM posting_history 
                    WHERE posted_at >= ?
                """, (since_24h,))
                
                recent_stats = cursor.fetchone()
                
                # Get total record count
                cursor = conn.execute("SELECT COUNT(*) FROM posting_history")
                total_records = cursor.fetchone()[0]
                
                # Get oldest record
                cursor = conn.execute("""
                    SELECT MIN(posted_at) FROM posting_history
                """)
                oldest_record = cursor.fetchone()[0]
                
                # Calculate success rate for last 24 hours
                total_24h = recent_stats[0] or 0
                success_24h = recent_stats[1] or 0
                success_rate_24h = (success_24h / total_24h) if total_24h > 0 else 1.0
                
                metrics = {
                    'total_records': total_records,
                    'oldest_record': oldest_record,
                    'last_24h_attempts': total_24h,
                    'last_24h_successes': success_24h,
                    'last_24h_success_rate': success_rate_24h,
                    'active_days_24h': recent_stats[2] or 0,
                    'database_healthy': True
                }
                
                return metrics
                
        except Exception as e:
            logger.error(f"Error getting health metrics: {e}")
            return {
                'database_healthy': False,
                'error': str(e)
            }
    
    def export_history(self, start_date: Optional[datetime] = None,
                      end_date: Optional[datetime] = None,
                      format_type: str = 'json') -> List[Dict[str, Any]]:
        """
        Export posting history data.
        
        Args:
            start_date: Start date for export
            end_date: End date for export
            format_type: Export format ('json' or 'csv')
            
        Returns:
            List of history records as dictionaries
        """
        try:
            query = "SELECT * FROM posting_history WHERE 1=1"
            params = []
            
            if start_date:
                query += " AND posted_at >= ?"
                params.append(start_date)
            
            if end_date:
                query += " AND posted_at <= ?"
                params.append(end_date)
            
            query += " ORDER BY posted_at ASC"
            
            with self.db_manager.get_connection() as conn:
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()
                
                # Get column names
                column_names = [description[0] for description in cursor.description]
                
                # Convert to dictionaries
                exported_data = []
                for row in rows:
                    record = dict(zip(column_names, row))
                    exported_data.append(record)
                
                self.logging_service.log_database_operation(
                    "export_history", True,
                    {
                        "exported_count": len(exported_data),
                        "start_date": start_date.isoformat() if start_date else None,
                        "end_date": end_date.isoformat() if end_date else None,
                        "format": format_type
                    }
                )
                
                return exported_data
                
        except Exception as e:
            logger.error(f"Error exporting history: {e}")
            self.logging_service.log_database_operation(
                "export_history", False, error=str(e)
            )
            return []