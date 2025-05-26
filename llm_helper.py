# llm_helper.py
import google.generativeai as genai
import os
import json

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Use the model name prefixed with "models/" as shown in working examples
# Let's try "models/gemini-1.5-flash-latest" first as "latest" is often a good alias.
# If that specific alias doesn't work, "models/gemini-pro" is a common alternative.
MODEL_NAME_FOR_API = "models/gemini-1.5-flash-latest"
# MODEL_NAME_FOR_API = "models/gemini-pro" # Alternative to try if flash doesn't work

IS_GEMINI_CONFIGURED = False

if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        print(f"LLM_HELPER.PY: Gemini API Key configured successfully. Will attempt to use model: {MODEL_NAME_FOR_API}")
        IS_GEMINI_CONFIGURED = True
    except Exception as e:
        print(f"LLM_HELPER.PY: Error configuring Gemini API Key: {e}")
        GEMINI_API_KEY = None
        IS_GEMINI_CONFIGURED = False
else:
    print("LLM_HELPER.PY WARNING: GEMINI_API_KEY not found in environment variables. LLM features will be disabled.")

def extract_metadata_and_generate_queries(amazon_product_name, amazon_product_url):
    print(f"LLM_HELPER.PY: extract_metadata_and_generate_queries called with Name: '{amazon_product_name}' URL: '{amazon_product_url}'")

    if not IS_GEMINI_CONFIGURED: # Check the flag
        print("LLM_HELPER.PY: Gemini API Key is not configured or configuration failed. Skipping LLM processing.")
        return {"metadata": {"Error": "LLM API Key not configured or configuration failed"}, "search_queries": {}}

    try:
        # Initialize the generative model WITH the "models/" prefix
        model = genai.GenerativeModel(MODEL_NAME_FOR_API)
        print(f"LLM_HELPER.PY: Gemini Model '{MODEL_NAME_FOR_API}' initialized successfully.")
    except Exception as e:
        print(f"LLM_HELPER.PY: Error initializing Gemini Model '{MODEL_NAME_FOR_API}': {e}")
        print(f"LLM_HELPER.PY: This might be due to an invalid API key, incorrect model name (ensure it's prefixed with 'models/'), or network/quota issue.")
        return {"metadata": {"Error": f"Failed to initialize LLM Model ('{MODEL_NAME_FOR_API}')"}, "search_queries": {}}

    prompt = f"""
    You are an expert e-commerce product analyst.
    Analyze the following Amazon product:
    Product Name: "{amazon_product_name}"
    Product URL: {amazon_product_url}

    Your tasks are:
    1. Extract key structured metadata for this product. Identify Brand, Model/Series, and 2-3 critical distinguishing specifications (e.g., storage size, color, screen size, type, material, quantity). Be concise.
    2. Based on this metadata, generate targeted search queries to find the *exact same product* on these Indian e-commerce platforms: Flipkart, Meesho. The queries should be suitable for direct use in their search bars or in a Google "site:" search.

    Provide your response ONLY in valid JSON format with the following structure:
    {{
      "metadata": {{
        "brand": "ExampleBrand",
        "model": "ExampleModel X100",
        "specifications": ["Spec1: Value1", "Spec2: Value2"]
      }},
      "search_queries": {{
        "Flipkart": "ExampleBrand ExampleModel X100 Value1 Value2",
        "Meesho": "ExampleBrand ExampleModel X100 Value1"
      }}
    }}

    If the product name is too generic or lacks detail, use your best judgment to extract what you can and form plausible queries. If a platform is unsuitable for the product type, you can omit it from search_queries or provide an empty string for its query.
    Focus on accuracy for finding the *identical* product. Ensure the entire output is a single, valid JSON object.
    """

    print(f"LLM_HELPER.PY: Sending prompt to Gemini model '{MODEL_NAME_FOR_API}' for product: '{amazon_product_name}'")
    try:
        response = model.generate_content(prompt)
        
        cleaned_response_text = response.text.strip()
        if cleaned_response_text.startswith("```json"):
            cleaned_response_text = cleaned_response_text[7:]
        if cleaned_response_text.endswith("```"):
            cleaned_response_text = cleaned_response_text[:-3]
        cleaned_response_text = cleaned_response_text.strip()

        print(f"LLM_HELPER.PY: Raw Gemini response text (cleaned for JSON parsing):\n{cleaned_response_text}")
        
        llm_data = json.loads(cleaned_response_text)
        print(f"LLM_HELPER.PY: Successfully parsed LLM data: {llm_data}")
        
        if "metadata" not in llm_data: llm_data["metadata"] = {"Warning": "Metadata missing from LLM response"}
        if "search_queries" not in llm_data: llm_data["search_queries"] = {}

        return llm_data
        
    except json.JSONDecodeError as e:
        problem_text = response.text if 'response' in locals() and hasattr(response, 'text') else 'Response object not available or no text attribute'
        print(f"LLM_HELPER.PY: Error decoding JSON from LLM response: {e}. Problematic text: {problem_text}")
        return {"metadata": {"Error": "Failed to parse LLM response as JSON"}, "search_queries": {"Flipkart": amazon_product_name, "Meesho": amazon_product_name}}
    except Exception as e:
        print(f"LLM_HELPER.PY: An error occurred with the LLM API call or response processing: {e}")
        return {"metadata": {"Error": f"LLM API call/processing failed: {str(e)}"}, "search_queries": {"Flipkart": amazon_product_name, "Meesho": amazon_product_name}}

print("LLM_HELPER.PY: 'extract_metadata_and_generate_queries' function has been defined by Python interpreter.")

if __name__ == '__main__':
    # ... (keep your existing __main__ block for direct testing, 
    # but ensure it also uses MODEL_NAME_FOR_API when calling genai.GenerativeModel) ...
    print("LLM_HELPER.PY: Running __main__ block for direct test...")
    from dotenv import load_dotenv
    project_root = os.path.dirname(os.path.abspath(__file__))
    load_dotenv(os.path.join(project_root, '.env'))
                                             
    TEST_GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not TEST_GEMINI_API_KEY:
        print("LLM_HELPER_TEST: Cannot test - GEMINI_API_KEY not found.")
    else:
        print(f"LLM_HELPER_TEST: GEMINI_API_KEY found. Configuring genai for test...")
        try:
            genai.configure(api_key=TEST_GEMINI_API_KEY)
            print("LLM_HELPER_TEST: Genai configured for test.")
            
            test_name = "Apple iPhone 15 (128 GB) - Pink"
            test_url = "https://www.amazon.in/Apple-iPhone-15-128-GB/dp/B0CHX3TW6X/"
            
            print(f"\nLLM_HELPER_TEST: Requesting metadata and queries for: '{test_name}' using model '{MODEL_NAME_FOR_API}'") # Use MODEL_NAME_FOR_API
            result = extract_metadata_and_generate_queries(test_name, test_url) # Call the function
            
            print("\n--- LLM Test Result (from __main__) ---")
            print(json.dumps(result, indent=2))

        except Exception as e:
            print(f"LLM_HELPER_TEST: Error during direct test execution: {e}")