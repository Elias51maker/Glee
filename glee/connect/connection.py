"""Connection class for making API calls."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:
    from glee.connect.storage import Credential


@dataclass
class ChatResponse:
    """Response from a chat request."""

    content: str
    model: str = ""
    raw: dict[str, Any] | None = None


class Connection:
    """A connection to an AI provider.

    Usage:
        from glee.connect import ConnectionStorage, Connection

        cred = ConnectionStorage.get("abc123")
        conn = Connection(cred)
        response = conn.chat("Say Hello")
        print(response.content)
    """

    def __init__(self, credential: Credential):
        self.credential = credential

    @property
    def sdk(self) -> str:
        return self.credential.sdk

    @property
    def vendor(self) -> str:
        return self.credential.vendor

    @property
    def is_oauth(self) -> bool:
        return self.credential.type == "oauth"

    def chat(self, message: str, max_tokens: int = 100) -> ChatResponse:
        """Send a chat message and get a response.

        Args:
            message: The message to send
            max_tokens: Maximum tokens in response

        Returns:
            ChatResponse with the assistant's reply
        """
        c = self.credential

        if c.sdk == "openai":
            return self._chat_openai(message, max_tokens)
        elif c.sdk == "openrouter":
            return self._chat_openrouter(message, max_tokens)
        elif c.sdk == "anthropic":
            return self._chat_anthropic(message, max_tokens)
        elif c.sdk == "vertex":
            return self._chat_vertex(message, max_tokens)
        elif c.sdk == "bedrock":
            return self._chat_bedrock(message, max_tokens)
        else:
            raise ValueError(f"Unknown SDK: {c.sdk}")

    def _chat_openai(self, message: str, max_tokens: int) -> ChatResponse:
        """Chat using OpenAI-compatible API."""
        from glee.connect.storage import OAuthCredential

        c = self.credential

        if isinstance(c, OAuthCredential):
            token = c.access

            if c.vendor == "github":
                # GitHub Copilot
                headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
                resp = httpx.post(
                    "https://api.githubcopilot.com/chat/completions",
                    headers=headers,
                    json={"model": "gpt-4o", "max_tokens": max_tokens, "messages": [{"role": "user", "content": message}]},
                    timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()
                return ChatResponse(
                    content=data["choices"][0]["message"]["content"].strip(),
                    model=data.get("model", ""),
                    raw=data,
                )

            elif c.vendor == "openai":
                # Codex OAuth - uses ChatGPT backend API with streaming
                url = "https://chatgpt.com/backend-api/codex/responses"
                headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
                if c.account_id:
                    headers["ChatGPT-Account-Id"] = c.account_id

                json_body = {
                    "model": "gpt-5.1-codex-mini",
                    "instructions": "You are a helpful assistant.",
                    "input": [{"role": "user", "content": message}],
                    "store": False,
                    "stream": True,
                }

                with httpx.stream("POST", url, headers=headers, json=json_body, timeout=30) as response:
                    if response.status_code == 200:
                        import json

                        content = ""
                        for chunk in response.iter_lines():
                            if chunk and chunk.startswith("data:"):
                                try:
                                    data = json.loads(chunk[5:].strip())
                                    if data.get("type") == "response.output_text.delta":
                                        content += data.get("delta", "")
                                except json.JSONDecodeError:
                                    pass
                        return ChatResponse(content=content or "OK", model="gpt-5.1-codex-mini")
                    else:
                        error_text = response.read().decode()[:200]
                        raise Exception(f"HTTP {response.status_code}: {error_text}")

            else:
                raise ValueError(f"Unknown OAuth vendor: {c.vendor}")

        else:
            # API key credentials (c is APICredential here)
            base_url = (c.base_url or "https://api.openai.com/v1").rstrip("/")  # type: ignore[union-attr]
            resp = httpx.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {c.key}", "Content-Type": "application/json"},  # type: ignore[union-attr]
                json={"model": "gpt-5-nano", "max_tokens": max_tokens, "messages": [{"role": "user", "content": message}]},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            return ChatResponse(
                content=data["choices"][0]["message"]["content"].strip(),
                model=data.get("model", ""),
                raw=data,
            )

    def _chat_openrouter(self, message: str, max_tokens: int) -> ChatResponse:
        """Chat using OpenRouter SDK."""
        from openrouter import OpenRouter

        from glee.connect.storage import APICredential

        c = self.credential
        if not isinstance(c, APICredential):
            raise ValueError("OpenRouter requires API key credential")

        with OpenRouter(api_key=c.key) as client:
            response = client.chat.send(
                model="minimax/minimax-m2",
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": message}],
            )

        # Extract content from response (SDK types are dynamic)
        content = ""
        model_name = ""
        raw = None

        completion = getattr(response, "chat_completion", None)
        if completion:
            choices: list[object] = getattr(completion, "choices", None) or []
            if choices:
                msg = getattr(choices[0], "message", None)
                if msg:
                    content = getattr(msg, "content", "") or ""
            model_name = getattr(completion, "model", "") or ""
            if hasattr(completion, "model_dump"):
                raw = completion.model_dump()

        return ChatResponse(
            content=str(content).strip(),
            model=str(model_name),
            raw=raw,
        )

    def _chat_anthropic(self, message: str, max_tokens: int) -> ChatResponse:
        """Chat using Anthropic API."""
        from glee.connect.storage import APICredential

        c = self.credential
        if not isinstance(c, APICredential):
            raise ValueError("Anthropic requires API key credential")

        resp = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": c.key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={"model": "claude-sonnet-4-20250514", "max_tokens": max_tokens, "messages": [{"role": "user", "content": message}]},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return ChatResponse(
            content=data["content"][0]["text"].strip(),
            model=data.get("model", ""),
            raw=data,
        )

    def _chat_vertex(self, message: str, max_tokens: int) -> ChatResponse:
        """Chat using Vertex AI."""
        from glee.connect.storage import APICredential

        c = self.credential
        if not isinstance(c, APICredential):
            raise ValueError("Vertex requires API credential")

        import google.auth
        import google.auth.transport.requests

        project_id = c.key
        region = c.base_url or "us-central1"

        credentials, _ = google.auth.default()  # type: ignore[attr-defined]
        credentials.refresh(google.auth.transport.requests.Request())  # type: ignore[union-attr]

        resp = httpx.post(
            f"https://{region}-aiplatform.googleapis.com/v1/projects/{project_id}/locations/{region}/publishers/google/models/gemini-2.0-flash:generateContent",
            headers={"Authorization": f"Bearer {credentials.token}", "Content-Type": "application/json"},  # type: ignore[union-attr]
            json={"contents": [{"role": "user", "parts": [{"text": message}]}], "generationConfig": {"maxOutputTokens": max_tokens}},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return ChatResponse(
            content=data["candidates"][0]["content"]["parts"][0]["text"].strip(),
            model="gemini-2.0-flash",
            raw=data,
        )

    def _chat_bedrock(self, message: str, max_tokens: int) -> ChatResponse:
        """Chat using AWS Bedrock."""
        import json

        from glee.connect.storage import APICredential

        c = self.credential
        if not isinstance(c, APICredential):
            raise ValueError("Bedrock requires API credential")

        import boto3

        region = c.base_url or "us-east-1"
        bedrock = boto3.client("bedrock-runtime", region_name=region)  # type: ignore[attr-defined]

        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": message}],
        })
        response = bedrock.invoke_model(modelId="anthropic.claude-sonnet-4-20250514-v1:0", body=body)  # type: ignore[union-attr]
        data = json.loads(response["body"].read())  # type: ignore[union-attr]
        return ChatResponse(
            content=data["content"][0]["text"].strip(),
            model="anthropic.claude-sonnet-4-20250514-v1:0",
            raw=data,
        )
