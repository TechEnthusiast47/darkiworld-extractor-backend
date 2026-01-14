# app.py - API Flask pour votre site d'animés (avec extraction Kodi)
from flask import Flask, jsonify, request
from flask_cors import CORS
from my_scraper import get_animes_from_page, get_episodes_from_anime, get_genres_from_page
from extractors import extract_video_url, ExtractorFactory, KodiVidmolyExtractor
import json

app = Flask(__name__)
CORS(app)  # Permet à votre site web d'appeler cette API

# Configuration
BASE_URL = "https://french-anime.com/"

# ============ ROUTES PRINCIPALES (existantes) ============

@app.route('/api/animes', methods=['GET'])
def api_get_animes():
    category = request.args.get('category', 'news')
    page = request.args.get('page', '1')
    
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
    result = get_genres_from_page(BASE_URL)
    return jsonify(result)

# ============ ROUTES EXTRACTION (nouvelles) ============

@app.route('/api/extract', methods=['GET'])
def api_extract_video():
    """
    Route principale d'extraction (Kodi-compatible)
    Usage: /api/extract?url=URL_VIDMOLY
    """
    embed_url = request.args.get('url', '')
    
    if not embed_url:
        return jsonify({
            'success': False,
            'error': 'Paramètre "url" manquant'
        }), 400
    
    # Utiliser notre extracteur Kodi
    result = extract_video_url(embed_url)
    return jsonify(result)

@app.route('/api/extract/kodi', methods=['GET'])
def api_extract_kodi():
    """
    Extraction EXACTEMENT comme Kodi
    Usage: /api/extract/kodi?url=URL_VIDMOLY
    """
    embed_url = request.args.get('url', '')
    
    if not embed_url:
        return jsonify({'success': False, 'error': 'URL manquante'}), 400
    
    # Utiliser l'extracteur Kodi exact
    extractor = KodiVidmolyExtractor()
    result = extractor.extract(embed_url)
    
    return jsonify(result)

@app.route('/api/extract/test', methods=['GET'])
def api_extract_test():
    """
    Test avec URL exemple Vidmoly
    """
    test_url = "https://vidmoly.net/embed-9itb8l2nsinl.html"
    custom_url = request.args.get('url', test_url)
    
    extractor = KodiVidmolyExtractor()
    can_extract = extractor.can_extract(custom_url)
    result = extractor.extract(custom_url)
    
    return jsonify({
        'test': True,
        'url': custom_url,
        'can_extract': can_extract,
        'result': result,
        'kodi_notes': {
            'pattern_used': 'sources: *[{file:"([^"]+)"',
            'cleaning_applied': 'replace(",", ""), replace(".urlset", "")',
            'referer_format': 'url + "|Referer=" + hostname'
        }
    })

@app.route('/api/extract/debug', methods=['GET'])
def api_extract_debug():
    """
    Debug complet de l'extraction
    """
    url = request.args.get('url', '')
    
    if not url:
        return jsonify({'error': 'URL requise'}), 400
    
    factory = ExtractorFactory()
    extractor = factory.get_extractor(url)
    
    debug_info = {
        'input_url': url,
        'extractor_selected': extractor.__class__.__name__,
        'can_extract': extractor.can_extract(url),
        'is_vidmoly': 'vidmoly' in url.lower(),
        'url_analysis': {
            'has_embed': 'embed' in url.lower(),
            'is_html': url.lower().endswith('.html'),
            'domain': urlparse(url).netloc if '://' in url else 'N/A'
        }
    }
    
    # Extraction
    result = extractor.extract(url)
    debug_info['extraction_result'] = result
    
    return jsonify(debug_info)

# ============ NOUVELLES ROUTES KODI (AJOUTÉES) ============

@app.route('/check-kodi')
def check_kodi():
    import os
    path = os.path.join(os.path.dirname(__file__), 'kodi-addons')
    exists = os.path.exists(path)
    return {
        'kodi_addons_exists': exists,
        'path': path,
        'files': os.listdir(path) if exists else []
    }

@app.route('/api/extract/kodi-direct', methods=['GET'])
def api_extract_kodi_direct():
    """
    Nouvelle route : utilise Kodi si disponible
    """
    url = request.args.get('url', '')
    
    if not url:
        return jsonify({'success': False, 'error': 'URL manquante'}), 400
    
    # Pour l'instant, utiliser ton extracteur actuel
    result = extract_video_url(url)
    result['note'] = 'Kodi pas encore chargé - utilisant extracteur actuel'
    
    return jsonify(result)

# ============ HEALTH CHECK ============

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'online',
        'service': 'anime-api-kodi',
        'version': '4.0',
        'base_url': BASE_URL,
        'features': ['scraping', 'kodi_exact_extraction', 'vidmoly_support'],
        'extractors': ['KodiVidmolyExtractor', 'DirectExtractor'],
        'kodi_compatibility': '100% avec vidmoly.py de Kodi'
    })

@app.route('/')
def home():
    return jsonify({
        'api': 'Anime Scraper avec extraction Kodi-exact',
        'description': 'API compatible avec le code original de Kodi vStream',
        'endpoints': {
            '/api/animes': 'Animés par catégorie (category, page)',
            '/api/search': 'Recherche (q)',
            '/api/anime/details': 'Détails anime (url)',
            '/api/extract': 'Extraction vidéo Kodi (url)',
            '/api/extract/kodi': 'Extraction exacte Kodi (url)',
            '/api/extract/kodi-direct': 'Extraction via Kodi (futur)',
            '/api/extract/test': 'Test extraction (url optionnel)',
            '/api/extract/debug': 'Debug extraction (url)',
            '/api/genres': 'Genres disponibles',
            '/check-kodi': 'Vérifier Kodi',
            '/api/health': 'Statut API'
        },
        'examples': {
            'extraction': '/api/extract?url=https://vidmoly.net/embed-xxx',
            'kodi_exact': '/api/extract/kodi?url=https://vidmoly.net/embed-xxx',
            'check_kodi': '/check-kodi'
        }
    })

# Fonction utilitaire pour urlparse
def urlparse(url):
    from urllib.parse import urlparse as parse_url
    return parse_url(url)

if __name__ == '__main__':
    print("🚀 API Anime Kodi-exact démarrée")
    print("🔧 Extracteur principal: KodiVidmolyExtractor")
    print("📖 Pattern Kodi: sources: *[{file:\"([^\"]+)\"")
    print("🔗 Test: /api/extract/test")
    app.run(debug=True, host='0.0.0.0', port=5000)
