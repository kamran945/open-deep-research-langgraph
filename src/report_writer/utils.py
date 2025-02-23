import yaml
import os

import asyncio
import requests
import time

from tavily import TavilyClient, AsyncTavilyClient
from duckduckgo_search import DDGS
from langsmith import traceable

from dotenv import load_dotenv, find_dotenv

# Load the API keys from .env
load_dotenv(find_dotenv(), override=True)


from src.report_writer.schemas_tasks import Section

tavily_client = TavilyClient()
tavily_async_client = AsyncTavilyClient()


def load_config(file_path=os.getenv("CONFIG_FILEPATH")):
    """Load configuration from a YAML file."""
    with open(file_path, "r") as file:
        config = yaml.safe_load(file)
    return config


def deduplicate_and_format_sources(
    search_response, max_tokens_per_source, include_raw_content=True
):
    """
    Takes a list of search responses and formats them into a readable string.
    Limits the raw_content to approximately max_tokens_per_source.

    Args:
        search_responses: List of search response dicts, each containing:
            - query: str
            - results: List of dicts with fields:
                - title: str
                - url: str
                - content: str
                - score: float
                - raw_content: str|None
        max_tokens_per_source: int
        include_raw_content: bool

    Returns:
        str: Formatted string with deduplicated sources
    """
    # Collect all results
    sources_list = []
    for response in search_response:
        sources_list.extend(response["results"])

    # Deduplicate by URL
    unique_sources = {source["url"]: source for source in sources_list}

    # Format output
    formatted_text = "Sources:\n\n"
    for i, source in enumerate(unique_sources.values(), 1):
        formatted_text += f"Source {source['title']}:\n===\n"
        formatted_text += f"URL: {source['url']}\n===\n"
        formatted_text += (
            f"Most relevant content from source: {source['content']}\n===\n"
        )
        if include_raw_content:
            # Using rough estimate of 4 characters per token
            char_limit = max_tokens_per_source * 4
            # Handle None raw_content
            raw_content = source.get("raw_content", "")
            if raw_content is None:
                raw_content = ""
                print(f"Warning: No raw_content found for source {source['url']}")
            if len(raw_content) > char_limit:
                raw_content = raw_content[:char_limit] + "... [truncated]"
            formatted_text += f"Full source content limited to {max_tokens_per_source} tokens: {raw_content}\n\n"

    return formatted_text.strip()


@traceable
async def tavily_search_async(search_queries):
    """
    Performs concurrent web searches using the Tavily API.

    Args:
        search_queries (List[SearchQuery]): List of search queries to process

    Returns:
            List[dict]: List of search responses from Tavily API, one per query. Each response has format:
                {
                    'query': str, # The original search query
                    'follow_up_questions': None,
                    'answer': None,
                    'images': list,
                    'results': [                     # List of search results
                        {
                            'title': str,            # Title of the webpage
                            'url': str,              # URL of the result
                            'content': str,          # Summary/snippet of content
                            'score': float,          # Relevance score
                            'raw_content': str|None  # Full page content if available
                        },
                        ...
                    ]
                }
    """

    search_tasks = []
    for query in search_queries:
        search_tasks.append(
            tavily_async_client.search(
                query, max_results=5, include_raw_content=True, topic="general"
            )
        )

    # Execute all searches concurrently
    search_docs = await asyncio.gather(*search_tasks)

    return search_docs


def deduplicate_and_format_sources_duck(search_response):
    """
    Takes a list of search responses and formats them into a readable string.

    Args:
        search_responses: List of search response dicts, each containing:
            - query: str
            - results: List of dicts with fields:
                - title: str
                - url: str
                - content: str

    Returns:
        str: Formatted string with deduplicated sources
    """
    # Collect all results
    sources_list = []
    for response in search_response:
        sources_list.extend(response["results"])

    # Deduplicate by URL
    unique_sources = {source["url"]: source for source in sources_list}

    # Format output
    formatted_text = "Sources:\n\n"
    for i, source in enumerate(unique_sources.values(), 1):
        formatted_text += f"Source {source['title']}:\n===\n"
        formatted_text += f"URL: {source['url']}\n===\n"
        formatted_text += (
            f"Most relevant content from source: {source['content']}\n===\n\n"
        )

    return formatted_text.strip()


@traceable
async def duckduckgo_search_async(search_queries):
    """
    Performs concurrent web searches using the DuckDuckGo API while avoiding rate limits.

    Args:
        search_queries (List[str]): List of search queries to process

    Returns:
        List[dict]: List of search responses from DuckDuckGo API, one per query. Each response has format:
            {
                'query': str,  # The original search query
                'results': [   # List of search results
                    {
                        'title': str,   # Title of the webpage
                        'url': str,     # URL of the result
                        'content': str  # Summary/snippet of content
                    },
                    ...
                ]
            }
    """
    semaphore = asyncio.Semaphore(3)  # Limit concurrent requests
    results = []

    async def fetch(query):
        async with semaphore:
            with DDGS() as ddgs:
                try:
                    search_result = await asyncio.to_thread(
                        ddgs.text, query, max_results=5
                    )
                    await asyncio.sleep(1.5)  # Avoid rate limits
                    return {
                        "query": query,
                        "results": [
                            {
                                "title": r["title"],
                                "url": r["href"],
                                "content": r["body"],
                            }
                            for r in search_result
                        ],
                    }
                except Exception as e:
                    print(f"Error fetching results for query '{query}': {e}")
                    return {"query": query, "results": []}

    results = await asyncio.gather(*(fetch(query) for query in search_queries))
    return results


def format_sections(sections: list[Section]) -> str:
    """Format a list of sections into a string"""
    formatted_str = ""
    for idx, section in enumerate(sections, 1):
        formatted_str += f"""
                        {'='*60}
                        Section {idx}: {section.section_number}
                        {'='*60}
                        Section {idx}: {section.name}
                        {'='*60}
                        Description:
                        {section.description}
                        Requires Research: 
                        {section.research}

                        Content:
                        {section.content if section.content else '[Not yet written]'}

                        """
    return formatted_str
