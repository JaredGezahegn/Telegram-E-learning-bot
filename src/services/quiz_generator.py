"""Quiz generator service for creating quizzes based on lessons."""

import logging
import re
from typing import List, Optional, Dict, Any
from datetime import datetime

from ..models.lesson import Lesson
from ..models.quiz import Quiz, QuizOption


logger = logging.getLogger(__name__)


class QuizGenerator:
    """Generates quizzes based on lesson content."""
    
    def __init__(self):
        """Initialize quiz generator."""
        self.quiz_templates = self._load_quiz_templates()
    
    def generate_quiz_for_lesson(self, lesson: Lesson) -> Optional[Quiz]:
        """Generate a quiz based on lesson content.
        
        Args:
            lesson: The lesson to create a quiz for.
            
        Returns:
            Generated quiz or None if generation fails.
        """
        try:
            # Extract key information from lesson
            lesson_info = self._extract_lesson_info(lesson)
            
            # Generate quiz based on lesson category and content
            if lesson.category == "grammar":
                return self._generate_grammar_quiz(lesson, lesson_info)
            elif lesson.category == "vocabulary":
                return self._generate_vocabulary_quiz(lesson, lesson_info)
            elif lesson.category == "common_mistakes":
                return self._generate_mistake_quiz(lesson, lesson_info)
            else:
                return self._generate_general_quiz(lesson, lesson_info)
                
        except Exception as e:
            logger.error(f"Failed to generate quiz for lesson {lesson.id}: {e}")
            return None
    
    def _extract_lesson_info(self, lesson: Lesson) -> Dict[str, Any]:
        """Extract key information from lesson content."""
        content = lesson.content
        
        # Extract examples (✅ and ❌ patterns)
        correct_examples_raw = re.findall(r'✅[^❌\n]*(?:\n[^✅❌\n]*)*', content, re.MULTILINE)
        wrong_examples_raw = re.findall(r'❌[^✅\n]*(?:\n[^✅❌\n]*)*', content, re.MULTILINE)
        
        # Also look for examples in bullet points
        bullet_examples = re.findall(r'•[^\n•]*', content)
        
        # Extract rules and tips
        rules = re.findall(r'📝[^📝\n]*(?:\n[^📝\n]*)*', content, re.MULTILINE)
        tips = re.findall(r'💡[^💡\n]*(?:\n[^💡\n]*)*', content, re.MULTILINE)
        
        # Extract structured information (🔹 patterns)
        structured_info = re.findall(r'🔹[^🔹\n]*(?:\n[^🔹\n]*)*', content, re.MULTILINE)
        
        # Clean up extracted text and get individual examples
        correct_examples = []
        for ex in correct_examples_raw:
            correct_examples.extend(self._extract_individual_examples(ex))
        
        wrong_examples = []
        for ex in wrong_examples_raw:
            wrong_examples.extend(self._extract_individual_examples(ex))
        
        bullet_examples = [self._clean_example_text(ex) for ex in bullet_examples]
        rules = [self._clean_example_text(rule) for rule in rules]
        tips = [self._clean_example_text(tip) for tip in tips]
        structured_info = [self._clean_example_text(info) for info in structured_info]
        
        # Filter out empty strings
        correct_examples = [ex for ex in correct_examples if ex.strip()]
        wrong_examples = [ex for ex in wrong_examples if ex.strip()]
        bullet_examples = [ex for ex in bullet_examples if ex.strip()]
        rules = [rule for rule in rules if rule.strip()]
        tips = [tip for tip in tips if tip.strip()]
        structured_info = [info for info in structured_info if info.strip()]
        
        return {
            'correct_examples': correct_examples,
            'wrong_examples': wrong_examples,
            'bullet_examples': bullet_examples,
            'rules': rules,
            'tips': tips,
            'structured_info': structured_info,
            'title': lesson.title,
            'tags': lesson.tags or []
        }
    
    def _truncate_explanation(self, explanation: str, max_length: int = 200) -> str:
        """Truncate explanation to fit Telegram's character limit.
        
        Args:
            explanation: Original explanation text
            max_length: Maximum allowed length (default 200 for Telegram polls)
            
        Returns:
            Truncated explanation that fits within the limit
        """
        if not explanation:
            return ""
        
        # Clean up the explanation first
        clean_explanation = self._clean_example_text(explanation)
        
        # If it's already short enough, return as is
        if len(clean_explanation) <= max_length:
            return clean_explanation
        
        # Truncate and add ellipsis
        truncated = clean_explanation[:max_length - 3].strip()
        
        # Try to break at a sentence or word boundary
        if '.' in truncated:
            # Break at the last complete sentence
            last_period = truncated.rfind('.')
            if last_period > max_length // 2:  # Only if we're not losing too much
                truncated = truncated[:last_period + 1]
        elif ' ' in truncated:
            # Break at the last complete word
            last_space = truncated.rfind(' ')
            if last_space > max_length // 2:  # Only if we're not losing too much
                truncated = truncated[:last_space]
        
        return truncated + "..." if len(clean_explanation) > len(truncated) else truncated
    
    def _extract_individual_examples(self, text: str) -> List[str]:
        """Extract individual example sentences from a text block."""
        if not text:
            return []
        
        # Remove emojis and formatting markers
        text = re.sub(r'[✅❌📝💡🔹⚠️🎯⏰]', '', text)
        
        # Remove section headers like "**Correct Examples:**", "**Wrong Examples:**", etc.
        text = re.sub(r'\*\*[^*]+\*\*:?\s*', '', text)
        
        # Remove italic markers
        text = re.sub(r'\*([^*]+)\*', r'\1', text)
        
        examples = []
        
        # Split by bullet points first
        bullet_parts = re.split(r'[•]', text)
        
        for part in bullet_parts:
            part = part.strip()
            if not part:
                continue
                
            # Further split by line breaks for multi-line examples
            line_parts = part.split('\n')
            
            for line in line_parts:
                line = line.strip()
                if line and len(line) > 10:  # Reasonable length
                    # Clean up whitespace
                    line = re.sub(r'\s+', ' ', line)
                    
                    # Remove parenthetical explanations like "(still living here)"
                    line = re.sub(r'\([^)]*\)', '', line)
                    line = line.strip()
                    
                    if line and len(line) > 5:
                        examples.append(line)
        
        return examples
    
    def _clean_example_text(self, text: str) -> str:
        """Clean up example text by removing formatting and extracting the first sentence."""
        examples = self._extract_individual_examples(text)
        return examples[0] if examples else ""
        """Clean up example text by removing formatting and extracting individual sentences."""
        if not text:
            return ""
        
        # Remove emojis and formatting markers
        text = re.sub(r'[✅❌📝💡🔹⚠️🎯⏰•]', '', text)
        
        # Remove section headers like "**Correct Examples:**", "**Wrong Examples:**", etc.
        text = re.sub(r'\*\*[^*]+\*\*:?\s*', '', text)
        
        # Remove italic markers
        text = re.sub(r'\*([^*]+)\*', r'\1', text)
        
        # Split into individual sentences/examples and take the first clean one
        sentences = []
        
        # Split by bullet points, line breaks, or periods
        parts = re.split(r'[•\n]|(?<=\.)\s+', text)
        
        for part in parts:
            clean_part = part.strip()
            if clean_part and len(clean_part) > 10:  # Reasonable length
                # Remove any remaining formatting
                clean_part = re.sub(r'\s+', ' ', clean_part)
                sentences.append(clean_part)
        
        # Return the first good sentence, or the cleaned text if no sentences found
        if sentences:
            return sentences[0].strip()
        else:
            # Fallback: just clean the original text
            text = re.sub(r'\s+', ' ', text)
            return text.strip()
    
    def _generate_grammar_quiz(self, lesson: Lesson, info: Dict[str, Any]) -> Quiz:
        """Generate a grammar-focused quiz."""
        
        # Try different quiz types for grammar
        if info['correct_examples'] and info['wrong_examples']:
            return self._create_correct_incorrect_quiz(lesson, info)
        elif info['rules']:
            return self._create_rule_application_quiz(lesson, info)
        else:
            return self._create_general_grammar_quiz(lesson, info)
    
    def _generate_vocabulary_quiz(self, lesson: Lesson, info: Dict[str, Any]) -> Quiz:
        """Generate a vocabulary-focused quiz."""
        
        if info['correct_examples']:
            return self._create_vocabulary_usage_quiz(lesson, info)
        else:
            return self._create_vocabulary_definition_quiz(lesson, info)
    
    def _generate_mistake_quiz(self, lesson: Lesson, info: Dict[str, Any]) -> Quiz:
        """Generate a common mistakes quiz."""
        
        if info['correct_examples'] and info['wrong_examples']:
            return self._create_mistake_identification_quiz(lesson, info)
        else:
            return self._create_general_mistake_quiz(lesson, info)
    
    def _generate_general_quiz(self, lesson: Lesson, info: Dict[str, Any]) -> Quiz:
        """Generate a general quiz when category is unknown."""
        
        return self._create_comprehension_quiz(lesson, info)
    
    def _create_correct_incorrect_quiz(self, lesson: Lesson, info: Dict[str, Any]) -> Quiz:
        """Create a quiz asking to identify correct usage."""
        
        question = f"Which sentence correctly demonstrates {info['title'].lower()}?"
        
        options = []
        
        # Add correct example as correct answer
        correct_text = None
        if info['correct_examples']:
            correct_text = info['correct_examples'][0]
        elif info['bullet_examples']:
            # Use first bullet example as correct if no explicit correct examples
            correct_text = info['bullet_examples'][0]
        
        if correct_text:
            correct_text = self._clean_example_text(correct_text)
            if correct_text:
                options.append(QuizOption(
                    text=correct_text,
                    is_correct=True,
                    explanation="This follows the correct grammar rule."
                ))
        
        # Add wrong examples as incorrect answers
        for wrong_ex in info['wrong_examples'][:3]:  # Max 3 wrong examples to avoid duplicates
            wrong_text = self._clean_example_text(wrong_ex)
            if wrong_text and wrong_text not in [opt.text for opt in options] and len(wrong_text) > 5:
                options.append(QuizOption(
                    text=wrong_text,
                    is_correct=False,
                    explanation="This violates the grammar rule."
                ))
        
        # If we don't have enough options, create some based on the lesson content
        if len(options) < 2:
            # Create options based on structured info or rules
            if info['structured_info']:
                for struct_info in info['structured_info'][:2]:
                    clean_info = self._clean_example_text(struct_info)
                    if clean_info and len(clean_info) > 10:  # Reasonable length
                        is_correct = len(options) == 0  # First one is correct if we have no correct answer yet
                        options.append(QuizOption(
                            text=clean_info,
                            is_correct=is_correct,
                            explanation="This demonstrates the lesson concept." if is_correct else "This is not the main focus."
                        ))
        
        # Generate additional distractors to reach 4-5 options
        additional_distractors = self._generate_grammar_distractors(lesson, info, len(options))
        options.extend(additional_distractors)
        
        # Ensure we have exactly 4-5 options
        while len(options) < 4:
            options.append(QuizOption(
                text=f"None of the above demonstrate {info['title'].lower()}",
                is_correct=False,
                explanation="One of the options is actually correct."
            ))
        
        # Limit to 5 options max
        options = options[:5]
        
        # Ensure exactly one correct answer
        correct_count = sum(1 for opt in options if opt.is_correct)
        if correct_count == 0:
            # Make the first option correct if none are marked correct
            options[0].is_correct = True
            options[0].explanation = "This is the correct example from the lesson."
        elif correct_count > 1:
            # Keep only the first correct answer
            found_correct = False
            for opt in options:
                if opt.is_correct and found_correct:
                    opt.is_correct = False
                    opt.explanation = "This is not the correct answer."
                elif opt.is_correct:
                    found_correct = True
        
        explanation = self._truncate_explanation(
            info['rules'][0] if info['rules'] else f"Remember the rule for {info['title'].lower()}."
        )
        
        return Quiz(
            lesson_id=lesson.id,
            question=question,
            options=options,
            explanation=explanation,
            difficulty=lesson.difficulty
        )
    
    def _create_rule_application_quiz(self, lesson: Lesson, info: Dict[str, Any]) -> Quiz:
        """Create a quiz about applying grammar rules."""
        
        question = f"According to the lesson on {info['title']}, which statement is true?"
        
        options = []
        
        # Use the main rule as correct answer
        if info['rules']:
            rule_text = info['rules'][0]
            rule_text = re.sub(r'\*\*.*?\*\*:', '', rule_text).strip()
            rule_text = re.sub(r'📝\s*', '', rule_text).strip()
            if rule_text:
                options.append(QuizOption(
                    text=rule_text,
                    is_correct=True,
                    explanation="This is the main rule from the lesson."
                ))
        
        # Create plausible but incorrect alternatives
        distractors = self._generate_rule_distractors(lesson, info)
        options.extend(distractors)
        
        # Ensure we have 4-5 options
        while len(options) < 4:
            options.append(QuizOption(
                text="This rule has no practical applications",
                is_correct=False,
                explanation="All grammar rules have practical uses."
            ))
        
        options = options[:5]  # Limit to 5 options
        
        explanation = self._truncate_explanation(
            info['tips'][0] if info['tips'] else f"Review the key rule for {info['title'].lower()}."
        )
        
        return Quiz(
            lesson_id=lesson.id,
            question=question,
            options=options,
            explanation=explanation,
            difficulty=lesson.difficulty
        )
    
    def _generate_rule_distractors(self, lesson: Lesson, info: Dict[str, Any]) -> List[QuizOption]:
        """Generate plausible but incorrect rule statements."""
        
        distractors = [
            QuizOption(
                text="The rule applies only to formal writing",
                is_correct=False,
                explanation="This rule applies to all English usage."
            ),
            QuizOption(
                text="There are no exceptions to this rule",
                is_correct=False,
                explanation="Most grammar rules have some exceptions."
            ),
            QuizOption(
                text="This rule is only used in American English",
                is_correct=False,
                explanation="This rule applies to all varieties of English."
            ),
            QuizOption(
                text="The rule is optional in spoken English",
                is_correct=False,
                explanation="Grammar rules apply to both spoken and written English."
            )
        ]
        
        return distractors
    
    def _create_vocabulary_usage_quiz(self, lesson: Lesson, info: Dict[str, Any]) -> Quiz:
        """Create a vocabulary usage quiz."""
        
        question = f"Choose the sentence that correctly uses the vocabulary from '{info['title']}':"
        
        options = []
        
        # Use correct example
        if info['correct_examples']:
            correct_text = info['correct_examples'][0]
            correct_text = re.sub(r'\*\*.*?\*\*:', '', correct_text).strip()
            options.append(QuizOption(
                text=correct_text,
                is_correct=True,
                explanation="This demonstrates correct vocabulary usage."
            ))
        
        # Generate vocabulary distractors
        distractors = self._generate_vocabulary_distractors(lesson, info)
        options.extend(distractors[:2])
        
        explanation = self._truncate_explanation(
            f"Remember the context and usage rules for {info['title'].lower()}."
        )
        
        return Quiz(
            lesson_id=lesson.id,
            question=question,
            options=options,
            explanation=explanation,
            difficulty=lesson.difficulty
        )
    
    def _create_general_grammar_quiz(self, lesson: Lesson, info: Dict[str, Any]) -> Quiz:
        """Create a general grammar quiz."""
        
        question = f"What is the main focus of the lesson '{info['title']}'?"
        
        options = [
            QuizOption(
                text=f"Understanding {info['title'].lower()}",
                is_correct=True,
                explanation="This is the main topic of the lesson."
            ),
            QuizOption(
                text="Learning new vocabulary words",
                is_correct=False,
                explanation="This lesson focuses on grammar, not vocabulary."
            ),
            QuizOption(
                text="Practicing pronunciation skills",
                is_correct=False,
                explanation="This lesson is about grammar rules, not pronunciation."
            ),
            QuizOption(
                text="Improving listening comprehension",
                is_correct=False,
                explanation="This lesson teaches grammar concepts."
            ),
            QuizOption(
                text="Developing writing style",
                is_correct=False,
                explanation="This lesson focuses on specific grammar rules."
            )
        ]
        
        return Quiz(
            lesson_id=lesson.id,
            question=question,
            options=options,
            explanation=f"The lesson teaches {info['title'].lower()}.",
            difficulty=lesson.difficulty
        )
    
    def _generate_grammar_distractors(self, lesson: Lesson, info: Dict[str, Any], current_count: int) -> List[QuizOption]:
        """Generate plausible but incorrect grammar distractors."""
        
        distractors = []
        needed = 4 - current_count  # We want at least 4 total options
        
        # Common grammar distractors based on lesson category
        if lesson.category == "grammar":
            if "present perfect" in lesson.title.lower():
                distractors.extend([
                    QuizOption(
                        text="I am living here for 5 years",
                        is_correct=False,
                        explanation="Present continuous is incorrect for duration."
                    ),
                    QuizOption(
                        text="I was lived here for 5 years",
                        is_correct=False,
                        explanation="This mixes past tense with past participle incorrectly."
                    ),
                    QuizOption(
                        text="I will live here for 5 years",
                        is_correct=False,
                        explanation="Future tense doesn't show completed action with present relevance."
                    )
                ])
            elif "article" in lesson.title.lower():
                distractors.extend([
                    QuizOption(
                        text="I work in the marketing department",
                        is_correct=False,
                        explanation="'The' is not needed with general job fields."
                    ),
                    QuizOption(
                        text="She is a engineer at company",
                        is_correct=False,
                        explanation="Should be 'an engineer' and 'the company'."
                    ),
                    QuizOption(
                        text="I saw the dog. A dog was friendly",
                        is_correct=False,
                        explanation="Should use 'the dog' for the second reference."
                    )
                ])
            elif "conditional" in lesson.title.lower():
                distractors.extend([
                    QuizOption(
                        text="If it will rain, I will stay home",
                        is_correct=False,
                        explanation="Don't use 'will' in the if-clause."
                    ),
                    QuizOption(
                        text="If it rains, I would stay home",
                        is_correct=False,
                        explanation="This mixes first and second conditional."
                    ),
                    QuizOption(
                        text="If it rained, I will stay home",
                        is_correct=False,
                        explanation="Tense mismatch between clauses."
                    )
                ])
            else:
                # Generic grammar distractors
                distractors.extend([
                    QuizOption(
                        text="This sentence contains a common grammar mistake",
                        is_correct=False,
                        explanation="This is a generic distractor."
                    ),
                    QuizOption(
                        text="The grammar in this option is incorrect",
                        is_correct=False,
                        explanation="This doesn't follow the lesson rule."
                    )
                ])
        
        elif lesson.category == "vocabulary":
            distractors.extend([
                QuizOption(
                    text="This uses the vocabulary word incorrectly",
                    is_correct=False,
                    explanation="The vocabulary is used in wrong context."
                ),
                QuizOption(
                    text="The meaning is completely different here",
                    is_correct=False,
                    explanation="This doesn't match the lesson vocabulary."
                ),
                QuizOption(
                    text="This sentence misuses the key terms",
                    is_correct=False,
                    explanation="The vocabulary usage is inappropriate."
                )
            ])
        
        else:
            # Generic distractors
            distractors.extend([
                QuizOption(
                    text="This option contains an error",
                    is_correct=False,
                    explanation="This doesn't follow the lesson rules."
                ),
                QuizOption(
                    text="This example is incorrect",
                    is_correct=False,
                    explanation="This violates the lesson principles."
                ),
                QuizOption(
                    text="This sentence has a mistake",
                    is_correct=False,
                    explanation="This doesn't demonstrate correct usage."
                )
            ])
        
        # Return only the number we need
        return distractors[:needed]
    
    def _generate_vocabulary_distractors(self, lesson: Lesson, info: Dict[str, Any]) -> List[QuizOption]:
        """Generate vocabulary distractors."""
        
        distractors = [
            QuizOption(
                text="The vocabulary is used incorrectly in context",
                is_correct=False,
                explanation="This shows incorrect usage."
            ),
            QuizOption(
                text="The meaning is completely different",
                is_correct=False,
                explanation="This doesn't match the lesson content."
            )
        ]
        
        return distractors
    
    def _create_mistake_identification_quiz(self, lesson: Lesson, info: Dict[str, Any]) -> Quiz:
        """Create a quiz about identifying common mistakes."""
        
        question = f"Which sentence contains the common mistake discussed in '{info['title']}'?"
        
        options = []
        
        # Use wrong example as the correct answer (identifying the mistake)
        if info['wrong_examples']:
            wrong_text = info['wrong_examples'][0]
            wrong_text = re.sub(r'\*\*.*?\*\*:', '', wrong_text).strip()
            options.append(QuizOption(
                text=wrong_text,
                is_correct=True,
                explanation="This sentence contains the common mistake from the lesson."
            ))
        
        # Use correct examples as distractors
        for correct_ex in info['correct_examples'][:2]:
            correct_text = re.sub(r'\*\*.*?\*\*:', '', correct_ex).strip()
            if correct_text:
                options.append(QuizOption(
                    text=correct_text,
                    is_correct=False,
                    explanation="This sentence is actually correct."
                ))
        
        explanation = f"Remember to avoid the common mistake: {info['title'].lower()}."
        
        return Quiz(
            lesson_id=lesson.id,
            question=question,
            options=options,
            explanation=explanation,
            difficulty=lesson.difficulty
        )
    
    def _create_general_mistake_quiz(self, lesson: Lesson, info: Dict[str, Any]) -> Quiz:
        """Create a general mistake quiz."""
        return self._create_general_grammar_quiz(lesson, info)
    
    def _create_vocabulary_definition_quiz(self, lesson: Lesson, info: Dict[str, Any]) -> Quiz:
        """Create a vocabulary definition quiz."""
        return self._create_general_grammar_quiz(lesson, info)
    
    def _create_comprehension_quiz(self, lesson: Lesson, info: Dict[str, Any]) -> Quiz:
        """Create a general comprehension quiz."""
        return self._create_general_grammar_quiz(lesson, info)
    
    def _load_quiz_templates(self) -> Dict[str, Any]:
        """Load quiz templates for different categories."""
        # This could be expanded to load from a file or database
        return {
            'grammar': {
                'question_starters': [
                    "Which sentence correctly demonstrates",
                    "According to the grammar rule",
                    "Choose the correct usage of"
                ]
            },
            'vocabulary': {
                'question_starters': [
                    "Which sentence uses the vocabulary correctly",
                    "What is the meaning of",
                    "Choose the best definition for"
                ]
            }
        }