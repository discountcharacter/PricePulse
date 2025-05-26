# test_import.py
print("Attempting to import db from database...")
try:
    from database import db
    print("Successfully imported db:", db)
except ImportError as e:
    print("ImportError:", e)
except Exception as e:
    print("Some other error during import:", e)

print("Attempting to import Product from database...")
try:
    from database import Product
    print("Successfully imported Product:", Product)
except ImportError as e:
    print("ImportError for Product:", e)
except Exception as e:
    print("Some other error during Product import:", e)