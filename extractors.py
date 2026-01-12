# extractors.py - Extracteurs de liens vidéo (Version Kodi-exact)
import requests
import re
import json
from urllib.parse import urlparse, urljoin
from abc import ABC, abstractmethod

class BaseExtractor(ABC):
    """Classe de base pour tous les extracteurs"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:139.0) Gecko/20100101 Firefox/139.0',
            'Accept': '*/*',
            'Accept-Language': 'fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3',
        }
    
    @abstractmethod
    def can_extract(self, url):
        pass
    
    @abstractmethod
    def extract(self, url):
        pass

class KodiVidmolyExtractor(BaseExtractor):
    """Extracteur Vidmoly EXACTEMENT comme Kodi"""
    
    def can_extract(self, url):
        url_lower = url.lower()
        return any(x in url_lower for x in ['vidmoly', 'vidmoly.to', 'vidmoly.net', '/embed-'])
    
    def extract(self, url):
        try:
            # ÉTAPE 1: Normalisation EXACTE comme Kodi
            url = url.replace('vidmoly.to', 'vidmoly.net')
            print(f"[KodiVidmoly] Extraction de: {url}")
            
            # ÉTAPE 2: Headers EXACTES comme Kodi cRequestHandler
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:139.0) Gecko/20100101 Firefox/139.0',
                'Referer': url,
                'Sec-Fetch-Dest': 'iframe',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            # ÉTAPE 3: Requête avec timeout comme Kodi
            response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
            response.raise_for_status()
            html = response.text
            
            # ÉTAPE 4: Pattern EXACT de Kodi vidmoly.py
            # Pattern: sources: *[{file:"URL"
            sPattern = r'sources: *\[{file:"([^"]+)'
            match = re.search(sPattern, html, re.IGNORECASE)
            
            if match:
                api_call = match.group(1).strip()
                print(f"[KodiVidmoly] Pattern Kodi trouvé: {api_call[:100]}...")
                
                # ÉTAPE 5: Nettoyage COMME Kodi (parfois commenté, parfois activé)
                # Dans Kodi: #api_call = api_call.replace(',', '').replace('.urlset', '')
                # On active le nettoyage car ça semble nécessaire
                api_call = api_call.replace(',', '').replace('.urlset', '')
                api_call = api_call.replace('\\/', '/')  # Décoder les slashes
                
                # ÉTAPE 6: Ajout du Referer EXACTEMENT comme Kodi
                # Kodi fait: api_call + '|Referer=' + util.urlHostName(self._url)
                # util.urlHostName() retourne juste le hostname
                parsed_url = urlparse(url)
                hostname = parsed_url.hostname
                kodi_full_url = api_call + '|Referer=' + hostname
                
                print(f"[KodiVidmoly] URL Kodi complète: {kodi_full_url[:150]}...")
                
                # ÉTAPE 7: Retourner COMME Kodi mais adapté pour le web
                # Pour le web, on sépare l'URL du Referer
                video_url = api_call  # URL pure pour la lecture
                referer = f"https://{hostname}"
                
                return {
                    'success': True,
                    'url': video_url,  # Pour le lecteur web
                    'kodi_url': kodi_full_url,  # Format exact Kodi
                    'method': 'kodi_exact_pattern',
                    'extractor': 'kodi_vidmoly',
                    'headers': {
                        'Referer': referer,
                        'User-Agent': headers['User-Agent'],
                        'Origin': referer
                    },
                    'kodi_compatible': True,
                    'note': 'Extraction identique à Kodi vidmoly.py'
                }
            
            # ÉTAPE 8: Fallback si pattern Kodi non trouvé
            print(f"[KodiVidmoly] Pattern Kodi non trouvé, recherche alternatives...")
            
            # Méthodes alternatives (comme Kodi pourrait faire)
            fallback_patterns = [
                r'file\s*:\s*["\'](https?://[^"\']+)["\']',
                r'src\s*:\s*["\'](https?://[^"\']+)["\']',
                r'"file"\s*:\s*"([^"]+)"',
                r'sources\s*:\s*\[\s*{\s*["\']?file["\']?\s*:\s*["\']([^"\']+)["\']',
            ]
            
            for i, pattern in enumerate(fallback_patterns):
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    video_url = match.group(1).strip()
                    print(f"[KodiVidmoly] Fallback {i} trouvé: {video_url[:100]}...")
                    
                    # Appliquer le même nettoyage
                    video_url = video_url.replace(',', '').replace('.urlset', '').replace('\\/', '/')
                    
                    parsed_url = urlparse(url)
                    hostname = parsed_url.hostname
                    
                    return {
                        'success': True,
                        'url': video_url,
                        'method': f'kodi_fallback_{i}',
                        'extractor': 'kodi_vidmoly',
                        'headers': {
                            'Referer': f"https://{hostname}",
                            'User-Agent': headers['User-Agent']
                        }
                    }
            
            # ÉTAPE 9: Aucun pattern trouvé
            print(f"[KodiVidmoly] Aucun pattern vidéo trouvé")
            
            return {
                'success': False,
                'error': 'Aucun pattern vidéo trouvé (identique à Kodi)',
                'extractor': 'kodi_vidmoly',
                'debug': {
                    'url': url,
                    'html_preview': html[:500],
                    'patterns_tried': ['kodi_exact'] + [f'fallback_{i}' for i in range(len(fallback_patterns))]
                }
            }
            
        except requests.RequestException as e:
            print(f"[KodiVidmoly] Erreur réseau: {e}")
            return {
                'success': False,
                'error': f'Erreur réseau: {str(e)}',
                'extractor': 'kodi_vidmoly'
            }
        except Exception as e:
            print(f"[KodiVidmoly] Erreur inattendue: {e}")
            return {
                'success': False,
                'error': f'Erreur: {str(e)}',
                'extractor': 'kodi_vidmoly'
            }

class DirectExtractor(BaseExtractor):
    """Pour liens directs (fallback)"""
    
    def can_extract(self, url):
        return True  # Accepte tout en dernier recours
    
    def extract(self, url):
        print(f"[DirectExtractor] Traitement: {url}")
        
        # Vérifier si c'est déjà une vidéo
        if any(x in url.lower() for x in ['.mp4', '.m3u8', '.mkv', '.webm']):
            return {
                'success': True,
                'url': url,
                'method': 'already_direct',
                'extractor': 'direct'
            }
        
        return {
            'success': False,
            'error': 'URL non reconnue comme lien vidéo direct',
            'extractor': 'direct'
        }

class ExtractorFactory:
    """Factory de gestion des extracteurs"""
    
    def __init__(self):
        self.extractors = [
            KodiVidmolyExtractor(),  # Premier: Kodi exact
            DirectExtractor()         # Dernier: fallback
        ]
        print(f"[Factory] {len(self.extractors)} extracteurs chargés")
    
    def get_extractor(self, url):
        for extractor in self.extractors:
            if extractor.can_extract(url):
                print(f"[Factory] Sélection: {extractor.__class__.__name__}")
                return extractor
        return DirectExtractor()
    
    def extract(self, url):
        extractor = self.get_extractor(url)
        return extractor.extract(url)

# Fonction principale pour l'API
def extract_video_url(url):
    print(f"\n{'='*60}")
    print(f"EXTRACTION KODI-STYLE DÉMARRÉE")
    print(f"URL: {url}")
    print(f"{'='*60}")
    
    factory = ExtractorFactory()
    result = factory.extract(url)
    
    print(f"{'='*60}")
    if result.get('success'):
        print(f"✅ SUCCÈS - {result.get('method')}")
        print(f"URL: {result.get('url', 'N/A')[:100]}...")
        print(f"Extracteur: {result.get('extractor')}")
    else:
        print(f"❌ ÉCHEC")
        print(f"Erreur: {result.get('error', 'Inconnue')}")
    print(f"{'='*60}\n")
    
    return result
