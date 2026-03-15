"""
Create a test user for the pneumonia detection system
Run this once to create a default admin user
"""

from app import app, db, User

with app.app_context():
    # Check if user already exists
    existing_user = User.query.filter_by(username='admin').first()
    
    if existing_user:
        print("❌ User 'admin' already exists!")
        print(f"   Username: admin")
        print(f"   Password: (use the password you set)")
    else:
        # Create new admin user
        admin = User(username='admin', role='admin')
        admin.set_password('admin123')  # Plain text password for testing
        
        db.session.add(admin)
        db.session.commit()
        
        print("✅ Test user created successfully!")
        print(f"   Username: admin")
        print(f"   Password: admin123")
        print("\nYou can now login with these credentials.")
