#import secrets
#print(secrets.token_hex(16))  # This will generate a secure random key

#bc8ba792963f7a8dabfa441d1f158701

from app import app  # Import the app object from your main app file

with app.test_request_context():
   print(app.url_map)  # Prints all routes with their methods and endpoints

