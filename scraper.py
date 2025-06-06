# scraper.py
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import quote_plus
import json
import random # Import the random module

# --- User-Agent List ---
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36 Edg/92.0.902.67',
    # You can add more User-Agents from real browsers here
]

def get_random_headers():
    """
    Returns a dictionary of headers with a randomly chosen User-Agent.
    """
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept-Language': 'en-US,en;q=0.9,hi;q=0.8',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Referer': 'https://www.google.com/'
    }

def clean_price(price_str):
    if price_str is None:
        return None
    cleaned = re.sub(r'[^\d.]', '', price_str)
    try:
        return float(cleaned)
    except ValueError:
        print(f"SCRAPER_CLEAN_PRICE: Could not convert '{cleaned}' (from original: '{price_str}') to float.")
        return None

def scrape_amazon_product_details(url):
    print(f"SCRAPER: Attempting to scrape Amazon URL: {url}")
    try:
        response = requests.get(url, headers=get_random_headers(), timeout=15) # Using random headers
        
        print(f"SCRAPER: Received status code {response.status_code} for URL: {url} (User-Agent: {response.request.headers.get('User-Agent')})")

        if response.status_code == 500:
            print(f"SCRAPER_ERROR_DETAIL: Received 500 Internal Server Error from Amazon.")
            print(f"SCRAPER_ERROR_DETAIL: Response Headers from Amazon: {response.headers}")
            print(f"SCRAPER_ERROR_DETAIL: Response text from Amazon (first 1000 chars): {response.text[:1000]}")
        
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        name_selectors = [
            '#productTitle', 'span#productTitle', '#title', 'h1#title', 
            'h1#title > span#productTitle'
        ]
        name = "Name not found"
        for selector in name_selectors:
            name_element = soup.select_one(selector)
            if name_element:
                name = name_element.get_text(strip=True)
                if name and name != "Back to results": break
        print(f"SCRAPER_DEBUG: Raw Name Found: '{name}'")

        price = None
        price_texts_seen = []
        price_selector_strings = [
            'span.a-price-whole', 'span.a-price .a-offscreen', '#corePrice_feature_div span.a-offscreen',
            'div#corePrice_feature_div span.a-price-whole', '#priceblock_ourprice', '#priceblock_dealprice',
            '.priceToPay span.a-price-whole', 'span[data-a-size="xl"] span.a-price-whole',
            'div.a-section table#buyNew_noncbb tbody tr.a-spacing-small td.a-span12 span#price_inside_buybox',
            'div#apex_desktop_newAccordionRow span.apexPriceToPay', 'span#sns-base-price', '#price_inside_buybox'
        ]
        
        for selector_str in price_selector_strings:
            price_el = soup.select_one(selector_str)
            if price_el:
                price_text = price_el.get_text(strip=True)
                price_texts_seen.append(f"'{selector_str}': '{price_text}'")
                price = clean_price(price_text)
                if price is not None and price > 0: break
        
        if price is None or price == 0.0:
            print("SCRAPER_DEBUG: Price not found via specific selectors. Trying currency symbol search.")
            potential_price_elements = soup.find_all(string=re.compile(r'₹|\$'))
            for text_node in potential_price_elements:
                parent = text_node.parent; attempts = 0
                while parent and attempts < 3:
                    price_text_candidate = parent.get_text(strip=True)
                    if len(price_text_candidate) < 50:
                        price_texts_seen.append(f"(Currency Symbol Search - Parent <{parent.name}>): '{price_text_candidate}'")
                        price = clean_price(price_text_candidate)
                        if price is not None and price > 0: break
                    parent = parent.parent; attempts += 1
                if price is not None and price > 0: break
        
        print(f"SCRAPER_DEBUG: All price texts evaluated: {price_texts_seen}")
        print(f"SCRAPER_DEBUG: Final Price Found: {price if price is not None else 'N/A'}")
        if price is None: price = 0.0

        image_url = "Image not found"
        img_selector_strings = [
            '#landingImage', '#imgTagWrapperId img', '#imgBlkFront', '#ivLargeImage',
            '#main-image-container img', 'div#altImages ul.a-unordered-list li.selected img'
        ]
        for selector_str in img_selector_strings:
            img_tag = soup.select_one(selector_str)
            if img_tag:
                potential_src = img_tag.get('src') or img_tag.get('data-src') or img_tag.get('data-old-hires')
                if potential_src and potential_src.startswith('http'):
                    image_url = potential_src; break
        
        if (image_url == "Image not found" or not image_url.startswith('http')):
            dynamic_image_elements = soup.select('img[data-a-dynamic-image]')
            if dynamic_image_elements:
                first_image_data_str = dynamic_image_elements[0].get('data-a-dynamic-image')
                if first_image_data_str:
                    try:
                        image_json_data = json.loads(first_image_data_str)
                        image_url = list(image_json_data.keys())[0]
                    except (json.JSONDecodeError, IndexError, TypeError) as e:
                        print(f"SCRAPER_DEBUG: Error parsing dynamic image JSON: {e}")
                        image_url = "Image not found"
        print(f"SCRAPER_DEBUG: Image URL Found: '{image_url}'")

        return {"name": name if name and name != "Name not found" else "N/A", "price": price, "image_url": image_url if image_url and image_url.startswith('http') and image_url != "Image not found" else "N/A", "url": url}

    except requests.exceptions.HTTPError as e:
        print(f"SCRAPER_HTTP_ERROR for {url}: {e} (User-Agent: {response.request.headers.get('User-Agent') if 'response' in locals() and response.request else 'N/A'})")
        if e.response is not None: print(f"SCRAPER_HTTP_ERROR_CONTENT (first 500 chars if any): {e.response.text[:500]}")
        return None
    except requests.exceptions.Timeout as e: print(f"SCRAPER_TIMEOUT for {url}: {e}"); return None
    except requests.exceptions.ConnectionError as e: print(f"SCRAPER_CONNECTION_ERROR for {url}: {e}"); return None
    except requests.exceptions.RequestException as e: print(f"SCRAPER_REQUEST_EXCEPTION for {url}: {e}"); return None
    except Exception as e:
        import traceback
        print(f"SCRAPER_GENERAL_PARSING_EXCEPTION scraping {url}: {e}")
        print(traceback.format_exc())
        return None

# --- Placeholder Scrapers for Bonus ---
def search_flipkart_and_get_top_product(query):
    search_url = f"https://www.flipkart.com/search?q={quote_plus(query)}"
    print(f"SCRAPER (Flipkart): Attempting to search with URL: {search_url}")
    try:
        response = requests.get(search_url, headers=get_random_headers(), timeout=15) # Using random headers
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        name_el = soup.select_one('div._4rR01T, a.s1Q9rs, .IRpwTa') 
        name = name_el.get_text(strip=True) if name_el else "Name not found on Flipkart"
        price_el = soup.select_one('div._30jeq3._1_WHN1, div._30jeq3')
        price = clean_price(price_el.get_text(strip=True)) if price_el else None
        link_el = soup.find('a', class_='_1fQZEK') or soup.find('a', class_='s1Q9rs') or soup.find('a', class_='IRpwTa')
        url = "https://www.flipkart.com" + link_el['href'] if link_el and link_el.get('href') and link_el['href'].startswith('/') else (link_el.get('href') if link_el else search_url)
        if price is not None: return {"platform": "Flipkart", "name": name, "price": price, "url": url}
        else: return {"platform": "Flipkart", "name": name, "price": "N/A", "url": url, "error": "Price not found with basic selectors"}
    except requests.exceptions.RequestException as e:
        print(f"SCRAPER (Flipkart): Request failed for query '{query}': {e}")
        return {"platform": "Flipkart", "name": query, "price": "N/A", "url": search_url, "error": f"Request failed: {e}"}
    except Exception as e:
        print(f"SCRAPER (Flipkart): Error scraping Flipkart for query '{query}': {e}")
        return {"platform": "Flipkart", "name": query, "price": "N/A", "url": search_url, "error": f"General scraping error: {e}"}

def search_meesho_and_get_top_product(query):
    search_url = f"https://www.meesho.com/search?q={quote_plus(query)}"
    print(f"SCRAPER (Meesho): Attempting to search for '{query}'. This is a placeholder.")
    try:
        response = requests.get(search_url, headers=get_random_headers(), timeout=15) # Using random headers
        response.raise_for_status()
        print(f"SCRAPER (Meesho): Accessed search page for '{query}'. Detailed data extraction not implemented.")
    except requests.exceptions.RequestException as e:
        print(f"SCRAPER (Meesho): Request to Meesho failed for query '{query}': {e}")
    except Exception as e:
        print(f"SCRAPER (Meesho): Error during Meesho placeholder search for query '{query}': {e}")
    return {"platform": "Meesho", "name": f"Search results for '{query}' on Meesho", "price": "N/A", "url": search_url, "error": "Meesho scraping requires advanced browser automation techniques."}


if __name__ == '__main__':
    test_urls_amazon = [
        "https://www.amazon.in/dp/B0CV7KZLL4/", 
        "https://www.amazon.in/Apple-iPhone-15-128-GB/dp/B0CHX1W1XY/",
        "https://www.amazon.in/dp/B0CS5XW6TN/",
        "https://www.amazon.in/dp/B0B27NFLTY/" 
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