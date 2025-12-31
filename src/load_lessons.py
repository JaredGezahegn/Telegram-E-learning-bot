#!/usr/bin/env python3
"""Load lessons into the database."""

import sys
import os
import json
from datetime import datetime

# Import models and services
from .models.lesson import Lesson
from .services.lesson_repository import LessonRepository


def load_lessons():
    """Load lessons from JSON into database."""
    
    # Load JSON data
    json_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'seed_lessons.json')
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    lessons = []
    for lesson_data in data['lessons']:
        lesson = Lesson.from_dict(lesson_data)
        lessons.append(lesson)
    
    # Save to database
    repo = LessonRepository()
    for lesson in lessons:
        repo.create_lesson(lesson)
    
    print(f"✅ Loaded {len(lessons)} lessons into database")
    
    # Verify
    all_lessons = repo.get_all_lessons()
    print(f"✅ Database now contains {len(all_lessons)} lessons")
    
    return len(lessons)


if __name__ == "__main__":
    load_lessons()