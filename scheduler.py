# scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler # Not used directly here, app.py manages instance
from scraper import scrape_amazon_product_details # Assuming this is your Amazon scraper function
from database import db, Product, PriceHistory, Alert # Make sure Alert is imported
from mail_sender import send_price_alert_email # Import your email sending function
import datetime

def check_and_send_alerts(app_context, product, current_price):
    """
    Checks active alerts for a product and sends emails if price drops below target.
    Requires an active app_context to be passed or used.
    """
    print(f"SCHEDULER (Alerts): Checking alerts for Product ID {product.id} ({product.name}) - Current Price: ₹{current_price:.2f}")
    # No need for 'with app_context:' here if we assume it's already active when called
    # from job_scrape_product, which runs within its own app_context.
    
    active_alerts = Alert.query.filter_by(product_id=product.id, is_active=True).all()
    
    if not active_alerts:
        # print(f"SCHEDULER (Alerts): No active alerts for {product.name}.")
        return

    print(f"SCHEDULER (Alerts): Found {len(active_alerts)} active alert(s) for {product.name}.")
    for alert in active_alerts:
        print(f"SCHEDULER (Alerts): Checking Alert ID {alert.id} for {alert.email} - Target: ₹{alert.target_price:.2f}")
        if current_price <= alert.target_price:
            print(f"SCHEDULER (Alerts): PRICE DROP! Product: {product.name}, Current: ₹{current_price:.2f}, Target: ₹{alert.target_price:.2f}, Email: {alert.email}")
            
            email_sent_successfully = send_price_alert_email(
                recipient_email=alert.email,
                product_name=product.name,
                product_url=product.url,
                current_price=current_price,
                target_price=alert.target_price,
                product_image_url=product.image_url # Pass image URL
            )
            
            if email_sent_successfully:
                alert.is_active = False # Deactivate alert to prevent re-sending for the same price drop
                db.session.commit() # Save the change to the alert's status
                print(f"SCHEDULER (Alerts): Alert ID {alert.id} for {alert.email} processed and deactivated.")
            else:
                print(f"SCHEDULER (Alerts): Email failed to send for Alert ID {alert.id}. Alert remains active.")
        # else:
        #     print(f"SCHEDULER (Alerts): Price ₹{current_price:.2f} not below target ₹{alert.target_price:.2f} for Alert ID {alert.id}")


def job_scrape_product(app, product_id):
    """
    Scheduled job to scrape a single product, update its price, and check for alerts.
    'app' is the Flask application instance.
    """
    print(f"SCHEDULER: job_scrape_product initiated for Product ID {product_id}")
    with app.app_context(): # Crucial for database and app config access
        product = Product.query.get(product_id)
        if not product:
            print(f"SCHEDULER: Product with ID {product_id} not found for scheduled scrape. Job might be stale.")
            # Consider removing the job from the scheduler if product is deleted
            # scheduler_instance = app.scheduler # If you attach scheduler to app
            # if scheduler_instance and scheduler_instance.get_job(f'scrape_product_{product_id}'):
            #     scheduler_instance.remove_job(f'scrape_product_{product_id}')
            #     print(f"SCHEDULER: Removed stale job for product ID {product_id}")
            return

        print(f"SCHEDULER: Running scheduled scrape for Product ID {product.id} - URL: {product.url}...")
        scraped_details = scrape_amazon_product_details(product.url) # Call your Amazon scraper
        
        if scraped_details and scraped_details.get("price") is not None:
            current_scraped_price = scraped_details["price"]
            print(f"SCHEDULER: Scraped price for '{product.name}': ₹{current_scraped_price:.2f}")

            # Update product name/image if they were 'N/A', blank, or 'Not found'
            # This ensures product details can be refined by later scrapes.
            if not product.name or product.name.lower() in ["n/a", "name not found"]:
                 product.name = scraped_details.get('name', product.name)
            if not product.image_url or product.image_url.lower() in ["n/a", "image not found"]:
                 product.image_url = scraped_details.get('image_url', product.image_url)

            # Add new price to history
            new_price_entry = PriceHistory(product_id=product.id, price=current_scraped_price, timestamp=datetime.datetime.utcnow())
            db.session.add(new_price_entry)
            db.session.commit()
            print(f"SCHEDULER: Logged new price for '{product.name}': ₹{current_scraped_price:.2f} at {new_price_entry.timestamp}")

            # --- Check and send alerts ---
            check_and_send_alerts(app, product, current_scraped_price) # Pass the app instance
        else:
            print(f"SCHEDULER: Failed to scrape valid price for '{product.name}' (URL: {product.url}) in scheduled job.")