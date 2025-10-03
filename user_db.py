# user_db.py

from passlib.context import CryptContext

# 1. Define the password context (for hashing and verifying)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
users_db = {
    "admin": {
        "username": "admin",
        "full_name": "Admin User",
        "role": "Administrator",
        "hashed_password": "$2a$14$bNvL1OAJFuxwGWCSjzSyM.1tirWJel7Nl77vMyGTyCmPKVJbrbhHa"
    },
    "editor": {
        "username": "editor",
        "full_name": "Editor User",
        "role": "Editor",
        "hashed_password": "$2a$14$mZSH/LUk6Kuqn6fywPpwb.Ukp5KFkohWiyVFK4.X4ZjPDjjiYSI.S"
    },
    "viewer": {
        "username": "viewer",
        "full_name": "Viewer User",
        "role": "Viewer",
        "hashed_password": "$2a$14$MrBBEpBw4ULeu/lRRilwP.iubRKe1xjpAJUx0fRhYrHpXVlKqp9g6"
        }
}