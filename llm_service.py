from providers.provider_manager import ProviderManager

class LLMService:
    @staticmethod
    def query_llm_with_fallback(config, system_prompt, messages_history, user_prompt, response_format_json=False):
        """
        Delegates queries to the centralized ProviderManager chat handler.
        """
        return ProviderManager.chat(
            system_prompt=system_prompt,
            messages_history=messages_history,
            user_prompt=user_prompt,
            response_format_json=response_format_json
        )
