# Top-level backward compatibility facade for the J.A.R.V.I.S. Decision Engine.
# Delegates all decision execution to desktop_engine.decision_engine.DecisionEngine.

from desktop_engine.decision_engine import DecisionEngine as ActualDecisionEngine

class DecisionEngine:
    def __init__(self, config=None, llm_callable=None):
        self._actual_engine = ActualDecisionEngine(config, llm_callable)

    def get_next_action(self, goal, desktop_state, action_history=None, failure_memory=None, observation=None, perception=None):
        """
        Reasons over the current desktop state and selects the single best next action.
        """
        return self._actual_engine.get_next_action(
            goal=goal,
            desktop_state=desktop_state,
            action_history=action_history,
            failure_memory=failure_memory,
            observation=observation,
            perception=perception
        )
