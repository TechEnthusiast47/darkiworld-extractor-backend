# app.py - API Flask pour votre site d'animés
from flask import Flask, jsonify, request
from flask_cors import CORS
from my_scraper import get_animes_from_page, get_episodes_from_anime, get_genres_from_page
from extractors import extract_video_url, ExtractorFactory, VidmolyExtractor
import json

app = Flask(__name__)
CORS(app)  # Permet à votre site web d'appeler cette API

# Configuration
BASE_URL = "https://french-anime.com/"

@app.route('/api/animes', methods=['GET'])
def api_get_animes():
    """
    Endpoint principal pour récupérer les animés
    Exemple: /api/animes?category=vf&page=2
    """
    category = request.args.get('category', 'news')
    page = request.args.get('page', '1')
    
    # Correspondance des catégories
    category_urls = {
        'news': BASE_URL,
        'vf': BASE_URL + '/animes-vf/',
        'vostfr': BASE_URL + '/animes-vostfr/',
        'films': BASE_URL + '/films-vf-vostfr/'
    }
    
    if category not in category_urls:
        category = 'news'
    
    url = category_urls[category]
    
    if page != '1':
        url = f"{url}page/{page}/"
    
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

# ============ ROUTES D'EXTRACTION ET DEBUG ============

@app.route('/api/extract', methods=['GET'])
def api_extract_video():
    """
    Extrait le lien vidéo direct depuis une URL d'embed
    Usage: /api/extract?url=URL_VIDMOLY_OU_AUTRE
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

@app.route('/api/extract/debug', methods=['GET'])
def api_extract_debug():
    """
    Debug détaillé de l'extraction
    """
    embed_url = request.args.get('url', '')
    
    if not embed_url:
        return jsonify({
            'success': False,
            'error': 'Paramètre "url" manquant'
        }), 400
    
    # Analyse détaillée
    factory = ExtractorFactory()
    extractor = factory.get_extractor(embed_url)
    
    debug_info = {
        'input_url': embed_url,
        'extractor_used': extractor.__class__.__name__,
        'can_extract': extractor.can_extract(embed_url),
        'extractor_details': {
            'name': extractor.__class__.__name__,
            'module': extractor.__class__.__module__
        }
    }
    
    # Si c'est Vidmoly, donner plus de détails
    if isinstance(extractor, VidmolyExtractor):
        debug_info['vidmoly_check'] = {
            'contains_vidmoly': 'vidmoly' in embed_url.lower(),
            'contains_embed': 'embed' in embed_url.lower(),
            'is_html': embed_url.lower().endswith('.html'),
            'url_lower': embed_url.lower()
        }
    
    # Tenter l'extraction
    result = extractor.extract(embed_url)
    debug_info['extraction_result'] = result
    
    return jsonify(debug_info)

@app.route('/api/extract/test/vidmoly', methods=['GET'])
def api_test_vidmoly():
    """
    Test spécifique Vidmoly avec exemple
    """
    # Exemple d'URL Vidmoly (à adapter si besoin)
    test_url = "https://vidmoly.net/embed-9itb8l2nsinl.html"
    custom_url = request.args.get('url', test_url)
    
    extractor = VidmolyExtractor()
    
    return jsonify({
        'test': True,
        'test_url': custom_url,
        'can_extract': extractor.can_extract(custom_url),
        'extraction_result': extractor.extract(custom_url),
        'vidmoly_check': {
            'domain_in_url': 'vidmoly' in custom_url.lower(),
            'embed_in_url': 'embed' in custom_url.lower(),
            'is_html': custom_url.lower().endswith('.html')
        }
    })

@app.route('/api/extract/list', methods=['GET'])
def api_extract_list():
    """
    Liste tous les extracteurs disponibles
    """
    factory = ExtractorFactory()
    
    extractors_info = []
    for extractor in factory.extractors:
        extractors_info.append({
            'name': extractor.__class__.__name__,
            'module': extractor.__class__.__module__,
            'description': extractor.__doc__ or 'No description'
        })
    
    return jsonify({
        'extractors_count': len(factory.extractors),
        'extractors': extractors_info
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    """
    Endpoint pour vérifier que l'API fonctionne
    """
    return jsonify({
        'status': 'online',
        'service': 'anime-scraper-api',
        'version': '2.1',
        'base_url': BASE_URL,
        'features': ['scraping', 'video_extraction', 'debug_tools'],
        'extractors': ['VidmolyExtractor', 'DirectExtractor']
    })

@app.route('/')
def home():
    """
    Page d'accueil de l'API
    """
    endpoints = {
        'endpoints': {
            '/api/animes': 'Liste des animés (category, page)',
            '/api/search': 'Recherche (q)',
            '/api/anime/details': 'Détails anime (url)',
            '/api/extract': 'Extraction vidéo (url)',
            '/api/extract/debug': 'Debug extraction (url)',
            '/api/extract/test/vidmoly': 'Test Vidmoly (url optionnel)',
            '/api/extract/list': 'Liste extracteurs',
            '/api/genres': 'Genres disponibles',
            '/api/health': 'Statut API'
        },
        'categories': ['news', 'vf', 'vostfr', 'films'],
        'examples': {
            'extraction': '/api/extract?url=https://vidmoly.net/embed-xxx',
            'debug': '/api/extract/debug?url=https://vidmoly.net/embed-xxx',
            'anime_details': '/api/anime/details?url=https://french-anime.com/anime/naruto'
        }
    }
    return jsonify(endpoints)

if __name__ == '__main__':
    print("🚀 API Anime Scraper avec extraction Vidmoly")
    print(f"📡 URL de base: {BASE_URL}")
    print("🔧 Extracteurs chargés: VidmolyExtractor, DirectExtractor")
    app.run(debug=True, host='0.0.0.0', port=5000)
