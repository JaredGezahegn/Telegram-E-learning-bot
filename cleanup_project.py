#!/usr/bin/env python3
"""
Clean up unnecessary test files and documentation from the project root.
Keeps essential files and moves others to an archive folder.
"""

import os
import shutil
from pathlib import Path

# Files to keep in root
KEEP_FILES = {
    # Essential docs
    'README.md',
    'DEPLOYMENT.md',
    'SUPABASE_SETUP.md',
    
    # Essential utilities
    'diagnose_telegram_issue.py',
    'reset_circuit_breaker.py',
    
    # Core application files (already in proper locations)
}

# Files to delete (temporary/obsolete)
DELETE_FILES = [
    # Obsolete documentation
    'BOT_STARTUP_GUIDE.md',
    'COMMIT_SUMMARY.md',
    'INTERACTIVE_BOT_PHASE1_COMPLETE.md',
    'INTERACTIVE_BOT_SETUP.md',
    'ISSUE_RESOLVED.md',
    'NEXT_STEPS.md',
    'PHASE2_CONTENT_BROWSING_COMPLETE.md',
    'PRODUCTION_DEPLOYMENT_FIXES.md',
    'PYTHON_VERSION_FIX.md',
    'PYTHON_VERSION_FIX_RENDER.md',
    'QUIZ_FEATURE_ADDED.md',
    'README_FIXES.md',
    'RENDER_DEPLOYMENT.md',
    
    # Test/debug scripts (root level only - keep tests/ folder)
    'check_bot_status.py',
    'check_lesson_categories.py',
    'check_supabase_tables.py',
    'clean_lessons.py',
    'create_interactive_tables.py',
    'create_tables_supabase.py',
    'debug_env.py',
    'debug_quiz_length.py',
    'debug_startup.py',
    'demo_bot_controller.py',
    'demo_lesson_management.py',
    'demo_scheduler.py',
    'diagnose_bot_issue.py',
    'explain_database_flow.py',
    'load_advanced_lessons.py',
    'load_data.py',
    'load_data_endpoint.py',
    'load_lessons_to_supabase.py',
    'manual_test_post.py',
    'post_lesson_now.py',
    'quick_test.py',
    'reschedule_test.py',
    'send_lesson_now.py',
    'setup_env_config.py',
    'setup_interactive_db.py',
    'setup_supabase.py',
    'simple_main.py',
    'simple_test.py',
    'start_bot.py',
    'test_admin_manual_post.py',
    'test_bot_interactive.py',
    'test_bot_run.py',
    'test_bot_startup.py',
    'test_bot_startup_interactive.py',
    'test_commands_basic.py',
    'test_content_browsing.py',
    'test_current_config.py',
    'test_deployment_interactive.py',
    'test_deployment_simple.py',
    'test_enhanced_bot.py',
    'test_formatting.py',
    'test_immediate_post.py',
    'test_improved_quiz.py',
    'test_interactive_integration.py',
    'test_interactive_setup.py',
    'test_lesson_manager.py',
    'test_lesson_post.py',
    'test_main_minimal.py',
    'test_manual_quiz_post.py',
    'test_minimal_scheduler.py',
    'test_multiple_lesson_types.py',
    'test_quiz_complete_flow.py',
    'test_quiz_database_quality.py',
    'test_quiz_fix.py',
    'test_quiz_generation.py',
    'test_quiz_posting_flow.py',
    'test_quiz_scheduling_issue.py',
    'test_real_lesson_quiz.py',
    'test_scheduler_20min.py',
    'test_scheduler_integration.py',
    'test_simple_deployment.py',
    'test_supabase_connection.py',
    'test_system_integration.py',
    'trigger_manual_post.py',
    'watch_bot.py',
    
    # Obsolete SQL files
    'simple_table_creation.sql',
    'supabase_manual_setup.sql',
    'interactive_bot_tables.sql',
    'supabase_simple_policies.sql',
    'supabase_security_policies.sql',
]

def cleanup():
    """Remove unnecessary files from project root."""
    root = Path('.')
    deleted = []
    errors = []
    
    print("🧹 Cleaning up project root directory...\n")
    
    for filename in DELETE_FILES:
        filepath = root / filename
        if filepath.exists():
            try:
                filepath.unlink()
                deleted.append(filename)
                print(f"✅ Deleted: {filename}")
            except Exception as e:
                errors.append((filename, str(e)))
                print(f"❌ Error deleting {filename}: {e}")
        else:
            print(f"⏭️  Skipped (not found): {filename}")
    
    print(f"\n📊 Summary:")
    print(f"   Deleted: {len(deleted)} files")
    print(f"   Errors: {len(errors)} files")
    
    if errors:
        print("\n⚠️  Files with errors:")
        for filename, error in errors:
            print(f"   - {filename}: {error}")
    
    print("\n✨ Cleanup complete!")
    print("\nRemaining essential files:")
    print("   - README.md (main documentation)")
    print("   - DEPLOYMENT.md (deployment guide)")
    print("   - SUPABASE_SETUP.md (database setup)")
    print("   - diagnose_telegram_issue.py (troubleshooting)")
    print("   - reset_circuit_breaker.py (troubleshooting)")
    print("   - tests/ (unit tests)")
    print("   - src/ (application code)")
    print("   - data/ (seed data)")

if __name__ == "__main__":
    cleanup()
