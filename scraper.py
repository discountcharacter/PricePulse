# scraper.py
import requests
from bs4 import BeautifulSoup
import re # For regular expressions, used in clean_price and finding price text
from urllib.parse import quote_plus # For URL encoding search queries for other platforms
import json # For parsing dynamic image data from Amazon

# --- Standard HEADERS ---
# Using a common browser User-Agent.
# For more robust scraping, consider rotating User-Agents or using more specific ones.
HEADERS = ({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9,hi;q=0.8', # Prefer English, then Hindi
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br', # Handle compressed content
    'DNT': '1', # Do Not Track Request Header
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1', # Ask for HTTPS
    'Referer': 'https://www.google.com/' # Common referer
})

def clean_price(price_str):
    """
    Cleans a price string by removing currency symbols, commas,
    and retaining only digits and a decimal point. Converts to float.
    Returns None if conversion fails.
    """
    if price_str is None:
        return None
    # Remove currency symbols (₹, $ etc.), commas, and keep only digits and decimal point
    cleaned = re.sub(r'[^\d.]', '', price_str)
    try:
        return float(cleaned)
    except ValueError:
        print(f"SCRAPER_CLEAN_PRICE: Could not convert '{cleaned}' (from original: '{price_str}') to float.")
        return None

def scrape_amazon_product_details(url):
    """
    Scrapes product name, price, and image URL from an Amazon product page.
    Returns a dictionary with product details or None if scraping fails.
    """
    print(f"SCRAPER: Attempting to scrape Amazon URL: {url}")
    try:
        response = requests.get(url, headers=HEADERS, timeout=15) # Slightly increased timeout
        
        print(f"SCRAPER: Received status code {response.status_code} for URL: {url}")

        # If it's a 500 error from Amazon, log more details before raising an exception
        if response.status_code == 500:
            print(f"SCRAPER_ERROR_DETAIL: Received 500 Internal Server Error from Amazon.")
            print(f"SCRAPER_ERROR_DETAIL: Response Headers from Amazon: {response.headers}")
            print(f"SCRAPER_ERROR_DETAIL: Response text from Amazon (first 1000 chars): {response.text[:1000]}")
        
        response.raise_for_status() # Raises HTTPError for bad responses (4XX or 5XX)
        
        soup = BeautifulSoup(response.content, 'html.parser')

        # --- Product Name Scraping ---
        name_selectors = [
            '#productTitle',
            'span#productTitle', # Sometimes it's a span within another element
            '#title', # A more generic ID sometimes used
            'h1#title',
            'h1#title > span#productTitle' # More specific combination
        ]
        name = "Name not found"
        for selector in name_selectors:
            name_element = soup.select_one(selector)
            if name_element:
                name = name_element.get_text(strip=True)
                if name and name != "Back to results": # Filter out navigation text sometimes caught
                    break # Found a good name
        print(f"SCRAPER_DEBUG: Raw Name Found: '{name}'")

        # --- Product Price Scraping ---
        price = None
        price_texts_seen = [] # For debugging which text strings were evaluated

        # List of CSS selectors to try for finding the price. Order can matter.
        price_selector_strings = [
            'span.a-price-whole',                           # Main integer part of price
            'span.a-price .a-offscreen',                    # Often contains full price for accessibility
            '#corePrice_feature_div span.a-offscreen',
            'div#corePrice_feature_div span.a-price-whole', # Price within a specific div
            '#priceblock_ourprice',                         # Older ID for main price
            '#priceblock_dealprice',                        # Price for deals
            '.priceToPay span.a-price-whole',               # Common pattern in some layouts
            'span[data-a-size="xl"] span.a-price-whole',    # Corrected: Space added. Price in a specifically sized span
            'div.a-section table#buyNew_noncbb tbody tr.a-spacing-small td.a-span12 span#price_inside_buybox', # Price in buy box
            'div#apex_desktop_newAccordionRow span.apexPriceToPay', # Another layout pattern
            'span#sns-base-price',                          # Subscription or base price
            '#price_inside_buybox'                          # More direct ID for price in buybox
        ]
        
        for selector_str in price_selector_strings:
            price_el = soup.select_one(selector_str)
            if price_el:
                price_text = price_el.get_text(strip=True)
                price_texts_seen.append(f"Selector '{selector_str}': '{price_text}'")
                price = clean_price(price_text)
                if price is not None and price > 0: # A valid positive price found
                    break 
        
        # Fallback: if no price found via specific selectors, search for text nodes containing currency symbols
        if price is None or price == 0.0:
            print("SCRAPER_DEBUG: Price not found via specific selectors. Trying currency symbol search.")
            potential_price_elements = soup.find_all(string=re.compile(r'₹|\$')) # Find text containing ₹ or $
            for text_node in potential_price_elements:
                parent = text_node.parent
                attempts = 0
                while parent and attempts < 3: # Check current element and a few parents
                    price_text_candidate = parent.get_text(strip=True)
                    # Filter out overly long strings that are unlikely to be just the price
                    if len(price_text_candidate) < 50: # Arbitrary limit to avoid huge text blocks
                        price_texts_seen.append(f"(Currency Symbol Search - Parent <{parent.name}>): '{price_text_candidate}'")
                        price = clean_price(price_text_candidate)
                        if price is not None and price > 0:
                            break
                    parent = parent.parent
                    attempts += 1
                if price is not None and price > 0:
                    break # Price found
        
        print(f"SCRAPER_DEBUG: All price texts evaluated: {price_texts_seen}")
        print(f"SCRAPER_DEBUG: Final Price Found: {price if price is not None else 'N/A'}")
        if price is None: price = 0.0 # Default if not found after all attempts

        # --- Product Image Scraping ---
        image_url = "Image not found"
        # List of CSS selectors for main product image candidates
        img_selector_strings = [
            '#landingImage',                           # Main image ID
            '#imgTagWrapperId img',                    # Image within a wrapper
            '#imgBlkFront',                            # Another common ID
            '#ivLargeImage',                           # Image viewer large image
            '#main-image-container img',               # Image in the main container
            'div#altImages ul.a-unordered-list li.selected img' # Selected thumbnail as a fallback
        ]
        
        for selector_str in img_selector_strings:
            img_tag = soup.select_one(selector_str)
            if img_tag:
                # Try 'src', 'data-src', then 'data-old-hires' which Amazon sometimes uses
                potential_src = img_tag.get('src') or img_tag.get('data-src') or img_tag.get('data-old-hires')
                if potential_src and potential_src.startswith('http'): # Ensure it's a full URL
                    image_url = potential_src
                    break # Found a valid image URL
        
        # Fallback for dynamically loaded images (often in 'data-a-dynamic-image' attribute)
        if (image_url == "Image not found" or not image_url.startswith('http')):
            dynamic_image_elements = soup.select('img[data-a-dynamic-image]')
            if dynamic_image_elements:
                first_image_data_str = dynamic_image_elements[0].get('data-a-dynamic-image')
                if first_image_data_str:
                    try:
                        image_json_data = json.loads(first_image_data_str)
                        # The JSON value is a dictionary where keys are image URLs and values are dimensions
                        image_url = list(image_json_data.keys())[0] 
                    except (json.JSONDecodeError, IndexError, TypeError) as e:
                        print(f"SCRAPER_DEBUG: Error parsing dynamic image JSON: {e}")
                        image_url = "Image not found" # Reset if parsing fails

        print(f"SCRAPER_DEBUG: Image URL Found: '{image_url}'")

        return {
            "name": name if name and name != "Name not found" else "N/A",
            "price": price, # Will be float or 0.0 if not found
            "image_url": image_url if image_url and image_url.startswith('http') and image_url != "Image not found" else "N/A",
            "url": url
        }

    except requests.exceptions.HTTPError as e:
        print(f"SCRAPER_HTTP_ERROR for {url}: {e}")
        if e.response is not None:
            print(f"SCRAPER_HTTP_ERROR_CONTENT (first 500 chars if any): {e.response.text[:500]}")
        return None # Indicates failure to scrape
    except requests.exceptions.Timeout as e:
        print(f"SCRAPER_TIMEOUT for {url}: {e}")
        return None
    except requests.exceptions.ConnectionError as e:
        print(f"SCRAPER_CONNECTION_ERROR for {url}: {e}")
        return None
    except requests.exceptions.RequestException as e: # Catch other general request exceptions
        print(f"SCRAPER_REQUEST_EXCEPTION for {url}: {e}")
        return None
    except Exception as e: # Catch any other exceptions during parsing (e.g., AttributeError if HTML is unexpected)
        import traceback # Import for printing full traceback
        print(f"SCRAPER_GENERAL_PARSING_EXCEPTION scraping {url}: {e}")
        print(traceback.format_exc()) # Print full traceback for these unexpected parsing errors
        return None


# --- Placeholder Scrapers for Bonus ---
def search_flipkart_and_get_top_product(query):
    """
    VERY basic placeholder to demonstrate flow. Will likely not work reliably.
    """
    search_url = f"https://www.flipkart.com/search?q={quote_plus(query)}"
    print(f"SCRAPER (Flipkart): Attempting to search with URL: {search_url}")
    try:
        response = requests.get(search_url, headers=HEADERS, timeout=15)
        response.raise_for_status() # Check for HTTP errors
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # These selectors are examples and EXTREMELY UNRELIABLE for Flipkart
        name_el = soup.select_one('div._4rR01T, a.s1Q9rs, .IRpwTa') 
        name = name_el.get_text(strip=True) if name_el else "Name not found on Flipkart"
        price_el = soup.select_one('div._30jeq3._1_WHN1, div._30jeq3')
        price = clean_price(price_el.get_text(strip=True)) if price_el else None
        link_el = soup.find('a', class_='_1fQZEK') or soup.find('a', class_='s1Q9rs') or soup.find('a', class_='IRpwTa')
        url = "https://www.flipkart.com" + link_el['href'] if link_el and link_el.get('href') and link_el['href'].startswith('/') else (link_el.get('href') if link_el else search_url)

        if price is not None:
            return {"platform": "Flipkart", "name": name, "price": price, "url": url}
        else:
            return {"platform": "Flipkart", "name": name, "price": "N/A", "url": url, "error": "Price not found with basic selectors"}
            
    except requests.exceptions.RequestException as e:
        print(f"SCRAPER (Flipkart): Request failed for query '{query}': {e}")
        return {"platform": "Flipkart", "name": query, "price": "N/A", "url": search_url, "error": f"Request failed: {e}"}
    except Exception as e:
        print(f"SCRAPER (Flipkart): Error scraping Flipkart for query '{query}': {e}")
        return {"platform": "Flipkart", "name": query, "price": "N/A", "url": search_url, "error": f"General scraping error: {e}"}

def search_meesho_and_get_top_product(query):
    """
    VERY basic placeholder. Meesho is very hard to scrape without browser automation.
    """
    search_url = f"https://www.meesho.com/search?q={quote_plus(query)}"
    print(f"SCRAPER (Meesho): Attempting to search for '{query}'. This is a placeholder.")
    try:
        response = requests.get(search_url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        # Meaningful parsing of Meesho with just requests/BS4 is highly improbable.
        print(f"SCRAPER (Meesho): Accessed search page for '{query}'. Detailed data extraction not implemented.")
    except requests.exceptions.RequestException as e:
        print(f"SCRAPER (Meesho): Request to Meesho failed for query '{query}': {e}") # e.g., 403 Forbidden
    except Exception as e:
        print(f"SCRAPER (Meesho): Error during Meesho placeholder search for query '{query}': {e}")
        
    return {"platform": "Meesho", "name": f"Search results for '{query}' on Meesho", "price": "N/A", "url": search_url, "error": "Meesho scraping requires advanced browser automation techniques."}


if __name__ == '__main__':
    # Test the Amazon scraper with a few URLs
    test_urls_amazon = [
        "https://www.amazon.in/dp/B0CV7KZLL4/", # Samsung Galaxy M14 (from assignment)
        "https://www.amazon.in/Apple-iPhone-15-128-GB/dp/B0CHX1W1XY/", # iPhone 15
        "https://www.amazon.in/dp/B0CS5XW6TN/", # Samsung Galaxy S24 Ultra
        "https://www.amazon.in/dp/B0B27NFLTY/" # Spigen Camera Lens Protector
    ]

    for test_url in test_urls_amazon:
        print(f"\n--- Testing Amazon Scraper with URL: {test_url} ---")
        details_amazon = scrape_amazon_product_details(test_url)
        if details_amazon:
            print(f"Name: {details_amazon['name']}")
            print(f"Price: ₹{details_amazon['price']:.2f}" if details_amazon['price'] is not None and details_amazon['price'] > 0 else f"Price: {details_amazon['price']}")
            print(f"Image URL: {details_amazon['image_url']}")
            print(f"Original URL: {details_amazon['url']}")
        else:
            print("Failed to retrieve Amazon product details for this URL during test.")
        print("-" * 30)

    # Test placeholder scrapers (expect limited results)
    # test_query_flipkart = "iPhone 15 128GB Blue"
    # print(f"\n--- Testing Flipkart Scraper with query: '{test_query_flipkart}' ---")
    # details_flipkart = search_flipkart_and_get_top_product(test_query_flipkart)
    # print(details_flipkart)

    # test_query_meesho = "Cotton Saree Red"
    # print(f"\n--- Testing Meesho Scraper with query: '{test_query_meesho}' ---")
    # details_meesho = search_meesho_and_get_top_product(test_query_meesho)
    # print(details_meesho)