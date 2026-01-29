"""User repository for managing user profiles and progress data."""

import logging
import requests
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from ..models.user_profile import UserProfile, UserProgress, QuizAttempt, UserSession
from ..models.admin_log import AdminActionLog, CommandUsageStats


logger = logging.getLogger(__name__)


class UserRepository:
    """Repository for user data operations using Supabase."""
    
    def __init__(self, supabase_manager):
        """Initialize user repository with Supabase manager.
        
        Args:
            supabase_manager: SupabaseManager instance for database operations
        """
        self.supabase = supabase_manager
        self.base_url = supabase_manager.base_url
        self.headers = supabase_manager.headers
    
    # User Profile Operations
    def create_user_profile(self, user_id: int, username: str = None, first_name: str = None, chat_id: int = None) -> Optional[UserProfile]:
        """Create a new user profile.
        
        Args:
            user_id: Telegram user ID
            username: Telegram username
            first_name: User's first name
            chat_id: Chat ID where user interacted
            
        Returns:
            Created UserProfile or None if failed
        """
        try:
            profile = UserProfile(
                user_id=user_id,
                username=username,
                first_name=first_name,
                chat_id=chat_id
            )
            
            response = requests.post(
                f"{self.base_url}/user_profiles",
                headers=self.headers,
                json=profile.to_dict(),
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"Created user profile for user {user_id}")
                return profile
            else:
                logger.error(f"Failed to create user profile: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating user profile for {user_id}: {e}")
            return None
    
    def get_user_profile(self, user_id: int) -> Optional[UserProfile]:
        """Get user profile by user ID.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            UserProfile or None if not found
        """
        try:
            response = requests.get(
                f"{self.base_url}/user_profiles?user_id=eq.{user_id}",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data:
                    return UserProfile.from_dict(data[0])
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting user profile for {user_id}: {e}")
            return None
    
    def update_user_profile(self, profile: UserProfile) -> bool:
        """Update user profile.
        
        Args:
            profile: UserProfile to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            update_data = profile.to_dict()
            # Remove user_id from update data as it's the primary key
            update_data.pop('user_id', None)
            
            response = requests.patch(
                f"{self.base_url}/user_profiles?user_id=eq.{profile.user_id}",
                headers=self.headers,
                json=update_data,
                timeout=10
            )
            
            success = response.status_code in [200, 204]
            if success:
                logger.info(f"Updated user profile for user {profile.user_id}")
            else:
                logger.error(f"Failed to update user profile: {response.status_code} - {response.text}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error updating user profile for {profile.user_id}: {e}")
            return False
    
    def get_or_create_user_profile(self, user_id: int, username: str = None, first_name: str = None, chat_id: int = None) -> Optional[UserProfile]:
        """Get existing user profile or create new one.
        
        Args:
            user_id: Telegram user ID
            username: Telegram username
            first_name: User's first name
            chat_id: Chat ID where user interacted
            
        Returns:
            UserProfile or None if failed
        """
        profile = self.get_user_profile(user_id)
        if profile:
            # Update activity timestamp
            profile.update_activity()
            self.update_user_profile(profile)
            return profile
        
        return self.create_user_profile(user_id, username, first_name, chat_id)
    
    # User Progress Operations
    def record_user_progress(self, progress: UserProgress) -> bool:
        """Record user progress entry.
        
        Args:
            progress: UserProgress entry to record
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = requests.post(
                f"{self.base_url}/user_progress",
                headers=self.headers,
                json=progress.to_dict(),
                timeout=10
            )
            
            success = response.status_code in [200, 201]
            if success:
                logger.info(f"Recorded progress for user {progress.user_id}: {progress.activity_type}")
            else:
                logger.error(f"Failed to record progress: {response.status_code} - {response.text}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error recording progress for user {progress.user_id}: {e}")
            return False
    
    def get_user_progress_history(self, user_id: int, limit: int = 50) -> List[UserProgress]:
        """Get user progress history.
        
        Args:
            user_id: Telegram user ID
            limit: Maximum number of entries to return
            
        Returns:
            List of UserProgress entries
        """
        try:
            response = requests.get(
                f"{self.base_url}/user_progress?user_id=eq.{user_id}&order=completion_timestamp.desc&limit={limit}",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return [UserProgress.from_dict(row) for row in data]
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting progress history for user {user_id}: {e}")
            return []
    
    # Quiz Attempt Operations
    def record_quiz_attempt(self, attempt: QuizAttempt) -> bool:
        """Record quiz attempt.
        
        Args:
            attempt: QuizAttempt to record
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = requests.post(
                f"{self.base_url}/quiz_attempts",
                headers=self.headers,
                json=attempt.to_dict(),
                timeout=10
            )
            
            success = response.status_code in [200, 201]
            if success:
                logger.info(f"Recorded quiz attempt for user {attempt.user_id}: score {attempt.score}%")
            else:
                logger.error(f"Failed to record quiz attempt: {response.status_code} - {response.text}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error recording quiz attempt for user {attempt.user_id}: {e}")
            return False
    
    def get_user_quiz_attempts(self, user_id: int, lesson_id: int = None) -> List[QuizAttempt]:
        """Get user quiz attempts.
        
        Args:
            user_id: Telegram user ID
            lesson_id: Optional lesson ID to filter by
            
        Returns:
            List of QuizAttempt entries
        """
        try:
            url = f"{self.base_url}/quiz_attempts?user_id=eq.{user_id}&order=completed_at.desc"
            if lesson_id:
                url += f"&lesson_id=eq.{lesson_id}"
            
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return [QuizAttempt.from_dict(row) for row in data]
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting quiz attempts for user {user_id}: {e}")
            return []
    
    def get_next_attempt_number(self, user_id: int, quiz_id: int) -> int:
        """Get the next attempt number for a quiz.
        
        Args:
            user_id: Telegram user ID
            quiz_id: Quiz ID
            
        Returns:
            Next attempt number
        """
        try:
            response = requests.get(
                f"{self.base_url}/quiz_attempts?user_id=eq.{user_id}&quiz_id=eq.{quiz_id}&select=attempt_number&order=attempt_number.desc&limit=1",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data:
                    return data[0]['attempt_number'] + 1
            
            return 1
            
        except Exception as e:
            logger.error(f"Error getting next attempt number: {e}")
            return 1
    
    # User Session Operations
    def create_user_session(self, session: UserSession) -> bool:
        """Create or update user session.
        
        Args:
            session: UserSession to create/update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Use upsert to handle both create and update
            response = requests.post(
                f"{self.base_url}/user_sessions",
                headers={**self.headers, 'Prefer': 'resolution=merge-duplicates'},
                json=session.to_dict(),
                timeout=10
            )
            
            success = response.status_code in [200, 201]
            if success:
                logger.info(f"Created/updated session for user {session.user_id}: {session.session_type}")
            else:
                logger.error(f"Failed to create session: {response.status_code} - {response.text}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error creating session for user {session.user_id}: {e}")
            return False
    
    def get_user_session(self, user_id: int) -> Optional[UserSession]:
        """Get active user session.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            UserSession or None if not found or expired
        """
        try:
            response = requests.get(
                f"{self.base_url}/user_sessions?user_id=eq.{user_id}&is_active=eq.true",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data:
                    session = UserSession.from_dict(data[0])
                    if not session.is_expired():
                        return session
                    else:
                        # Session expired, deactivate it
                        self.deactivate_user_session(user_id)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting session for user {user_id}: {e}")
            return None
    
    def update_user_session(self, user_id: int, session_data: Dict[str, Any]) -> bool:
        """Update user session data.
        
        Args:
            user_id: Telegram user ID
            session_data: Data to update in session
            
        Returns:
            True if successful, False otherwise
        """
        try:
            session = self.get_user_session(user_id)
            if session:
                session.update_session(session_data)
                return self.create_user_session(session)
            
            return False
            
        except Exception as e:
            logger.error(f"Error updating session for user {user_id}: {e}")
            return False
    
    def deactivate_user_session(self, user_id: int) -> bool:
        """Deactivate user session.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = requests.patch(
                f"{self.base_url}/user_sessions?user_id=eq.{user_id}",
                headers=self.headers,
                json={'is_active': False},
                timeout=10
            )
            
            return response.status_code in [200, 204]
            
        except Exception as e:
            logger.error(f"Error deactivating session for user {user_id}: {e}")
            return False
    
    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions.
        
        Returns:
            Number of sessions cleaned up
        """
        try:
            now = datetime.utcnow().isoformat()
            response = requests.patch(
                f"{self.base_url}/user_sessions?expires_at=lt.{now}&is_active=eq.true",
                headers=self.headers,
                json={'is_active': False},
                timeout=10
            )
            
            if response.status_code in [200, 204]:
                # Get count of updated sessions (this is approximate)
                logger.info("Cleaned up expired user sessions")
                return 1  # Return 1 as we don't get exact count from Supabase
            
            return 0
            
        except Exception as e:
            logger.error(f"Error cleaning up expired sessions: {e}")
            return 0
    
    # Admin and Statistics Operations
    def record_admin_action(self, log_entry: AdminActionLog) -> bool:
        """Record admin action log.
        
        Args:
            log_entry: AdminActionLog to record
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = requests.post(
                f"{self.base_url}/admin_action_logs",
                headers=self.headers,
                json=log_entry.to_dict(),
                timeout=10
            )
            
            success = response.status_code in [200, 201]
            if success:
                logger.info(f"Recorded admin action: {log_entry.action_type} by {log_entry.admin_user_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error recording admin action: {e}")
            return False
    
    def record_command_usage(self, stats: CommandUsageStats) -> bool:
        """Record command usage statistics.
        
        Args:
            stats: CommandUsageStats to record
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = requests.post(
                f"{self.base_url}/command_usage_stats",
                headers=self.headers,
                json=stats.to_dict(),
                timeout=10
            )
            
            return response.status_code in [200, 201]
            
        except Exception as e:
            logger.error(f"Error recording command usage: {e}")
            return False
    
    def get_user_statistics(self) -> Dict[str, Any]:
        """Get comprehensive user statistics.
        
        Returns:
            Dictionary with user statistics
        """
        try:
            # Get total users
            users_response = requests.get(
                f"{self.base_url}/user_profiles?select=user_id,is_active,registration_date",
                headers=self.headers,
                timeout=10
            )
            
            stats = {
                'total_users': 0,
                'active_users': 0,
                'new_users_today': 0,
                'new_users_week': 0,
                'total_lessons_completed': 0,
                'total_quizzes_taken': 0,
                'average_quiz_score': 0.0,
                'error': None
            }
            
            if users_response.status_code == 200:
                users_data = users_response.json()
                stats['total_users'] = len(users_data)
                
                now = datetime.utcnow()
                today = now.date()
                week_ago = now - timedelta(days=7)
                
                active_count = 0
                new_today = 0
                new_week = 0
                total_lessons = 0
                total_quizzes = 0
                total_score = 0.0
                
                for user in users_data:
                    if user.get('is_active'):
                        active_count += 1
                    
                    reg_date = user.get('registration_date')
                    if reg_date:
                        reg_datetime = datetime.fromisoformat(reg_date.replace('Z', '+00:00'))
                        if reg_datetime.date() == today:
                            new_today += 1
                        if reg_datetime >= week_ago:
                            new_week += 1
                    
                    total_lessons += user.get('total_lessons_completed', 0)
                    total_quizzes += user.get('total_quizzes_taken', 0)
                    total_score += user.get('average_quiz_score', 0.0)
                
                stats.update({
                    'active_users': active_count,
                    'new_users_today': new_today,
                    'new_users_week': new_week,
                    'total_lessons_completed': total_lessons,
                    'total_quizzes_taken': total_quizzes,
                    'average_quiz_score': total_score / max(1, len(users_data))
                })
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting user statistics: {e}")
            return {'error': str(e)}
    
    def get_command_usage_stats(self, days: int = 7) -> Dict[str, Any]:
        """Get command usage statistics.
        
        Args:
            days: Number of days to look back
            
        Returns:
            Dictionary with command usage statistics
        """
        try:
            cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
            
            response = requests.get(
                f"{self.base_url}/command_usage_stats?execution_time=gte.{cutoff_date}",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                command_counts = {}
                success_counts = {}
                total_commands = len(data)
                successful_commands = 0
                
                for entry in data:
                    cmd = entry['command_name']
                    command_counts[cmd] = command_counts.get(cmd, 0) + 1
                    
                    if entry.get('success', True):
                        successful_commands += 1
                        success_counts[cmd] = success_counts.get(cmd, 0) + 1
                
                return {
                    'total_commands': total_commands,
                    'successful_commands': successful_commands,
                    'success_rate': (successful_commands / max(1, total_commands)) * 100,
                    'command_counts': command_counts,
                    'success_counts': success_counts,
                    'days': days
                }
            
            return {'error': 'Failed to fetch command stats'}
            
        except Exception as e:
            logger.error(f"Error getting command usage stats: {e}")
            return {'error': str(e)}


def create_user_repository(supabase_manager) -> UserRepository:
    """Create and return a UserRepository instance.
    
    Args:
        supabase_manager: SupabaseManager instance
        
    Returns:
        UserRepository instance
    """
    return UserRepository(supabase_manager)