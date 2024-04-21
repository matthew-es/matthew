import os

# OpenAI
import openai
import tiktoken as tt
openai.api_key = os.getenv("OPENAI_API_KEY")
ai_openai = openai

# Anthropic
import anthropic
anthropic.api_key = os.getenv("ANTHROPIC_API_KEY")
ai_anthropic = anthropic