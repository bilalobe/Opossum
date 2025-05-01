"""Opossum fact checking tools for DSPy integration."""

import dspy
import json
import os
import logging
import time
import re
from typing import List, Tuple
from difflib import SequenceMatcher
from functools import lru_cache

# Setup logging with more detailed formatting
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class OpossumFactTool(dspy.Tool):
    """
    Advanced tool for searching opossum facts with multiple matching strategies.

    Features:
    - Multiple search methods (keyword, fuzzy, regex)
    - Result caching for performance
    - Configurable matching parameters
    - Robust error handling with fallbacks
    - Detailed logging
    """

    name = "opossum_fact_lookup"
    input_variable = "query"
    output_variable = "fact"
    description = "Looks up facts about opossums from the Opossum knowledge base using keyword matching, fuzzy search, and pattern recognition."

    def __init__(
        self,
        data_file: str = "opossum_dataset_converted.json",
        fallback_paths: List[str] = None,
        threshold: float = 0.2,
        max_results: int = 1,
        search_method: str = "auto",
        cache_size: int = 128,
    ):
        """
        Initialize the Opossum fact lookup tool.

        Args:
            data_file: Path to the JSON knowledge base
            fallback_paths: Additional paths to try if data_file not found
            threshold: Minimum matching score (0-1) for results
            max_results: Maximum number of results to return
            search_method: 'keyword', 'fuzzy', 'regex', or 'auto'
            cache_size: Size of the LRU cache for query results
        """
        super().__init__()
        self.data_file = data_file
        self.fallback_paths = fallback_paths or [
            os.path.join("..", "..", "..", data_file),
            os.path.join("data", data_file),
            os.path.join("resources", data_file),
        ]
        self.threshold = threshold
        self.max_results = max_results
        self.search_method = search_method
        self._knowledge_base = None
        self._last_load_time = 0
        self._cache_timeout = 300  # 5 minutes cache timeout

        # Initialize the knowledge base
        self._load_knowledge_base()

    def _find_data_file(self) -> str:
        """
        Locate the data file by checking multiple possible locations.

        Returns:
            Path to the data file if found, otherwise the original path
        """
        # First check the primary path
        if os.path.exists(self.data_file):
            return self.data_file

        # Try fallback paths
        for path in self.fallback_paths:
            if os.path.exists(path):
                logger.info(f"Found knowledge base at fallback path: {path}")
                return path

        # If we have a relative path, try to find it from various starting points
        rel_file = os.path.basename(self.data_file)
        for root, _, files in os.walk(os.getcwd(), topdown=True, followlinks=False):
            if rel_file in files:
                path = os.path.join(root, rel_file)
                logger.info(f"Found knowledge base by traversal: {path}")
                return path

        logger.warning(f"Could not locate knowledge base file: {self.data_file}")
        return self.data_file  # Return original even if not found

    def _load_knowledge_base(self) -> None:
        """Load or reload the knowledge base if needed."""
        current_time = time.time()

        # Skip reload if cache is fresh
        if (
            self._knowledge_base is not None
            and current_time - self._last_load_time < self._cache_timeout
        ):
            return

        try:
            file_path = self._find_data_file()

            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

                # Validate and normalize the data
                if isinstance(data, list):
                    # Transform data for consistent access
                    normalized_data = []
                    for item in data:
                        if isinstance(item, dict):
                            fact = item.get(
                                "fact", item.get("description", item.get("text", ""))
                            )
                            if fact:
                                normalized_data.append(
                                    {
                                        "fact": fact,
                                        "keywords": set(fact.lower().split()),
                                        "original": item,
                                    }
                                )
                        elif isinstance(item, str) and item.strip():
                            normalized_data.append(
                                {
                                    "fact": item,
                                    "keywords": set(item.lower().split()),
                                    "original": item,
                                }
                            )

                    self._knowledge_base = normalized_data
                    self._last_load_time = current_time
                    logger.info(
                        f"Loaded {len(normalized_data)} normalized facts from {file_path}"
                    )
                else:
                    raise ValueError("Knowledge base must be a list")

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Error processing knowledge base: {e}")
            # Initialize with empty data but don't update last_load_time to force retry
            self._knowledge_base = self._knowledge_base or []

        except Exception as e:
            logger.error(f"Unexpected error loading knowledge base: {e}", exc_info=True)
            self._knowledge_base = self._knowledge_base or []

    def _keyword_search(self, query: str) -> List[Tuple[str, float]]:
        """
        Search facts using keyword overlap.

        Args:
            query: The search query

        Returns:
            List of (fact, score) tuples sorted by relevance
        """
        query_terms = set(query.lower().split())
        results = []

        for item in self._knowledge_base:
            if not query_terms:
                continue

            # Calculate keyword overlap
            fact_terms = item["keywords"]
            overlap = len(query_terms.intersection(fact_terms))

            # Calculate a normalized score
            if overlap > 0:
                # Weight by both absolute overlap and percentage overlap
                score = (overlap / len(query_terms) * 0.7) + (
                    overlap / max(1, len(fact_terms)) * 0.3
                )
                results.append((item["fact"], score))

        return sorted(results, key=lambda x: x[1], reverse=True)

    def _fuzzy_search(self, query: str) -> List[Tuple[str, float]]:
        """
        Search facts using fuzzy string matching.

        Args:
            query: The search query

        Returns:
            List of (fact, score) tuples sorted by relevance
        """
        query = query.lower()
        results = []

        for item in self._knowledge_base:
            fact = item["fact"].lower()
            # Calculate sequence similarity ratio
            similarity = SequenceMatcher(None, query, fact).ratio()

            # Look for query as a substring with bonus
            if query in fact:
                similarity += 0.2

            results.append((item["fact"], similarity))

        return sorted(results, key=lambda x: x[1], reverse=True)

    def _regex_search(self, query: str) -> List[Tuple[str, float]]:
        """
        Search facts using regex pattern matching.

        Args:
            query: The search query

        Returns:
            List of (fact, score) tuples sorted by relevance
        """
        results = []

        # Create regex pattern from query, escaping special chars
        try:
            # Split query into words and create pattern to match any word
            words = re.escape(query).replace(r"\ ", "|")
            pattern = re.compile(f"({words})", re.IGNORECASE)

            for item in self._knowledge_base:
                fact = item["fact"]
                matches = pattern.findall(fact)

                if matches:
                    # Score based on number of matches and coverage
                    score = len(matches) / len(fact.split())
                    results.append((fact, score))
        except re.error:
            logger.warning(f"Invalid regex pattern from query: {query}")

        return sorted(results, key=lambda x: x[1], reverse=True)

    @lru_cache(maxsize=128)
    def _search(self, query: str, method: str) -> List[Tuple[str, float]]:
        """
        Search the knowledge base using the specified method.

        Args:
            query: The search query
            method: Search method to use

        Returns:
            List of (fact, score) tuples sorted by relevance
        """
        if not self._knowledge_base:
            self._load_knowledge_base()
            if not self._knowledge_base:
                return [("Error: Opossum knowledge base is not available.", 0.0)]

        method = method.lower()

        if method == "keyword" or (method == "auto" and len(query.split()) > 2):
            return self._keyword_search(query)
        elif method == "fuzzy" or (method == "auto" and len(query) < 20):
            return self._fuzzy_search(query)
        elif method == "regex":
            return self._regex_search(query)
        else:
            # If method is unrecognized or auto for longer text, combine results
            keyword_results = dict(self._keyword_search(query))
            fuzzy_results = dict(self._fuzzy_search(query))

            # Combine scores with weights
            combined_results = {}
            for fact in set(keyword_results.keys()) | set(fuzzy_results.keys()):
                keyword_score = keyword_results.get(fact, 0)
                fuzzy_score = fuzzy_results.get(fact, 0)
                # Weight keyword matches more heavily than fuzzy
                combined_results[fact] = (keyword_score * 0.7) + (fuzzy_score * 0.3)

            return sorted(combined_results.items(), key=lambda x: x[1], reverse=True)

    def __call__(self, query: str) -> str:
        """
        Search the knowledge base for facts related to the query.

        Args:
            query: The search query

        Returns:
            Matching fact(s) or error message
        """
        start_time = time.time()
        logger.info(f"Searching for: '{query}' using method '{self.search_method}'")

        # Perform the search
        results = self._search(query, self.search_method)

        # Filter by threshold and limit by max_results
        filtered_results = [
            (fact, score) for fact, score in results if score >= self.threshold
        ][: self.max_results]

        if not filtered_results:
            response = f"No facts found in the Opossum knowledge base for '{query}'."
            logger.info(f"No results above threshold {self.threshold} for '{query}'")
        elif len(filtered_results) == 1:
            response = filtered_results[0][0]
            logger.info(
                f"Found 1 result with score {filtered_results[0][1]:.2f} in {time.time()-start_time:.3f}s"
            )
        else:
            # Format multiple results
            response = "Found multiple relevant facts:\n\n"
            for i, (fact, score) in enumerate(filtered_results, 1):
                response += f"{i}. {fact}\n\n"
            logger.info(
                f"Found {len(filtered_results)} results in {time.time()-start_time:.3f}s"
            )

        return response


# Example usage with customized configuration
if __name__ == "__main__":
    # Configure DSPy
    try:
        # This would be set up in your actual application
        import dspy

        dspy.settings.configure(lm="openai")
    except:
        logger.warning("Could not configure DSPy - running in demo mode only")

    # Create tool with custom settings
    opossum_tool = OpossumFactTool(threshold=0.25, max_results=2, search_method="auto")

    # Create ReAct agent with our tool
    class QuestionWithFacts(dspy.Signature):
        """Answer questions using the opossum knowledge base."""

        question = dspy.InputField()
        answer = dspy.OutputField(
            desc="A comprehensive answer incorporating retrieved facts if necessary."
        )

    agent = dspy.ReAct(QuestionWithFacts, tools=[opossum_tool])

    # Test with a question
    test_questions = [
        "How many teeth does an opossum have?",
        "What do opossums eat in the wild?",
        "How long is an opossum's gestation period?",
    ]

    for question in test_questions:
        try:
            result = agent(question=question)
            print(f"\nQuestion: {question}")
            print(f"Answer: {result.answer}")
        except Exception as e:
            print(f"Error processing question: {e}")
