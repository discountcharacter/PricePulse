# app.py
print("DEBUG: app.py (Web Service) script started")

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import os
import datetime
from dotenv import load_dotenv

# Load environment variables from .env file (especially for local development)
# On Render, these will be set in the dashboard.
load_dotenv()

# --- Project specific imports ---
from database import db, Product, PriceHistory, Alert
from scraper import scrape_amazon_product_details, search_flipkart_and_get_top_product, search_meesho_and_get_top_product
from apscheduler.schedulers.background import BackgroundScheduler # For defining jobs

# For AI Bonus (ensure llm_helper.py exists and is correct)
from llm_helper import extract_metadata_and_generate_queries

print("DEBUG: Imports in app.py successful")

app = Flask(__name__)

# --- Database Configuration ---
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")
if SQLALCHEMY_DATABASE_URL:
    if SQLALCHEMY_DATABASE_URL.startswith("postgres://"): # Render provides postgres://
        SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)
    print(f"DEBUG: Using DATABASE_URL from environment: {SQLALCHEMY_DATABASE_URL[:30]}...") # Print only a part for security
else:
    print("DEBUG: DATABASE_URL not found in environment, falling back to local SQLite.")
    SQLALCHEMY_DATABASE_URL = 'sqlite:///pricepulse.db'

app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", os.urandom(24)) # Use env var for SECRET_KEY

print("DEBUG: Flask app configured")

db.init_app(app)
print("DEBUG: Database initialized with app")
with app.app_context():
    db.create_all()
    print("DEBUG (app.py - WEB): db.create_all() CALLED ON APP INITIALIZATION.")

# --- Global Scheduler Instance ---
# This instance is used by the web app to ADD job definitions.
# The actual running of the scheduler (scheduler.start()) will be handled by run_scheduler.py in the worker.
# For this to work seamlessly across processes, APScheduler would ideally be configured
# with a persistent job store (e.g., SQLAlchemyJobStore using the PostgreSQL DB).
# For simplicity now, we assume the worker (run_scheduler.py) will also poll the DB
# on its startup to ensure jobs for all existing products are scheduled in its own instance.
scheduler = BackgroundScheduler(daemon=True, timezone="UTC")
# DO NOT START THE SCHEDULER HERE in the web service (app.py)
# scheduler.start() # <-- This line should be in run_scheduler.py
print("DEBUG: Scheduler instance defined in app.py (but not started by web service).")


def job_scrape_product_wrapper(product_id):
    """
    Wrapper function for the scheduler to call job_scrape_product
    within the Flask application context. This needs to be accessible by both
    app.py (if adding jobs) and run_scheduler.py (if it imports this).
    It's better if run_scheduler.py has its own direct call to scheduler.py's job.
    For now, this is here as it was part of app.py's original structure.
    """
    print(f"DEBUG (app.py wrapper): job_scrape_product_wrapper called for product_id: {product_id}")
    with app.app_context(): # 'app' here refers to the global Flask app instance
        from scheduler import job_scrape_product
        job_scrape_product(app, product_id)
    print(f"DEBUG (app.py wrapper): job_scrape_product_wrapper finished for product_id: {product_id}")


def initialize_web_application_startup(current_app):
    """
    Function to handle application startup tasks specifically for the WEB SERVICE:
    - Create database tables if they don't exist.
    The scheduler itself and its jobs will be managed by the separate background worker process.
    """
    print("DEBUG (app.py - WEB): initialize_web_application_startup() called")
    with current_app.app_context():
        db.create_all()
        print("DEBUG (app.py - WEB): db.create_all() done in initialize_web_application_startup")
        # No scheduler start or job loading here for the web service.

# --- Flask Routes ---

@app.route('/', methods=['GET'])
def home():
    print("DEBUG (app.py - WEB): Route '/' called")
    products = Product.query.order_by(Product.created_at.desc()).all()
    return render_template('index.html', products=products)

@app.route('/track_product', methods=['POST'])
def track_product():
    print("DEBUG (app.py - WEB): Route '/track_product' called")
    url = request.form.get('product_url')
    if not url or "amazon" not in url.lower():
        flash("Please enter a valid Amazon product URL.", "error")
        return redirect(url_for('home'))

    product = Product.query.filter_by(url=url).first()
    if product:
        flash(f"Product '{product.name or 'this URL'}' is already being tracked.", "info")
        return redirect(url_for('product_detail', product_id=product.id))

    print(f"DEBUG (app.py - WEB): Attempting initial scrape for new URL: {url}")
    details = scrape_amazon_product_details(url)

    if not details or details.get("price") is None:
        flash(f"Could not retrieve initial product details from {url}. Check URL or try again later.", "error")
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

    # The web service can attempt to add the job definition.
    # The background worker (run_scheduler.py) will be the one actually running the scheduler
    # and should also have logic to pick up any products from the DB that don't have active jobs.
    job_id = f'scrape_product_{new_product.id}'
    # Note: Accessing scheduler.get_job() or scheduler.add_job() here might interact
    # with a MemoryJobStore if a persistent one isn't configured for APScheduler.
    # For a robust multi-process setup, a persistent job store (e.g., SQLAlchemyJobStore)
    # for APScheduler is recommended.
    # For now, we assume the worker (run_scheduler.py) will handle ensuring jobs are active.
    print(f"DEBUG (app.py - WEB): Product {new_product.id} added. Worker process should schedule it.")

    return redirect(url_for('product_detail', product_id=new_product.id))

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    print(f"DEBUG (app.py - WEB): Route '/product/{product_id}' called")
    product = Product.query.get_or_404(product_id)
    prices = PriceHistory.query.filter_by(product_id=product.id).order_by(PriceHistory.timestamp.asc()).all()
    return render_template('product_detail.html', product=product, prices=prices)

@app.route('/api/product/<int:product_id>/prices')
def api_product_prices(product_id):
    print(f"DEBUG (app.py - WEB): Route '/api/product/{product_id}/prices' called")
    product = Product.query.get(product_id)
    if not product:
        return jsonify({"error": "Product not found"}), 404
        
    prices_query = PriceHistory.query.filter_by(product_id=product_id).order_by(PriceHistory.timestamp.asc()).all()
    if not prices_query:
        return jsonify([])
        
    price_data = [{"timestamp": p.timestamp.isoformat(), "price": p.price} for p in prices_query]
    return jsonify(price_data)

@app.route('/delete_product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    print(f"DEBUG (app.py - WEB): Route '/delete_product/{product_id}' called")
    product_to_delete = Product.query.get_or_404(product_id)
    job_id = f'scrape_product_{product_to_delete.id}'
    
    # The web service might not have direct control over the worker's scheduler instance
    # to remove a job effectively without a shared job store.
    # The worker's scheduler should ideally handle jobs for non-existent products gracefully.
    # For now, we'll log the intent.
    print(f"DEBUG (app.py - WEB): Product {product_id} deletion requested. Worker process should stop scheduling job {job_id} if it's running.")
    # if scheduler.get_job(job_id): # This might not reflect the worker's scheduler state
    #     try:
    #         scheduler.remove_job(job_id)
    #     except Exception as e:
    #         print(f"DEBUG (app.py - WEB): Error trying to remove job {job_id} from web instance scheduler: {e}")

    db.session.delete(product_to_delete)
    db.session.commit()
    flash(f"Product '{product_to_delete.name}' and its tracking data have been deleted.", "success")
    return redirect(url_for('home'))

@app.route('/add_alert/<int:product_id>', methods=['POST'])
def add_alert(product_id):
    print(f"DEBUG (app.py - WEB): Route '/add_alert/{product_id}' called")
    product = Product.query.get_or_404(product_id)
    email_address = request.form.get('email')
    target_price_str = request.form.get('target_price')

    if not email_address or not target_price_str:
        flash("Email and target price are required.", "error")
        return redirect(url_for('product_detail', product_id=product_id))
    
    try:
        target_price_float = float(target_price_str)
        if target_price_float <= 0:
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

@app.route('/product/<int:product_id>/trigger_comparison', methods=['POST'])
def trigger_product_comparison(product_id):
    product = Product.query.get_or_404(product_id)
    print(f"APP (WEB - Comparison): Triggering comparison for Product ID {product_id}: {product.name}")

    if not product.name or product.name in ["N/A", "Name not found"]:
        flash("Product name not available, cannot perform AI comparison.", "error")
        return redirect(url_for('product_detail', product_id=product_id))

    llm_data = extract_metadata_and_generate_queries(product.name, product.url)
    
    if "Error" in llm_data.get("metadata", {}):
        flash(f"LLM processing error: {llm_data['metadata']['Error']}", "warning")
        search_queries = {"Flipkart": product.name, "Meesho": product.name}
    else:
        search_queries = llm_data.get("search_queries", {"Flipkart": product.name, "Meesho": product.name})
    
    comparison_results_display = []

    flipkart_query = search_queries.get("Flipkart", product.name) 
    if flipkart_query:
        print(f"APP (WEB - Comparison): Searching Flipkart with query: '{flipkart_query}'")
        flipkart_data = search_flipkart_and_get_top_product(flipkart_query)
        if flipkart_data:
            comparison_results_display.append(f"Flipkart: {flipkart_data.get('name', 'N/A')} - Price: {flipkart_data.get('price', 'N/A')}")

    meesho_query = search_queries.get("Meesho", product.name)
    if meesho_query:
        print(f"APP (WEB - Comparison): Searching Meesho with query: '{meesho_query}'")
        meesho_data = search_meesho_and_get_top_product(meesho_query)
        if meesho_data:
            comparison_results_display.append(f"Meesho: {meesho_data.get('name', 'N/A')} - Price: {meesho_data.get('price', 'N/A')}")
    
    if comparison_results_display:
        flash_message = "Comparison search results (logged to server): " + " | ".join(comparison_results_display)
        flash(flash_message, "info")
    else:
        flash("Could not find comparison data from other platforms with current methods, or LLM/scrapers encountered issues.", "warning")

    return redirect(url_for('product_detail', product_id=product_id))

# --- Main execution block (for local development or if run directly by WSGI server) ---
if __name__ == '__main__':
    print("DEBUG (app.py - WEB): Inside __main__ block for web server")
    # Call the initialization function that's safe for the web service
    initialize_web_application_startup(app) 
    
    port = int(os.getenv("PORT", 5000)) # Render sets PORT environment variable
    debug_mode = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1", "t")

    print(f"DEBUG (app.py - WEB): About to call app.run() on host 0.0.0.0, port {port}, debug={debug_mode}")
    # For Render, Gunicorn will be the entry point, not this app.run().
    # However, this is useful for local development.
    app.run(debug=debug_mode, host='0.0.0.0', port=port)
    print("DEBUG (app.py - WEB): app.run() has finished (This should only appear if the server was stopped locally, e.g. CTRL+C)")