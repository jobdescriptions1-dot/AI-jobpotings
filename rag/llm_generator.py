import os
import logging
from typing import Dict, Any, List
from groq import Groq
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class RAGLLMGenerator:
    """Generates natural language answers for RAG query results"""
    
    def __init__(self):
        """Initialize the LLM generator"""
        load_dotenv()
        self.api_key = os.getenv('GROQ_API_KEY')
        self.model = "llama-3.1-8b-instant"
        
        if self.api_key:
            try:
                self.client = Groq(api_key=self.api_key)
                logger.info("RAG LLM Generator initialized with Groq")
            except Exception as e:
                logger.error(f"Failed to initialize Groq client: {e}")
                self.client = None
        else:
            logger.warning("GROQ_API_KEY not found. LLM generation disabled.")
            self.client = None
            
    def generate_answer(self, query: str, results_response: Dict[str, Any]) -> str:
        """
        Generate a natural language answer based on the query and results.
        
        Args:
            query: The user's original question
            results_response: The dictionary returned by QueryEngine.process_query
            
        Returns:
            String containing the formatted natural language answer
        """
        if not self.client:
            return "AI enhanced answering is unavailable (Missing API Key)."
            
        try:
            # 1. Prepare Context from Results
            context_text = self._prepare_context(results_response)
            
            # 2. Construct Prompt
            system_prompt = """You are a helpful AI assistant for a job search system.
            Your goal is to answer the user's question directly and concisely based ONLY on the provided search results.
            
            FORMATTING RULES:
            - Use BOLD highlights for key numbers or important terms (e.g., **20 jobs**).
            - Use bullet points for lists.
            - Keep it professional but conversational.
            - If no jobs are found, politely say so and suggest broader terms.
            - Do NOT make up information not present in the results.
            - Return ONLY the answer text, no JSON or code blocks."""
            
            user_prompt = f"""
            USER QUESTION: "{query}"
            
            SEARCH RESULTS SUMMARY:
            {context_text}
            
            Please provide a helpful, natural language answer to the user's question based on these results.
            """
            
            # 3. Call LLM
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.model,
                temperature=0.3,
                max_tokens=500,
            )
            
            return chat_completion.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generating LLM answer: {e}")
            return "I found some results, but couldn't generate a summary description for them."

    def _prepare_context(self, results_data: Dict) -> str:
        """Convert result dict into a text summary for the LLM"""
        
        # Handle Stats/Aggregation Response
        if results_data.get('question_type') == 'state_stats':
            summary = results_data.get('summary', '')
            results = results_data.get('results', [])
            stats_text = "\n".join([f"- {r['state']}: {r['count']} jobs" for r in results[:10]])
            return f"Stats Summary: {summary}\n\nTop States:\n{stats_text}"
            
        # Handle Standard Job Search Response
        total = results_data.get('total_results', 0)
        results = results_data.get('results', [])
        
        if total == 0:
            return "No results found."
            
        context = f"Found {total} total jobs.\n\nTop {len(results)} matches:\n"
        
        for i, job in enumerate(results, 1):
            title = job.get('title', 'Unknown Title')
            state = job.get('state', 'Unknown State')
            loc = job.get('location', 'Unknown Location')
            # Use content_preview if available, otherwise description snippet
            desc = job.get('content_preview', '') or job.get('description', '')[:200]
            
            context += f"{i}. {title}\n   Location: {loc} ({state})\n   Snippet: {desc}...\n\n"
            
        return context
