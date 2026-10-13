# LLM Service with multi-provider support
import os
import json
import httpx
from typing import Optional, Dict, Any, List
from backend.app.core.config import get_settings


class LLMService:
    """Unified LLM client supporting OpenAI-compatible, Anthropic, Gemini, and Ollama."""

    def __init__(self):
        settings = get_settings()
        self.api_key = settings.LLM_API_KEY or os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("GEMINI_API_KEY") or ""
        self.base_url = settings.LLM_BASE_URL
        self.model = settings.LLM_MODEL
        self.provider = settings.LLM_PROVIDER.lower()
        self.timeout = 120.0

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            if self.provider == "anthropic":
                headers["x-api-key"] = self.api_key
                headers["anthropic-version"] = "2023-06-01"
            elif self.provider == "gemini":
                # Gemini uses API key as query param
                pass
            else:
                headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _get_url(self, endpoint: str) -> str:
        if self.provider == "gemini":
            # Gemini: base_url should be like https://generativelanguage.googleapis.com/v1beta
            return f"{self.base_url}/models/{self.model}:{endpoint}?key={self.api_key}"
        elif self.provider == "ollama":
            # Ollama: base_url like http://localhost:11434
            return f"{self.base_url}/api/{endpoint}"
        else:
            # OpenAI-compatible
            return f"{self.base_url}/{endpoint}"

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: int = 2048) -> str:
        """Send chat completion request."""
        if self.provider == "anthropic":
            return self._chat_anthropic(messages, temperature, max_tokens)
        elif self.provider == "gemini":
            return self._chat_gemini(messages, temperature, max_tokens)
        elif self.provider == "ollama":
            return self._chat_ollama(messages, temperature, max_tokens)
        else:
            return self._chat_openai_compatible(messages, temperature, max_tokens)

    def _chat_openai_compatible(self, messages: List[Dict[str, str]], temperature: float, max_tokens: int) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(self._get_url("chat/completions"), headers=self._get_headers(), json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    def _chat_anthropic(self, messages: List[Dict[str, str]], temperature: float, max_tokens: int) -> str:
        # Convert to Anthropic format
        system = ""
        user_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                user_messages.append({"role": msg["role"], "content": msg["content"]})

        payload = {
            "model": self.model,
            "messages": user_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system:
            payload["system"] = system

        headers = self._get_headers()
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(self._get_url("messages"), headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["content"][0]["text"]

    def _chat_gemini(self, messages: List[Dict[str, str]], temperature: float, max_tokens: int) -> str:
        # Convert to Gemini format
        contents = []
        for msg in messages:
            role = "user" if msg["role"] in ("user", "system") else "model"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(self._get_url("generateContent"), headers=self._get_headers(), json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]

    def _chat_ollama(self, messages: List[Dict[str, str]], temperature: float, max_tokens: int) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "options": {"temperature": temperature, "num_predict": max_tokens},
            "stream": False,
        }
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(self._get_url("chat"), headers=self._get_headers(), json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["message"]["content"]

    def generate(self, prompt: str, system: str = "You are a helpful AI assistant.", temperature: float = 0.7) -> str:
        """Generate response from a single prompt."""
        return self.chat([
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ], temperature=temperature)

    def classify(self, text: str, categories: List[str], instructions: str = "") -> Dict[str, Any]:
        """Classify text into categories."""
        sep = ", "
        prompt = f"{instructions}Classify: {text}\nCategories: {sep.join(categories)}\nRespond as JSON: {{\"category\": \"...\", \"confidence\": 0.95, \"reasoning\": \"...\"}}"
        raw = self.chat([
            {"role": "system", "content": "Respond only with valid JSON."},
            {"role": "user", "content": prompt},
        ], temperature=0.1)
        start, end = raw.find("{"), raw.rfind("}") + 1
        try:
            return json.loads(raw[start:end])
        except Exception:
            return {"category": "unknown", "confidence": 0.0, "reasoning": raw}

    def analyze_costs(self, cost_data: Dict[str, Any], recommendations: List[Dict[str, Any]]) -> str:
        """Generate natural language cost analysis."""
        prompt = f"""Analyze the following cloud cost data and optimization recommendations.
Provide a concise executive summary highlighting:
1. Top cost drivers
2. Biggest waste sources
3. Priority actions with estimated savings
4. Risk considerations

Cost Data:
{json.dumps(cost_data, indent=2)}

Recommendations:
{json.dumps(recommendations, indent=2)}

Respond in plain text, business-focused, no markdown."""
        return self.generate(prompt, system="You are a FinOps expert analyzing cloud costs.")

    def generate_optimization_plan(self, analysis_data: Dict[str, Any], target_savings: float) -> str:
        """Generate prioritized optimization plan."""
        prompt = f"""Create a prioritized optimization plan to achieve ${target_savings:,.0f}/month savings.

Analysis Data:
{json.dumps(analysis_data, indent=2)}

Provide:
1. Prioritized action list (high/medium/low priority)
2. Estimated savings per action
3. Implementation effort (low/medium/high)
4. Risk level (low/medium/high)
5. Timeline (weeks)
6. Total projected savings

Format as structured text, no markdown."""
        return self.generate(prompt, system="You are a FinOps expert creating cloud optimization plans.")

    def answer_question(self, question: str, context: Dict[str, Any]) -> str:
        """Answer natural language cost question."""
        prompt = f"""Answer the following question based on the provided cost analysis context.

Question: {question}

Context:
{json.dumps(context, indent=2)}

Provide a direct, data-grounded answer. If the context doesn't contain enough information, say so.
Do not hallucinate numbers. Cite specific findings from the context."""
        return self.generate(prompt, system="You are a FinOps assistant answering cost questions.")


def create_llm_service() -> LLMService:
    return LLMService()