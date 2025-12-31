#!/usr/bin/env python3
"""
Script to load seed lesson data into the database.
This script validates the JSON data and loads it into the lesson database.
"""

import json
import sys
import os
from pathlib import Path

# Add src to path to import models
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from models.lesson import Lesson
from models.database import DatabaseManager


def load_seed_lessons(json_file_path: str = "data/seed_lessons.json") -> list[Lesson]:
    """Load and validate lesson data from JSON file."""
    
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Seed data file not found: {json_file_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in seed data file: {e}")
    
    if 'lessons' not in data:
        raise ValueError("Seed data must contain 'lessons' key")
    
    lessons = []
    for i, lesson_data in enumerate(data['lessons']):
        try:
            lesson = Lesson.from_dict(lesson_data)
            lesson.validate()  # Validate the lesson data
            lessons.append(lesson)
        except Exception as e:
            raise ValueError(f"Invalid lesson data at index {i}: {e}")
    
    return lessons


def main():
    """Load seed data and display statistics."""
    
    try:
        lessons = load_seed_lessons()
        
        print(f"✅ Successfully loaded {len(lessons)} lessons")
        
        # Count by category
        categories = {}
        difficulties = {}
        
        for lesson in lessons:
            categories[lesson.category] = categories.get(lesson.category, 0) + 1
            difficulties[lesson.difficulty] = difficulties.get(lesson.difficulty, 0) + 1
        
        print("\n📊 Category Distribution:")
        for category, count in categories.items():
            percentage = (count / len(lessons)) * 100
            print(f"  {category}: {count} lessons ({percentage:.1f}%)")
        
        print("\n📈 Difficulty Distribution:")
        for difficulty, count in difficulties.items():
            percentage = (count / len(lessons)) * 100
            print(f"  {difficulty}: {count} lessons ({percentage:.1f}%)")
        
        # Validate minimum requirements
        if len(lessons) < 50:
            print(f"⚠️  Warning: Only {len(lessons)} lessons (minimum 50 recommended)")
        
        if categories.get('grammar', 0) < 20:
            print(f"⚠️  Warning: Only {categories.get('grammar', 0)} grammar lessons (20+ recommended)")
        
        if categories.get('vocabulary', 0) < 18:
            print(f"⚠️  Warning: Only {categories.get('vocabulary', 0)} vocabulary lessons (18+ recommended)")
        
        if categories.get('common_mistakes', 0) < 13:
            print(f"⚠️  Warning: Only {categories.get('common_mistakes', 0)} common mistake lessons (13+ recommended)")
        
        print("\n✅ Seed data validation complete!")
        
    except Exception as e:
        print(f"❌ Error loading seed data: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()