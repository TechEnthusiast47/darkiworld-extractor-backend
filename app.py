# app.py - API avec système Kodi léger
from flask import Flask, jsonify, request
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

# ============ IMPORT KODI SYSTÈME ============
try:
    from kodi_extractors import extract_with_kodi, is_kodi_available, get_kodi_status
    KODI_AVAILABLE = True
except ImportError:
    KODI_AVAILABLE = False
    print("⚠️  Module kodi_extractors non trouvé")

# ============ ROUTES SIMPLES ============

@app.route('/')
def home():
    return jsonify({
        'api': 'API Extracteurs Kodi Léger',
        'status': 'online',
        'kodi_system': KODI_AVAILABLE,
        'routes': {
            '/extract': 'Extraction vidéo (url param)',
            '/extract/kodi': 'Forcer extraction Kodi',
            '/kodi/status': 'Statut système Kodi',
            '/health': 'Santé API'
        }
    })

@app.route('/extract', methods=['GET'])
def extract():
    """Extraction intelligente : Kodi si disponible, sinon fallback"""
    url = request.args.get('url', '')
    
    if not url:
        return jsonify({'success': False, 'error': 'URL manquante'}), 400
    
    # 1. Essayer Kodi si disponible
    if KODI_AVAILABLE and is_kodi_available():
        result = extract_with_kodi(url)
        if result.get('success'):
            result['method'] = 'kodi_primary'
            return jsonify(result)
    
    # 2. Fallback simple (pour démo)
    return jsonify({
        'success': False,
        'error': 'Aucun extracteur disponible',
        'kodi_available': KODI_AVAILABLE and is_kodi_available(),
        'method': 'fallback'
    })

@app.route('/extract/kodi', methods=['GET'])
def extract_kodi():
    """Forcer l'utilisation de Kodi"""
    url = request.args.get('url', '')
    
    if not url:
        return jsonify({'success': False, 'error': 'URL manquante'}), 400
    
    if not KODI_AVAILABLE:
        return jsonify({
            'success': False,
            'error': 'Système Kodi non disponible',
            'note': 'Vérifiez kodi_extractors.py et kodi_downloader.py'
        }), 503
    
    if not is_kodi_available():
        return jsonify({
            'success': False,
            'error': 'Extracteurs Kodi encore en chargement',
            'note': 'Attendez 30 secondes'
        }), 503
    
    result = extract_with_kodi(url)
    result['method'] = 'kodi_forced'
    
    return jsonify(result)

@app.route('/kodi/status', methods=['GET'])
def kodi_status():
    """Statut du système Kodi"""
    if not KODI_AVAILABLE:
        return jsonify({
            'kodi_system': False,
            'error': 'Modules Kodi non trouvés'
        })
    
    status = get_kodi_status()
    return jsonify({
        'kodi_system': True,
        'status': status
    })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'kodi_available': KODI_AVAILABLE,
        'kodi_ready': is_kodi_available() if KODI_AVAILABLE else False
    })

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 API Extracteurs Kodi Léger")
    print(f"📦 Système Kodi: {'✅ Disponible' if KODI_AVAILABLE else '❌ Non disponible'}")
    print("🌐 Routes:")
    print("   /extract?url=URL → Extraction intelligente")
    print("   /extract/kodi?url=URL → Kodi uniquement")
    print("   /kodi/status → Statut Kodi")
    print("=" * 60)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
