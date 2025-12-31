# Seed Lesson Data

This directory contains the seed lesson content for the Telegram English Bot.

## Files

- `seed_lessons.json` - Main seed data file containing 51 high-quality English lessons
- `load_seed_data.py` - Validation and loading script for the seed data

## Content Overview

The seed data contains **51 lessons** distributed across three categories:

### Category Distribution
- **Grammar**: 20 lessons (39.2%) - Core grammar concepts and rules
- **Vocabulary**: 18 lessons (35.3%) - Practical vocabulary for different contexts
- **Common Mistakes**: 13 lessons (25.5%) - Frequent errors and corrections

### Difficulty Levels
- **Beginner**: 15 lessons (29.4%) - Basic concepts for new learners
- **Intermediate**: 26 lessons (51.0%) - Standard level for most learners
- **Advanced**: 10 lessons (19.6%) - Complex topics for advanced students

## Lesson Format

Each lesson follows this structure:

```json
{
  "title": "Lesson Title",
  "content": "Formatted lesson content with Telegram markup",
  "category": "grammar|vocabulary|common_mistakes",
  "difficulty": "beginner|intermediate|advanced",
  "tags": ["tag1", "tag2", "tag3"],
  "source": "manual"
}
```

### Content Features

- **Engaging Format**: Uses emojis and Telegram markdown for visual appeal
- **Clear Structure**: Consistent formatting with rules, examples, and tips
- **Practical Examples**: Real-world usage examples for each concept
- **Memory Aids**: Helpful tricks and mnemonics for difficult concepts

## Grammar Lessons (20)

Topics covered include:
- Tenses (Present Perfect, Past Continuous, Future Forms)
- Conditionals (Zero, First, Second)
- Modal Verbs (Can, Could, May, Might)
- Passive Voice
- Reported Speech
- Articles and Prepositions
- Question Formation
- Subject-Verb Agreement

## Vocabulary Lessons (18)

Practical vocabulary for:
- Business and workplace
- Travel and transportation
- Health and medicine
- Technology and digital life
- Food and cooking
- Money and banking
- Education and academic life
- Entertainment and sports

## Common Mistakes (13)

Frequent errors including:
- Its vs It's
- Your vs You're
- There, Their, They're
- Affect vs Effect
- Less vs Fewer
- Who vs Whom
- Apostrophe usage
- Double negatives

## Usage

To validate the seed data:

```bash
python data/load_seed_data.py
```

This script will:
- Validate JSON format
- Check lesson data integrity
- Display distribution statistics
- Verify minimum content requirements

## Requirements Met

✅ **50+ lessons**: 51 lessons provided  
✅ **Category distribution**: Grammar 40%, Vocabulary 35%, Common Mistakes 25%  
✅ **Telegram formatting**: Rich markup with emojis and structure  
✅ **Quality content**: Educational value with clear explanations  
✅ **Proper tagging**: Relevant tags for categorization  
✅ **Difficulty levels**: Appropriate distribution across skill levels  

## Integration

The seed data is designed to be loaded into the SQLite database during system initialization. The lesson repository will use this data to provide content for daily posting.