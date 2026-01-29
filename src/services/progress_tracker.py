"""Progress tracking service for user learning activities."""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from ..models.user_profile import UserProfile, UserProgress, QuizAttempt
from ..models.admin_log import CommandUsageStats
from .user_repository import UserRepository


logger = logging.getLogger(__name__)


class ProgressTracker:
    """Tracks and manages user learning progress and statistics."""
    
    def __init__(self, user_repository: UserRepository):
        """Initialize progress tracker.
        
        Args:
            user_repository: UserRepository for data operations
        """
        self.user_repo = user_repository
    
    def record_lesson_completion(self, user_id: int, lesson_id: int, lesson_title: str, 
                               difficulty: str = "", category: str = "", time_spent: int = None) -> bool:
        """Record a lesson completion for a user.
        
        Args:
            user_id: Telegram user ID
            lesson_id: ID of completed lesson
            lesson_title: Title of completed lesson
            difficulty: Lesson difficulty level
            category: Lesson category/topic
            time_spent: Time spent on lesson in seconds
            
        Returns:
            True if recorded successfully, False otherwise
        """
        try:
            # Get or create user profile
            profile = self.user_repo.get_or_create_user_profile(user_id)
            if not profile:
                logger.error(f"Failed to get/create profile for user {user_id}")
                return False
            
            # Record progress entry
            progress = UserProgress(
                user_id=user_id,
                activity_type='lesson',
                content_id=lesson_id,
                content_title=lesson_title,
                difficulty_level=difficulty,
                topic_category=category,
                time_spent=time_spent
            )
            
            if not self.user_repo.record_user_progress(progress):
                logger.error(f"Failed to record progress for user {user_id}")
                return False
            
            # Update user profile
            profile.add_lesson_completion()
            self._update_learning_streak(profile, 'lesson')
            
            if category and category not in profile.preferred_topics:
                profile.add_preferred_topic(category)
            
            if not self.user_repo.update_user_profile(profile):
                logger.error(f"Failed to update profile for user {user_id}")
                return False
            
            logger.info(f"Recorded lesson completion for user {user_id}: {lesson_title}")
            return True
            
        except Exception as e:
            logger.error(f"Error recording lesson completion for user {user_id}: {e}")
            return False
    
    def record_quiz_attempt(self, user_id: int, quiz_id: int, lesson_id: int, 
                          score: float, total_questions: int, correct_answers: int,
                          time_taken: int = 0, is_practice: bool = False,
                          answers: List[Dict[str, Any]] = None) -> bool:
        """Record a quiz attempt for a user.
        
        Args:
            user_id: Telegram user ID
            quiz_id: Quiz ID
            lesson_id: Associated lesson ID
            score: Quiz score as percentage (0.0 to 100.0)
            total_questions: Total number of questions
            correct_answers: Number of correct answers
            time_taken: Time taken in seconds
            is_practice: Whether this was a practice attempt
            answers: List of answer details
            
        Returns:
            True if recorded successfully, False otherwise
        """
        try:
            # Get or create user profile
            profile = self.user_repo.get_or_create_user_profile(user_id)
            if not profile:
                logger.error(f"Failed to get/create profile for user {user_id}")
                return False
            
            # Get next attempt number
            attempt_number = self.user_repo.get_next_attempt_number(user_id, quiz_id)
            
            # Record quiz attempt
            attempt = QuizAttempt(
                user_id=user_id,
                quiz_id=quiz_id,
                lesson_id=lesson_id,
                attempt_number=attempt_number,
                score=score,
                total_questions=total_questions,
                correct_answers=correct_answers,
                time_taken=time_taken,
                is_practice_mode=is_practice,
                answers=answers or []
            )
            
            if not self.user_repo.record_quiz_attempt(attempt):
                logger.error(f"Failed to record quiz attempt for user {user_id}")
                return False
            
            # Update user profile (only for non-practice attempts)
            if not is_practice:
                profile.add_quiz_attempt(score)
                self._update_learning_streak(profile, 'quiz')
                
                if not self.user_repo.update_user_profile(profile):
                    logger.error(f"Failed to update profile for user {user_id}")
                    return False
            
            logger.info(f"Recorded quiz attempt for user {user_id}: score {score}% ({'practice' if is_practice else 'regular'})")
            return True
            
        except Exception as e:
            logger.error(f"Error recording quiz attempt for user {user_id}: {e}")
            return False
    
    def get_user_progress(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get comprehensive user progress data.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Dictionary with progress data or None if user not found
        """
        try:
            profile = self.user_repo.get_user_profile(user_id)
            if not profile:
                return None
            
            # Get recent progress history
            recent_progress = self.user_repo.get_user_progress_history(user_id, limit=10)
            
            # Get recent quiz attempts
            recent_quizzes = self.user_repo.get_user_quiz_attempts(user_id)[:5]
            
            # Calculate additional statistics
            stats = self._calculate_detailed_stats(user_id, profile, recent_progress, recent_quizzes)
            
            return {
                'profile': profile.get_progress_summary(),
                'recent_activities': [
                    {
                        'type': p.activity_type,
                        'title': p.content_title,
                        'date': p.completion_timestamp.strftime('%Y-%m-%d %H:%M') if p.completion_timestamp else '',
                        'score': p.score
                    }
                    for p in recent_progress
                ],
                'recent_quizzes': [
                    {
                        'lesson_id': q.lesson_id,
                        'score': q.score,
                        'attempt': q.attempt_number,
                        'date': q.completed_at.strftime('%Y-%m-%d %H:%M') if q.completed_at else '',
                        'is_practice': q.is_practice_mode
                    }
                    for q in recent_quizzes
                ],
                'statistics': stats
            }
            
        except Exception as e:
            logger.error(f"Error getting progress for user {user_id}: {e}")
            return None
    
    def calculate_learning_streaks(self, user_id: int) -> Dict[str, int]:
        """Calculate learning streaks for a user.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Dictionary with streak information
        """
        try:
            # Get recent progress (last 30 days)
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            progress_history = self.user_repo.get_user_progress_history(user_id, limit=100)
            
            # Filter to recent activities
            recent_activities = [
                p for p in progress_history 
                if p.completion_timestamp and p.completion_timestamp >= cutoff_date
            ]
            
            if not recent_activities:
                return {'current_streak': 0, 'longest_streak': 0, 'days_active': 0}
            
            # Group activities by date
            activity_dates = set()
            for activity in recent_activities:
                if activity.completion_timestamp:
                    activity_dates.add(activity.completion_timestamp.date())
            
            # Calculate current streak
            current_streak = 0
            check_date = datetime.utcnow().date()
            
            while check_date in activity_dates:
                current_streak += 1
                check_date -= timedelta(days=1)
            
            # Calculate longest streak
            sorted_dates = sorted(activity_dates)
            longest_streak = 0
            temp_streak = 1
            
            for i in range(1, len(sorted_dates)):
                if (sorted_dates[i] - sorted_dates[i-1]).days == 1:
                    temp_streak += 1
                else:
                    longest_streak = max(longest_streak, temp_streak)
                    temp_streak = 1
            
            longest_streak = max(longest_streak, temp_streak)
            
            return {
                'current_streak': current_streak,
                'longest_streak': longest_streak,
                'days_active': len(activity_dates)
            }
            
        except Exception as e:
            logger.error(f"Error calculating streaks for user {user_id}: {e}")
            return {'current_streak': 0, 'longest_streak': 0, 'days_active': 0}
    
    def generate_progress_report(self, user_id: int) -> Optional[str]:
        """Generate a formatted progress report for a user.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Formatted progress report string or None if user not found
        """
        try:
            progress_data = self.get_user_progress(user_id)
            if not progress_data:
                return None
            
            profile = progress_data['profile']
            stats = progress_data['statistics']
            
            report = f"""
📊 **Your Learning Progress**

👤 **Profile:**
• Lessons completed: {profile['lessons_completed']}
• Quizzes taken: {profile['quizzes_taken']}
• Average quiz score: {profile['average_score']}%
• Days learning: {profile['days_active']}

🔥 **Streaks:**
• Current streak: {profile['current_streak']} days
• Longest streak: {profile['longest_streak']} days

📈 **This Week:**
• Lessons: {stats.get('lessons_this_week', 0)}
• Quizzes: {stats.get('quizzes_this_week', 0)}
• Average score: {stats.get('avg_score_this_week', 0):.1f}%

🎯 **Favorite Topics:**
{', '.join(profile['preferred_topics']) if profile['preferred_topics'] else 'None yet'}

💪 **Keep it up!** You're doing great!
            """.strip()
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating progress report for user {user_id}: {e}")
            return None
    
    def record_command_usage(self, command_name: str, user_id: int, chat_type: str, 
                           success: bool = True, response_time_ms: int = 0, 
                           error_type: str = None) -> bool:
        """Record command usage statistics.
        
        Args:
            command_name: Name of the command used
            user_id: Telegram user ID
            chat_type: Type of chat ('private', 'group', 'channel')
            success: Whether command executed successfully
            response_time_ms: Response time in milliseconds
            error_type: Type of error if command failed
            
        Returns:
            True if recorded successfully, False otherwise
        """
        try:
            stats = CommandUsageStats(
                command_name=command_name,
                user_id=user_id,
                chat_type=chat_type,
                success=success,
                response_time_ms=response_time_ms,
                error_type=error_type
            )
            
            return self.user_repo.record_command_usage(stats)
            
        except Exception as e:
            logger.error(f"Error recording command usage: {e}")
            return False
    
    def _update_learning_streak(self, profile: UserProfile, activity_type: str) -> None:
        """Update learning streak based on activity.
        
        Args:
            profile: UserProfile to update
            activity_type: Type of activity ('lesson', 'quiz')
        """
        try:
            # Check if user was active today
            today = datetime.utcnow().date()
            last_activity_date = profile.last_activity.date() if profile.last_activity else None
            
            if last_activity_date == today:
                # Already active today, no streak change needed
                return
            elif last_activity_date == today - timedelta(days=1):
                # Active yesterday, increment streak
                profile.update_streak(increment=True)
            else:
                # Gap in activity, reset streak
                profile.update_streak(increment=False)
                # Start new streak with today's activity
                profile.update_streak(increment=True)
            
        except Exception as e:
            logger.error(f"Error updating learning streak: {e}")
    
    def _calculate_detailed_stats(self, user_id: int, profile: UserProfile, 
                                recent_progress: List[UserProgress], 
                                recent_quizzes: List[QuizAttempt]) -> Dict[str, Any]:
        """Calculate detailed statistics for user progress.
        
        Args:
            user_id: Telegram user ID
            profile: User profile
            recent_progress: Recent progress entries
            recent_quizzes: Recent quiz attempts
            
        Returns:
            Dictionary with detailed statistics
        """
        try:
            now = datetime.utcnow()
            week_ago = now - timedelta(days=7)
            
            # This week's activities
            lessons_this_week = len([
                p for p in recent_progress 
                if p.activity_type == 'lesson' and p.completion_timestamp and p.completion_timestamp >= week_ago
            ])
            
            quizzes_this_week = len([
                q for q in recent_quizzes 
                if not q.is_practice_mode and q.completed_at and q.completed_at >= week_ago
            ])
            
            # Average score this week
            week_scores = [
                q.score for q in recent_quizzes 
                if not q.is_practice_mode and q.completed_at and q.completed_at >= week_ago
            ]
            avg_score_this_week = sum(week_scores) / len(week_scores) if week_scores else 0
            
            # Improvement trend (compare last 5 quizzes to previous 5)
            all_scores = [q.score for q in recent_quizzes if not q.is_practice_mode]
            improvement_trend = 0
            if len(all_scores) >= 10:
                recent_avg = sum(all_scores[:5]) / 5
                older_avg = sum(all_scores[5:10]) / 5
                improvement_trend = recent_avg - older_avg
            
            return {
                'lessons_this_week': lessons_this_week,
                'quizzes_this_week': quizzes_this_week,
                'avg_score_this_week': avg_score_this_week,
                'improvement_trend': improvement_trend,
                'total_practice_quizzes': len([q for q in recent_quizzes if q.is_practice_mode]),
                'best_score': max([q.score for q in recent_quizzes], default=0),
                'activity_level': self._calculate_activity_level(lessons_this_week, quizzes_this_week)
            }
            
        except Exception as e:
            logger.error(f"Error calculating detailed stats: {e}")
            return {}
    
    def _calculate_activity_level(self, lessons_week: int, quizzes_week: int) -> str:
        """Calculate user activity level based on weekly activity.
        
        Args:
            lessons_week: Lessons completed this week
            quizzes_week: Quizzes taken this week
            
        Returns:
            Activity level string
        """
        total_activity = lessons_week + quizzes_week
        
        if total_activity >= 10:
            return "Very Active"
        elif total_activity >= 5:
            return "Active"
        elif total_activity >= 2:
            return "Moderate"
        elif total_activity >= 1:
            return "Light"
        else:
            return "Inactive"


def create_progress_tracker(user_repository: UserRepository) -> ProgressTracker:
    """Create and return a ProgressTracker instance.
    
    Args:
        user_repository: UserRepository instance
        
    Returns:
        ProgressTracker instance
    """
    return ProgressTracker(user_repository)