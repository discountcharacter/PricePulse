# app.py
print("DEBUG: app.py script started")
from dotenv import load_dotenv
load_dotenv()
print("DEBUG: app.py script started")

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import os
import datetime # Ensure datetime is imported

# --- Project specific imports ---
from database import db, Product, PriceHistory, Alert # Make sure ProductComparison is added to database.py if you implement it
# Ensure scraper.py has all these functions if you use them for the bonus
from scraper import scrape_amazon_product_details, search_flipkart_and_get_top_product, search_meesho_and_get_top_product
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

# For AI Bonus (ensure llm_helper.py exists and is correct)
from llm_helper import extract_metadata_and_generate_queries

print("DEBUG: Imports in app.py successful")

load_dotenv() # Load environment variables from .env file

app = Flask(__name__)
# Get the database URL from the environment variable set by Render (or your .env for local)
# RENDER_POSTGRES_INTERNAL_URL is an example, Render might use DATABASE_URL
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL") # Render typically sets DATABASE_URL for its PostgreSQL
if SQLALCHEMY_DATABASE_URL and SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URL or 'sqlite:///pricepulse.db' # Fallback to SQLite for local if DATABASE_URL not set
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.getenv("SECRET_KEY", os.urandom(24)) # Also use env var for secret key

print("DEBUG: Flask app initialized")

db.init_app(app)
print("DEBUG: Database initialized with app")

# --- Global Scheduler Instance ---
scheduler = BackgroundScheduler(daemon=True, timezone="UTC") # Added timezone for clarity
print("DEBUG: Scheduler instance created")

def job_scrape_product_wrapper(product_id):
    """
    Wrapper function for the scheduler to call job_scrape_product
    within the Flask application context.
    """
    print(f"DEBUG (app.py wrapper): job_scrape_product_wrapper called for product_id: {product_id}")
    with app.app_context():
        from scheduler import job_scrape_product # Import here to use the latest scheduler.py
        job_scrape_product(app, product_id) # Pass the app instance
    print(f"DEBUG (app.py wrapper): job_scrape_product_wrapper finished for product_id: {product_id}")

def initialize_application_startup(current_app):
    """
    Function to handle application startup tasks:
    - Create database tables.
    - Initialize and start the scheduler with jobs for existing products.
    """
    print("DEBUG (app.py): initialize_application_startup() called")
    with current_app.app_context():
        db.create_all() # Create database tables if they don't exist
        print("DEBUG (app.py): db.create_all() done in initialize_application_startup")

        products_to_track = Product.query.all()
        print(f"DEBUG (app.py): Found {len(products_to_track)} products in DB during startup.")
        for p in products_to_track:
            job_id = f'scrape_product_{p.id}'
            if not scheduler.get_job(job_id):
                print(f"DEBUG (app.py): Adding job for existing product {p.id} ('{p.name}') in startup.")
                scheduler.add_job(
                    job_scrape_product_wrapper,
                    'interval',
                    minutes=30, # As per assignment: "every 30 minutes or 1 hour" [cite: 2]
                    args=[p.id],
                    id=job_id,
                    replace_existing=True
                )
            else:
                print(f"DEBUG (app.py): Job for product {p.id} ('{p.name}') already exists (startup check).")

        if not scheduler.running:
            try:
                scheduler.start()
                print("DEBUG (app.py): Scheduler started in initialize_application_startup")
            except Exception as e:
                print(f"DEBUG (app.py): Error starting scheduler in initialize_application_startup: {e}")
        else:
            print("DEBUG (app.py): Scheduler was already running (startup check).")

# --- Flask Routes ---

@app.route('/', methods=['GET'])
def home():
    print("DEBUG (app.py): Route '/' called")
    products = Product.query.order_by(Product.created_at.desc()).all()
    return render_template('index.html', products=products)

@app.route('/track_product', methods=['POST'])
def track_product():
    print("DEBUG (app.py): Route '/track_product' called")
    url = request.form.get('product_url')
    if not url or "amazon" not in url.lower():
        flash("Please enter a valid Amazon product URL.", "error")
        return redirect(url_for('home'))

    product = Product.query.filter_by(url=url).first()
    if product:
        flash(f"Product '{product.name or 'this URL'}' is already being tracked.", "info")
        return redirect(url_for('product_detail', product_id=product.id))

    print(f"DEBUG (app.py): Attempting initial scrape for new URL: {url}")
    details = scrape_amazon_product_details(url)

    if not details or details.get("price") is None:
        flash(f"Could not retrieve initial product details from {url}. Amazon might have blocked the request, the page structure might be different, or the product is unavailable. Please try another URL.", "error")
        return redirect(url_for('home'))

    new_product = Product(
        url=url,
        name=details.get('name', "N/A"),
        image_url=details.get('image_url', "N/A")
    )
    db.session.add(new_product)
    db.session.commit()

    first_price = PriceHistory(product_id=new_product.id, price=details["price"], timestamp=datetime.datetime.utcnow())
    db.session.add(first_price)
    db.session.commit()
    
    flash(f"Started tracking: {new_product.name or 'New Product'}", "success")

    job_id = f'scrape_product_{new_product.id}'
    if not scheduler.get_job(job_id):
        scheduler.add_job(
            job_scrape_product_wrapper,
            'interval',
            minutes=30, # As per assignment [cite: 2]
            args=[new_product.id],
            id=job_id,
            replace_existing=True
        )
        print(f"DEBUG (app.py): Added new scrape job for product ID {new_product.id}: {new_product.name}")
    
    if not scheduler.running:
        try:
            scheduler.start()
            print("DEBUG (app.py): Scheduler (re)started in track_product.")
        except Exception as e:
             print(f"DEBUG (app.py): Error starting scheduler in track_product: {e}")

    return redirect(url_for('product_detail', product_id=new_product.id))

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    print(f"DEBUG (app.py): Route '/product/{product_id}' called")
    product = Product.query.get_or_404(product_id)
    prices = PriceHistory.query.filter_by(product_id=product.id).order_by(PriceHistory.timestamp.asc()).all()
    
    # For bonus multi-platform - this assumes you have a ProductComparison model and relationship
    # defined in database.py and linked to Product model with a backref like 'comparisons'
    # comparisons = product.comparisons # Access via relationship
    # return render_template('product_detail.html', product=product, prices=prices, comparisons=comparisons)
    return render_template('product_detail.html', product=product, prices=prices)

@app.route('/api/product/<int:product_id>/prices')
def api_product_prices(product_id):
    print(f"DEBUG (app.py): Route '/api/product/{product_id}/prices' called")
    product = Product.query.get(product_id) # Check if product exists
    if not product:
        return jsonify({"error": "Product not found"}), 404 # Return 404 if no product
        
    prices_query = PriceHistory.query.filter_by(product_id=product_id).order_by(PriceHistory.timestamp.asc()).all()
    if not prices_query: # Check if there are any prices
        return jsonify([]) # Return empty list if no prices, chart.js should handle this
        
    price_data = [{"timestamp": p.timestamp.isoformat(), "price": p.price} for p in prices_query]
    return jsonify(price_data)

@app.route('/delete_product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    print(f"DEBUG (app.py): Route '/delete_product/{product_id}' called")
    product_to_delete = Product.query.get_or_404(product_id)
    job_id = f'scrape_product_{product_to_delete.id}'
    
    if scheduler.get_job(job_id):
        try:
            scheduler.remove_job(job_id)
            print(f"DEBUG (app.py): Removed job {job_id} from scheduler for product '{product_to_delete.name}'.")
        except Exception as e: # Catch specific scheduler exceptions if known, otherwise general Exception
            print(f"DEBUG (app.py): Error removing job {job_id} from scheduler: {e}")

    db.session.delete(product_to_delete)
    db.session.commit()
    flash(f"Product '{product_to_delete.name}' and its tracking data have been deleted.", "success")
    return redirect(url_for('home'))

@app.route('/add_alert/<int:product_id>', methods=['POST'])
def add_alert(product_id):
    print(f"DEBUG (app.py): Route '/add_alert/{product_id}' called")
    product = Product.query.get_or_404(product_id)
    email_address = request.form.get('email')
    target_price_str = request.form.get('target_price')

    if not email_address or not target_price_str:
        flash("Email and target price are required.", "error")
        return redirect(url_for('product_detail', product_id=product_id))
    
    try:
        target_price_float = float(target_price_str)
        if target_price_float <= 0: # Price should be positive
            flash("Target price must be a positive value.", "error")
            return redirect(url_for('product_detail', product_id=product_id))
    except ValueError:
        flash("Invalid target price format. Please enter a number.", "error")
        return redirect(url_for('product_detail', product_id=product_id))

    existing_alert = Alert.query.filter_by(
        product_id=product.id, 
        email=email_address, 
        target_price=target_price_float, 
        is_active=True
    ).first()

    if existing_alert:
        flash(f"An active alert for ₹{target_price_float:.2f} already exists for this product and email ({email_address}).", "info")
    else:
        new_alert = Alert(product_id=product.id, email=email_address, target_price=target_price_float, is_active=True)
        db.session.add(new_alert)
        db.session.commit()
        flash(f"Success! Alert set for {product.name}. You'll be notified at {email_address} if the price drops below ₹{target_price_float:.2f}.", "success")
    
    return redirect(url_for('product_detail', product_id=product_id))

# --- Bonus AI Comparison Route ---
@app.route('/product/<int:product_id>/trigger_comparison', methods=['POST'])
def trigger_product_comparison(product_id):
    product = Product.query.get_or_404(product_id)
    print(f"APP (Comparison): Triggering comparison for Product ID {product_id}: {product.name}")

    if not product.name or product.name in ["N/A", "Name not found"]:
        flash("Product name not available, cannot perform AI comparison.", "error")
        return redirect(url_for('product_detail', product_id=product_id))

    # Call LLM helper
    llm_data = extract_metadata_and_generate_queries(product.name, product.url)
    
    if "Error" in llm_data.get("metadata", {}): # Check if metadata extraction itself had an error
        flash(f"LLM processing error: {llm_data['metadata']['Error']}", "warning")
        # Fallback to using product name for searches if queries are missing
        search_queries = {
            "Flipkart": product.name,
            "Meesho": product.name
        }
    else:
        search_queries = llm_data.get("search_queries", { # Ensure search_queries is a dict
            "Flipkart": product.name, # Fallback if "search_queries" key is missing
            "Meesho": product.name
        })
    
    comparison_results_display = [] # For flashing messages or session

    # --- Flipkart ---
    flipkart_query = search_queries.get("Flipkart", product.name) 
    if flipkart_query:
        print(f"APP (Comparison): Searching Flipkart with query: '{flipkart_query}'")
        flipkart_data = search_flipkart_and_get_top_product(flipkart_query) # From scraper.py
        if flipkart_data:
            comparison_results_display.append(f"Flipkart: {flipkart_data.get('name', 'N/A')} - Price: {flipkart_data.get('price', 'N/A')}")
            # If you implement ProductComparison model:
            # comp_fk = ProductComparison(original_product_id=product.id, platform_name="Flipkart", ...)
            # db.session.add(comp_fk)

    # --- Meesho ---
    meesho_query = search_queries.get("Meesho", product.name)
    if meesho_query:
        print(f"APP (Comparison): Searching Meesho with query: '{meesho_query}'")
        meesho_data = search_meesho_and_get_top_product(meesho_query) # From scraper.py
        if meesho_data:
            comparison_results_display.append(f"Meesho: {meesho_data.get('name', 'N/A')} - Price: {meesho_data.get('price', 'N/A')}")
            # If you implement ProductComparison model:
            # comp_m = ProductComparison(original_product_id=product.id, platform_name="Meesho", ...)
            # db.session.add(comp_m)
    
    # db.session.commit() # If saving ProductComparison objects to DB

    if comparison_results_display:
        flash_message = "Comparison search results (logged to server): " + " | ".join(comparison_results_display)
        flash(flash_message, "info")
    else:
        flash("Could not find comparison data from other platforms with current methods, or LLM/scrapers encountered issues.", "warning")

    return redirect(url_for('product_detail', product_id=product_id))


# --- Main execution block ---
if __name__ == '__main__':
    print("DEBUG (app.py): Inside __main__ block")

    # Call the initialization function explicitly when running the script directly
    initialize_application_startup(app) # This creates tables and starts scheduler with existing jobs

    print("DEBUG (app.py): About to call app.run()")
    # use_reloader=False is important for APScheduler not to run its jobs twice in debug mode
    # and to prevent issues with some versions of Werkzeug reloader and background threads.
    app.run(debug=True, use_reloader=False) 
    print("DEBUG (app.py): app.run() has finished (This should only appear if the server was stopped, e.g. CTRL+C)")