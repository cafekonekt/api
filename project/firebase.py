import firebase_admin
from firebase_admin import credentials, auth

# Path to your Firebase service account key JSON file
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)