
from flask import Flask, render_template, request, redirect, url_for, session, flash
from backend.models import * 
from datetime import date
from flask import jsonify


app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///household.sqlite3"
app.app_context().push()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'abcdefgh'  # Change this to a random secret key
db.init_app(app)


# Set up the application context

@app.route('/')
def home(): 
          with app.app_context():
                       return render_template('login.html')  # The login form will be displayed 

@app.route('/login', methods=["GET", "POST"])
def user_login():
    if request.method == "POST":
        uname = request.form.get("uname")
        pwd = request.form.get("pwd")
        usr = User.query.filter_by(uname=uname, pwd=pwd).first()  # Get existing user

        if usr:
            if usr.role == 1:
                # Admin logic
                user_summary = fetch_user()  # Calling
                return redirect(url_for('dashboard', name=usr.uname, User=None))
            elif usr.role == 2:
                # Professional logic
                if usr.status == 'approved':
                    session['user_type'] = 'professional'
                    session['user_id'] = usr.user_id
                    return redirect(url_for('professional_dashboard'))
                else:
                    flash('Your account is not approved yet.', 'warning')
                    return redirect(url_for('user_login'))
            elif usr.role == 3:
                # Customer logic
                session['user_type'] = 'customer'
                session['user_id'] = usr.user_id
                return redirect(url_for('customer_dashboard'))
        else:
            flash('Invalid credentials, please try again.', 'error')
            return redirect(url_for('user_login'))

    # Render the login form for GET requests or if no valid user is found
    return render_template("login.html", msg="")
    
@app.route('/dashboard')
def dashboard():
     # Fetch all service requests with necessary details
    service_requests = db.session.query(
        ServiceRequest.request_id,
        ServiceRequest.status,
        ServiceRequest.request_date.label("request_date"),
        User.uname.label("assigned_professional")
    ).join(User, ServiceRequest.professional_id == User.user_id).all()

    users = fetch_user()
    services = Service.query.all()

     # Assuming you have a way to get the current admin's user ID
    admin_user_id = session.get('admin_user_id')  # Example: stored in session

    # Fetch the admin's name from the database
    admin = User.query.filter_by(user_id=admin_user_id).first()
    admin_name = admin.uname if admin else 'Admin'  # Fallback to 'Admin' if not found


    return render_template('admin_dashboard.html', name='Admin', User=users, services=services, service_requests=service_requests)

        

@app.route('/dashboard/add_service', methods=['GET', 'POST'])
def add_service():
    if request.method == 'POST':
        service_name = request.form.get('service_name')
        description = request.form.get('description')
        base_price = request.form.get('base_price', type=float)

        if not service_name or base_price is None or base_price <= 0:
            flash('Service name and a valid base price are required.', 'error')
            return redirect(url_for('add_service'))

        new_service = Service(service_name=service_name, description=description, base_price=base_price)

        try:
            db.session.add(new_service)
            db.session.commit()
            print("Service added to database:", new_service)
            flash('New service added successfully!', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            print("Error adding service to database:", e)
            flash(f'An error occurred: {str(e)}', 'error')
            return redirect(url_for('add_service'))

    return render_template('admin_newservice.html')


@app.route('/admin_search', methods=['GET'])
def admin_search():
    query = request.args.get('query', '').strip()
    category = request.args.get('category', '').strip()
    search_results = {}

    if category == 'customers':
        search_results['customers'] = User.query.filter(
            User.role == 3,  # Assuming role 3 is for customers
            User.uname.ilike(f'%{query}%')
        ).all()
    elif category == 'professionals':
        search_results['professionals'] = User.query.filter(
            User.role == 2,  # Assuming role 2 is for professionals
            User.uname.ilike(f'%{query}%')
        ).all()
    elif category == 'service_requests':
        search_results['service_requests'] = ServiceRequest.query.filter(
            ServiceRequest.status.ilike(f'%{query}%')
        ).all()

    return render_template('admin dashboard(search).html', search_results=search_results, query=query, category=category)
        
    


@app.route('/admin_summary')
def admin_summary():
    return render_template('admin dashboard(summary).html') 
    
# Temporary storage for booked services
service_packages={}
booked_services = []


@app.route('/service_requests/<service_name>')
def service_requests(service_name):
    services = service_packages.get(service_name, [])
    return render_template('service_requests.html', services=services, service_name=service_name)



professionals_data = {}

@app.route('/create_request/<service_name>', methods=['GET', 'POST'])
def create_request(service_name):
    print(f"Creating request for service: {service_name}")
    if request.method == 'POST':
        professional_id = request.form.get('professional')
        customer_id = session.get('user_id')
        service = Service.query.filter_by(service_name=service_name).first()
        
        print(f"Customer ID: {customer_id}, Professional ID: {professional_id}, Service: {service}")

        if service and customer_id and professional_id:
            new_request = ServiceRequest(
                customer_id=customer_id, 
                professional_id=professional_id, 
                service_id=service.service_id, 
                status='requested'
            )
            db.session.add(new_request)
            db.session.commit()
            flash('Service request created successfully!', 'success')
            return redirect(url_for('customer_dashboard'))
        else:
            flash('Error creating service request. Please ensure all fields are filled correctly.', 'danger')

    professionals = ProfessionalInformation.query.filter_by(service_name=service_name).all()
    return render_template('create_request.html', service_name=service_name, professionals=professionals)



@app.route('/edit_request/<int:request_id>', methods=['GET', 'POST'])
def edit_request(request_id):
    service_request = ServiceRequest.query.get(request_id)
    if request.method == 'POST':
        # Update the request details
        service_request.description = request.form.get('description')
        db.session.commit()
        flash('Service request updated successfully!', 'success')
        return redirect(url_for('customer_dashboard'))
    
    return render_template('edit_request.html', request=service_request)

@app.route('/delete_request/<int:request_id>', methods=['POST'])
def delete_request(request_id):
    service_request = ServiceRequest.query.get(request_id)
    if service_request:
        db.session.delete(service_request)
        db.session.commit()
        flash('Service request deleted successfully!', 'success')
    else:
        flash('Service request not found.', 'error')
    return redirect(url_for('customer_dashboard'))

@app.route('/customer_dashboard')
def customer_dashboard():
    # Assume `customer_id` is stored in the session after login
    customer_id = session.get('user_id')

    # Fetch the customer's name
    customer = User.query.filter_by(user_id=customer_id).first()
    customer_name = customer.uname if customer else 'Customer'  # Fallback to 'Customer' if not found

    # Retrieve service requests for the logged-in customer
    service_requests = ServiceRequest.query.filter_by(customer_id=customer_id).all()

    # Debugging: Print out the service requests
    for request in service_requests:
        print(f"Request ID: {request.request_id}, Service ID: {request.service_id}, Status: {request.status}")

    return render_template('customer dashboard(home).html', name=customer_name, service_requests=service_requests)
@app.route('/close_request/<int:request_id>', methods=['POST'])
def close_request(request_id):
    service_request = ServiceRequest.query.get(request_id)
    if service_request:
        service_request.status = 'closed'
        db.session.commit()
        flash('Service request closed successfully!', 'success')
        return redirect(url_for('service_rating', request_id=request_id))
    else:
        flash('Service request not found.', 'error')
        return redirect(url_for('customer_dashboard'))
    
@app.route('/service_rating/<int:request_id>', methods=['GET', 'POST'])
def service_rating(request_id):
    if request.method == 'POST':
        rating = request.form.get('rating', type=int)
        review = request.form.get('review')
        
        # Save the rating and review to the database
        new_rating = ServiceRating(service_request_id=request_id, rating=rating, review=review)
        db.session.add(new_rating)
        db.session.commit()
        
        flash('Thank you for your feedback!', 'success')
        return redirect(url_for('customer_dashboard'))
    
    return render_template('service_rating.html', request_id=request_id)   

@app.route('/service_details/<int:service_id>')
def service_details(service_id):
    # Fetch the service details using the service_id
    service = Service.query.get(service_id)
    if not service:
        flash('Service not found.', 'error')
        return redirect(url_for('admin_dashboard'))

    # Fetch all service requests related to this service
    service_requests = db.session.query(
        ServiceRequest.request_id,
        ServiceRequest.status,
        ServiceRequest.request_date,
        User.uname.label("customer_name"),
        ProfessionalInformation.user_id.label("professional_id"),
        ProfessionalInformation.service_name.label("professional_service")
    ).join(User, ServiceRequest.customer_id == User.user_id) \
     .join(ProfessionalInformation, ServiceRequest.professional_id == ProfessionalInformation.user_id) \
     .filter(ServiceRequest.service_id == service_id).all()

    return render_template('service_details.html', service=service, service_requests=service_requests) 

@app.route('/customer_search', methods=['GET'])
def customer_search():
    query = request.args.get('query', '').strip()
    service_filter = request.args.get('service_filter', '').strip()
    search_results = []

    # Define the allowed service names
    allowed_services = ['Electrician', 'Plumbing', 'Cook']

    # Build the query
    professionals_query = db.session.query(
        User.uname,
        ProfessionalInformation.service_name,
        User.user_id,
        Service.base_price
    ).join(ProfessionalInformation, User.user_id == ProfessionalInformation.user_id
    ).join(ServiceRequest, User.user_id == ServiceRequest.professional_id
    ).join(Service, ServiceRequest.service_id == Service.service_id)

    if query:
        professionals_query = professionals_query.filter(
            (User.uname.ilike(f'%{query}%')) |
            (ProfessionalInformation.service_name.ilike(f'%{query}%'))
        )

    if service_filter and service_filter in allowed_services:
        professionals_query = professionals_query.filter(
            ProfessionalInformation.service_name == service_filter
        )

    professionals = professionals_query.all()

    # Prepare search results
    for professional in professionals:
        search_results.append({
            'professional_name': professional.uname,
            'service_name': professional.service_name,
            'base_price': professional.base_price,
            'professional_id': professional.user_id
        })

    return render_template('customer(search).html', search_results=search_results)

@app.route('/customer_summary')
def customer_summary():
    return render_template('customer(summary).html') 
      


@app.route('/professional_dashboard')
def professional_dashboard():
    if session.get('user_type') == 'professional':
        professional_id = session.get('user_id')

        # Fetch the professional's name
        professional = User.query.filter_by(user_id=professional_id).first()
        professional_name = professional.uname if professional else 'Professional'  # Fallback to 'Professional' if not found

        # Fetch today's services
        today_services = db.session.query(
            ServiceRequest.request_id,
            ServiceRequest.status,
            ServiceRequest.request_date,
            Service.service_name,
            User.uname.label("customer_name")
        ).join(Service, ServiceRequest.service_id == Service.service_id) \
         .join(User, ServiceRequest.customer_id == User.user_id) \
         .filter(
            ServiceRequest.professional_id == professional_id,
            ServiceRequest.status == 'requested',
            db.func.date(ServiceRequest.request_date) == date.today()
         ).all()

        # Fetch closed services
        closed_services = db.session.query(
            ServiceRequest.request_id.label("id"),
            Service.service_name,
            ServiceRequest.request_date.label("requested_date")
        ).join(Service, ServiceRequest.service_id == Service.service_id) \
         .filter(
            ServiceRequest.professional_id == professional_id,
            ServiceRequest.status == 'closed'
         ).all()

        return render_template('professional dashboard(home).html', name=professional_name, today_services=today_services, closed_services=closed_services)
    
    flash('Unauthorized access!', 'danger')
    return redirect(url_for('home'))

    
@app.route('/professional_profile', methods=['GET', 'POST'])
def professional_profile():
    if 'user_type' in session and session['user_type'] == 'professional':
        professional_id = session.get('user_id')
        professional = User.query.get(professional_id)

        if request.method == 'POST':
            # Update profile details
            professional.uname = request.form.get('uname')
            professional.professional_information.email = request.form.get('email')
            professional.professional_information.service_name = request.form.get('service_name')
            professional.professional_information.experience = request.form.get('experience')
            db.session.commit()
            flash('Profile updated successfully!', 'success')

        return render_template('professional_profile.html', professional=professional)
    else:
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('home'))
    
@app.route('/professional_search', methods=['GET'])
def professional_search():
    query = request.args.get('query', '').strip()
    search_results = []

    if query:
        # Search by customer name
        search_results = User.query.join(CustomerInformation).filter(
            User.uname.ilike(f'%{query}%'),
            User.role == 3  # Assuming role 3 is for customers
        ).all()
    else:
        # Return all customers if no query is provided
        search_results = User.query.join(CustomerInformation).filter(
            User.role == 3
        ).all()

    return render_template('professional dashboard(search).html', search_results=search_results)
@app.route('/professional_summary')
def professional_summary():
    # Implement the logic for the professional summary functionality
    return render_template('professional dashboard(summary).html')
 
    
@app.route('/professional/<int:professional_id>')
def professional_details(professional_id):
    # Fetch the professional's details using the professional_id
    professional = User.query.get(professional_id)
    if professional and professional.professional_information:
        details = {
            'id': professional.user_id,
            'name': professional.uname,
            'experience': professional.professional_information.experience,
            'service_name': professional.professional_information.service_name,
            'email': professional.professional_information.email
        }
        return render_template('professional_details.html', details=details)
    else:
        flash('Professional not found.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/approve_professional/<int:professional_id>', methods=['POST'])
def approve_professional(professional_id):
    professional = User.query.get(professional_id)
    if professional:
        professional.status = 'approved'
        try:
            db.session.commit()
            flash(f'Professional {professional.uname} approved successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error approving professional.', 'error')
    else:
        flash('Professional not found.', 'error')
    return redirect(url_for('dashboard'))

@app.route('/delete_professional/<int:professional_id>', methods=['POST'])
def delete_professional(professional_id):
    professional = User.query.get(professional_id)
    if professional:
        db.session.delete(professional)
        db.session.commit()
        flash(f'Professional {professional.uname} deleted successfully!', 'success')
    else:
        flash('Professional not found.', 'error')
    return redirect(url_for('dashboard'))

@app.route('/reject_professional/<int:professional_id>', methods=['POST'])
def reject_professional(professional_id):
    professional = User.query.get(professional_id)
    if professional:
        professional.status = 'rejected'
        db.session.commit()
        flash(f'Professional {professional.uname} rejected successfully!', 'success')
    else:
        flash('Professional not found.', 'error')
    return redirect(url_for('dashboard'))
    
@app.route('/edit_service/<int:service_id>', methods=['GET', 'POST'])
def edit_service(service_id):
    service = Service.query.get(service_id)
    if request.method == 'POST':
        # Update service details
        service.service_name = request.form.get('service_name')
        service.base_price = request.form.get('base_price', type=float)
        db.session.commit()
        flash('Service details updated successfully!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('edit_service.html', service=service)

@app.route('/delete_service/<int:service_id>', methods=['POST'])
def delete_service(service_id):
    service = Service.query.get(service_id)
    if service:
        db.session.delete(service)
        db.session.commit()
        flash('Service deleted successfully!', 'success')
    else:
        flash('Service not found.', 'error')
    return redirect(url_for('dashboard'))

@app.route('/approve_request/<int:request_id>', methods=['POST'])
def approve_request(request_id):
    service_request = ServiceRequest.query.get(request_id)
    if service_request:
        service_request.status = 'approved'
        db.session.commit()
        flash('Service request approved successfully!', 'success')
    else:
        flash('Service request not found.', 'error')
    return redirect(url_for('professional_dashboard'))

@app.route('/reject_request/<int:request_id>', methods=['POST'])
def reject_request(request_id):
    service_request = ServiceRequest.query.get(request_id)
    if service_request:
        service_request.status = 'rejected'
        db.session.commit()
        flash('Service request rejected successfully!', 'success')
    else:
        flash('Service request not found.', 'error')
    return redirect(url_for('professional_dashboard'))



# Customer registration route
@app.route('/register', methods=["GET", "POST"])
def customer_register():
        if request.method == "POST":
             uname = request.form.get("uname")
             pwd = request.form.get("pwd")
             email = request.form.get("email")
             address = request.form.get("address")
             Pincode = request.form.get("Pincode")

            # Check if username or email already exists
             existing_user = User.query.filter_by(uname=uname).first()
             existing_email = CustomerInformation.query.filter_by(email=email).first()

             if existing_user:
                  return render_template("customer signup.html", msg="Username already taken.")
             elif existing_email:
                  return render_template("customer signup.html", msg="Email already registered.")

        # Create new User entry
             new_user = User(uname=uname, pwd=pwd, role=3)  # Role 3 for customers
             db.session.add(new_user)
             db.session.commit()  # Commit to generate user_id

        # Create new CustomerInformation entry
             customer_info = CustomerInformation(
                  user_id=new_user.user_id,
                  email=email,
                  address=address,
                  Pincode=Pincode
             )
             db.session.add(customer_info)
             db.session.commit()  # Save customer information

        # Redirect to login page after successful registration
             return redirect(url_for('user_login'))
        return render_template("customer signup.html", msg="")
              
 # professional signup   
@app.route('/signup', methods=["GET", "POST"])
def professional_register():
        if request.method == "POST":
             uname = request.form.get("uname")
             pwd = request.form.get("pwd")
             email = request.form.get("email")
             service_name = request.form.get("service_name")
             experience = request.form.get("experience")

            # Check if username or email already exists
             existing_user = User.query.filter_by(uname=uname).first()
             existing_email = ProfessionalInformation.query.filter_by(email=email).first()

             if existing_user:
                  return render_template("service signup.html", msg="Username already taken.")
             elif existing_email:
                  return render_template("service signup.html", msg="Email already registered.")

        # Create new User entry
             new_user = User(uname=uname, pwd=pwd, role=2, status='pending')  # Role 3 for customers
             db.session.add(new_user)
             db.session.commit()  # Commit to generate user_id

        # Create new CustomerInformation entry
             professional_info = ProfessionalInformation(
                  user_id=new_user.user_id,
                  email=email,
                  service_name=service_name,
                  experience=experience
             )
             db.session.add(professional_info)
             db.session.commit()  # Save professional information

        # Redirect to login page after successful registration
             return redirect(url_for('user_login'))
        return render_template("service signup.html", msg="")


#udf for reading all general user
def fetch_user():
    # Query all users with role 2 (professionals)
    users = User.query.filter_by(role=2).all()
    user_list = {
        usr.user_id: [
            usr.uname,
            usr.professional_information.experience,
            usr.professional_information.service_name,
            usr.status
        ]
        for usr in users if usr.professional_information
    }
    return user_list
     
@app.route('/service_requests_data')
def service_requests_data():
    # Query the database for service request counts by status
    service_request_counts = db.session.query(
        ServiceRequest.status,
        db.func.count(ServiceRequest.request_id).label('count')
    ).group_by(ServiceRequest.status).all()

    # Prepare data for JSON response
    data = {
        'labels': [status for status, _ in service_request_counts],
        'counts': [count for _, count in service_request_counts]
    }
    return jsonify(data)

@app.route('/show_service_requests_graph')
def show_service_requests_graph():
    return render_template('service_requests_graph.html')

@app.route('/professional_service_requests_data')
def professional_service_requests_data():
    professional_id = session.get('user_id')
    
    # Query the database for service requests specific to the logged-in professional
    service_request_counts = db.session.query(
        ServiceRequest.status,
        db.func.count(ServiceRequest.request_id).label('count')
    ).filter(ServiceRequest.professional_id == professional_id).group_by(ServiceRequest.status).all()

    data = {
        'labels': [status for status, _ in service_request_counts],
        'counts': [count for _, count in service_request_counts]
    }
    return jsonify(data)

@app.route('/professional_ratings_data')
def professional_ratings_data():
    professional_id = session.get('user_id')
    
    # Query the database for ratings specific to the logged-in professional
    ratings_counts = db.session.query(
        ServiceRating.rating,
        db.func.count(ServiceRating.rating_id).label('count')
    ).join(ServiceRequest, ServiceRating.service_request_id == ServiceRequest.request_id) \
     .filter(ServiceRequest.professional_id == professional_id) \
     .group_by(ServiceRating.rating).all()

    # Convert query results to a dictionary for easy access
    ratings_dict = {rating: count for rating, count in ratings_counts}

    data = {
        'labels': ['1', '2', '3', '4', '5'],  # Assuming ratings are from 1 to 5
        'counts': [ratings_dict.get(rating, 0) for rating in range(1, 6)]
    }
    return jsonify(data)

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
