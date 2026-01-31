"""Admin action log model for tracking administrative activities."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class AdminActionLog:
    """Log entry for administrative actions."""
    
    id: Optional[int] = None
    admin_user_id: int = 0
    admin_username: Optional[str] = None
    action_type: str = ""
    action_details: str = ""
    target_user_id: Optional[int] = None
    timestamp: Optional[datetime] = None
    success: bool = True
    error_message: Optional[str] = None
    
    def __post_init__(self):
        """Initialize default values after creation."""
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert admin log entry to dictionary for database storage.
        
        Returns:
            Dictionary representation of admin log entry
        """
        return {
            'id': self.id,
            'admin_user_id': self.admin_user_id,
            'admin_username': self.admin_username,
            'action_type': self.action_type,
            'action_details': self.action_details,
            'target_user_id': self.target_user_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'success': self.success,
            'error_message': self.error_message
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AdminActionLog':
        """Create admin log entry from dictionary data.
        
        Args:
            data: Dictionary containing admin log data
            
        Returns:
            AdminActionLog instance
        """
        timestamp = None
        if data.get('timestamp'):
            timestamp = datetime.fromisoformat(data['timestamp'])
        
        return cls(
            id=data.get('id'),
            admin_user_id=data['admin_user_id'],
            admin_username=data.get('admin_username'),
            action_type=data.get('action_type', ''),
            action_details=data.get('action_details', ''),
            target_user_id=data.get('target_user_id'),
            timestamp=timestamp,
            success=data.get('success', True),
            error_message=data.get('error_message')
        )


@dataclass
class CommandUsageStats:
    """Statistics for command usage tracking."""
    
    id: Optional[int] = None
    command_name: str = ""
    user_id: int = 0
    chat_type: str = ""  # 'private', 'group', 'channel'
    execution_time: Optional[datetime] = None
    success: bool = True
    response_time_ms: int = 0
    error_type: Optional[str] = None
    
    def __post_init__(self):
        """Initialize default values after creation."""
        if self.execution_time is None:
            self.execution_time = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert command usage stats to dictionary for database storage.
        
        Returns:
            Dictionary representation of command usage stats
        """
        return {
            'id': self.id,
            'command_name': self.command_name,
            'user_id': self.user_id,
            'chat_type': self.chat_type,
            'execution_time': self.execution_time.isoformat() if self.execution_time else None,
            'success': self.success,
            'response_time_ms': self.response_time_ms,
            'error_type': self.error_type
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CommandUsageStats':
        """Create command usage stats from dictionary data.
        
        Args:
            data: Dictionary containing command usage data
            
        Returns:
            CommandUsageStats instance
        """
        execution_time = None
        if data.get('execution_time'):
            execution_time = datetime.fromisoformat(data['execution_time'])
        
        return cls(
            id=data.get('id'),
            command_name=data.get('command_name', ''),
            user_id=data['user_id'],
            chat_type=data.get('chat_type', ''),
            execution_time=execution_time,
            success=data.get('success', True),
            response_time_ms=data.get('response_time_ms', 0),
            error_type=data.get('error_type')
        )