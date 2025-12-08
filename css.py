from crawl4ai import JsonCssExtractionStrategy
from crawl4ai import LLMConfig

# Generate a schema (one-time cost)
html = "<div class='product'><h2>Gaming Laptop</h2><span class='price'>$999.99</span></div>"

# Or using Ollama (open source, no token needed)
schema = JsonCssExtractionStrategy.generate_schema(
    html,
    llm_config=LLMConfig(
        provider="ollama/llama3.3", api_token=None
    ),  # Not needed for Ollama
)

# Use the schema for fast, repeated extractions
strategy = JsonCssExtractionStrategy(schema)
