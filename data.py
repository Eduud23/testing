import os
import base64
import json
from io import BytesIO
from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, db
from collections import defaultdict

# Decode the base64 string and load it as a Firebase credential
encoded_credentials = os.getenv('FIREBASE_CREDENTIALS')
if encoded_credentials:
    decoded_credentials = base64.b64decode(encoded_credentials)
    credentials_json = json.load(BytesIO(decoded_credentials))
    cred = credentials.Certificate(credentials_json)
else:
    raise ValueError("Firebase credentials not set in environment variables.")

# Initialize Firebase
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://gearup-df833-default-rtdb.asia-southeast1.firebasedatabase.app/'
})

app = Flask(__name__)

def jaccard_similarity(set1, set2):
    if not set1 or not set2:
        return 0.0
    intersection = set1.intersection(set2)
    union = set1.union(set2)
    return len(intersection) / len(union)

def generate_recommendations(current_user_id):
    ref = db.reference("user_interactions")
    all_users = ref.get()

    if not all_users or current_user_id not in all_users:
        return {"error": "No user interactions found or user not in database."}

    current_user_products = set(all_users[current_user_id].keys())

    recommended_products = defaultdict(int)
    popular_products = defaultdict(int)
    other_user_products = set()

    total_similarity = 0.0
    user_comparisons = 0

    for user_id, user_products in all_users.items():
        if user_id == current_user_id:
            continue
        
        other_user_product_set = set(user_products.keys())
        other_user_products.update(other_user_product_set)
        
        for product_id in other_user_product_set:
            popular_products[product_id] += 1
        
        similarity = jaccard_similarity(current_user_products, other_user_product_set)
        
        if similarity > 0.0:
            total_similarity += similarity
            user_comparisons += 1
    
    average_similarity = (total_similarity / user_comparisons) if user_comparisons > 0 else 0.0
    similarity_threshold = max(average_similarity * 0.5, 0.05)

    for user_id, user_products in all_users.items():
        if user_id == current_user_id:
            continue
        
        other_user_product_set = set(user_products.keys())
        similarity = jaccard_similarity(current_user_products, other_user_product_set)
        
        if similarity >= similarity_threshold:
            for product_id in other_user_product_set:
                if product_id not in current_user_products:
                    recommended_products[product_id] += 1
    
    sorted_recommendations = sorted(recommended_products.keys(), key=lambda k: recommended_products[k], reverse=True)
    
    if not sorted_recommendations and len(all_users) == 2:
        sorted_recommendations = list(other_user_products)

    return {"recommended_products": sorted_recommendations}

@app.route('/recommendations/<user_id>', methods=['GET'])
def get_recommendations(user_id):
    recommendations = generate_recommendations(user_id)
    
    if 'error' in recommendations:
        return jsonify(recommendations), 400
    
    return jsonify(recommendations), 200

if __name__ == "__main__":
    app.run(debug=True)
