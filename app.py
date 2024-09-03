from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, Email, EqualTo
import io
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
from werkzeug.utils import secure_filename
from datetime import timedelta

app = Flask(__name__)

# Ensure pytesseract is correctly configured
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# MySQL and Flask configuration
app.config['SECRET_KEY'] = 'bc8ba792963f7a8dabfa441d1f158701'
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Akshita@2003'
app.config['MYSQL_DB'] = 'login_credentials_drdoapp'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=5)  # 5 minutes of inactivity will log out the user


mysql = MySQL(app)
bcrypt = Bcrypt(app)


# Forms
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=50)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


# Routes
@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    # Check if the request contains files
    if 'file' not in request.files:
        flash('No file part', 'danger')
        print('No file part in request')
        return redirect(request.url)

    file = request.files['file']

    # Check if a file was selected
    if file.filename == '':
        flash('No selected file', 'danger')
        print('No selected file')
        return redirect(request.url)

    # Validate file type
    if file and file.filename.endswith('.pdf'):
        filename = secure_filename(file.filename)
        file_content = file.read()

        # Debug: Print file information
        print(f"File Name: {filename}")
        print(f"File Size: {len(file_content)} bytes")

        try:
            cur = mysql.connection.cursor()
            cur.execute("INSERT INTO pdf_files (file_name, file_data) VALUES (%s, %s)", (filename, file_content))
            mysql.connection.commit()
            cur.close()
            flash('File uploaded successfully!', 'success')
            print('File uploaded successfully!')
        except Exception as e:
            flash(f'Failed to upload file: {e}', 'danger')
            print(f'Failed to upload file: {e}')
            return redirect(url_for('home'))

        return redirect(url_for('home'))
    else:
        flash('Invalid file type. Only PDFs are allowed.', 'danger')
        print('Invalid file type')
        return redirect(request.url)

@app.route('/search_by_name', methods=['GET'])
def search_by_name():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    file_name = request.args.get('file_name')
    cur = mysql.connection.cursor()
    cur.execute("SELECT file_name FROM pdf_files WHERE file_name = %s", (file_name,))
    file = cur.fetchone()
    cur.close()

    if file:
        return render_template('search_by_name_results.html', file_name=file_name, file_path=file_name)
    else:
        return render_template('search_by_name_results.html', file_name=file_name, file_path=None)


@app.route('/search_by_keywords', methods=['GET'])
def search_by_keywords():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    keywords = request.args.get('keywords').lower()
    found_files = []

    cur = mysql.connection.cursor()
    cur.execute("SELECT file_name, file_data FROM pdf_files")
    files = cur.fetchall()
    cur.close()

    for filename, file_content in files:
        if search_pdf_for_keywords(file_content, keywords):
            found_files.append(filename)

    return render_template('results.html', keywords=keywords, found_files=found_files)


def search_pdf_for_keywords(file_content, keywords):
    doc = fitz.open(stream=file_content, filetype="pdf")
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text = page.get_text()
        if keywords in text.lower():
            return True

        # OCR if necessary
        pix = page.get_pixmap()
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        text = pytesseract.image_to_string(img)
        if keywords in text.lower():
            return True

    return False


from flask import Flask, request, send_file
import io

@app.route('/open_file/<filename>')
def open_file(filename):
    cur = mysql.connection.cursor()
    cur.execute("SELECT file_data FROM pdf_files WHERE file_name = %s", (filename,))
    file_content = cur.fetchone()[0]
    cur.close()

    # Use BytesIO to create an in-memory binary stream
    return send_file(
        io.BytesIO(file_content),
        mimetype='application/pdf',
        as_attachment=False,  # Ensures the file is opened in the browser instead of downloading
        download_name=filename  # Specifies the name for the file when opened
    )


# Download file route
@app.route('/download/<filename>')
def download_file(filename):
    cur = mysql.connection.cursor()
    cur.execute("SELECT file_data FROM pdf_files WHERE file_name = %s", (filename,))
    file = cur.fetchone()
    cur.close()

    if file:
        # Sending file for downloading
        return send_file(io.BytesIO(file[0]), mimetype='application/pdf', as_attachment=True, download_name=filename)
    else:
        flash('File not found!', 'danger')
        return redirect(url_for('home'))




@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
                    (form.username.data, form.email.data, hashed_password))
        mysql.connection.commit()
        cur.close()
        flash('Your account has been created!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)


from flask import session

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s", [form.email.data])
        user = cur.fetchone()
        cur.close()
        if user and bcrypt.check_password_hash(user[3], form.password.data):  # Access password_hash by index
            session['user_id'] = user[0]  # User ID is assumed to be the first element
            session['username'] = user[1]  # Username is assumed to be the second element
            session.permanent = True  # Makes the session permanent so it uses the configured timeout
            return redirect(url_for('home'))
        else:
            flash('Login unsuccessful. Please check your email and password', 'danger')
    return render_template('login.html', form=form)



@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    #flash('You have been logged out!', 'info')
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)
