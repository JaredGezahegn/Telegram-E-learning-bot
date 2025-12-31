"""Quiz model for lesson-based quizzes."""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime
import json


@dataclass
class QuizOption:
    """Represents a quiz option/answer choice."""
    text: str
    is_correct: bool
    explanation: Optional[str] = None


@dataclass
class Quiz:
    """Represents a quiz based on a lesson."""
    id: Optional[int] = None
    lesson_id: int = None
    question: str = ""
    options: List[QuizOption] = None
    explanation: str = ""
    difficulty: str = "intermediate"
    created_at: Optional[datetime] = None
    usage_count: int = 0
    
    def __post_init__(self):
        if self.options is None:
            self.options = []
        if self.created_at is None:
            self.created_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert quiz to dictionary."""
        return {
            'id': self.id,
            'lesson_id': self.lesson_id,
            'question': self.question,
            'options': [
                {
                    'text': opt.text,
                    'is_correct': opt.is_correct,
                    'explanation': opt.explanation
                }
                for opt in self.options
            ],
            'explanation': self.explanation,
            'difficulty': self.difficulty,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'usage_count': self.usage_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Quiz':
        """Create quiz from dictionary."""
        options = []
        for opt_data in data.get('options', []):
            options.append(QuizOption(
                text=opt_data['text'],
                is_correct=opt_data['is_correct'],
                explanation=opt_data.get('explanation')
            ))
        
        return cls(
            id=data.get('id'),
            lesson_id=data.get('lesson_id'),
            question=data.get('question', ''),
            options=options,
            explanation=data.get('explanation', ''),
            difficulty=data.get('difficulty', 'intermediate'),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else None,
            usage_count=data.get('usage_count', 0)
        )
    
    def get_correct_option_index(self) -> Optional[int]:
        """Get the index of the correct option (0-based)."""
        for i, option in enumerate(self.options):
            if option.is_correct:
                return i
        return None
    
    def get_correct_option(self) -> Optional[QuizOption]:
        """Get the correct option."""
        for option in self.options:
            if option.is_correct:
                return option
        return None
    
    def validate(self) -> bool:
        """Validate quiz data."""
        if not self.question.strip():
            raise ValueError("Quiz question cannot be empty")
        
        if len(self.options) < 2:
            raise ValueError("Quiz must have at least 2 options")
        
        if len(self.options) > 10:
            raise ValueError("Quiz cannot have more than 10 options")
        
        correct_count = sum(1 for opt in self.options if opt.is_correct)
        if correct_count != 1:
            raise ValueError("Quiz must have exactly one correct answer")
        
        for option in self.options:
            if not option.text.strip():
                raise ValueError("Quiz option text cannot be empty")
        
        return True