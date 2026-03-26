from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from openai import OpenAI

from minuteflow.config import ModelEndpointConfig
from minuteflow.utils import guess_mime_type


class OpenAICompatibleClient:
    def __init__(self, config: ModelEndpointConfig) -> None:
        if not config.is_configured:
            raise ValueError("Model endpoint is not fully configured")
        self._config = config
        self._client = OpenAI(
            base_url=config.base_url,
            api_key=config.api_key or "not-required",
        )

    def text_completion(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        response = self._client.chat.completions.create(
            model=self._config.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )
        message = response.choices[0].message.content or ""
        return {
            "model": self._config.model,
            "content": message,
            "raw": response.model_dump(),
        }

    def vision_completion(self, system_prompt: str, user_prompt: str, image_paths: list[str]) -> dict[str, Any]:
        content: list[dict[str, Any]] = [{"type": "text", "text": user_prompt}]
        for image_path in image_paths:
            image_bytes = Path(image_path).read_bytes()
            encoded = base64.b64encode(image_bytes).decode("ascii")
            mime = guess_mime_type(image_path)
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime};base64,{encoded}"},
                }
            )
        response = self._client.chat.completions.create(
            model=self._config.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content},
            ],
            temperature=0.2,
        )
        message = response.choices[0].message.content or ""
        return {
            "model": self._config.model,
            "content": message,
            "raw": response.model_dump(),
        }

