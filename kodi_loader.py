"""
kodi_loader.py
Charge automatiquement les extracteurs Kodi en arrière-plan.
N'affecte pas le fonctionnement normal de l'API.
"""

import os
import sys
import subprocess
import threading
import time
import importlib.util

# ============ CONFIGURATION ============

KODI_PATH = os.path.join(os.path.dirname(__file__), 'kodi-addons')
KODI_REPO_URL = "https://github.com/TechEnthusiast47/venom-xbmc-addons.git"
HOSTERS_PATH = os.path.join(KODI_PATH, 'resources', 'hosters')

# Extracteurs à charger (les plus utiles)
EXTRACTORS_TO_LOAD = [
    'vidmoly',    # Vidmoly.net
    'voe',        # Voe.sx
    'streamtape', # Streamtape.com
    'dood',       # DoodStream
    'mixdrop',    # MixDrop
    'filelions',  # FileLions
    'netu',       # NetU/Waaw/Hqq
    'streamlare', # Streamlare
    'streamvid',  # Streamvid
    'vudeo',      # Vudeo
]

# Stockage des extracteurs chargés
KODI_EXTRACTORS = {}
KODI_LOADED = False
KODI_LOADING = False

# ============ FONCTIONS UTILITAIRES ============

def log(message):
    """Journalisation simple"""
    print(f"[KodiLoader] {message}")

def download_kodi():
    """Télécharge le dépôt Kodi si absent"""
    try:
        if os.path.exists(KODI_PATH):
            log("✅ Kodi déjà présent")
            return True
        
        log("📥 Téléchargement de Kodi...")
        
        # Option 1: Essayer git submodule
        try:
            result = subprocess.run(
                ['git', 'submodule', 'update', '--init', '--recursive'],
                cwd=os.path.dirname(__file__),
                capture_output=True,
                text=True,
                timeout=120
            )
            if result.returncode == 0:
                log("✅ Kodi téléchargé via git submodule")
                return True
        except:
            pass
        
        # Option 2: Clone direct
        log("🔄 Tentative de clone direct...")
        result = subprocess.run(
            ['git', 'clone', '--depth', '1', KODI_REPO_URL, KODI_PATH],
            capture_output=True,
            text=True,
            timeout=180
        )
        
        if result.returncode == 0:
            log("✅ Kodi cloné avec succès")
            return True
        else:
            log(f"❌ Échec du clone: {result.stderr[:200]}")
            return False
            
    except Exception as e:
        log(f"❌ Erreur téléchargement: {e}")
        return False

def load_extractors():
    """Charge les extracteurs Kodi"""
    global KODI_EXTRACTORS, KODI_LOADED
    
    try:
        # Vérifier si le dossier hosters existe
        if not os.path.exists(HOSTERS_PATH):
            log("❌ Dossier hosters non trouvé")
            return
        
        # Ajouter au chemin Python
        if HOSTERS_PATH not in sys.path:
            sys.path.insert(0, HOSTERS_PATH)
        
        # Charger chaque extracteur
        loaded_count = 0
        for extractor_name in EXTRACTORS_TO_LOAD:
            try:
                file_path = os.path.join(HOSTERS_PATH, f'{extractor_name}.py')
                
                if not os.path.exists(file_path):
                    log(f"⚠️  Fichier non trouvé: {extractor_name}.py")
                    continue
                
                # Charger dynamiquement le module
                spec = importlib.util.spec_from_file_location(extractor_name, file_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Récupérer la classe cHoster
                if hasattr(module, 'cHoster'):
                    KODI_EXTRACTORS[extractor_name] = module.cHoster
                    loaded_count += 1
                    log(f"✅ {extractor_name}")
                else:
                    log(f"⚠️  cHoster non trouvé dans {extractor_name}")
                    
            except Exception as e:
                log(f"⚠️  Erreur {extractor_name}: {str(e)[:100]}")
        
        KODI_LOADED = loaded_count > 0
        log(f"🎯 {loaded_count}/{len(EXTRACTORS_TO_LOAD)} extracteurs chargés")
        
    except Exception as e:
        log(f"❌ Erreur chargement extracteurs: {e}")

def background_load():
    """Charge Kodi en arrière-plan"""
    global KODI_LOADING
    
    if KODI_LOADING:
        return
    
    KODI_LOADING = True
    log("🚀 Démarrage chargement Kodi...")
    
    # 1. Télécharger Kodi
    if download_kodi():
        # 2. Charger les extracteurs
        load_extractors()
    else:
        log("⚠️  Kodi non disponible - l'API continue normalement")
    
    KODI_LOADING = False

# ============ FONCTION D'EXTRACTION ============

def extract_with_kodi(url):
    """
    Utilise les extracteurs Kodi pour extraire un lien vidéo.
    Retourne le résultat ou None si échec.
    """
    if not KODI_LOADED:
        return None
    
    try:
        url_lower = url.lower()
        
        # Mapping URL → extracteur
        mapping = {
            'vidmoly': 'vidmoly',
            'voe.sx': 'voe',
            'streamtape': 'streamtape',
            'doodstream': 'dood',
            'dood.': 'dood',
            'mixdrop': 'mixdrop',
            'filelions': 'filelions',
            'netu': 'netu',
            'waaw': 'netu',
            'hqq': 'netu',
            'streamlare': 'streamlare',
            'streamvid': 'streamvid',
            'vudeo': 'vudeo',
        }
        
        # Trouver l'extracteur
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
                from urllib.parse import urlparse
                
                # Formater comme Kodi
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
                    'kodi_result': result,
                    'headers': {
                        'Referer': referer,
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                }
    
    except Exception as e:
        log(f"❌ Erreur extraction Kodi: {e}")
    
    return None

# ============ FONCTIONS D'ÉTAT ============

def get_kodi_status():
    """Retourne l'état de Kodi"""
    return {
        'loaded': KODI_LOADED,
        'loading': KODI_LOADING,
        'extractors_available': list(KODI_EXTRACTORS.keys()),
        'extractors_count': len(KODI_EXTRACTORS),
        'kodi_path_exists': os.path.exists(KODI_PATH),
        'hosters_path_exists': os.path.exists(HOSTERS_PATH)
    }

def is_kodi_available():
    """Vérifie si Kodi est prêt à l'emploi"""
    return KODI_LOADED

# ============ DÉMARRAGE AUTOMATIQUE ============

# Démarrer le chargement en arrière-plan au démarrage
log("🔄 Programme de chargement Kodi initialisé")
loader_thread = threading.Thread(target=background_load, daemon=True)
loader_thread.start()

# ============ TEST ============

if __name__ == '__main__':
    print("🔍 Test du KodiLoader")
    print(f"📁 Kodi path: {KODI_PATH}")
    print(f"📁 Exists: {os.path.exists(KODI_PATH)}")
    
    # Attendre un peu
    time.sleep(3)
    
    status = get_kodi_status()
    print(f"✅ Kodi loaded: {status['loaded']}")
    print(f"📦 Extracteurs: {status['extractors_available']}")
