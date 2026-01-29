"""User profile model for interactive Telegram bot."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
import json


@dataclass
class UserProfile:
    """User profile for tracking learning progress and preferences."""
    
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    chat_id: Optional[int] = None
    registration_date: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    total_lessons_completed: int = 0
    total_quizzes_taken: int = 0
    average_quiz_score: float = 0.0
    current_streak: int = 0
    longest_streak: int = 0
    preferred_difficulty: Optional[str] = None
    preferred_topics: List[str] = field(default_factory=list)
    is_active: bool = True
    
    def __post_init__(self):
        """Initialize default values after creation."""
        if self.registration_date is None:
            self.registration_date = datetime.utcnow()
        if self.last_activity is None:
            self.last_activity = datetime.utcnow()
    
    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.utcnow()
    
    def add_lesson_completion(self) -> None:
        """Record a lesson completion."""
        self.total_lessons_completed += 1
        self.update_activity()
    
    def add_quiz_attempt(self, score: float) -> None:
        """Record a quiz attempt and update average score.
        
        Args:
            score: Quiz score as a percentage (0.0 to 100.0)
        """
        self.total_quizzes_taken += 1
        
        # Calculate new average score
        if self.total_quizzes_taken == 1:
            self.average_quiz_score = score
        else:
            total_score = self.average_quiz_score * (self.total_quizzes_taken - 1) + score
            self.average_quiz_score = total_score / self.total_quizzes_taken
        
        self.update_activity()
    
    def update_streak(self, increment: bool = True) -> None:
        """Update learning streak.
        
        Args:
            increment: True to increment streak, False to reset to 0
        """
        if increment:
            self.current_streak += 1
            if self.current_streak > self.longest_streak:
                self.longest_streak = self.current_streak
        else:
            self.current_streak = 0
    
    def add_preferred_topic(self, topic: str) -> None:
        """Add a topic to preferred topics list.
        
        Args:
            topic: Topic to add to preferences
        """
        if topic not in self.preferred_topics:
            self.preferred_topics.append(topic)
    
    def remove_preferred_topic(self, topic: str) -> None:
        """Remove a topic from preferred topics list.
        
        Args:
            topic: Topic to remove from preferences
        """
        if topic in self.preferred_topics:
            self.preferred_topics.remove(topic)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert user profile to dictionary for database storage.
        
        Returns:
            Dictionary representation of user profile
        """
        return {
            'user_id': self.user_id,
            'username': self.username,
            'first_name': self.first_name,
            'chat_id': self.chat_id,
            'registration_date': self.registration_date.isoformat() if self.registration_date else None,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'total_lessons_completed': self.total_lessons_completed,
            'total_quizzes_taken': self.total_quizzes_taken,
            'average_quiz_score': self.average_quiz_score,
            'current_streak': self.current_streak,
            'longest_streak': self.longest_streak,
            'preferred_difficulty': self.preferred_difficulty,
            'preferred_topics': json.dumps(self.preferred_topics),
            'is_active': self.is_active
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserProfile':
        """Create user profile from dictionary data.
        
        Args:
            data: Dictionary containing user profile data
            
        Returns:
            UserProfile instance
        """
        # Parse datetime fields
        registration_date = None
        if data.get('registration_date'):
            registration_date = datetime.fromisoformat(data['registration_date'])
        
        last_activity = None
        if data.get('last_activity'):
            last_activity = datetime.fromisoformat(data['last_activity'])
        
        # Parse preferred topics JSON
        preferred_topics = []
        if data.get('preferred_topics'):
            try:
                preferred_topics = json.loads(data['preferred_topics'])
            except (json.JSONDecodeError, TypeError):
                preferred_topics = []
        
        return cls(
            user_id=data['user_id'],
            username=data.get('username'),
            first_name=data.get('first_name'),
            chat_id=data.get('chat_id'),
            registration_date=registration_date,
            last_activity=last_activity,
            total_lessons_completed=data.get('total_lessons_completed', 0),
            total_quizzes_taken=data.get('total_quizzes_taken', 0),
            average_quiz_score=data.get('average_quiz_score', 0.0),
            current_streak=data.get('current_streak', 0),
            longest_streak=data.get('longest_streak', 0),
            preferred_difficulty=data.get('preferred_difficulty'),
            preferred_topics=preferred_topics,
            is_active=data.get('is_active', True)
        )
    
    def get_progress_summary(self) -> Dict[str, Any]:
        """Get a summary of user progress for display.
        
        Returns:
            Dictionary with progress summary
        """
        return {
            'lessons_completed': self.total_lessons_completed,
            'quizzes_taken': self.total_quizzes_taken,
            'average_score': round(self.average_quiz_score, 1),
            'current_streak': self.current_streak,
            'longest_streak': self.longest_streak,
            'days_active': (datetime.utcnow() - self.registration_date).days if self.registration_date else 0,
            'preferred_topics': self.preferred_topics[:5],  # Limit to top 5
            'is_active': self.is_active
        }


@dataclass
class UserProgress:
    """Individual user progress entry for tracking learning activities."""
    
    id: Optional[int] = None
    user_id: int = 0
    activity_type: str = ""  # 'lesson', 'quiz', 'practice'
    content_id: int = 0
    content_title: str = ""
    completion_timestamp: Optional[datetime] = None
    score: Optional[float] = None  # For quizzes
    time_spent: Optional[int] = None  # In seconds
    difficulty_level: str = ""
    topic_category: str = ""
    
    def __post_init__(self):
        """Initialize default values after creation."""
        if self.completion_timestamp is None:
            self.completion_timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert progress entry to dictionary for database storage.
        
        Returns:
            Dictionary representation of progress entry
        """
        return {
            'id': self.id,
            'user_id': self.user_id,
            'activity_type': self.activity_type,
            'content_id': self.content_id,
            'content_title': self.content_title,
            'completion_timestamp': self.completion_timestamp.isoformat() if self.completion_timestamp else None,
            'score': self.score,
            'time_spent': self.time_spent,
            'difficulty_level': self.difficulty_level,
            'topic_category': self.topic_category
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserProgress':
        """Create progress entry from dictionary data.
        
        Args:
            data: Dictionary containing progress data
            
        Returns:
            UserProgress instance
        """
        completion_timestamp = None
        if data.get('completion_timestamp'):
            completion_timestamp = datetime.fromisoformat(data['completion_timestamp'])
        
        return cls(
            id=data.get('id'),
            user_id=data['user_id'],
            activity_type=data.get('activity_type', ''),
            content_id=data.get('content_id', 0),
            content_title=data.get('content_title', ''),
            completion_timestamp=completion_timestamp,
            score=data.get('score'),
            time_spent=data.get('time_spent'),
            difficulty_level=data.get('difficulty_level', ''),
            topic_category=data.get('topic_category', '')
        )


@dataclass
class QuizAttempt:
    """Quiz attempt record for detailed quiz tracking."""
    
    id: Optional[int] = None
    user_id: int = 0
    quiz_id: int = 0
    lesson_id: int = 0
    attempt_number: int = 1
    score: float = 0.0
    total_questions: int = 0
    correct_answers: int = 0
    time_taken: int = 0  # In seconds
    is_practice_mode: bool = False
    completed_at: Optional[datetime] = None
    answers: List[Dict[str, Any]] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize default values after creation."""
        if self.completed_at is None:
            self.completed_at = datetime.utcnow()
    
    def calculate_score(self) -> float:
        """Calculate score percentage based on correct answers.
        
        Returns:
            Score as percentage (0.0 to 100.0)
        """
        if self.total_questions == 0:
            return 0.0
        return (self.correct_answers / self.total_questions) * 100.0
    
    def add_answer(self, question_id: int, user_answer: str, correct_answer: str, is_correct: bool) -> None:
        """Add an answer to the quiz attempt.
        
        Args:
            question_id: ID of the question
            user_answer: User's selected answer
            correct_answer: The correct answer
            is_correct: Whether the user's answer was correct
        """
        answer_data = {
            'question_id': question_id,
            'user_answer': user_answer,
            'correct_answer': correct_answer,
            'is_correct': is_correct,
            'timestamp': datetime.utcnow().isoformat()
        }
        self.answers.append(answer_data)
        
        if is_correct:
            self.correct_answers += 1
        
        self.total_questions = len(self.answers)
        self.score = self.calculate_score()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert quiz attempt to dictionary for database storage.
        
        Returns:
            Dictionary representation of quiz attempt
        """
        return {
            'id': self.id,
            'user_id': self.user_id,
            'quiz_id': self.quiz_id,
            'lesson_id': self.lesson_id,
            'attempt_number': self.attempt_number,
            'score': self.score,
            'total_questions': self.total_questions,
            'correct_answers': self.correct_answers,
            'time_taken': self.time_taken,
            'is_practice_mode': self.is_practice_mode,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'answers': json.dumps(self.answers)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QuizAttempt':
        """Create quiz attempt from dictionary data.
        
        Args:
            data: Dictionary containing quiz attempt data
            
        Returns:
            QuizAttempt instance
        """
        completed_at = None
        if data.get('completed_at'):
            completed_at = datetime.fromisoformat(data['completed_at'])
        
        answers = []
        if data.get('answers'):
            try:
                answers = json.loads(data['answers'])
            except (json.JSONDecodeError, TypeError):
                answers = []
        
        return cls(
            id=data.get('id'),
            user_id=data['user_id'],
            quiz_id=data.get('quiz_id', 0),
            lesson_id=data.get('lesson_id', 0),
            attempt_number=data.get('attempt_number', 1),
            score=data.get('score', 0.0),
            total_questions=data.get('total_questions', 0),
            correct_answers=data.get('correct_answers', 0),
            time_taken=data.get('time_taken', 0),
            is_practice_mode=data.get('is_practice_mode', False),
            completed_at=completed_at,
            answers=answers
        )


@dataclass
class UserSession:
    """User session for managing multi-step interactions."""
    
    user_id: int
    session_type: str  # 'quiz', 'browse', 'practice'
    session_data: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_active: bool = True
    
    def __post_init__(self):
        """Initialize default values after creation."""
        now = datetime.utcnow()
        if self.created_at is None:
            self.created_at = now
        if self.last_updated is None:
            self.last_updated = now
        if self.expires_at is None:
            # Default session timeout: 30 minutes
            from datetime import timedelta
            self.expires_at = now + timedelta(minutes=30)
    
    def update_session(self, data: Dict[str, Any]) -> None:
        """Update session data and timestamp.
        
        Args:
            data: New data to merge into session
        """
        self.session_data.update(data)
        self.last_updated = datetime.utcnow()
    
    def is_expired(self) -> bool:
        """Check if session has expired.
        
        Returns:
            True if session is expired, False otherwise
        """
        return datetime.utcnow() > self.expires_at
    
    def extend_session(self, minutes: int = 30) -> None:
        """Extend session expiration time.
        
        Args:
            minutes: Minutes to extend the session
        """
        from datetime import timedelta
        self.expires_at = datetime.utcnow() + timedelta(minutes=minutes)
        self.last_updated = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary for storage.
        
        Returns:
            Dictionary representation of session
        """
        return {
            'user_id': self.user_id,
            'session_type': self.session_type,
            'session_data': json.dumps(self.session_data),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_active': self.is_active
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserSession':
        """Create session from dictionary data.
        
        Args:
            data: Dictionary containing session data
            
        Returns:
            UserSession instance
        """
        created_at = None
        if data.get('created_at'):
            created_at = datetime.fromisoformat(data['created_at'])
        
        last_updated = None
        if data.get('last_updated'):
            last_updated = datetime.fromisoformat(data['last_updated'])
        
        expires_at = None
        if data.get('expires_at'):
            expires_at = datetime.fromisoformat(data['expires_at'])
        
        session_data = {}
        if data.get('session_data'):
            try:
                session_data = json.loads(data['session_data'])
            except (json.JSONDecodeError, TypeError):
                session_data = {}
        
        return cls(
            user_id=data['user_id'],
            session_type=data.get('session_type', ''),
            session_data=session_data,
            created_at=created_at,
            last_updated=last_updated,
            expires_at=expires_at,
            is_active=data.get('is_active', True)
        )