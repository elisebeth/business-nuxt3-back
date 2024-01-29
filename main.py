from flask import Flask, request, jsonify, g
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flasgger import Swagger, swag_from
from flask_swagger_ui import get_swaggerui_blueprint

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'your_jwt_secret_key'
app.config['SWAGGER'] = {'title': 'Your API Title', 'uiversion': 3}
db = SQLAlchemy(app)
jwt = JWTManager(app)
swagger = Swagger(app)

SWAGGER_URL = '/swagger'
API_URL = '/static/swagger.json'

swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={'app_name': "Your API Name"}
)


app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

# Модель Product
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200))
    price = db.Column(db.Integer)
    image = db.Column(db.String(100))
    users = db.relationship('User', secondary='user_product_favorite', back_populates='favorites')

# Модель User
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    favorites = db.relationship('Product', secondary='user_product_favorite', back_populates='users')


# Промежуточная таблица для отношения "многие ко многим" между User и Product
user_product_favorite = db.Table('user_product_favorite',
                                 db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
                                 db.Column('product_id', db.Integer, db.ForeignKey('product.id'), primary_key=True)
                                 )



# Регистрация нового пользователя
@app.route('/registration', methods=['POST'])
@swag_from('swagger_docs/register.yml')
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"message": "Missing username or password"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"message": "Username already taken"}), 400

    new_user = User(username=username, password=password)
    access_token = create_access_token(new_user.id)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User registered successfully", "access_token": access_token}), 201


# Получение токена для аутентификации
@app.route('/login', methods=['POST'])
@swag_from('swagger_docs/login.yml')
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username, password=password).first()

    if not user:
        return jsonify({"message": "Пользователя с таким username не существует"}), 401

    access_token = create_access_token(identity=user.id)
    return jsonify(access_token=access_token), 200


# Защищенный маршрут для разлогинивания
@app.route('/logout', methods=['POST'])
@jwt_required()
@swag_from('swagger_docs/logout.yml')
def logout():
    # Поскольку токены в этом примере хранятся на клиенте, просто игнорируем запрос разлогинивания
    return jsonify({"message": "Successfully logged out"}), 200


# Получение списка избранных товаров пользователя
@app.route('/favorites', methods=['GET'])
@jwt_required()
@swag_from('swagger_docs/get_favorites.yml')
def get_favorites():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    favorites = [{'id': product.id, 'title': product.title, 'description': product.description,
                  'price': product.price, 'image': product.image} for product in user.favorites]

    return jsonify(favorites), 200


# Добавление товара в избранное пользователя
@app.route('/favorites/add', methods=['POST'])
@jwt_required()
@swag_from('swagger_docs/add_to_favorites.yml')
def add_to_favorites():
    data = request.get_json()
    product_id = data.get('product_id')

    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    product = Product.query.get(product_id)

    if product not in user.favorites:
        user.favorites.append(product)
        db.session.commit()

    return jsonify({"message": "Product added to favorites successfully"}), 200


# Удаление товара из избранного пользователя
@app.route('/favorites/remove', methods=['DELETE'])
@jwt_required()
@swag_from('swagger_docs/remove_from_favorites.yml')
def remove_from_favorites():
    data = request.get_json()
    product_id = data.get('product_id')

    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    product = Product.query.get(product_id)

    if product in user.favorites:
        user.favorites.remove(product)
        db.session.commit()

    return jsonify({"message": "Product removed from favorites successfully"}), 200


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=3333)
