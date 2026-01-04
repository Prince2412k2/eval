from typing import AsyncGenerator, List, Dict
from groq import AsyncGroq
import json

RAG_PROMPT = """
You are a helpful policy assistant. Your job is to answer questions about policies using the provided context.

Instructions:
1. **Use the Context**: Answer based on the information in the context below. Look for relevant details even if the wording doesn't match exactly.

2. **Be Helpful**: If the user's question is related to information in the context, provide that information. For example:
   - "How much will I spend at work?" → Look for information about work-related expenses, reimbursements, or costs
   - "What's the refund policy?" → Provide details about returns, refunds, and related procedures

3. **Interpret Intent**: Understand what the user is really asking. Common questions about policies include:
   - Costs, fees, expenses, reimbursements
   - Time limits, deadlines, durations
   - Eligibility, requirements, conditions
   - Procedures, processes, steps

4. **Provide Complete Answers**: Include all relevant details like amounts, timeframes, conditions, and exceptions.

5. **Use Markdown Formatting**: Format your response using markdown for better readability:
   - Use **bold** for important terms or amounts
   - Use bullet points or numbered lists for multiple items
   - Use headings (##) to organize longer responses
   - Use code blocks for specific values or references

6. **Be Clear About Limitations**: If the context truly doesn't contain relevant information, say: "I don't have information about that in the available policy documents."

7. **Stay Grounded**: Don't make up information. Only use what's in the context.

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
    
    @staticmethod
    async def extract_citations_structured(
        query: str,
        chunks: List[Dict],
        groq: AsyncGroq
    ) -> List[Dict]:
        """
        Use fast LLM to extract structured citations from context chunks.
        
        Args:
            query: User's question
            chunks: Context chunks to extract citations from
            groq: Groq client
            
        Returns:
            List of citation dicts with chunk_index, text_span, claim_text, citation_type
        """
        from app.service.citation_service import CitationService
        
        # Build prompt for citation extraction
        prompt = CitationService.build_citation_extraction_prompt(query, chunks)
        
        try:
            # Use fast model with JSON mode for structured output
            resp = await groq.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.1-8b-instant",  # Fast & cheap model
                response_format={"type": "json_object"},  # Structured JSON output
                temperature=0.1,  # Low temperature for consistency
            )
            
            # Parse JSON response
            content = resp.choices[0].message.content
            citations_data = json.loads(content)
            
            # Return citations array
            return citations_data.get("citations", [])
            
        except json.JSONDecodeError as e:
            # Fallback: return empty list if JSON parsing fails
            print(f"Citation extraction JSON parse error: {e}")
            return []
        except Exception as e:
            # Catch any other errors
            print(f"Citation extraction error: {e}")
            return []
