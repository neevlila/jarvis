"""
Session Manager for J.A.R.V.I.S. Desktop Engine.

Manages task session lifecycle, goal tracking, action audit logs,
and failure memory for closed-loop adaptation.
"""

import time
from typing import List, Dict, Any, Optional


class SessionManager:
    """
    Tracks state, action history, and failure memory across an agent automation session.
    """

    def __init__(self, max_steps: int = 15, max_failures: int = 5):
        self.current_goal: Optional[str] = None
        self.action_history: List[Dict[str, Any]] = []
        self.failure_memory: List[Dict[str, Any]] = []
        self.is_active: bool = False
        self.start_time: float = 0.0
        self.max_steps: int = max_steps
        self.max_failures: int = max_failures

    def start_session(self, goal: str):
        """Initializes a new task session."""
        self.current_goal = goal
        self.action_history = []
        self.failure_memory = []
        self.is_active = True
        self.start_time = time.time()

    def end_session(self):
        """Terminates the current session."""
        self.is_active = False

    def log_action(self, action_dict: Dict[str, Any], execution_result: Optional[Dict[str, Any]] = None, verification_result: Optional[Dict[str, Any]] = None):
        """Logs an executed action and its verification outcome."""
        entry = {
            "timestamp": time.time(),
            "step": len(self.action_history) + 1,
            "action": action_dict,
            "execution": execution_result,
            "verification": verification_result
        }
        self.action_history.append(entry)

    def log_failure(self, action: str, target: Any, reason: str):
        """Records a failed attempt into failure memory so the decision engine can adapt."""
        attempt_count = sum(
            1 for f in self.failure_memory
            if f.get("action") == action and str(f.get("target")) == str(target)
        ) + 1

        self.failure_memory.append({
            "action": action,
            "target": target,
            "reason": reason,
            "attempt": attempt_count,
            "timestamp": time.time()
        })

    def has_failed_previously(self, action: str, target: Any) -> bool:
        """Checks whether this exact action and target previously failed in this session."""
        for f in self.failure_memory:
            if f.get("action") == action and str(f.get("target")) == str(target):
                return True
        return False

    def is_step_limit_reached(self) -> bool:
        """Prevents runaway infinite automation loops."""
        return len(self.action_history) >= self.max_steps or len(self.failure_memory) >= self.max_failures

    def get_session_summary(self) -> Dict[str, Any]:
        """Provides full audit summary of the task execution."""
        return {
            "is_active": self.is_active,
            "current_goal": self.current_goal,
            "steps_taken": len(self.action_history),
            "failures_recorded": len(self.failure_memory),
            "duration_seconds": round(time.time() - self.start_time, 2) if self.start_time else 0.0,
            "history": self.action_history,
            "failure_memory": self.failure_memory
        }
