"""Utility for using Google Gemini with LangChain compatibility."""
import google.generativeai as genai
from typing import List, Optional, Any, Iterator
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.callbacks import CallbackManagerForLLMRun


class GeminiLLM(BaseChatModel):
    """LangChain-compatible wrapper for Google Gemini."""
    
    model: str = "gemini-1.5-pro"
    api_key: str = None
    temperature: float = 0.7
    
    def __init__(self, model: str = "gemini-1.5-pro", api_key: str = None, temperature: float = 0.7, **kwargs):
        super().__init__(**kwargs)
        self.model = model
        self.api_key = api_key
        self.temperature = temperature
        if api_key:
            genai.configure(api_key=api_key)
        self._client = None
    
    @property
    def client(self):
        """Lazy initialization of Gemini client."""
        if self._client is None:
            self._client = genai.GenerativeModel(self.model)
        return self._client
    
    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Generate response from messages."""
        prompt = self._format_messages(messages)
        try:
            response = self.client.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(temperature=self.temperature)
            )
            return self._create_result(response)
        except Exception as e:
            raise Exception(f"Gemini API error: {str(e)}")
    
    def _format_messages(self, messages: List[BaseMessage]) -> str:
        """Convert LangChain messages to text prompt."""
        parts = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                parts.append(f"System: {msg.content}")
            elif isinstance(msg, HumanMessage):
                parts.append(f"Human: {msg.content}")
            elif isinstance(msg, AIMessage):
                parts.append(f"Assistant: {msg.content}")
            else:
                content = msg.content if hasattr(msg, 'content') else str(msg)
                parts.append(str(content))
        return "\n".join(parts)
    
    def _create_result(self, response) -> ChatResult:
        """Create LangChain ChatResult from Gemini response."""
        try:
            text = response.text if hasattr(response, 'text') else str(response)
        except Exception:
            text = str(response)
        message = AIMessage(content=text)
        generation = ChatGeneration(message=message)
        return ChatResult(generations=[generation])
    
    @property
    def _llm_type(self) -> str:
        return "gemini"
    
    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Iterator[ChatGeneration]:
        """Stream responses (not implemented for now)."""
        result = self._generate(messages, stop=stop, run_manager=run_manager, **kwargs)
        yield result.generations[0]

