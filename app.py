# app.py - API Flask pour votre site d'animés
from flask import Flask, jsonify, request
from flask_cors import CORS
from my_scraper import get_animes_from_page, get_episodes_from_anime, get_genres_from_page
# AJOUTER CET IMPORT :
from extractors import extract_video_url
import json

app = Flask(__name__)
CORS(app)  # Permet à votre site web d'appeler cette API

# Configuration - À ADAPTER SI LE SITE A CHANGÉ
BASE_URL = "https://french-anime.com/"  # ⚠️ REMPLACEZ CE LIEN

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

# ============ NOUVELLE ROUTE D'EXTRACTION ============

@app.route('/api/extract', methods=['GET'])
def api_extract_video():
    """
    Extrait le lien vidéo direct depuis une URL d'embed
    Usage: /api/extract?url=URL_VIDMOLY_OU_AUTRE
    
    Retourne:
    {
        "success": true,
        "url": "https://lien-direct.mp4",
        "method": "kodi_pattern",
        "extractor": "vidmoly"
    }
    """
    embed_url = request.args.get('url', '')
    
    if not embed_url:
        return jsonify({
            'success': False,
            'error': 'Paramètre "url" manquant'
        }), 400
    
    # Utiliser notre système d'extraction
    result = extract_video_url(embed_url)
    
    return jsonify(result)

# Route spécifique pour tests
@app.route('/api/extract/test', methods=['GET'])
def api_extract_test():
    """
    Route de test pour l'extraction
    """
    test_cases = [
        "https://vidmoly.net/embed-example",  # Remplacer par un vrai exemple
        "https://direct-link.mp4",
    ]
    
    results = []
    for test_url in test_cases:
        result = extract_video_url(test_url)
        results.append({
            'input': test_url,
            'output': result
        })
    
    return jsonify({
        'test': True,
        'results': results,
        'extractors_loaded': ['VidmolyExtractor', 'DirectExtractor']
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    """
    Endpoint pour vérifier que l'API fonctionne
    """
    return jsonify({
        'status': 'online',
        'service': 'anime-scraper-api',
        'version': '2.0',  # Version augmentée
        'base_url': BASE_URL,
        'features': ['scraping', 'video_extraction']
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
            '/api/extract': 'Extraction de lien vidéo direct (paramètre: url)',  # NOUVEAU
            '/api/genres': 'Liste des genres disponibles',
            '/api/health': 'Vérification du statut de l\'API'
        },
        'categories': ['news', 'vf', 'vostfr', 'films'],
        'example': '/api/extract?url=https://vidmoly.net/embed-xyz123'
    }
    return jsonify(endpoints)

if __name__ == '__main__':
    # Lancer l'API en mode développement
    app.run(debug=True, host='0.0.0.0', port=5000)
