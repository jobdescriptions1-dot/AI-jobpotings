"""
Hybrid search query engine combining semantic + structured search
"""
from typing import List, Dict, Any, Optional, Tuple
import logging
from .llm_generator import RAGLLMGenerator
from datetime import datetime, timedelta
import re
import json

logger = logging.getLogger(__name__)

class QueryEngine:
    """Hybrid search engine for RAG system"""
    
    def __init__(self, chroma_manager, sqlite_manager):
        self.chroma_manager = chroma_manager
        self.sqlite_manager = sqlite_manager
        self.llm_generator = RAGLLMGenerator()
    
    def process_query(self, query: str) -> Dict:
        """
        Process a natural language query
        
        Args:
            query: Natural language query
            
        Returns:
            Dict with query results
        """
        try:
            # Step 1: Parse query for intent and filters
            parsed_query = self._parse_natural_language(query)
            
            # --- Handle Stats Aggregation ---
            if parsed_query.get('question_type') == 'state_stats':
                state_stats = self.sqlite_manager.get_state_stats()
                # Sort by count desc
                state_stats.sort(key=lambda x: x[1], reverse=True)
                
                total_states = len(state_stats)
                states_str = ", ".join([f"{state} ({count})" for state, count in state_stats])
                
                raw_response = {
                    'query': query,
                    'parsed_intent': 'get_stats',
                    'question_type': 'state_stats',
                    'filters_applied': {},
                    'total_results': total_states,
                    'results': [{'state': s, 'count': c, 'title': f"{s} State Stats"} for s, c in state_stats],
                    'summary': f"Found {total_states} states with active jobs: {states_str}"
                }
                
                # Add LLM Answer
                raw_response['answer'] = self.llm_generator.generate_answer(query, raw_response)
                return raw_response
            # --------------------------------
            
            # Step 2: Extract structured filters
            filters = parsed_query.get('filters', {})
            
            # Step 3: Perform hybrid search
            structured_results = []
            semantic_results = []
            
            # Only do structured search if we have meaningful filters
            if filters and not self._should_skip_structured(filters):
                structured_results = self.sqlite_manager.search_jobs(
                    filters=filters,
                    limit=20
                )
            
            # Always do semantic search for context
            semantic_results = self.chroma_manager.search_similar_jobs(
                query=query,
                n_results=10,
                filter_conditions=self._convert_to_chroma_filters(filters)
            )
            
            # Step 4: Combine and rank results
            combined_results = self._combine_results(
                structured_results, 
                semantic_results,
                query
            )
            
            # Step 5: Generate response
            response = self._generate_response(
                query=query,
                parsed_query=parsed_query,
                results=combined_results
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Query processing error: {e}")
            return {
                'error': str(e),
                'query': query,
                'results': []
            }
    
    def _parse_natural_language(self, query: str) -> Dict:
        """Parse natural language query for intent and filters"""
        query_lower = query.lower()
        result = {
            'original_query': query,
            'intent': 'search_jobs',
            'filters': {},
            'question_type': 'general'
        }
        
        # Extract state
        states = {
            'georgia': 'GA', 'texas': 'TX', 'virginia': 'VA', 
            'north carolina': 'NC', 'nc': 'NC', 'florida': 'FL',
            'california': 'CA', 'new york': 'NY'
        }
        
        for state_name, state_code in states.items():
            if state_name in query_lower:
                result['filters']['state'] = state_code
                break
        
        # Extract work mode
        work_modes = ['hybrid', 'remote', 'local', 'onsite']
        for mode in work_modes:
            if mode in query_lower:
                result['filters']['work_mode'] = mode.title()
                break
        
        # Extract date ranges
        date_filters = self._extract_date_filters(query_lower)
        result['filters'].update(date_filters)
        
        # Extract skill mentions
        skill_keywords = ['skill', 'experience', 'requires', 'needs', 'with']
        skill_patterns = [
            r'with\s+(\w+\s+\w+)\s+experience',
            r'requires?\s+(\w+\s*\w*)',
            r'skill\sin\s+(\w+)',
            r'(\w+\s+developer)',
            r'(\w+\s+analyst)',
            r'(\w+\s+manager)'
        ]
        
        for pattern in skill_patterns:
            match = re.search(pattern, query_lower)
            if match:
                skill = match.group(1).strip()
                if len(skill) > 2:
                    result['filters']['skill'] = skill
                    break
        
        # Extract job title patterns
        title_patterns = [
            r'(\w+\s+developer)',
            r'(\w+\s+analyst)',
            r'(\w+\s+manager)',
            r'(\w+\s+engineer)',
            r'(\w+\s+consultant)'
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, query_lower)
            if match:
                title = match.group(1).strip()
                if not result['filters'].get('skill'):
                    result['filters']['title'] = title
                if not result['filters'].get('skill'):
                    result['filters']['title'] = title
                break
        
        # Check for state aggregation intent
        state_keywords = ['how many states', 'list states', 'list of states', 'states are present', 'count by state', 'states count']
        for keyword in state_keywords:
            if keyword in query_lower:
                result['question_type'] = 'state_stats'
                result['intent'] = 'get_stats'
                break
        
        # Check for Odoo posting queries
        odoo_keywords = ['posted', 'posting', 'odoo', 'uploaded', 'submitted to odoo']
        for keyword in odoo_keywords:
            if keyword in query_lower:
                result['intent'] = 'search_odoo_postings'
                result['question_type'] = 'odoo_status'
                break
        
        # Check for submission count queries
        if 'submission' in query_lower or 'submissions' in query_lower:
            result['question_type'] = 'submission_count'
            # Try to extract number
            num_match = re.search(r'(\d+)\+?\s+submissions?', query_lower)
            if num_match:
                result['filters']['min_submissions'] = int(num_match.group(1))
        
        # Check for Excel/tracking queries
        excel_keywords = ['tracking', 'excel', 'report', 'submission count']
        for keyword in excel_keywords:
            if keyword in query_lower:
                result['question_type'] = 'tracking_info'
                break
        
        return result
    
    def _extract_date_filters(self, query: str) -> Dict:
        """Extract date-related filters from query"""
        filters = {}
        today = datetime.now().date()
        
        # Today
        if 'today' in query:
            filters['due_date_after'] = today.isoformat()
            filters['due_date_before'] = today.isoformat()
        
        # Tomorrow
        elif 'tomorrow' in query:
            tomorrow = today + timedelta(days=1)
            filters['due_date_after'] = tomorrow.isoformat()
            filters['due_date_before'] = tomorrow.isoformat()
        
        # This week
        elif 'this week' in query:
            start_of_week = today - timedelta(days=today.weekday())
            end_of_week = start_of_week + timedelta(days=6)
            filters['due_date_after'] = start_of_week.isoformat()
            filters['due_date_before'] = end_of_week.isoformat()
        
        # Next week
        elif 'next week' in query:
            start_of_next_week = today + timedelta(days=(7 - today.weekday()))
            end_of_next_week = start_of_next_week + timedelta(days=6)
            filters['due_date_after'] = start_of_next_week.isoformat()
            filters['due_date_before'] = end_of_next_week.isoformat()
        
        # This month
        elif 'this month' in query:
            start_of_month = today.replace(day=1)
            next_month = start_of_month.replace(month=start_of_month.month+1) if start_of_month.month < 12 else start_of_month.replace(year=start_of_month.year+1, month=1)
            end_of_month = next_month - timedelta(days=1)
            filters['due_date_after'] = start_of_month.isoformat()
            filters['due_date_before'] = end_of_month.isoformat()
        
        # Last week/month (for Odoo postings)
        elif 'last week' in query:
            start_of_last_week = today - timedelta(days=today.weekday() + 7)
            end_of_last_week = start_of_last_week + timedelta(days=6)
            filters['posted_after'] = start_of_last_week.isoformat()
            filters['posted_before'] = end_of_last_week.isoformat()
        
        elif 'last month' in query:
            first_day_of_last_month = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
            last_day_of_last_month = today.replace(day=1) - timedelta(days=1)
            filters['posted_after'] = first_day_of_last_month.isoformat()
            filters['posted_before'] = last_day_of_last_month.isoformat()
        
        return filters
    
    def _should_skip_structured(self, filters: Dict) -> bool:
        """Determine if structured search should be skipped"""
        # Skip if only generic filters
        if len(filters) == 1 and 'skill' in filters:
            return False
        return len(filters) == 0
    
    def _convert_to_chroma_filters(self, filters: Dict) -> Optional[Dict]:
        """Convert filters to ChromaDB format"""
        if not filters:
            return None
        
        chroma_filter = {}
        
        if 'state' in filters:
            chroma_filter['state'] = filters['state']
        
        if 'work_mode' in filters:
            chroma_filter['work_mode'] = filters['work_mode']
        
        return chroma_filter if chroma_filter else None
    
    def _combine_results(self, structured_results: List, 
                        semantic_results: List, query: str) -> List[Dict]:
        """Combine results from both sources"""
        combined = []
        
        # Add structured results
        for result in structured_results:
            result['source'] = 'structured'
            result['relevance_score'] = 0.8
            combined.append(result)
        
        # Add semantic results
        for result in semantic_results:
            # Check if this job already exists in structured results
            job_id = result.get('metadata', {}).get('job_id')
            
            if job_id:
                # Check if already in combined
                already_exists = False
                for existing in combined:
                    if existing.get('job_id') == job_id:
                        already_exists = True
                        # Update with semantic info
                        existing['semantic_similarity'] = result.get('similarity_score', 0)
                        existing['source'] = 'hybrid'
                        break
                
                if not already_exists:
                    combined.append({
                        'source': 'semantic',
                        'job_id': job_id,
                        'title': result.get('metadata', {}).get('title', ''),
                        'state': result.get('metadata', {}).get('state', ''),
                        'work_mode': result.get('metadata', {}).get('work_mode', ''),
                        'similarity_score': result.get('similarity_score', 0),
                        'content_preview': result.get('document', '')[:200] + '...' if result.get('document') else ''
                    })
        
        # Sort by relevance
        combined.sort(key=lambda x: x.get('similarity_score', x.get('relevance_score', 0)), reverse=True)
        
        return combined[:15]  # Return top 15
    
    def _generate_response(self, query: str, parsed_query: Dict, results: List[Dict]) -> Dict:
        """Generate response for the query"""
        response = {
            'query': query,
            'parsed_intent': parsed_query['intent'],
            'question_type': parsed_query['question_type'],
            'filters_applied': parsed_query.get('filters', {}),
            'total_results': len(results),
            'results': results[:10],  # Return top 10
            'summary': self._generate_summary(results, parsed_query)
        }
        
        # Generate LLM Answer
        response['answer'] = self.llm_generator.generate_answer(query, response)
        
        return response
    
    def _generate_summary(self, results: List[Dict], parsed_query: Dict) -> str:
        """Generate a natural language summary"""
        if not results:
            return "No jobs found matching your criteria."
        
        filters = parsed_query.get('filters', {})
        
        # Count by state
        state_counts = {}
        for result in results:
            state = result.get('state')
            if state:
                state_counts[state] = state_counts.get(state, 0) + 1
        
        # Generate summary
        summary_parts = []
        
        if state_counts:
            state_str = ', '.join([f"{state} ({count})" for state, count in state_counts.items()])
            summary_parts.append(f"Found {len(results)} jobs in {state_str}")
        
        if filters.get('work_mode'):
            summary_parts.append(f"Work mode: {filters['work_mode']}")
        
        if filters.get('skill'):
            summary_parts.append(f"Skill: {filters['skill']}")
        
        # Add top job titles if available
        titles = []
        for result in results[:3]:
            title = result.get('title')
            if title and title not in titles:
                titles.append(title)
        
        if titles:
            summary_parts.append(f"Positions include: {', '.join(titles)}")
        
        return '. '.join(summary_parts)