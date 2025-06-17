def get_user_data(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"  # SQL injection
    password = "admin123"  # Hardcoded password
    
    # Missing docstring
    # Poor variable names
    for i in range(100):
        for j in range(100):  # Nested loops O(n²)
            print(i * j)