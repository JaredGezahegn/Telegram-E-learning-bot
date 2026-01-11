#!/usr/bin/env python3
"""
Debug startup issues by testing imports step by step.
"""

import sys
import os
import traceback

def test_imports():
    """Test imports step by step to identify issues."""
    print("🔍 Debug Startup - Testing Imports")
    print("=" * 50)
    
    try:
        print("1. Testing basic Python imports...")
        import asyncio
        import logging
        print("   ✅ Basic imports OK")
        
        print("2. Testing path setup...")
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
        print("   ✅ Path setup OK")
        
        print("3. Testing config import...")
        from src.config import get_config
        config = get_config()
        print(f"   ✅ Config OK - Database: {config.database_type}")
        
        print("4. Testing database factory...")
        from src.services.database_factory import create_lesson_repository
        print("   ✅ Database factory import OK")
        
        print("5. Testing lesson manager...")
        from src.services.lesson_manager import LessonManager
        print("   ✅ Lesson manager import OK")
        
        print("6. Testing bot controller import...")
        try:
            from src.services.bot_controller import create_bot_controller
            print("   ✅ Bot controller import OK")
        except Exception as e:
            print(f"   ❌ Bot controller import failed: {e}")
            print("   📝 This is likely the httpcore issue")
            return False
        
        print("7. Testing scheduler import...")
        from src.services.scheduler import create_scheduler_service
        print("   ✅ Scheduler import OK")
        
        print("8. Testing system integration...")
        from src.services.system_integration_service import SystemIntegrationService
        print("   ✅ System integration import OK")
        
        print("\n" + "=" * 50)
        print("✅ ALL IMPORTS SUCCESSFUL!")
        print("✅ The app should start properly now")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Import failed: {e}")
        print("\n📋 Full traceback:")
        traceback.print_exc()
        return False

def main():
    """Main function."""
    success = test_imports()
    
    if success:
        print("\n🎉 Startup debug successful!")
        print("The bot should work properly in production.")
    else:
        print("\n💥 Startup debug failed!")
        print("There are still import issues to resolve.")

if __name__ == "__main__":
    main()