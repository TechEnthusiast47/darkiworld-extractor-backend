"""
kodi_extractors.py
Charge et utilise les extracteurs Kodi téléchargés
"""
import os
import sys
import importlib.util
import threading
import time

class KodiExtractorSystem:
    def __init__(self):
        self.extractors_dir = os.path.join(os.path.dirname(__file__), "kodi_extractors")
        self.extractors = {}
        self.ready = False
        self.loading = False
        
        # Démarrer le chargement en arrière-plan
        self.load_thread = threading.Thread(target=self.load_all_extractors, daemon=True)
        self.load_thread.start()
    
    def is_ready(self):
        return self.ready
    
    def wait_until_ready(self, timeout=30):
        """Attend que le système soit prêt"""
        start = time.time()
        while not self.ready and time.time() - start < timeout:
            time.sleep(1)
        return self.ready
    
    def load_extractor(self, extractor_name):
        """Charge un extracteur spécifique"""
        try:
            file_path = os.path.join(self.extractors_dir, f"{extractor_name}.py")
            
            if not os.path.exists(file_path):
                return None
            
            # Charger dynamiquement
            spec = importlib.util.spec_from_file_location(extractor_name, file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Récupérer la classe cHoster
            if hasattr(module, 'cHoster'):
                return module.cHoster
                
        except Exception as e:
            print(f"⚠️  Erreur chargement {extractor_name}: {e}")
        
        return None
    
    def load_all_extractors(self):
        """Charge tous les extracteurs disponibles"""
        if self.loading:
            return
        
        self.loading = True
        print("🔄 Chargement des extracteurs Kodi...")
        
        try:
            if not os.path.exists(self.extractors_dir):
                print("❌ Dossier extracteurs non trouvé")
                self.ready = True
                return
            
            # Ajouter au chemin Python
            if self.extractors_dir not in sys.path:
                sys.path.insert(0, self.extractors_dir)
            
            # Liste des extracteurs à charger (priorité)
            extractors_to_load = [
                'vidmoly', 'voe', 'streamtape', 'dood',
                'mixdrop', 'filelions', 'netu', 'streamlare'
            ]
            
            for name in extractors_to_load:
                extractor_class = self.load_extractor(name)
                if extractor_class:
                    self.extractors[name] = extractor_class
                    print(f"✅ {name}")
            
            self.ready = True
            print(f"🎯 {len(self.extractors)} extracteurs chargés")
            
        except Exception as e:
            print(f"❌ Erreur chargement: {e}")
            self.ready = True
        
        self.loading = False
    
    def get_extractor_for_url(self, url):
        """Trouve l'extracteur approprié pour une URL"""
        url_lower = url.lower()
        
        mapping = {
            'vidmoly': ['vidmoly', 'vidmoly.to', 'vidmoly.net'],
            'voe': ['voe', 'voe.sx', 'voe-unblock'],
            'streamtape': ['streamtape', 'strtape', 'stape'],
            'dood': ['dood', 'doodstream', 'ds2play', 'dood.'],
            'mixdrop': ['mixdrop', 'mixdroop'],
            'filelions': ['filelions', 'fviplions'],
            'netu': ['netu', 'waaw', 'hqq', 'netu.tv'],
            'streamlare': ['streamlare', 'slares'],
        }
        
        for extractor_name, keywords in mapping.items():
            if extractor_name in self.extractors:
                for keyword in keywords:
                    if keyword in url_lower:
                        return self.extractors[extractor_name], extractor_name
        
        return None, None
    
    def extract(self, url):
        """Extrait un lien vidéo avec l'extracteur Kodi"""
        if not self.ready:
            return {
                'success': False,
                'error': 'Extracteurs Kodi non encore chargés',
                'extractor': 'kodi_system'
            }
        
        try:
            extractor_class, extractor_name = self.get_extractor_for_url(url)
            
            if not extractor_class:
                return {
                    'success': False,
                    'error': f'Aucun extracteur Kodi trouvé pour: {url}',
                    'extractor': 'kodi_system'
                }
            
            print(f"🔧 Utilisation extracteur Kodi: {extractor_name}")
            
            # Utiliser l'extracteur comme Kodi le fait
            extractor_instance = extractor_class()
            extractor_instance._url = url
            
            if hasattr(extractor_instance, '_getMediaLinkForGuest'):
                success, result = extractor_instance._getMediaLinkForGuest()
                
                if success:
                    # Format Kodi: "url|Referer=hostname"
                    if isinstance(result, str) and '|Referer=' in result:
                        video_url, referer_part = result.split('|Referer=', 1)
                        referer = f"https://{referer_part}"
                    else:
                        video_url = result
                        from urllib.parse import urlparse as parse_url
                        referer = f"https://{parse_url(url).netloc}"
                    
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
                else:
                    return {
                        'success': False,
                        'error': f'Kodi extraction failed: {result}',
                        'extractor': f'kodi_{extractor_name}'
                    }
            else:
                return {
                    'success': False,
                    'error': 'Méthode _getMediaLinkForGuest non trouvée',
                    'extractor': f'kodi_{extractor_name}'
                }
                
        except Exception as e:
            print(f"❌ Erreur extraction Kodi: {e}")
            return {
                'success': False,
                'error': str(e),
                'extractor': 'kodi_system'
            }

# Instance globale
kodi_system = KodiExtractorSystem()

# Fonctions d'export
def extract_with_kodi(url):
    return kodi_system.extract(url)

def is_kodi_available():
    return kodi_system.is_ready()

def get_kodi_status():
    return {
        'ready': kodi_system.ready,
        'loading': kodi_system.loading,
        'extractors_loaded': list(kodi_system.extractors.keys()),
        'extractors_count': len(kodi_system.extractors)
    }
