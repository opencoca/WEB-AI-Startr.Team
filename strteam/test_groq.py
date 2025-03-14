#!/usr/bin/env python3
# Script to test Groq API connectivity

import os
import openai
import logging
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('test_groq')

def test_groq_api():
    """Test Groq API connectivity"""
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        logger.error("GROQ_API_KEY not found in environment variables")
        return False
    
    logger.info(f"Using Groq API key: {api_key[:4]}****")
    
    # Create OpenAI client with Groq base URL
    client = openai.OpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1"
    )
    
    logger.info("Sending request to Groq API...")
    
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=10
        )
        logger.info(f"Response received: {response}")
        return True
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        if hasattr(e, "response"):
            logger.error(f"Response status: {e.response.status_code}")
            logger.error(f"Response body: {e.response.text}")
        return False

def test_llama3_model():
    """Test LLAMA_3 model through our ModelFactory"""
    from strteam.camel.typing import ModelType
    from strteam.camel.model_backend import ModelFactory
    
    logger.info("Creating LLAMA_3 model backend...")
    model = ModelFactory.create(ModelType.LLAMA_3)
    
    logger.info("LLAMA_3 model created, sending test message...")
    
    try:
        response = model.run(messages=[{"role": "user", "content": "Say hello in one word"}])
        logger.info(f"Response received: {response}")
        return True
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "llama3":
        test_llama3_model()
    else:
        test_groq_api() 