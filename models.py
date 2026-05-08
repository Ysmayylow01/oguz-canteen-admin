from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Admin(db.Model):
    """Admin ulanyjylar üçin model"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    def __repr__(self):
        return f'<Admin {self.username}>'


class Category(db.Model):
    """Iýmit kategoriýalary üçin model"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    section = db.Column(db.String(20), default='main', server_default='main')
    items = db.relationship('FoodItem', backref='category', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Category {self.name}>'


class FoodItem(db.Model):
    """Iýmit önümleri üçin model"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    image = db.Column(db.Text, nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    available = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<FoodItem {self.name}>'


class Order(db.Model):
    """Sargytlar üçin model"""
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_phone = db.Column(db.String(20), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, preparing, ready, completed
    section = db.Column(db.String(20), default='main', server_default='main')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Order {self.id} - {self.customer_name}>'


class OrderItem(db.Model):
    """Sargytdaky önümler üçin model"""
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    food_item_id = db.Column(db.Integer, db.ForeignKey('food_item.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    note = db.Column(db.Text, nullable=True)
    food_item = db.relationship('FoodItem')

    def __repr__(self):
        return f'<OrderItem {self.id}>'


class Banner(db.Model):
    """Bannerlary saklamak üçin model"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=True)
    image = db.Column(db.Text, nullable=False)
    active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f'<Banner {self.id}>'


class WeeklyMeal(db.Model):
    """Hepdäniň naharlary üçin model (0=Duşenbe ... 6=Ýekşenbe)"""
    id = db.Column(db.Integer, primary_key=True)
    day_of_week = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=True)
    image = db.Column(db.Text, nullable=True)
    section = db.Column(db.String(20), default='main', server_default='main')

    def __repr__(self):
        return f'<WeeklyMeal {self.day_of_week}:{self.name}>'