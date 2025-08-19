import abc
from typing import Any

import litellm
import tenacity

from app.utils.prompts import templates

from .aClasses import AInfrastructure


class ATextSummarizer(AInfrastructure, abc.ABC):
    @abc.abstractmethod
    async def summarize(self, content: str) -> str:
        raise NotImplementedError


class TextSummarizer(ATextSummarizer):
    def __init__(self, model: str):
        self.model = model

    async def summarize(self, content: str) -> str:
        system_prompt = templates.summary.instructions
        prompt = templates.summary.prompt.render(text=content)

        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}]

        summarized_content = await self._get_llm_estimation(messages)

        return summarized_content

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        retry=tenacity.retry_if_exception_type(Exception),
    )
    async def _get_llm_estimation(self, messages: list[dict[str, Any]]) -> str:
        try:
            response = await litellm.acompletion(
                model=self.model,
                messages=messages,
                temperature=0.3,
            )
        except Exception as e:
            print(e)
            raise e

        response_raw_content: str = response["choices"][0]["message"]["content"]

        return response_raw_content
