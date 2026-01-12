# app.py - API Anime avec extraction Kodi
from flask import Flask, jsonify, request
from flask_cors import CORS
from my_scraper import get_animes_from_page, get_episodes_from_anime, get_genres_from_page
from extractors import extract_video_url, ExtractorFactory, VidmolyExtractor
import json

app = Flask(__name__)
CORS(app)

BASE_URL = "https://french-anime.com/"

# ============ ROUTES PRINCIPALES ============

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
    
    url = category_urls.get(category, category_urls['news'])
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
            'error': 'Minimum 2 caractères',
            'results': []
        }), 400
    
    search_url = f"{BASE_URL}?do=search&mode=advanced&subaction=search&story={query}"
    result = get_animes_from_page(search_url)
    return jsonify(result)

@app.route('/api/anime/details', methods=['GET'])
def api_anime_details():
    anime_url = request.args.get('url', '')
    if not anime_url:
        return jsonify({'success': False, 'error': 'URL requise'}), 400
    
    result = get_episodes_from_anime(anime_url)
    return jsonify(result)

@app.route('/api/genres', methods=['GET'])
def api_get_genres():
    result = get_genres_from_page(BASE_URL)
    return jsonify(result)

# ============ ROUTES EXTRACTION ============

@app.route('/api/extract', methods=['GET'])
def api_extract_video():
    """Route principale d'extraction (Kodi-compatible)"""
    embed_url = request.args.get('url', '')
    
    if not embed_url:
        return jsonify({'success': False, 'error': 'URL manquante'}), 400
    
    result = extract_video_url(embed_url)
    return jsonify(result)

@app.route('/api/extract/kodi-test', methods=['GET'])
def api_kodi_test():
    """Test spécifique pattern Kodi"""
    test_url = request.args.get('url', 'https://vidmoly.net/embed-9itb8l2nsinl.html')
    
    extractor = VidmolyExtractor()
    
    return jsonify({
        'test': 'kodi_pattern',
        'url': test_url,
        'can_extract': extractor.can_extract(test_url),
        'pattern_used': 'sources: *[{file:"([^"]+)"',
        'result': extractor.extract(test_url)
    })

@app.route('/api/extract/debug', methods=['GET'])
def api_extract_debug():
    """Debug complet"""
    url = request.args.get('url', '')
    if not url:
        return jsonify({'error': 'URL requise'}), 400
    
    factory = ExtractorFactory()
    extractor = factory.get_extractor(url)
    
    debug_info = {
        'input_url': url,
        'extractor': extractor.__class__.__name__,
        'can_extract': extractor.can_extract(url),
        'vidmoly_check': {
            'has_vidmoly': 'vidmoly' in url.lower(),
            'has_embed': 'embed' in url.lower(),
            'is_html': url.lower().endswith('.html')
        }
    }
    
    # Extraction
    result = extractor.extract(url)
    debug_info['extraction_result'] = result
    
    return jsonify(debug_info)

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'online',
        'service': 'anime-api-kodi',
        'version': '3.0',
        'features': ['scraping', 'kodi_extraction', 'vidmoly_support'],
        'extractors': ['VidmolyExtractor', 'DirectExtractor']
    })

@app.route('/')
def home():
    return jsonify({
        'api': 'Anime Scraper avec extraction Kodi',
        'endpoints': {
            '/api/animes': 'Animés par catégorie',
            '/api/search': 'Recherche',
            '/api/anime/details': 'Détails anime',
            '/api/extract': 'Extraction vidéo',
            '/api/extract/kodi-test': 'Test pattern Kodi',
            '/api/extract/debug': 'Debug extraction',
            '/api/health': 'Statut API'
        }
    })

if __name__ == '__main__':
    print("🚀 API Anime Kodi-compatible démarrée")
    print("🔧 Extracteurs: VidmolyExtractor (pattern Kodi exact)")
    app.run(debug=True, host='0.0.0.0', port=5000)
