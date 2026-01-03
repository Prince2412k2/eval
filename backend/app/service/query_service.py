from typing import AsyncGenerator
from groq import AsyncGroq

RAG_PROMPT = """
You are an intelligent and helpful AI assistant. Your goal is to provide accurate and concise answers based *only* on the provided context.

Here are the rules you must follow:
1.  **Answer from Context Only**: Use *only* the information present in the "Context" section below to answer the user's question. Do not use any outside knowledge.
2.  **Faithful Summarization/Quoting**: If the context directly answers the question, quote or summarize it accurately.
3.  **Handle Missing Information**: If the context does not contain enough information to answer the question, state clearly that you do not have that information. Do not make up answers.
4.  **Conciseness**: Provide answers that are as concise as possible while still being comprehensive. Avoid unnecessary verbosity.
5.  **Avoid Self-Reference**: Do not mention that you are using context or that you are an AI. Just provide the answer.

Context:
{context}
"""


class QueryService:
    @staticmethod
    async def query(
        que: str, context: str, groq: AsyncGroq
    ) -> AsyncGenerator[str, None]:
        """
        Streams model responses token-by-token from Groq.
        Yields each content chunk as soon as it arrives.
        """
        prompt = RAG_PROMPT.format(context=context)

        resp = await groq.chat.completions.create(
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": que},
            ],
            # model="llama-3.1-8b-instant",
            model="openai/gpt-oss-120b",
            stream=True,
        )

        async for chunk in resp:
            delta = chunk.choices[0].delta
            content = delta.content or ""
            if content:
                yield content
