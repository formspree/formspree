from werkzeug.security import generate_password_hash, check_password_hash

def hash_pwd(password):
    return generate_password_hash(password)

def check_password(password):
    return check_password_hash(hash_pwd(password), password)
