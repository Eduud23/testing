import os
import json
from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, db
from collections import defaultdict

# Fetch Firebase credentials from environment variables
firebase_credentials = {
    "type": os.getenv("FIREBASE_TYPE"),
    "project_id": os.getenv("FIREBASE_PROJECT_ID"),
    "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
    "private_key": os.getenv("FIREBASE_PRIVATE_KEY").replace('\\n', '\n'),  # Ensure \n is replaced with an actual newline
    "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
    "client_id": os.getenv("FIREBASE_CLIENT_ID"),
    "auth_uri": os.getenv("FIREBASE_AUTH_URI"),
    "token_uri": os.getenv("FIREBASE_TOKEN_URI"),
    "auth_provider_x509_cert_url": os.getenv("FIREBASE_AUTH_PROVIDER_X509_CERT_URL"),
    "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_X509_CERT_URL")
}

# Initialize Firebase with the service account key
cred = credentials.Certificate(firebase_credentials)
firebase_admin.initialize_app(cred, {
    'databaseURL': os.getenv('FIREBASE_DATABASE_URL')  # Fetch Firebase DB URL from environment
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
        app.logger.debug(f"Error: {recommendations['error']}")
        return jsonify(recommendations), 400
    
    return jsonify(recommendations), 200

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

