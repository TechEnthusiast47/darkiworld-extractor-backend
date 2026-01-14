# app.py - API Flask pour extraction vidéo (Kodi + système actuel)
from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import sys
import subprocess
import importlib.util

app = Flask(__name__)
CORS(app)

# ============ CHARGEMENT KODI (silencieux) ============

def setup_kodi():
    """Charge les extracteurs Kodi si disponibles"""
    kodi_extractors = {}
    
    try:
        # 1. Télécharger Kodi si absent
        kodi_path = os.path.join(os.path.dirname(__file__), 'kodi-addons')
        if not os.path.exists(kodi_path):
            print("📥 Tentative de téléchargement Kodi...")
            try:
                subprocess.run(['git', 'submodule', 'update', '--init', '--recursive'], 
                             check=True, capture_output=True, timeout=60)
                print("✅ Kodi téléchargé")
            except:
                # Fallback: clone direct
                repo_url = "https://github.com/TechEnthusiast47/venom-xbmc-addons"
                subprocess.run(['git', 'clone', '--depth', '1', repo_url, kodi_path],
                             capture_output=True)
        
        # 2. Vérifier si Kodi est présent
        hosters_path = os.path.join(kodi_path, 'resources', 'hosters')
        if not os.path.exists(hosters_path):
            print("❌ Dossier hosters Kodi non trouvé")
            return kodi_extractors
        
        # 3. Charger quelques extracteurs
        sys.path.insert(0, hosters_path)
        extractors_to_load = ['vidmoly', 'voe', 'streamtape', 'dood', 'mixdrop']
        
        for name in extractors_to_load:
            try:
                file_path = os.path.join(hosters_path, f'{name}.py')
                if os.path.exists(file_path):
                    spec = importlib.util.spec_from_file_location(name, file_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    if hasattr(module, 'cHoster'):
                        kodi_extractors[name] = module.cHoster
                        print(f"✅ Extracteur Kodi chargé: {name}")
            except Exception as e:
                print(f"⚠️  Erreur chargement {name}: {e}")
                
    except Exception as e:
        print(f"⚠️  Setup Kodi échoué: {e}")
    
    return kodi_extractors

# Charger Kodi au démarrage
KODI_EXTRACTORS = setup_kodi()
HAS_KODI = len(KODI_EXTRACTORS) > 0

# ============ EXTRACTEUR ACTUEL (fallback) ============

class CurrentExtractor:
    """Ton extracteur actuel (simplifié)"""
    def extract(self, url):
        # ICI METS TON CODE D'EXTRACTION ACTUEL
        # (celui qui marche déjà)
        from urllib.parse import urlparse
        import re
        import requests
        
        if 'vidmoly' in url:
            # Pattern Kodi-like pour Vidmoly
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Referer': 'https://vidmoly.net/'
                }
                r = requests.get(url, headers=headers, timeout=10)
                
                # Pattern similaire à Kodi
                pattern = r'sources:\s*\[\{file:"([^"]+)"'
                match = re.search(pattern, r.text)
                
                if match:
                    video_url = match.group(1)
                    return {
                        'success': True,
                        'url': video_url,
                        'extractor': 'current_vidmoly',
                        'headers': {
                            'Referer': f'https://{urlparse(url).netloc}',
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                        }
                    }
            except Exception as e:
                pass
        
        # Fallback pour autres hébergeurs
        return {
            'success': False,
            'error': 'Extraction non supportée',
            'extractor': 'current'
        }

current_extractor = CurrentExtractor()

# ============ EXTRACTEUR KODI DIRECT ============

def extract_with_kodi(url):
    """Utilise les vrais extracteurs Kodi"""
    try:
        url_lower = url.lower()
        
        # Mapping URLs → extracteurs Kodi
        mapping = {
            'vidmoly': 'vidmoly',
            'voe.sx': 'voe',
            'streamtape': 'streamtape',
            'dood': 'dood',
            'mixdrop': 'mixdrop',
            'filelions': 'filelions'
        }
        
        # Trouver le bon extracteur
        extractor_name = None
        for key, name in mapping.items():
            if key in url_lower:
                extractor_name = name
                break
        
        if not extractor_name or extractor_name not in KODI_EXTRACTORS:
            return None
        
        # Utiliser l'extracteur Kodi
        extractor_class = KODI_EXTRACTORS[extractor_name]
        extractor = extractor_class()
        extractor._url = url
        
        if hasattr(extractor, '_getMediaLinkForGuest'):
            success, result = extractor._getMediaLinkForGuest()
            
            if success:
                # Format Kodi: "url|Referer=hostname"
                if isinstance(result, str) and '|Referer=' in result:
                    video_url, referer_part = result.split('|Referer=', 1)
                    referer = f"https://{referer_part}"
                else:
                    video_url = result
                    referer = f"https://{urlparse(url).netloc}"
                
                return {
                    'success': True,
                    'url': video_url,
                    'kodi_result': result,
                    'extractor': f'kodi_{extractor_name}',
                    'headers': {
                        'Referer': referer,
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                }
                
    except Exception as e:
        print(f"❌ Erreur extraction Kodi: {e}")
    
    return None

# ============ ROUTES ============

@app.route('/')
def home():
    return jsonify({
        'api': 'Extracteur Vidéo',
        'status': 'online',
        'features': {
            'kodi_available': HAS_KODI,
            'kodi_extractors': list(KODI_EXTRACTORS.keys()) if HAS_KODI else [],
            'extractors': ['current', 'kodi_direct']
        },
        'endpoints': {
            '/extract': 'Extraction intelligente (Kodi si disponible)',
            '/extract/kodi': 'Forcer extraction Kodi',
            '/extract/current': 'Forcer extracteur actuel',
            '/check': 'Vérifier état',
            '/check-kodi': 'Vérifier Kodi'
        }
    })

@app.route('/extract', methods=['GET'])
def extract():
    """Extraction intelligente : essaie Kodi d'abord, puis fallback"""
    url = request.args.get('url', '')
    
    if not url:
        return jsonify({'success': False, 'error': 'URL manquante'}), 400
    
    # 1. Essayer Kodi si disponible
    if HAS_KODI:
        kodi_result = extract_with_kodi(url)
        if kodi_result and kodi_result.get('success'):
            kodi_result['method'] = 'kodi_primary'
            return jsonify(kodi_result)
    
    # 2. Fallback: extracteur actuel
    result = current_extractor.extract(url)
    result['method'] = 'current_fallback'
    result['kodi_available'] = HAS_KODI
    
    return jsonify(result)

@app.route('/extract/kodi', methods=['GET'])
def extract_kodi_only():
    """Forcer l'utilisation de Kodi"""
    url = request.args.get('url', '')
    
    if not url:
        return jsonify({'success': False, 'error': 'URL manquante'}), 400
    
    if not HAS_KODI:
        return jsonify({
            'success': False,
            'error': 'Kodi non disponible',
            'kodi_available': False
        }), 503
    
    result = extract_with_kodi(url)
    
    if result:
        return jsonify(result)
    else:
        return jsonify({
            'success': False,
            'error': 'Kodi a échoué ou extracteur non trouvé',
            'kodi_extractors': list(KODI_EXTRACTORS.keys())
        }), 404

@app.route('/extract/current', methods=['GET'])
def extract_current():
    """Forcer l'utilisation de l'extracteur actuel"""
    url = request.args.get('url', '')
    
    if not url:
        return jsonify({'success': False, 'error': 'URL manquante'}), 400
    
    result = current_extractor.extract(url)
    result['method'] = 'current_forced'
    
    return jsonify(result)

@app.route('/check')
def check():
    """Vérifier l'état de l'API"""
    return jsonify({
        'status': 'online',
        'kodi': {
            'available': HAS_KODI,
            'extractors_loaded': list(KODI_EXTRACTORS.keys()) if HAS_KODI else [],
            'count': len(KODI_EXTRACTORS)
        },
        'extractors': {
            'current': 'available',
            'kodi': 'available' if HAS_KODI else 'unavailable'
        }
    })

@app.route('/check-kodi')
def check_kodi():
    """Vérifier Kodi spécifiquement"""
    path = os.path.join(os.path.dirname(__file__), 'kodi-addons')
    exists = os.path.exists(path)
    
    return jsonify({
        'kodi_addons_exists': exists,
        'path': path,
        'has_kodi_extractors': HAS_KODI,
        'extractors': list(KODI_EXTRACTORS.keys()) if HAS_KODI else [],
        'files': os.listdir(path) if exists else []
    })

# ============ DÉMARRAGE ============

def urlparse(url):
    from urllib.parse import urlparse as parse_url
    return parse_url(url)

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 API Extracteur Vidéo")
    print(f"✅ Kodi disponible: {HAS_KODI}")
    if HAS_KODI:
        print(f"📦 Extracteurs Kodi: {list(KODI_EXTRACTORS.keys())}")
    print("🌐 Endpoints:")
    print("   /extract?url=URL → Extraction intelligente")
    print("   /extract/kodi?url=URL → Kodi uniquement")
    print("   /extract/current?url=URL → Extracteur actuel")
    print("   /check → État API")
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
