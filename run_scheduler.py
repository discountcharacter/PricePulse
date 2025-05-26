# run_scheduler.py
import os
from app import app, scheduler # Import your Flask app instance and scheduler instance
from database import db, Product # Import models if needed by scheduler setup
from app import job_scrape_product_wrapper # Import the wrapper

print("RUN_SCHEDULER: Starting scheduler process...")

def start_scheduler_jobs(flask_app_instance, scheduler_instance):
    with flask_app_instance.app_context():
        # This logic is similar to initialize_application_startup in app.py,
        # but focused only on adding jobs and starting the scheduler.
        # db.create_all() # Tables should be created by the web service on its first run or via migrations
        
        products_to_track = Product.query.all()
        print(f"RUN_SCHEDULER: Found {len(products_to_track)} products in DB to schedule.")
        for p in products_to_track:
            job_id = f'scrape_product_{p.id}'
            if not scheduler_instance.get_job(job_id):
                print(f"RUN_SCHEDULER: Adding job for product {p.id} ('{p.name}').")
                scheduler_instance.add_job(
                    job_scrape_product_wrapper,
                    'interval',
                    minutes=30, # Or your desired interval
                    args=[p.id],
                    id=job_id,
                    replace_existing=True
                )
            else:
                print(f"RUN_SCHEDULER: Job for product {p.id} ('{p.name}') already exists.")

        if not scheduler_instance.running:
            try:
                scheduler_instance.start()
                print("RUN_SCHEDULER: Scheduler started successfully.")
            except Exception as e:
                print(f"RUN_SCHEDULER: Error starting scheduler: {e}")
        else:
            print("RUN_SCHEDULER: Scheduler was already running (should not happen on fresh start).")

if __name__ == '__main__':
    # This allows the scheduler to run indefinitely when this script is executed.
    # The Flask app context is needed for database access within scheduled jobs.
    # We pass the app instance to functions that need the context.
    
    # Initialize DB with app for this script to use models correctly
    # This is important because we are not running the full app.py startup.
    with app.app_context():
        db.init_app(app) # Ensure db is associated with app in this context too

    start_scheduler_jobs(app, scheduler)

    # Keep the script running so the scheduler thread stays alive
    import time
    try:
        while True:
            time.sleep(60) # Sleep for a minute, check logs, etc.
            # You could add more sophisticated health checks here if needed
            # print("RUN_SCHEDULER: Scheduler process alive...")
    except (KeyboardInterrupt, SystemExit):
        print("RUN_SCHEDULER: Scheduler process shutting down...")
        if scheduler.running:
            scheduler.shutdown()