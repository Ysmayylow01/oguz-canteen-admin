from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from models import db, Admin, Category, FoodItem, Order, OrderItem, WeeklyMeal
import os
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = 'oguz-canteen-secret-key-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///oguz_canteen.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Upload config
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db.init_app(app)
BASE_URL = "http://10.192.6.44:5000"

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ==================== CLIENT ROUTES ====================
def format_image_url(image):
    if image and not image.startswith(('http://', 'https://')):
        return f"{BASE_URL}{image}"
    return image

DAY_NAMES_TK = ['Duşenbe', 'Sişenbe', 'Çarşenbe', 'Penşenbe', 'Anna', 'Şenbe', 'Ýekşenbe']


def _group_weekly_meals():
    """Hepdäniň naharlaryny günler boýunça toparlamak"""
    meals = WeeklyMeal.query.order_by(WeeklyMeal.day_of_week, WeeklyMeal.id).all()
    days = [{'index': i, 'name': name, 'meals': []} for i, name in enumerate(DAY_NAMES_TK)]
    for meal in meals:
        if 0 <= meal.day_of_week < 7:
            days[meal.day_of_week]['meals'].append(meal)
    return days


@app.route('/')
def home():
    """Esasy menýu sahypasy"""
    categories = Category.query.all()
    weekly_days = _group_weekly_meals()
    from datetime import datetime as _dt
    today_index = _dt.now().weekday()
    return render_template(
        'client/home.html',
        categories=categories,
        weekly_days=weekly_days,
        today_index=today_index,
    )


@app.route('/track-order')
def track_order():
    """Sargyt yzarlamak sahypasy"""
    order_id = request.args.get('id', '')
    return render_template('client/track_order.html', order_id=order_id)


# ==================== API ROUTES ====================

@app.route('/api/orders', methods=['POST'])
def create_order():
    """Täze sargyt döretmek"""
    data = request.json
    try:
        # Sargyt döret
        order = Order(
            customer_name=data['name'],
            customer_phone=data['phone'],
            total_amount=sum(item['price'] * item['quantity'] for item in data['items'])
        )
        db.session.add(order)
        db.session.flush()
        
        # Sargyt önümlerini goş
        for item in data['items']:
            order_item = OrderItem(
                order_id=order.id,
                food_item_id=item['id'],
                quantity=item['quantity'],
                price=item['price'] * item['quantity']
            )
            db.session.add(order_item)
        
        db.session.commit()
        return jsonify({'success': True, 'order_id': order.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/orders/<int:order_id>')
def get_order(order_id):
    """Sargyt maglumatlaryny almak"""
    order = Order.query.get(order_id)
    if not order:
        return jsonify({'success': False})
    
    return jsonify({
        'success': True,
        'order': {
            'id': order.id,
            'customer_name': order.customer_name,
            'customer_phone': order.customer_phone,
            'total_amount': order.total_amount,
            'status': order.status,
            'created_at': order.created_at.isoformat(),
            'items': [{
                'food_item': {'name': item.food_item.name},
                'quantity': item.quantity,
                'price': item.price
            } for item in order.items]
        }
    })


# ==================== ADMIN ROUTES ====================

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin giriş sahypasy"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        admin = Admin.query.filter_by(username=username).first()
        
        if admin and check_password_hash(admin.password, password):
            session['admin'] = True
            return redirect('/admin')
        return render_template('admin/login.html', error='Invalid credentials')
    
    return render_template('admin/login.html')


@app.route('/admin/logout')
def admin_logout():
    """Admin çykmak"""
    session.pop('admin', None)
    return redirect('/admin/login')


@app.route('/admin')
def admin_dashboard():
    """Admin dolandyryş paneli"""
    if not session.get('admin'):
        return redirect('/admin/login')
    
    stats = {
        'categories': Category.query.count(),
        'items': FoodItem.query.count(),
        'orders': Order.query.count(),
        'pending': Order.query.filter_by(status='pending').count()
    }
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()
    
    return render_template('admin/dashboard.html', stats=stats, recent_orders=recent_orders)


@app.route('/admin/categories', methods=['GET', 'POST'])
def admin_categories():
    """Kategoriýalary dolandyrmak"""
    if not session.get('admin'):
        return redirect('/admin/login')
    
    if request.method == 'POST':
        category = Category(name=request.form['name'])
        db.session.add(category)
        db.session.commit()
        return redirect('/admin/categories')
    
    categories = Category.query.all()
    return render_template('admin/categories.html', categories=categories)


@app.route('/admin/categories/delete/<int:id>')
def delete_category(id):
    """Kategoriýany pozmak"""
    if not session.get('admin'):
        return redirect('/admin/login')
    
    category = Category.query.get_or_404(id)
    db.session.delete(category)
    db.session.commit()
    return redirect('/admin/categories')


@app.route('/admin/items', methods=['GET', 'POST'])
def admin_items():
    """Iýmit önümlerini dolandyrmak"""
    if not session.get('admin'):
        return redirect('/admin/login')
    
    if request.method == 'POST':
        image_path = ''
        
        # Surat upload
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                # Faýl adyny üýtgeşik et
                ext = file.filename.rsplit('.', 1)[1].lower()
                filename = f"{uuid.uuid4().hex}.{ext}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                image_path = f"/static/uploads/{filename}"
        
        item = FoodItem(
            name=request.form['name'],
            price=float(request.form['price']),
            category_id=int(request.form['category_id']),
            image=image_path
        )
        db.session.add(item)
        db.session.commit()
        return redirect('/admin/items')
    
    categories = Category.query.all()
    items = FoodItem.query.all()
    return render_template('admin/items.html', categories=categories, items=items)


@app.route('/admin/items/toggle/<int:id>')
def toggle_item(id):
    """Önümiň elýeterliligini üýtgetmek"""
    if not session.get('admin'):
        return redirect('/admin/login')
    
    item = FoodItem.query.get_or_404(id)
    item.available = not item.available
    db.session.commit()
    return redirect('/admin/items')


@app.route('/admin/items/delete/<int:id>')
def delete_item(id):
    """Önümi pozmak"""
    if not session.get('admin'):
        return redirect('/admin/login')
    
    item = FoodItem.query.get_or_404(id)
    
    # Suraty hem poz (eger bar bolsa we local faýl bolsa)
    if item.image and item.image.startswith('/static/uploads/'):
        image_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), item.image.lstrip('/'))
        if os.path.exists(image_file):
            os.remove(image_file)
    
    db.session.delete(item)
    db.session.commit()
    return redirect('/admin/items')


@app.route('/admin/weekly', methods=['GET', 'POST'])
def admin_weekly():
    """Hepdäniň naharlaryny dolandyrmak"""
    if not session.get('admin'):
        return redirect('/admin/login')

    if request.method == 'POST':
        image_path = ''
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                ext = file.filename.rsplit('.', 1)[1].lower()
                filename = f"{uuid.uuid4().hex}.{ext}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                image_path = f"/static/uploads/{filename}"

        price_raw = request.form.get('price', '').strip()
        meal = WeeklyMeal(
            day_of_week=int(request.form['day_of_week']),
            name=request.form['name'],
            description=request.form.get('description', ''),
            price=float(price_raw) if price_raw else None,
            image=image_path,
        )
        db.session.add(meal)
        db.session.commit()
        return redirect('/admin/weekly')

    weekly_days = _group_weekly_meals()
    return render_template('admin/weekly.html', weekly_days=weekly_days, day_names=DAY_NAMES_TK)


@app.route('/admin/weekly/delete/<int:id>')
def delete_weekly(id):
    """Hepdäniň naharyny pozmak"""
    if not session.get('admin'):
        return redirect('/admin/login')

    meal = WeeklyMeal.query.get_or_404(id)
    if meal.image and meal.image.startswith('/static/uploads/'):
        image_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), meal.image.lstrip('/'))
        if os.path.exists(image_file):
            os.remove(image_file)

    db.session.delete(meal)
    db.session.commit()
    return redirect('/admin/weekly')


@app.route('/admin/orders')
def admin_orders():
    """Sargytlary dolandyrmak"""
    if not session.get('admin'):
        return redirect('/admin/login')
    
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('admin/orders.html', orders=orders)


@app.route('/admin/orders/update/<int:id>', methods=['POST'])
def update_order_status(id):
    """Sargyt statusyny täzelemek"""
    if not session.get('admin'):
        return jsonify({'success': False})
    
    order = Order.query.get_or_404(id)
    order.status = request.json['status']
    db.session.commit()
    return jsonify({'success': True})


# ==================== INITIALIZATION ====================

def init_db():
    """Database-ni başlatmak we başlangyç maglumatlary goşmak"""
    with app.app_context():
        db.create_all()
        
        # Default admin döret
        if not Admin.query.first():
            admin = Admin(
                username='admin',
                password=generate_password_hash('admin123')
            )
            db.session.add(admin)
        
        # Mysallar üçin maglumatlary goş
        if not Category.query.first():
            categories_data = [
                ('Esasy Tagamlar', [
                    ('Towuk Çörek', 12.99, 'https://images.unsplash.com/photo-1598103442097-8b74394b95c6?w=500'),
                    ('Sygyr Eti', 18.99, 'https://images.unsplash.com/photo-1600891964092-4316c288032e?w=500'),
                    ('Balyk we Kartof', 14.99, 'https://images.unsplash.com/photo-1579208575657-c595a05383b7?w=500'),
                ]),
                ('Salatlar', [
                    ('Sezar Salaty', 8.99, 'https://images.unsplash.com/photo-1546793665-c74683f339c1?w=500'),
                    ('Grek Salaty', 9.99, 'https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?w=500'),
                ]),
                ('Içgiler', [
                    ('Apelsin Şiresi', 4.99, 'https://images.unsplash.com/photo-1600271886742-f049cd451bba?w=500'),
                    ('Kofe', 3.99, 'https://images.unsplash.com/photo-1509042239860-f550ce710b93?w=500'),
                    ('Buzly Çaý', 3.49, 'https://images.unsplash.com/photo-1556679343-c7306c1976bc?w=500'),
                ]),
                ('Süýjülikler', [
                    ('Şokolad Torti', 6.99, 'https://images.unsplash.com/photo-1578985545062-69928b1d9587?w=500'),
                    ('Doňdurma', 4.99, 'https://images.unsplash.com/photo-1563805042-7684c019e1cb?w=500'),
                ]),
            ]
            
            for cat_name, items in categories_data:
                category = Category(name=cat_name)
                db.session.add(category)
                db.session.flush()
                
                for item_name, price, image in items:
                    item = FoodItem(
                        name=item_name,
                        price=price,
                        image=image,
                        category_id=category.id
                    )
                    db.session.add(item)
        
        db.session.commit()
        print("✅ Database üstünlikli başladyldy!")
        print("👤 Admin maglumatlary: username='admin', password='admin123'")


#hello
@app.route('/api/categories', methods=['GET'])
def api_get_categories():
    """Ähli kategoriýalary JSON formatda almak"""
    categories = Category.query.all()
    result = []
    for category in categories:
        result.append({
            'id': category.id,
            'name': category.name,
            'items': [{
                'id': item.id,
                'name': item.name,
                'price': item.price,
                'image': format_image_url(item.image),
                'category_id': item.category_id,
                'available': item.available
            } for item in category.items if item.available]
        })
    return jsonify(result)


@app.route('/api/foods', methods=['GET'])
def api_get_all_foods():
    """Ähli iýmit önümlerini almak"""
    foods = FoodItem.query.filter_by(available=True).all()
    result = [{
        'id': food.id,
        'name': food.name,
        'price': food.price,
        'image': format_image_url(food.image),
        'category_id': food.category_id,
        'available': food.available
    } for food in foods]
    return jsonify(result)


@app.route('/api/weekly', methods=['GET'])
def api_get_weekly_meals():
    """Hepdäniň naharlaryny günler boýunça JSON formatda almak"""
    days = _group_weekly_meals()
    result = []
    for day in days:
        result.append({
            'day_index': day['index'],
            'day_name': day['name'],
            'meals': [{
                'id': meal.id,
                'name': meal.name,
                'description': meal.description or '',
                'price': meal.price,
                'image': format_image_url(meal.image) if meal.image else None,
            } for meal in day['meals']]
        })
    return jsonify(result)


@app.route('/api/categories/<int:category_id>/foods', methods=['GET'])
def api_get_foods_by_category(category_id):
    """Kategoriýa boýunça önümleri almak"""
    foods = FoodItem.query.filter_by(
        category_id=category_id,
        available=True
    ).all()
    result = [{
        'id': food.id,
        'name': food.name,
        'price': food.price,
        'image': format_image_url(food.image),
        'category_id': food.category_id,
        'available': food.available
    } for food in foods]
    return jsonify(result)

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000,host="0.0.0.0")