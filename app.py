# app.py - API Flask pour votre site d'animés
from flask import Flask, jsonify, request
from flask_cors import CORS
from my_scraper import get_animes_from_page, get_episodes_from_anime, get_genres_from_page
import json

app = Flask(__name__)
CORS(app)  # Permet à votre site web d'appeler cette API

# Configuration - À ADAPTER SI LE SITE A CHANGÉ
BASE_URL = "https://votre-site-d-anime-actuel.com"  # ⚠️ REMPLACEZ CE LIEN

@app.route('/api/animes', methods=['GET'])
def api_get_animes():
    """
    Endpoint principal pour récupérer les animés
    Exemple: /api/animes?category=vf&page=2
    """
    category = request.args.get('category', 'news')
    page = request.args.get('page', '1')
    
    # Correspondance des catégories (comme dans l'addon Kodi original)
    category_urls = {
        'news': BASE_URL,                     # Derniers ajouts
        'vf': BASE_URL + '/animes-vf/',       # Version française
        'vostfr': BASE_URL + '/animes-vostfr/',  # Version originale
        'films': BASE_URL + '/films-vf-vostfr/'  # Films
    }
    
    # Construire l'URL complète
    if category not in category_urls:
        category = 'news'
    
    url = category_urls[category]
    
    # Ajouter la pagination si ce n'est pas la page 1
    if page != '1':
        url = f"{url}page/{page}/"
    
    # Utiliser notre scraper
    result = get_animes_from_page(url)
    return jsonify(result)

@app.route('/api/search', methods=['GET'])
def api_search():
    """
    Endpoint pour rechercher des animés
    Exemple: /api/search?q=naruto
    """
    query = request.args.get('q', '')
    
    if not query or len(query) < 2:
        return jsonify({
            'success': False,
            'error': 'La recherche doit contenir au moins 2 caractères',
            'query': query,
            'results': []
        }), 400
    
    # Construction de l'URL de recherche (identique à l'addon Kodi)
    search_url = f"{BASE_URL}?do=search&mode=advanced&subaction=search&story={query}"
    
    result = get_animes_from_page(search_url)
    return jsonify(result)

@app.route('/api/anime/details', methods=['GET'])
def api_anime_details():
    """
    Endpoint pour les détails et épisodes d'un animé
    Exemple: /api/anime/details?url=https://site.com/anime/naruto
    """
    anime_url = request.args.get('url', '')
    
    if not anime_url:
        return jsonify({
            'success': False,
            'error': 'Le paramètre "url" est requis'
        }), 400
    
    # Récupérer les épisodes
    result = get_episodes_from_anime(anime_url)
    return jsonify(result)

@app.route('/api/genres', methods=['GET'])
def api_get_genres():
    """
    Endpoint pour la liste des genres disponibles
    Exemple: /api/genres
    """
    result = get_genres_from_page(BASE_URL)
    return jsonify(result)

@app.route('/api/health', methods=['GET'])
def health_check():
    """
    Endpoint pour vérifier que l'API fonctionne
    """
    return jsonify({
        'status': 'online',
        'service': 'anime-scraper-api',
        'version': '1.0',
        'base_url': BASE_URL
    })

@app.route('/')
def home():
    """
    Page d'accueil de l'API
    """
    endpoints = {
        'endpoints': {
            '/api/animes': 'Liste des animés par catégorie (paramètres: category, page)',
            '/api/search': 'Recherche d\'animés (paramètre: q)',
            '/api/anime/details': 'Détails d\'un animé (paramètre: url)',
            '/api/genres': 'Liste des genres disponibles',
            '/api/health': 'Vérification du statut de l\'API'
        },
        'categories': ['news', 'vf', 'vostfr', 'films'],
        'example': '/api/animes?category=vf&page=1'
    }
    return jsonify(endpoints)

if __name__ == '__main__':
    # Lancer l'API en mode développement
    app.run(debug=True, host='0.0.0.0', port=5000)
