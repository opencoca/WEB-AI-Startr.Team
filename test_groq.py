#!/usr/bin/env python3
import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Check for GROQ_API_KEY environment variable
if "GROQ_API_KEY" not in os.environ or not os.environ["GROQ_API_KEY"]:
    logging.error("GROQ_API_KEY environment variable is not set!")
    print("\nTo set the environment variable, run:")
    print("export GROQ_API_KEY=your_groq_api_key_here")
    sys.exit(1)

try:
    # Try importing OpenAI SDK
    import openai
    
    # Initialize client with Groq's base URL
    client = openai.OpenAI(
        api_key=os.environ["GROQ_API_KEY"],
        base_url="https://api.groq.com/openai/v1"
    )
    
    # Test with a simple request
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, please provide a short greeting."}
        ],
        max_tokens=100
    )
    
    # Print the response
    logging.info(f"API connection successful!")
    print("\nGroq API Response:")
    print(f"Model: llama-3.3-70b-versatile")
    print(f"Response: {response.choices[0].message.content}")
    
except Exception as e:
    logging.error(f"Error testing Groq API: {str(e)}")
    print("\nTroubleshooting tips:")
    print("1. Make sure your Groq API key is valid")
    print("2. Check your internet connection")
    print("3. Verify that the llama-3.3-70b-versatile model is available on Groq")