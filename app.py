from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
import MySQLdb.cursors
import re
from MySQLdb import IntegrityError

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# MySQL connection
app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "lesotho_high_schools"

mysql = MySQL(app)

#HOME
@app.route('/')
def index():
    return render_template('index.html')

#STUDENTS ROUTES/REGISTER
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form['full_name']
        student_number = request.form['student_number']
        email = request.form['email']
        school_name = request.form['school_name']
        pw = request.form['password']

        hashed_pw = generate_password_hash(pw)

        try:
            cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cur.execute('INSERT INTO students (full_name, student_number, email, password, school_name) VALUES (%s, %s, %s, %s, %s)', (full_name, student_number, email, hashed_pw, school_name))
            mysql.connection.commit()
            flash('Registration successful! Please log in.')
            return redirect(url_for('login'))
            
        except IntegrityError as e:
            if 'Duplicate entry' in str(e):
              flash('Student number or Password already taken try another.')
            
            else:
              flash('SOMETHING WENT WRONG.')
            
        finally:
            cur.close()
        

    return render_template('register.html')

#STUDENTS ROUTES/LOGIN
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        student_number = request.form['student_number']

        password = request.form['password']
        
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute('SELECT * FROM students WHERE student_number = %s', (student_number,))
        student = cur.fetchone()
        #print(f"Student data: {student}, type: {type(student)}")
        cur.close()

        if student and check_password_hash(student['password'], password):
            session['student_id'] = student['id']
            session['student_name'] = student['full_name']
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid student number or password')
    return render_template('login.html')

#STUDENTS ROUTES/DASHBOARD
@app.route('/dashboard')
def dashboard():
    if 'student_id' not in session:
        return redirect(url_for('login'))
    
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM institutions")
    institutions = cur.fetchall()
    
    cur.close()

    return render_template('dashboard.html', name=session['student_name'], institutions=institutions)


#STUDENTS ROUTES/APPLY
@app.route('/apply/<int:institution_id>', methods=['GET', 'POST'])
def apply(institution_id):
    if 'student_id' not in session:
        return redirect(url_for('login'))
    
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute('SELECT * FROM courses WHERE institution_id = %s', (institution_id,))
    courses = cur.fetchall()
    
    if request.method == 'POST':
        course_id = int(request.form['course'])
        english_grade = request.form['english']
        maths_grade = request.form['maths']
        science_grade = request.form['science']
        sesotho_grade = request.form['sesotho']
        
        # Fetch course requirements
        cur.execute('''
            SELECT c.*, i.name as institution_name
            FROM courses c
            JOIN institutions i ON c.institution_id = i.id
            WHERE c.id = %s
        ''', (course_id,))
        course = cur.fetchone()

        # Check qualification
        def qualifies(student_grade, req_grade):
            grades = {'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5, 'F': 6}
            return grades.get(student_grade.upper(), 6) <= grades.get(req_grade.upper(), 6)

        qualified = (
            qualifies(english_grade, course['English_req']) and
            qualifies(maths_grade, course['Maths_req']) and
            qualifies(science_grade, course['Science_req']) and
            qualifies(sesotho_grade, course['Sesotho_req'])
        )

        # Record application
        cur.execute('INSERT INTO applications (student_id, institution_id, course_id, english_grade, maths_grade, science_grade, sesotho_grade) VALUES (%s, %s, %s, %s, %s, %s, %s)',
                    (session['student_id'], institution_id, course_id, english_grade, maths_grade, science_grade, sesotho_grade))
        mysql.connection.commit()
        flash('Application submitted.')
        # Show qualification result
        return render_template('application_result.html', qualified=qualified, course=course)
    
    cur.close()
    
    return render_template('apply.html', courses=courses)

#LOGOUT ROUTE
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

#ADMIN ROUTES/REGISTER
@app.route('/admin_register', methods=['GET', 'POST'])
def admin_register():
    if request.method == 'POST':
        full_name = request.form['full_name']
        username = request.form['username']
        email = request.form['email']
        school_name = request.form['school_name']
        pw = request.form['password']

        hashed_pw = generate_password_hash(pw)

        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute('INSERT INTO admin (full_name, username, email, password, school_name) VALUES (%s, %s, %s, %s, %s)', (full_name, username, email, hashed_pw, school_name))
        mysql.connection.commit()
        flash('Registration successful! Please log in.')
        
        cur.close()
        return redirect(url_for('admin_login'))

    return render_template('admin_register.html')

# ADMNIN ROUTES/ADMIN_LOGIN
@app.route('/admin_login', methods=['GET', 'POST']) 
def admin_login(): 
    if request.method == 'POST': 
        username = request.form['username'] 
        password = request.form['password'] 

        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute('SELECT * FROM admin WHERE username = %s', (username,))
        admin_log = cur.fetchone()
        print(f"Admin data: {admin_log}, type: {type(admin_log)}")
        cur.close()
        if admin_log and check_password_hash(admin_log['password'], password): 
            session['admin_log_id'] = admin_log['id']
            session['admin_log_name'] = admin_log['full_name'] 
            return redirect(url_for('admin_dashboard')) 
        else: 
            flash('Invalid admin credentials') 
    return render_template('admin_login.html')

# ADMNIN ROUTES/DASHBOARD  
# Admin Dashboard
@app.route('/admin_dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if 'admin_log_id' not in session:
        return redirect(url_for('admin_login'))

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    search_query = request.form.get('search', '')
    
    if search_query:
         search_query = search_query.lower()
         cur.execute("SELECT * FROM institutions WHERE LOWER(name) LIKE %s", ('%' + search_query + '%',))

    else:
        cur.execute('SELECT * FROM institutions')
    
    institutions = cur.fetchall()

    for institution in institutions:
        cur.execute('SELECT * FROM courses WHERE institution_id = %s', (institution['id'],))
        institution['courses'] = cur.fetchall()

    cur.close()
    return render_template('admin_dashboard.html', institutions=institutions, search_query=search_query)


# ADDING INSTITUTION 
@app.route('/add_institution', methods=['GET', 'POST'])
def add_institution():
    if 'admin_log_id' not in session:
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        name = request.form['name']
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute('INSERT INTO institutions (name) VALUES (%s)', (name,))
        mysql.connection.commit()
        cur.close()
        #print(f"name: {name}")
        return redirect(url_for('admin_dashboard'))

    
    return render_template('manage_institutions.html', action='Add', institution=None)

#manage everything here
@app.route('/admin/manage_institutions/<int:institution_id>', methods=["GET", "POST"])
def manage_institutions(institution_id):
    print(f"Accessing manage_institutions with ID: {institution_id}")
    return render_template('manage_institutions.html', institution_id=institution_id)


# EDIT INSTITUTION  
@app.route('/edit_institution/<int:inst_id>', methods=['GET', 'POST'])
def edit_institution(inst_id):
    if 'admin_log_id' not in session:
        return redirect(url_for('admin_login'))
      
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    if request.method == 'POST':
        print(f"Form data for editing institution: {request.form}")
        # Use the same field name as in the insert route.
        name = request.form['name']
        cur.execute('UPDATE institutions SET name=%s WHERE id=%s', (name, inst_id))
        mysql.connection.commit()
        cur.close()
        return redirect(url_for('admin_dashboard'))
    else:
        cur.execute('SELECT * FROM institutions WHERE id=%s', (inst_id,))
        institution = cur.fetchone()
        cur.close()
        return render_template('manage_institutions.html', action='Edit', institution=institution)


# DELETE INSTITUTION 
@app.route('/delete_institution/<int:inst_id>')
def delete_institution(inst_id):
    if 'admin_log_id' not in session:
        return redirect(url_for('admin_login'))
     
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute('DELETE FROM institutions WHERE id=%s', (inst_id,))
    # Optionally delete associated courses.
    cur.execute('DELETE FROM courses WHERE institution_id=%s', (inst_id,))
    mysql.connection.commit()
    cur.close()
      
    return redirect(url_for('admin_dashboard'))


# ADD COURSES 
@app.route('/add_course/<int:inst_id>', methods=['GET', 'POST'])
def add_course(inst_id):
    if 'admin_log_id' not in session:
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        course_name = request.form['course_name']
        English_req = request.form['english_req']
        Maths_req = request.form['maths_req']
        Science_req = request.form['science_req']
        Sesotho_req = request.form['sesotho_req']

        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute('''
            INSERT INTO courses (institution_id, course_name, English_req, Maths_req, Science_req, Sesotho_req)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (inst_id, course_name, English_req, Maths_req, Science_req, Sesotho_req))
        mysql.connection.commit()
        cur.close()
        return redirect(url_for('admin_dashboard'))
    
    return render_template('add_course.html', inst_id=inst_id)

# EDIT COURSE
@app.route('/edit_course/<int:course_id>', methods=['GET', 'POST'])
def edit_course(course_id):
    if 'admin_log_id' not in session:
        return redirect(url_for('admin_login'))

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST':
        course_name = request.form['course_name']
        English_req = request.form['english_req']
        Maths_req = request.form['maths_req']
        Science_req = request.form['science_req']
        Sesotho_req = request.form['sesotho_req']
        
        cur.execute('''
            UPDATE courses SET course_name=%s, English_req=%s, Maths_req=%s, Science_req=%s, Sesotho_req=%s
            WHERE id=%s
        ''', (course_name, English_req, Maths_req, Science_req, Sesotho_req, course_id))
        mysql.connection.commit()
        cur.close()
        return redirect(url_for('admin_dashboard'))
    else:
        cur.execute('SELECT * FROM courses WHERE id=%s', (course_id,))
        course = cur.fetchone()
        cur.close()
        return render_template('edit_course.html', course=course)

# DELETE COURSE
@app.route('/delete_course/<int:course_id>')
def delete_course(course_id):
    if 'admin_log_id' not in session:
        return redirect(url_for('admin_login'))

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute('DELETE FROM courses WHERE id=%s', (course_id,))
    mysql.connection.commit()
    cur.close()
    return redirect(url_for('admin_dashboard'))

#feedback
@app.route('/feedback', methods=['POST'])
def feedback():
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    user_id = request.form.get('user_id')
    institution_id = request.form.get('institution_id')
    comment = request.form.get('comment')
    rating = request.form.get('rating')

    # **Validation Checks**
    if not user_id or not institution_id or not comment or not rating:
        return "Error: All fields must be filled."

    if not rating.isdigit() or int(rating) < 1 or int(rating) > 5:
        return "Error: Rating must be a number between 1 and 5."

    if len(comment) > 500:  # Limit character count
        return "Error: Comment too long (max 500 characters)."

    if not re.match("^[a-zA-Z0-9\s.,!?'-]+$", comment):  # Prevent special characters
        return "Error: Invalid characters in comment."

    # **Insert Valid Data**
    cur.execute("INSERT INTO feedback (user_id, institution_id, comment, rating) VALUES (%s, %s, %s, %s)", 
                (user_id, institution_id, comment, rating))
    mysql.connection.commit()

    return redirect(url_for('feedback'))

#explore institutions
@app.route('/explore')
def explore_institutions():
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    search_query = request.args.get('search', '')
    filter_location = request.args.get('location', '')

    query = "SELECT id, name, location, avg_rating, description FROM explore WHERE 1=1"
    params = []

    if search_query:
        query += " AND name LIKE %s"
        params.append(f"%{search_query}%")

    if filter_location:
        query += " AND location = %s"
        params.append(filter_location)

    query += " ORDER BY avg_rating DESC"
    cur.execute(query, tuple(params))
    institutions = cur.fetchall()

    cur.execute("SELECT DISTINCT location FROM explore ORDER BY location")
    locations = cur.fetchall()

    return render_template('explore_institutions.html', institutions=institutions, locations=locations)

#institution details
@app.route('/institution/<int:id>')
def institution_details(id):
    # Fetch institution details
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT name, location, description, avg_rating FROM explore WHERE id = %s", (id,))
    institution = cur.fetchone()

    # Fetch reviews for the institution
    cur.execute("SELECT r.review, r.rating, r.timestamp, u.username FROM institution_reviews r JOIN users u ON r.user_id = u.id WHERE r.institution_id = %s ORDER BY r.timestamp DESC", (id,))
    reviews = cur.fetchall()

    return render_template('institution_details.html', institution=institution, reviews=reviews)




if __name__ == '__main__':
    app.run(debug=True)