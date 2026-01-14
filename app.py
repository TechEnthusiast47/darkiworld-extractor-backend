# app.py - API avec ton extracteur actuel + Kodi en option
from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import sys
import subprocess
import importlib.util
import re
import requests
from urllib.parse import urlparse

app = Flask(__name__)
CORS(app)

# ============ TON EXTRACTEUR ACTUEL (qui marche) ============

class CurrentExtractor:
    """TON extracteur actuel (copié de ton extractors.py)"""
    
    def extract(self, url):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://vidmoly.net/',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0'
            }
            
            r = requests.get(url, headers=headers, timeout=10)
            html = r.text
            
            # Pattern Kodi-like pour Vidmoly
            pattern = r'sources:\s*\[\{file:"([^"]+)"'
            match = re.search(pattern, html)
            
            if match:
                video_url = match.group(1)
                # Nettoyage (comme Kodi)
                video_url = video_url.replace(',', '').replace('.urlset', '')
                
                return {
                    'success': True,
                    'url': video_url,
                    'extractor': 'current_vidmoly',
                    'headers': {
                        'Referer': f'https://{urlparse(url).netloc}',
                        'Origin': f'https://{urlparse(url).netloc}',
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    },
                    'kodi_compatible': True,
                    'method': 'kodi_exact_pattern'
                }
            else:
                # Essayer un autre pattern
                pattern2 = r'file:\s*"([^"]+)"'
                match2 = re.search(pattern2, html)
                if match2:
                    video_url = match2.group(1)
                    return {
                        'success': True,
                        'url': video_url,
                        'extractor': 'current_fallback',
                        'headers': {'Referer': url},
                        'method': 'fallback_pattern'
                    }
                
        except Exception as e:
            print(f"❌ Erreur extraction: {e}")
        
        return {
            'success': False,
            'error': 'Extraction non supportée',
            'extractor': 'current'
        }

# Instance globale
current_extractor = CurrentExtractor()

# ============ KODI (optionnel) ============

KODI_EXTRACTORS = {}
HAS_KODI = False

def setup_kodi():
    """Charge Kodi en arrière-plan"""
    global KODI_EXTRACTORS, HAS_KODI
    
    try:
        kodi_path = os.path.join(os.path.dirname(__file__), 'kodi-addons')
        
        # Télécharger si absent
        if not os.path.exists(kodi_path):
            print("📥 Tentative téléchargement Kodi...")
            try:
                # Essayer git submodule
                result = subprocess.run(
                    ['git', 'submodule', 'update', '--init', '--recursive'],
                    capture_output=True, text=True, timeout=30
                )
                if result.returncode == 0:
                    print("✅ Kodi téléchargé (submodule)")
                else:
                    # Fallback: clone direct
                    subprocess.run([
                        'git', 'clone', '--depth', '1',
                        'https://github.com/TechEnthusiast47/venom-xbmc-addons.git',
                        kodi_path
                    ], capture_output=True)
                    print("✅ Kodi téléchargé (clone direct)")
            except:
                print("⚠️  Impossible de télécharger Kodi")
                return
        
        # Vérifier hosters
        hosters_path = os.path.join(kodi_path, 'resources', 'hosters')
        if not os.path.exists(hosters_path):
            print("❌ Dossier hosters manquant")
            return
        
        # Charger extracteurs
        sys.path.insert(0, hosters_path)
        extractors_to_load = ['vidmoly', 'voe', 'streamtape']
        
        for name in extractors_to_load:
            try:
                file_path = os.path.join(hosters_path, f'{name}.py')
                if os.path.exists(file_path):
                    spec = importlib.util.spec_from_file_location(name, file_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    if hasattr(module, 'cHoster'):
                        KODI_EXTRACTORS[name] = module.cHoster
                        print(f"✅ Extracteur Kodi chargé: {name}")
            except:
                pass
        
        HAS_KODI = len(KODI_EXTRACTORS) > 0
        
    except Exception as e:
        print(f"⚠️  Setup Kodi échoué: {e}")

# Démarrer en arrière-plan
import threading
kodi_thread = threading.Thread(target=setup_kodi, daemon=True)
kodi_thread.start()

# ============ EXTRACTION KODI ============

def extract_with_kodi(url):
    """Utilise Kodi si disponible"""
    if not HAS_KODI:
        return None
    
    try:
        url_lower = url.lower()
        
        # Trouver extracteur
        extractor_name = None
        if 'vidmoly' in url_lower:
            extractor_name = 'vidmoly'
        elif 'voe' in url_lower:
            extractor_name = 'voe'
        elif 'streamtape' in url_lower:
            extractor_name = 'streamtape'
        
        if not extractor_name or extractor_name not in KODI_EXTRACTORS:
            return None
        
        # Extraire avec Kodi
        extractor_class = KODI_EXTRACTORS[extractor_name]
        extractor = extractor_class()
        extractor._url = url
        
        if hasattr(extractor, '_getMediaLinkForGuest'):
            success, result = extractor._getMediaLinkForGuest()
            
            if success:
                # Format Kodi
                if isinstance(result, str) and '|Referer=' in result:
                    video_url, referer_part = result.split('|Referer=', 1)
                    referer = f"https://{referer_part}"
                else:
                    video_url = result
                    referer = f"https://{urlparse(url).netloc}"
                
                return {
                    'success': True,
                    'url': video_url,
                    'extractor': f'kodi_{extractor_name}',
                    'headers': {'Referer': referer},
                    'kodi_result': result,
                    'method': 'kodi_direct'
                }
                
    except Exception as e:
        print(f"❌ Erreur Kodi: {e}")
    
    return None

# ============ ROUTES PRINCIPALES ============

@app.route('/')
def home():
    return jsonify({
        'api': 'DarkiWorld Extractor',
        'status': 'online',
        'kodi_available': HAS_KODI,
        'endpoints': {
            '/extract': 'Extraction vidéo (URL requise)',
            '/extract/kodi': 'Forcer Kodi',
            '/extract/test': 'Test avec Vidmoly',
            '/check': 'État API',
            '/check-kodi': 'État Kodi'
        },
        'example': '/extract?url=https://vidmoly.net/embed-xxx'
    })

@app.route('/extract', methods=['GET'])
def extract():
    """Extraction principale"""
    url = request.args.get('url', '')
    
    if not url:
        return jsonify({'success': False, 'error': 'URL manquante'}), 400
    
    # 1. Essayer Kodi
    if HAS_KODI:
        kodi_result = extract_with_kodi(url)
        if kodi_result and kodi_result.get('success'):
            kodi_result['method'] = 'kodi_primary'
            return jsonify(kodi_result)
    
    # 2. Ton extracteur actuel (garanti)
    result = current_extractor.extract(url)
    result['method'] = 'current_primary'
    result['kodi_available'] = HAS_KODI
    
    return jsonify(result)

@app.route('/extract/kodi', methods=['GET'])
def extract_kodi():
    """Forcer Kodi"""
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
            'error': 'Kodi a échoué pour cette URL',
            'kodi_extractors': list(KODI_EXTRACTORS.keys())
        })

@app.route('/extract/test', methods=['GET'])
def extract_test():
    """Test avec Vidmoly"""
    test_url = "https://vidmoly.net/embed-9itb8l2nsinl.html"
    custom_url = request.args.get('url', test_url)
    
    # Utiliser ton extracteur (garanti)
    result = current_extractor.extract(custom_url)
    result['test'] = True
    result['url'] = custom_url
    result['kodi_available'] = HAS_KODI
    
    return jsonify(result)

@app.route('/check')
def check():
    """État API"""
    return jsonify({
        'status': 'online',
        'kodi': {
            'available': HAS_KODI,
            'extractors_loaded': list(KODI_EXTRACTORS.keys()) if HAS_KODI else [],
            'count': len(KODI_EXTRACTORS)
        },
        'current_extractor': 'available'
    })

@app.route('/check-kodi')
def check_kodi():
    """État Kodi"""
    path = os.path.join(os.path.dirname(__file__), 'kodi-addons')
    exists = os.path.exists(path)
    
    return jsonify({
        'kodi_addons_exists': exists,
        'has_kodi': HAS_KODI,
        'extractors': list(KODI_EXTRACTORS.keys()) if HAS_KODI else []
    })

# ============ DÉMARRAGE ============

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 DarkiWorld Extractor API")
    print(f"📦 Kodi: {'✅ Disponible' if HAS_KODI else '❌ Non disponible'}")
    print("🌐 Endpoints:")
    print("   /extract?url=URL → Extraction principale")
    print("   /extract/test → Test Vidmoly")
    print("   /check → État")
    print("=" * 50)
    
    # Attendre un peu que Kodi charge
    import time
    time.sleep(2)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
