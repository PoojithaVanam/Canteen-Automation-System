from flask import Flask, render_template, request, redirect, url_for, session
from functools import wraps
import pdfkit  # To generate PDF invoices
from flask import send_file
import io

app = Flask(__name__)
app.secret_key = 'canteen_secret_key'

# In-memory storage
menu_items = []
orders = []
students = []
admins = [{'username': 'admin', 'password': 'admin123'}]  # default admin

# Set the path to wkhtmltopdf (update this with your installation path)
config = pdfkit.configuration(wkhtmltopdf=r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe")

# Login required decorator
def login_required(role):
    def wrapper(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user' not in session or session.get('role') != role:
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    return wrapper

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        role = request.form.get('role')
        username = request.form.get('username')
        password = request.form.get('password')

        if not (role and username and password):
            return "Missing data", 400

        if role == 'student':
            students.append({'username': username, 'password': password})
        else:
            admins.append({'username': username, 'password': password})

        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        role = request.form.get('role')
        username = request.form.get('username')
        password = request.form.get('password')

        users = students if role == 'student' else admins
        for user in users:
            if user['username'] == username and user['password'] == password:
                session['user'] = username
                session['role'] = role
                return redirect(url_for('dashboard' if role == 'admin' else 'student_dashboard'))
        return "Login Failed", 401
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required('admin')
def dashboard():
    stats = {
        'total': len(orders),
        'accepted': sum(1 for o in orders if o['status'] == 'Accepted'),
        'rejected': sum(1 for o in orders if o['status'] == 'Rejected'),
        'completed': sum(1 for o in orders if o['status'] == 'Completed'),
        'delivered': sum(1 for o in orders if o['status'] == 'Delivered')
    }
    return render_template('dashboard.html', orders=orders, stats=stats, enumerate=enumerate)

@app.route('/admin-dashboard')
@login_required('admin')
def admin_dashboard():
    stats = {
        'total': len(orders),
        'accepted': sum(1 for o in orders if o['status'] == 'Accepted'),
        'rejected': sum(1 for o in orders if o['status'] == 'Rejected'),
        'completed': sum(1 for o in orders if o['status'] == 'Completed'),
        'delivered': sum(1 for o in orders if o['status'] == 'Delivered')
    }
    return render_template('dashboard.html', orders=orders, stats=stats, enumerate=enumerate)

@app.route('/student_dashboard')
@login_required('student')
def student_dashboard():
    return render_template('student_dashboard.html')

@app.route('/menu')
@login_required('student')
def menu():
    return render_template('menu.html', items=menu_items)

@app.route("/order", methods=["GET", "POST"])
@login_required('student')
def order():
    if request.method == "POST":
        item_name = request.form["item"]
        quantity = int(request.form["quantity"])

        # Find item price
        item = next((i for i in menu_items if i['item'] == item_name), None)
        if not item:
            return "Item not found", 404

        price = item['price']
        total_price = quantity * price

        order = {
            'id': len(orders),  # assign order ID
            'student': session['user'],
            'item': item_name,
            'quantity': quantity,
            'status': 'Pending',
            'total_price': total_price
        }

        orders.append(order)
        return render_template("order_success.html", order=order)

    return render_template("order.html", items=menu_items)

@app.route('/admin/add_item', methods=['GET', 'POST'])
@login_required('admin')
def add_item():
    if request.method == 'POST':
        item = request.form.get('item')
        price = request.form.get('price')

        if not item or not price:
            return "Missing item or price", 400

        try:
            price = float(price)
        except ValueError:
            return "Invalid price value", 400

        menu_items.append({'item': item, 'price': price})
        return redirect(url_for('dashboard'))
    return render_template('add_item.html')

@app.route('/admin/update', methods=['POST'])
@login_required('admin')
def update_order():
    order_id = int(request.form.get('id', -1))
    status = request.form.get('status')

    if 0 <= order_id < len(orders):
        orders[order_id]['status'] = status
    return redirect(url_for('dashboard'))

# Route to display the successful order page
@app.route('/order_successful/<int:order_id>')
def order_successful(order_id):
    order = next((o for o in orders if o['id'] == order_id), None)
    if not order:
        return "Order not found", 404
    return render_template('order_successful.html', order=order)

# Route to handle the invoice download
@app.route('/order/invoice/<int:order_id>')
def download_invoice(order_id):
    order = next((o for o in orders if o['id'] == order_id), None)

    if not order:
        print(f"Order with ID {order_id} not found.")
        return "Order not found", 404

    # If order exists, generate the invoice PDF
    invoice_content = f"Invoice\n\nOrder ID: {order['id']}\nItem: {order['item']}\nQuantity: {order['quantity']}\nTotal Price: {order['total_price']}"
    
    # Generate the PDF from the string content
    pdf = pdfkit.from_string(invoice_content, False, configuration=config)
    
    # Create a BytesIO object to send the PDF file in the response
    pdf_io = io.BytesIO(pdf)
    pdf_io.seek(0)  # Rewind the file pointer to the beginning
    
    # Return the PDF file as a downloadable response
    return send_file(pdf_io, as_attachment=True, download_name=f"invoice_{order_id}.pdf", mimetype="application/pdf")


if __name__ == '__main__':
    app.run(debug=True)
