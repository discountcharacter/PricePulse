print("DEBUG: app.py script started")
from dotenv import load_dotenv
load_dotenv()
from flask_sqlalchemy import SQLAlchemy
import datetime

db = SQLAlchemy()

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String, unique=True, nullable=False)
    name = db.Column(db.String, nullable=True)
    image_url = db.Column(db.String, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    prices = db.relationship('PriceHistory', backref='product', lazy=True, cascade="all, delete-orphan")
    alerts = db.relationship('Alert', backref='product', lazy=True, cascade="all, delete-orphan") # For bonus

    def __repr__(self):
        return f'<Product {self.name or self.url}>'

class PriceHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    price = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def __repr__(self):
        return f'<Price {self.price} at {self.timestamp}>'

# For Bonus Email Alert
class Alert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    email = db.Column(db.String, nullable=False)
    target_price = db.Column(db.Float, nullable=False)
    is_active = db.Column(db.Boolean, default=True) # To avoid sending multiple emails for the same price drop
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    def __repr__(self): # <--- ADD THIS METHOD
        return f'<Alert for product {self.product_id} to {self.email}>'