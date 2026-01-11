#!/usr/bin/env python3
"""Load advanced lessons into Supabase database."""

import os
import json
import requests
from pathlib import Path

# Load environment variables from .env file
def load_env_file():
    """Load environment variables from .env file."""
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

# Load .env file
load_env_file()

def load_advanced_lessons():
    """Load advanced lessons from JSON file."""
    json_path = Path(__file__).parent / 'data' / 'advanced_lessons.json'
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data['lessons']

def insert_lesson_to_supabase(lesson_data, url, key):
    """Insert a single lesson to Supabase."""
    headers = {
        'apikey': key,
        'Authorization': f'Bearer {key}',
        'Content-Type': 'application/json',
        'Prefer': 'return=representation'
    }
    
    # Prepare lesson data for Supabase
    supabase_lesson = {
        'title': lesson_data['title'],
        'content': lesson_data['content'],
        'category': lesson_data['category'],
        'difficulty': lesson_data['difficulty'],
        'tags': lesson_data.get('tags', []),
        'source': lesson_data.get('source', 'manual'),
        'usage_count': 0
    }
    
    response = requests.post(
        f"{url}/rest/v1/lessons",
        headers=headers,
        json=supabase_lesson,
        timeout=10
    )
    
    return response

def main():
    """Main function to load advanced lessons."""
    print("🚀 Loading Advanced English Lessons to Supabase")
    print("=" * 60)
    
    # Get credentials
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_ANON_KEY')
    
    if not url or not key:
        print("❌ Missing Supabase credentials!")
        print("Make sure SUPABASE_URL and SUPABASE_ANON_KEY are set in .env")
        return 1
    
    print(f"✅ URL: {url}")
    print(f"✅ Key: {key[:20]}...")
    
    # Load advanced lessons
    try:
        lessons = load_advanced_lessons()
        print(f"📚 Loaded {len(lessons)} advanced lessons from JSON")
    except Exception as e:
        print(f"❌ Error loading lessons from JSON: {e}")
        return 1
    
    # Show lesson categories
    categories = {}
    for lesson in lessons:
        cat = lesson['category']
        categories[cat] = categories.get(cat, 0) + 1
    
    print("\n📊 Advanced Lesson Categories:")
    for category, count in categories.items():
        print(f"  • {category.replace('_', ' ').title()}: {count} lessons")
    
    # Insert lessons
    success_count = 0
    failed_lessons = []
    
    print(f"\n🔄 Inserting {len(lessons)} advanced lessons...")
    
    for i, lesson in enumerate(lessons, 1):
        print(f"   {i:2d}/{len(lessons)}: {lesson['title'][:50]}...")
        
        try:
            response = insert_lesson_to_supabase(lesson, url, key)
            
            if response.status_code in [200, 201]:
                success_count += 1
                print(f"      ✅ Success")
            else:
                print(f"      ❌ Failed: {response.status_code} - {response.text[:100]}")
                failed_lessons.append(lesson['title'])
                
        except Exception as e:
            print(f"      ❌ Error: {e}")
            failed_lessons.append(lesson['title'])
    
    # Summary
    print("\n" + "=" * 60)
    print(f"✅ Successfully inserted: {success_count}/{len(lessons)} advanced lessons")
    
    if failed_lessons:
        print(f"❌ Failed lessons: {len(failed_lessons)}")
        for title in failed_lessons[:3]:  # Show first 3 failures
            print(f"  - {title}")
        if len(failed_lessons) > 3:
            print(f"  ... and {len(failed_lessons) - 3} more")
    
    # Verify total lesson count
    try:
        headers = {
            'apikey': key,
            'Authorization': f'Bearer {key}',
        }
        
        response = requests.get(
            f"{url}/rest/v1/lessons?select=id",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            total_lessons = len(response.json())
            print(f"✅ Total lessons in Supabase: {total_lessons}")
            print(f"🎉 Your bot now has {total_lessons} lessons for {total_lessons} days of content!")
        else:
            print(f"⚠️  Could not verify lesson count: {response.status_code}")
            
    except Exception as e:
        print(f"⚠️  Could not verify lesson count: {e}")
    
    return 0 if success_count > 0 else 1

if __name__ == "__main__":
    exit(main())