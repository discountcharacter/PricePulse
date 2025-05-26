# scraper.py

import requests
from bs4 import BeautifulSoup
import re
# Ensure these are imported if you use them in the functions below
from urllib.parse import quote_plus 

# --- VERY IMPORTANT ---
HEADERS = ({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9,hi;q=0.8',
    'Referer': 'https://www.google.com/',
    'DNT': '1',
    'Connection': 'keep-alive'
})

def clean_price(price_str):
    if price_str is None:
        return None
    cleaned = re.sub(r'[^\d.]', '', price_str)
    try:
        return float(cleaned)
    except ValueError:
        return None

def scrape_amazon_product_details(url):
    # ... (your existing Amazon scraper code) ...
    print(f"DEBUG: scraper.py - scrape_amazon_product_details called for URL: {url}")
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        name_element = soup.find(id='productTitle') or soup.find('span', id='title_feature_div')
        name = name_element.get_text(strip=True) if name_element else "Name not found"
        
        price = None
        price_elements = soup.select('span.a-offscreen')
        if price_elements:
            for pe in price_elements:
                price_text = pe.get_text(strip=True)
                if price_text.startswith('₹') or price_text.startswith('$'):
                    price = clean_price(price_text)
                    if price: break
        
        if not price:
            price_selectors = [
                '.a-price-whole', '.a-offscreen', '#corePrice_feature_div .a-price-whole',
                '#priceblock_ourprice', '#priceblock_dealprice', '.priceToPay span.a-price-whole',
                'span[data-a-size="xl"]span.a-price-whole'
            ]
            for selector in price_selectors:
                price_el = soup.select_one(selector)
                if price_el:
                    price_text = price_el.get_text(strip=True)
                    price = clean_price(price_text)
                    if price: break
        
        if price is None:
             price = 0.0

        image_url = "Image not found"
        img_tag = soup.find(id='landingImage') or soup.find(id='imgTagWrapperId')
        if img_tag:
            if img_tag.name == 'img':
                 image_url = img_tag.get('src') or img_tag.get('data-old-hires')
            elif img_tag.find('img'):
                 image_url = img_tag.find('img').get('src') or img_tag.find('img').get('data-old-hires')

        if "not found" in image_url or not image_url:
            dynamic_image_elements = soup.select('img[data-a-dynamic-image]')
            if dynamic_image_elements:
                first_image_data = dynamic_image_elements[0].get('data-a-dynamic-image')
                if first_image_data:
                    try:
                        import json
                        image_json = json.loads(first_image_data)
                        image_url = list(image_json.keys())[0]
                    except json.JSONDecodeError:
                        pass

        return {"name": name if name else "N/A", "price": price, "image_url": image_url if image_url else "N/A", "url": url}
    except requests.exceptions.Timeout:
        print(f"Timeout while scraping {url}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Request failed for {url}: {e}")
        return None
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None

# --- Placeholder Scrapers for Bonus ---
# Ensure these functions are defined at the top level (not indented under anything else)

def search_flipkart_and_get_top_product(query):
    """
    VERY basic attempt to search Flipkart and get price of the first result.
    This is a placeholder and highly prone to breaking due to site changes and anti-bot measures.
    """
    search_url = f"https://www.flipkart.com/search?q={quote_plus(query)}"
    print(f"SCRAPER (Flipkart): Attempting to search with URL: {search_url}")
    try:
        response = requests.get(search_url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        product_blocks = soup.select('div._1AtVbE div._13oc-S')
        if not product_blocks: product_blocks = soup.select('div._2kHMtA')
        if not product_blocks: product_blocks = soup.select('div.cPHDOP')

        if not product_blocks:
            print("SCRAPER (Flipkart): No product blocks found with current selectors.")
            return {"platform": "Flipkart", "name": query, "price": "N/A", "url": search_url, "error": "No product blocks found"}

        first_product = product_blocks[0]
        name_el = first_product.select_one('div._4rR01T, a.s1Q9rs, a.IRpwTa, .s1Q9rs, .IRpwTa, ._4rR01T')
        name = name_el.get_text(strip=True) if name_el else "Name not found on Flipkart"
        price_el = first_product.select_one('div._30jeq3._1_WHN1, div._30jeq3')
        price = clean_price(price_el.get_text(strip=True)) if price_el else None
        link_el = first_product.find('a', href=True)
        url = "https://www.flipkart.com" + link_el['href'] if link_el and link_el['href'].startswith('/') else (link_el['href'] if link_el else search_url)

        if price is not None:
            print(f"SCRAPER (Flipkart): Found '{name}' - Price: ₹{price:.2f} - URL: {url}")
            return {"platform": "Flipkart", "name": name, "price": price, "url": url}
        else:
            print(f"SCRAPER (Flipkart): Found '{name}' but could not extract price. URL: {url}")
            return {"platform": "Flipkart", "name": name, "price": "N/A", "url": url, "error": "Price not found"}
    except requests.exceptions.RequestException as e:
        print(f"SCRAPER (Flipkart): Request failed for query '{query}': {e}")
        return {"platform": "Flipkart", "name": query, "price": "N/A", "url": search_url, "error": f"Request failed: {e}"}
    except Exception as e:
        print(f"SCRAPER (Flipkart): Error scraping Flipkart for query '{query}': {e}")
        return {"platform": "Flipkart", "name": query, "price": "N/A", "url": search_url, "error": f"Scraping error: {e}"}

def search_meesho_and_get_top_product(query):
    search_url = f"https://www.meesho.com/search?q={quote_plus(query)}"
    print(f"SCRAPER (Meesho): Attempting to search for '{query}'. Meesho is very difficult to scrape with simple requests.")
    try:
        response = requests.get(search_url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        print(f"SCRAPER (Meesho): Accessed search page for '{query}'. Specific detail extraction is unreliable here.")
    except requests.exceptions.RequestException as e:
        print(f"SCRAPER (Meesho): Request to Meesho failed for query '{query}': {e}")
    except Exception as e:
        print(f"SCRAPER (Meesho): Error during Meesho placeholder search for query '{query}': {e}")
    return {"platform": "Meesho", "name": f"Search results for '{query}' (details not reliably extractable)", "price": "N/A", "url": search_url, "error": "Meesho scraping requires advanced techniques."}

# Keep this if you test scraper.py directly
if __name__ == '__main__':
    test_url_amazon = "https://www.amazon.in/dp/B0CV7KZLL4/"
    print(f"Testing Amazon scraper with URL: {test_url_amazon}")
    details_amazon = scrape_amazon_product_details(test_url_amazon)
    if details_amazon:
        print(f"Amazon - Name: {details_amazon['name']}, Price: {details_amazon['price']}, Image: {details_amazon['image_url']}")
    else:
        print("Failed to retrieve Amazon product details during test.")

    test_query_flipkart = "iPhone 15"
    print(f"\nTesting Flipkart scraper with query: {test_query_flipkart}")
    details_flipkart = search_flipkart_and_get_top_product(test_query_flipkart)
    if details_flipkart:
        print(f"Flipkart - Platform: {details_flipkart.get('platform')}, Name: {details_flipkart.get('name')}, Price: {details_flipkart.get('price')}, URL: {details_flipkart.get('url')}, Error: {details_flipkart.get('error')}")

    test_query_meesho = "saree"
    print(f"\nTesting Meesho scraper with query: {test_query_meesho}")
    details_meesho = search_meesho_and_get_top_product(test_query_meesho)
    if details_meesho:
        print(f"Meesho - Platform: {details_meesho.get('platform')}, Name: {details_meesho.get('name')}, Price: {details_meesho.get('price')}, URL: {details_meesho.get('url')}, Error: {details_meesho.get('error')}")