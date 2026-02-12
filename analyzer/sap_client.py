"""SAP AI Core Converse API クライアント。

OAuth2クライアント認証でトークンを取得し、
Converse APIおよびTool Calling APIを呼び出す。
"""

import requests

from analyzer.config import AppConfig


class SAPAICoreClient:
    """SAP AI Core Claude クライアント。"""

    def __init__(self, config: AppConfig):
        self.auth_url = config.auth_url
        self.client_id = config.client_id
        self.client_secret = config.client_secret
        self.base_url = config.base_url
        self.resource_group = config.resource_group
        self.deployment_id = config.deployment_id
        self._access_token: str | None = None

    def _get_access_token(self) -> str:
        """OAuth2クライアント認証でアクセストークンを取得する。"""
        if self._access_token:
            return self._access_token

        token_url = f"{self.auth_url}/oauth/token"
        response = requests.post(
            token_url,
            auth=(self.client_id, self.client_secret),
            data={"grant_type": "client_credentials"},
        )
        if response.status_code != 200:
            raise Exception(f"トークン取得失敗: {response.status_code}")

        self._access_token = response.json()["access_token"]
        return self._access_token

    def converse(
        self,
        prompt: str,
        tools: list[dict] | None = None,
        max_tokens: int = 16384,
        temperature: float = 0.7,
    ) -> dict:
        """Converse APIを呼び出す。"""
        token = self._get_access_token()
        url = f"{self.base_url}/inference/deployments/{self.deployment_id}/converse"

        headers = {
            "Authorization": f"Bearer {token}",
            "AI-Resource-Group": self.resource_group,
            "Content-Type": "application/json",
        }

        payload = {
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": prompt}]}
            ],
            "inferenceConfig": {
                "maxTokens": max_tokens,
                "temperature": temperature,
            },
        }

        if tools:
            payload["toolConfig"] = {"tools": tools, "toolChoice": {"any": {}}}

        response = requests.post(url, headers=headers, json=payload)
        if response.status_code != 200:
            raise Exception(
                f"API呼び出し失敗: {response.status_code} - {response.text}"
            )

        return response.json()

    def converse_with_tools(
        self,
        prompt: str,
        tools: list[dict],
        max_tokens: int = 16384,
        temperature: float = 0.7,
    ) -> dict:
        """Tool Calling付きConverse APIを呼び出し、ツール結果を返す。"""
        result = self.converse(prompt, tools, max_tokens, temperature)

        tool_calls: dict = {}
        for block in (
            result.get("output", {}).get("message", {}).get("content", [])
        ):
            if "toolUse" in block:
                tool_use = block["toolUse"]
                tool_calls[tool_use.get("name")] = tool_use.get("input", {})

        return tool_calls
