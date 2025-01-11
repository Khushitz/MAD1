from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey


db=SQLAlchemy()

class User(db.Model):
    __tablename__="User"
    user_id = db.Column(db.Integer, primary_key=True)
    uname=db.Column(db.String(20), nullable = False)
    pwd = db.Column(db.String(20), nullable = False)
    role = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(10), default='pending', nullable=False)

    # Define the one-to-one relationship with CustomerInformation
    customer_information = db.relationship('CustomerInformation', back_populates='user', uselist=False)
    professional_information = db.relationship('ProfessionalInformation', back_populates='user', uselist=False, cascade='all, delete-orphan' )


class CustomerInformation(db.Model):
    __tablename__ = "customer_information"
    user_id = db.Column(db.Integer, db.ForeignKey('User.user_id'), primary_key=True)
    email = db.Column(db.String(50), unique=True, nullable=False)
    address = db.Column(db.String(255), nullable=False)
    Pincode = db.Column(db.Integer(), nullable=False)

      # Define the reverse relationship to User
    user = db.relationship('User', back_populates='customer_information')

# Professional Information (Details specific to service professionals)
class ProfessionalInformation(db.Model):
    __tablename__ = "professional_information"
    user_id = db.Column(db.Integer, db.ForeignKey('User.user_id'), primary_key=True)
    email = db.Column(db.String(50), unique=True, nullable=False)
    service_name = db.Column(db.String(50), nullable=False)
    experience = db.Column(db.Integer, nullable=False)

    user = db.relationship('User', back_populates='professional_information') 

# Service Model (Services offered)
class Service(db.Model):
    __tablename__ = "services"
    service_id = db.Column(db.Integer, primary_key=True)
    service_name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    base_price = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f'<Service {self.service_name}>'

# Service Requests (Linking customers and professionals with services)
class ServiceRequest(db.Model):
    __tablename__ = "service_requests"
    request_id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('User.user_id'), nullable=False)
    professional_id = db.Column(db.Integer, db.ForeignKey('User.user_id'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('services.service_id'), nullable=False)
    status = db.Column(db.String(20), default="requested", nullable=False)  # requested, accepted, completed, closed
    request_date = db.Column(db.DateTime, default=db.func.current_timestamp(), nullable=False)

    # Define relationships with User and Service
    customer = db.relationship('User', foreign_keys=[customer_id], backref='customer_requests')
    professional = db.relationship('User', foreign_keys=[professional_id], backref='professional_requests')
    service = db.relationship('Service', backref='service_requests')

# Rating and Review (After the service is completed)
class ServiceRating(db.Model):
    __tablename__ = "service_ratings"
    rating_id = db.Column(db.Integer, primary_key=True)
    service_request_id = db.Column(db.Integer, db.ForeignKey('service_requests.request_id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # Rating out of 5
    review = db.Column(db.Text, nullable=True)

    service_request = db.relationship('ServiceRequest', backref='ratings')

# Admin Activity (To manage services, add, edit, or remove services)

class AdminServiceManagement(db.Model):
    __tablename__ = "admin_service_management"
    action_id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('User.user_id'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('services.service_id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)  # 'Add', 'Edit', 'Remove'

    admin = db.relationship('User', backref='admin_actions')
    service = db.relationship('Service', backref='service_admin_actions')
    

    

