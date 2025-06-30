#!/usr/bin/env python3
"""
LLM Query Agent for Natural Language Database Interactions

This module provides intelligent natural language to database query conversion
and result interpretation for the DHI Transaction Analytics system.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import re
from dataclasses import dataclass
from enum import Enum

import openai
from anthropic import Anthropic
import requests

logger = logging.getLogger(__name__)

class LLMProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    GROQ = "groq"

class QueryType(Enum):
    SQL = "sql"
    CYPHER = "cypher"
    PYTHON = "python"
    ANALYSIS = "analysis"

@dataclass
class QueryResult:
    success: bool
    query_type: QueryType
    generated_query: str
    raw_results: Any
    interpreted_results: str
    visualization_suggestions: List[str]
    confidence_score: float
    execution_time: float
    error_message: Optional[str] = None

class LLMQueryAgent:
    """
    Intelligent agent for converting natural language queries into database operations
    and interpreting results for users.
    """
    
    def __init__(self, provider: LLMProvider = LLMProvider.OPENAI):
        self.provider = provider
        self.client = None
        self._initialize_client()
        
        # Database schema information
        self.db_schemas = self._load_database_schemas()
        
        # Query templates and examples
        self.query_templates = self._load_query_templates()
        
    def _initialize_client(self):
        """Initialize the LLM client based on provider."""
        try:
            if self.provider == LLMProvider.OPENAI:
                api_key = os.getenv('OPENAI_API_KEY')
                if api_key:
                    openai.api_key = api_key
                    self.client = openai
                else:
                    logger.warning("OpenAI API key not found, falling back to Ollama")
                    self.provider = LLMProvider.OLLAMA
                    self._initialize_ollama()
                    
            elif self.provider == LLMProvider.ANTHROPIC:
                api_key = os.getenv('ANTHROPIC_API_KEY')
                if api_key:
                    self.client = Anthropic(api_key=api_key)
                else:
                    logger.warning("Anthropic API key not found, falling back to Ollama")
                    self.provider = LLMProvider.OLLAMA
                    self._initialize_ollama()
                    
            elif self.provider == LLMProvider.OLLAMA:
                self._initialize_ollama()
                
            elif self.provider == LLMProvider.GROQ:
                api_key = os.getenv('GROQ_API_KEY')
                if api_key:
                    # Initialize Groq client
                    pass
                else:
                    logger.warning("Groq API key not found, falling back to Ollama")
                    self.provider = LLMProvider.OLLAMA
                    self._initialize_ollama()
                    
        except Exception as e:
            logger.error(f"Failed to initialize LLM client: {e}")
            # Fall back to Ollama local deployment
            self.provider = LLMProvider.OLLAMA
            self._initialize_ollama()
    
    def _initialize_ollama(self):
        """Initialize local Ollama connection."""
        try:
            # Check if Ollama is running locally
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            if response.status_code == 200:
                self.client = "ollama"
                logger.info("Connected to local Ollama instance")
            else:
                logger.error("Ollama not available, using fallback mode")
                self.client = "fallback"
        except Exception as e:
            logger.error(f"Could not connect to Ollama: {e}")
            self.client = "fallback"
    
    def _load_database_schemas(self) -> Dict[str, Any]:
        """Load database schema information for query generation."""
        return {
            "transactions": {
                "table": "transactions",
                "columns": [
                    {"name": "account_id", "type": "string", "description": "Account identifier"},
                    {"name": "transaction_id", "type": "string", "description": "Unique transaction ID"},
                    {"name": "amount", "type": "float", "description": "Transaction amount"},
                    {"name": "date", "type": "date", "description": "Transaction date"},
                    {"name": "merchant_name", "type": "string", "description": "Merchant or company name"},
                    {"name": "category", "type": "string", "description": "Transaction category"},
                    {"name": "subcategory", "type": "string", "description": "Transaction subcategory"},
                    {"name": "account_name", "type": "string", "description": "Account name"},
                ],
                "relationships": ["accounts", "categories", "merchants"]
            },
            "accounts": {
                "table": "accounts",
                "columns": [
                    {"name": "account_id", "type": "string", "description": "Account identifier"},
                    {"name": "account_name", "type": "string", "description": "Account display name"},
                    {"name": "account_type", "type": "string", "description": "Type of account (checking, savings, credit)"},
                    {"name": "balance", "type": "float", "description": "Current account balance"},
                    {"name": "institution_name", "type": "string", "description": "Bank or financial institution"},
                ],
                "relationships": ["transactions"]
            },
            "neo4j_nodes": {
                "Transaction": ["account_id", "amount", "date", "merchant_name", "category"],
                "Account": ["account_id", "name", "type", "institution"],
                "Merchant": ["name", "category", "location"],
                "Category": ["name", "parent_category"],
            },
            "neo4j_relationships": {
                "BELONGS_TO": "Transaction -> Account",
                "PAID_TO": "Transaction -> Merchant", 
                "CATEGORIZED_AS": "Transaction -> Category",
                "SIMILAR_TO": "Transaction -> Transaction",
            }
        }
    
    def _load_query_templates(self) -> Dict[str, List[str]]:
        """Load common query patterns and templates."""
        return {
            "spending_analysis": [
                "Show me spending by category for {time_period}",
                "What are my top expenses in {category}?",
                "How much did I spend at {merchant}?",
            ],
            "trend_analysis": [
                "Compare my spending this month vs last month",
                "Show spending trends over the last {period}",
                "When do I spend the most money?",
            ],
            "account_analysis": [
                "What's my account balance?",
                "Show transactions for {account_name}",
                "Which account has the most activity?",
            ],
            "anomaly_detection": [
                "Find unusual transactions",
                "Show me large transactions over ${amount}",
                "Detect spending pattern changes",
            ]
        }
    
    async def process_natural_language_query(self, user_query: str, context: Dict[str, Any] = None) -> QueryResult:
        """
        Process a natural language query and return structured results.
        
        Args:
            user_query: Natural language query from user
            context: Additional context like date ranges, user preferences
            
        Returns:
            QueryResult with query, results, and interpretation
        """
        start_time = datetime.now()
        
        try:
            # 1. Analyze query intent and determine query type
            query_analysis = await self._analyze_query_intent(user_query, context)
            
            # 2. Generate appropriate database query
            generated_query = await self._generate_database_query(
                user_query, query_analysis, context
            )
            
            # 3. Execute the query
            raw_results = await self._execute_query(generated_query, query_analysis['type'])
            
            # 4. Interpret results in natural language
            interpretation = await self._interpret_results(
                user_query, generated_query, raw_results, query_analysis
            )
            
            # 5. Suggest visualizations
            viz_suggestions = await self._suggest_visualizations(
                query_analysis, raw_results
            )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return QueryResult(
                success=True,
                query_type=QueryType(query_analysis['type']),
                generated_query=generated_query,
                raw_results=raw_results,
                interpreted_results=interpretation,
                visualization_suggestions=viz_suggestions,
                confidence_score=query_analysis.get('confidence', 0.8),
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Error processing query: {e}")
            
            return QueryResult(
                success=False,
                query_type=QueryType.ANALYSIS,
                generated_query="",
                raw_results=None,
                interpreted_results=f"Sorry, I couldn't process your query: {str(e)}",
                visualization_suggestions=[],
                confidence_score=0.0,
                execution_time=execution_time,
                error_message=str(e)
            )
    
    async def _analyze_query_intent(self, user_query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Analyze user query to determine intent and required query type."""
        
        # Keywords mapping to query types
        sql_keywords = ['sum', 'count', 'average', 'total', 'group by', 'spending', 'balance', 'transactions']
        cypher_keywords = ['related', 'connected', 'similar', 'network', 'relationship', 'path', 'influence']
        analysis_keywords = ['analyze', 'insights', 'patterns', 'trends', 'anomalies', 'predict']
        
        query_lower = user_query.lower()
        
        # Determine primary query type based on keywords
        if any(keyword in query_lower for keyword in cypher_keywords):
            query_type = "cypher"
        elif any(keyword in query_lower for keyword in analysis_keywords):
            query_type = "analysis"
        else:
            query_type = "sql"
        
        # Extract time periods
        time_patterns = {
            'today': datetime.now().date(),
            'yesterday': (datetime.now() - timedelta(days=1)).date(),
            'this week': datetime.now().date() - timedelta(days=7),
            'this month': datetime.now().date() - timedelta(days=30),
            'last month': datetime.now().date() - timedelta(days=60),
            'this year': datetime.now().date() - timedelta(days=365),
        }
        
        detected_timeframe = None
        for period, date_val in time_patterns.items():
            if period in query_lower:
                detected_timeframe = period
                break
        
        # Extract entities (amounts, categories, merchants)
        entities = self._extract_entities(user_query)
        
        return {
            'type': query_type,
            'timeframe': detected_timeframe,
            'entities': entities,
            'intent': self._classify_intent(query_lower),
            'confidence': 0.85  # Base confidence score
        }
    
    def _extract_entities(self, query: str) -> Dict[str, List[str]]:
        """Extract relevant entities from the query."""
        entities = {
            'amounts': [],
            'categories': [],
            'merchants': [],
            'accounts': []
        }
        
        # Extract dollar amounts
        amount_pattern = r'\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'
        amounts = re.findall(amount_pattern, query)
        entities['amounts'] = amounts
        
        # Common categories (could be enhanced with ML)
        common_categories = [
            'food', 'groceries', 'restaurants', 'gas', 'transportation',
            'shopping', 'entertainment', 'bills', 'utilities', 'healthcare'
        ]
        
        query_lower = query.lower()
        for category in common_categories:
            if category in query_lower:
                entities['categories'].append(category)
        
        return entities
    
    def _classify_intent(self, query: str) -> str:
        """Classify the user's intent."""
        if any(word in query for word in ['how much', 'total', 'sum', 'spent']):
            return 'spending_analysis'
        elif any(word in query for word in ['trend', 'over time', 'compare', 'vs']):
            return 'trend_analysis'
        elif any(word in query for word in ['balance', 'account']):
            return 'account_analysis'
        elif any(word in query for word in ['unusual', 'anomaly', 'strange', 'large']):
            return 'anomaly_detection'
        else:
            return 'general_query'
    
    async def _generate_database_query(self, user_query: str, analysis: Dict[str, Any], context: Dict[str, Any] = None) -> str:
        """Generate appropriate database query based on analysis."""
        
        if self.client == "fallback":
            return self._generate_fallback_query(user_query, analysis)
        
        # Create prompt for LLM
        prompt = self._create_query_generation_prompt(user_query, analysis, context)
        
        try:
            if self.provider == LLMProvider.OPENAI:
                response = await self._query_openai(prompt)
            elif self.provider == LLMProvider.ANTHROPIC:
                response = await self._query_anthropic(prompt)
            elif self.provider == LLMProvider.OLLAMA:
                response = await self._query_ollama(prompt)
            else:
                response = self._generate_fallback_query(user_query, analysis)
            
            # Extract query from response
            return self._extract_query_from_response(response, analysis['type'])
            
        except Exception as e:
            logger.error(f"LLM query generation failed: {e}")
            return self._generate_fallback_query(user_query, analysis)
    
    def _create_query_generation_prompt(self, user_query: str, analysis: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Create a detailed prompt for query generation."""
        
        schema_info = json.dumps(self.db_schemas, indent=2)
        
        prompt = f"""
You are an expert database query generator for a financial transaction analytics system.

USER QUERY: "{user_query}"

QUERY ANALYSIS:
- Type: {analysis['type']}
- Intent: {analysis['intent']}
- Timeframe: {analysis.get('timeframe', 'not specified')}
- Entities: {analysis.get('entities', {})}

DATABASE SCHEMA:
{schema_info}

INSTRUCTIONS:
1. Generate a {analysis['type'].upper()} query that answers the user's question
2. Use proper syntax and table/column names from the schema
3. Include appropriate WHERE clauses for time filtering
4. Optimize for performance
5. Return ONLY the query, no explanations

QUERY TYPE SPECIFIC GUIDELINES:
- SQL: Use standard SQL syntax, focus on aggregations and filtering
- CYPHER: Use Neo4j Cypher syntax, focus on relationships and graph patterns
- ANALYSIS: Return Python code for data analysis using pandas/numpy

Generate the query:
"""
        return prompt
    
    async def _query_openai(self, prompt: str) -> str:
        """Query OpenAI API."""
        try:
            response = await openai.ChatCompletion.acreate(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert database query generator."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.1
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    async def _query_anthropic(self, prompt: str) -> str:
        """Query Anthropic Claude API."""
        try:
            response = await self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=500,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text.strip()
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise
    
    async def _query_ollama(self, prompt: str) -> str:
        """Query local Ollama instance."""
        try:
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "llama2",  # or codellama for better code generation
                    "prompt": prompt,
                    "stream": False
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()['response'].strip()
            else:
                raise Exception(f"Ollama API error: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Ollama API error: {e}")
            raise
    
    def _generate_fallback_query(self, user_query: str, analysis: Dict[str, Any]) -> str:
        """Generate basic queries when LLM is not available."""
        
        query_type = analysis['type']
        intent = analysis['intent']
        
        if query_type == "sql":
            if intent == "spending_analysis":
                return """
                SELECT category, SUM(amount) as total_spending 
                FROM transactions 
                WHERE date >= date('now', '-30 days')
                GROUP BY category 
                ORDER BY total_spending DESC
                """
            elif intent == "trend_analysis":
                return """
                SELECT DATE(date) as transaction_date, SUM(amount) as daily_spending
                FROM transactions 
                WHERE date >= date('now', '-30 days')
                GROUP BY DATE(date)
                ORDER BY transaction_date
                """
            else:
                return """
                SELECT * FROM transactions 
                WHERE date >= date('now', '-7 days')
                ORDER BY date DESC 
                LIMIT 50
                """
        
        elif query_type == "cypher":
            return """
            MATCH (t:Transaction)-[:BELONGS_TO]->(a:Account)
            WHERE t.date >= date() - duration('P30D')
            RETURN t, a
            ORDER BY t.date DESC
            LIMIT 50
            """
        
        else:  # analysis
            return """
            # Basic transaction analysis
            import pandas as pd
            df = pd.read_sql("SELECT * FROM transactions WHERE date >= date('now', '-30 days')", connection)
            summary = df.groupby('category')['amount'].agg(['sum', 'count', 'mean'])
            print(summary)
            """
    
    def _extract_query_from_response(self, response: str, query_type: str) -> str:
        """Extract clean query from LLM response."""
        
        # Remove common prefixes/suffixes
        response = response.strip()
        
        # Remove markdown code blocks
        if "```" in response:
            parts = response.split("```")
            for part in parts:
                if query_type.lower() in part.lower() or "select" in part.lower() or "match" in part.lower():
                    response = part.strip()
                    break
        
        # Remove explanatory text
        lines = response.split('\n')
        query_lines = []
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#') and not line.startswith('//'):
                query_lines.append(line)
        
        return '\n'.join(query_lines)
    
    async def _execute_query(self, query: str, query_type: str) -> Any:
        """Execute the generated query against appropriate database."""
        
        # This would integrate with actual database connections
        # For now, return mock data
        
        if query_type == "sql":
            return [
                {"category": "Food & Dining", "total_spending": 1250.75},
                {"category": "Transportation", "total_spending": 890.50},
                {"category": "Shopping", "total_spending": 675.25},
            ]
        elif query_type == "cypher":
            return [
                {"transaction_id": "tx_1", "amount": 45.67, "merchant": "Starbucks"},
                {"transaction_id": "tx_2", "amount": 125.00, "merchant": "Gas Station"},
            ]
        else:
            return {"analysis": "Basic spending patterns show highest expenses in food category"}
    
    async def _interpret_results(self, user_query: str, generated_query: str, raw_results: Any, analysis: Dict[str, Any]) -> str:
        """Convert raw query results into natural language interpretation."""
        
        if self.client == "fallback":
            return self._generate_fallback_interpretation(raw_results, analysis)
        
        prompt = f"""
Convert the following database query results into a natural, conversational response to the user's question.

USER QUESTION: "{user_query}"
QUERY EXECUTED: "{generated_query}"
RESULTS: {json.dumps(raw_results, indent=2)}

Provide a clear, helpful interpretation that:
1. Directly answers the user's question
2. Highlights key insights from the data
3. Uses natural language (avoid technical jargon)
4. Suggests actionable next steps if appropriate

Response:
"""
        
        try:
            if self.provider == LLMProvider.OPENAI:
                response = await self._query_openai(prompt)
            elif self.provider == LLMProvider.ANTHROPIC:
                response = await self._query_anthropic(prompt)
            elif self.provider == LLMProvider.OLLAMA:
                response = await self._query_ollama(prompt)
            else:
                response = self._generate_fallback_interpretation(raw_results, analysis)
                
            return response
            
        except Exception as e:
            logger.error(f"Result interpretation failed: {e}")
            return self._generate_fallback_interpretation(raw_results, analysis)
    
    def _generate_fallback_interpretation(self, raw_results: Any, analysis: Dict[str, Any]) -> str:
        """Generate basic interpretation when LLM is not available."""
        
        if isinstance(raw_results, list) and len(raw_results) > 0:
            if analysis['intent'] == 'spending_analysis':
                total = sum(item.get('total_spending', 0) for item in raw_results if isinstance(item, dict))
                return f"Based on your recent transactions, you've spent ${total:.2f} across {len(raw_results)} categories. Your top spending category appears to be {raw_results[0].get('category', 'unknown')}."
            else:
                return f"I found {len(raw_results)} results matching your query. The data shows recent transaction activity across multiple categories."
        else:
            return "I found some results for your query, but couldn't provide a detailed interpretation at this time."
    
    async def _suggest_visualizations(self, analysis: Dict[str, Any], raw_results: Any) -> List[str]:
        """Suggest appropriate visualizations for the results."""
        
        suggestions = []
        
        intent = analysis.get('intent', '')
        
        if intent == 'spending_analysis':
            suggestions.extend([
                "pie_chart:spending_by_category",
                "bar_chart:top_categories",
                "treemap:hierarchical_spending"
            ])
        elif intent == 'trend_analysis':
            suggestions.extend([
                "line_chart:spending_over_time",
                "area_chart:cumulative_spending",
                "heatmap:spending_patterns"
            ])
        elif intent == 'account_analysis':
            suggestions.extend([
                "bar_chart:account_balances",
                "donut_chart:account_distribution"
            ])
        else:
            suggestions.extend([
                "table:detailed_results",
                "summary_cards:key_metrics"
            ])
        
        return suggestions

# Singleton instance
query_agent = LLMQueryAgent()
