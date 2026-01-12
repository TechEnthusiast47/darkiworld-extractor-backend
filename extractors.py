# extractors.py - Extracteurs de liens vidéo
import requests
import re
import json
from urllib.parse import urlparse, urljoin
from abc import ABC, abstractmethod

class BaseExtractor(ABC):
    """Classe de base pour tous les extracteurs"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': '*/*',
            'Accept-Language': 'fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3',
        }
    
    @abstractmethod
    def can_extract(self, url):
        """Vérifie si cet extracteur peut gérer cette URL"""
        pass
    
    @abstractmethod
    def extract(self, url):
        """Extrait le lien vidéo direct"""
        pass
    
    def _fetch_page(self, url, referer=None):
        """Récupère une page web avec headers"""
        headers = self.headers.copy()
        if referer:
            headers['Referer'] = referer
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text

class VidmolyExtractor(BaseExtractor):
    """Extracteur pour Vidmoly (basé sur le code Kodi)"""
    
    def can_extract(self, url):
        return 'vidmoly' in url
    
    def extract(self, url):
        try:
            # Normaliser l'URL
            url = url.replace('vidmoly.to', 'vidmoly.net')
            
            print(f"[VidmolyExtractor] Extraction de: {url}")
            
            # 1. Récupérer la page
            html = self._fetch_page(url, referer=url)
            
            # 2. Pattern Kodi principal: sources: [{file:"URL"
            pattern_kodi = r'sources\s*:\s*\[\s*{\s*file\s*:\s*"([^"]+)"'
            match_kodi = re.search(pattern_kodi, html, re.IGNORECASE | re.DOTALL)
            
            if match_kodi:
                video_url = match_kodi.group(1).strip()
                # Nettoyage comme dans Kodi
                video_url = video_url.replace(',', '').replace('.urlset', '')
                
                return {
                    'success': True,
                    'url': video_url,
                    'method': 'kodi_pattern',
                    'extractor': 'vidmoly'
                }
            
            # 3. Chercher dans les scripts JSON
            script_pattern = r'sources\s*:\s*(\[[^\]]+\])'
            script_match = re.search(script_pattern, html, re.IGNORECASE | re.DOTALL)
            
            if script_match:
                try:
                    json_str = script_match.group(1)
                    json_str = json_str.replace("'", '"')
                    json_str = re.sub(r',\s*]', ']', json_str)  # Retirer virgule finale
                    
                    sources = json.loads(json_str)
                    if sources and len(sources) > 0 and sources[0].get('file'):
                        return {
                            'success': True,
                            'url': sources[0]['file'],
                            'method': 'json_sources',
                            'extractor': 'vidmoly'
                        }
                except (json.JSONDecodeError, KeyError):
                    pass
            
            # 4. Chercher URLs directes
            direct_patterns = [
                r'file\s*:\s*["\'](https?://[^"\']+\.(mp4|m3u8|mkv|webm)[^"\']*)["\']',
                r'src\s*:\s*["\'](https?://[^"\']+\.(mp4|m3u8|mkv|webm)[^"\']*)["\']',
                r'"(https?://[^"]+\.(mp4|m3u8|mkv|webm)[^"]*)"'
            ]
            
            for pattern in direct_patterns:
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    return {
                        'success': True,
                        'url': match.group(1),
                        'method': 'direct_url',
                        'extractor': 'vidmoly'
                    }
            
            # 5. Fallback général
            fallback_pattern = r'(https?://[^\s"\']+\.(mp4|m3u8|mkv|webm)[^\s"\']*)'
            fallback_match = re.search(fallback_pattern, html, re.IGNORECASE)
            
            if fallback_match:
                return {
                    'success': True,
                    'url': fallback_match.group(0),
                    'method': 'fallback',
                    'extractor': 'vidmoly'
                }
            
            return {
                'success': False,
                'error': 'Aucun lien vidéo trouvé',
                'extractor': 'vidmoly',
                'debug': {'url': url, 'html_preview': html[:300]}
            }
            
        except requests.RequestException as e:
            return {
                'success': False,
                'error': f'Erreur réseau: {str(e)}',
                'extractor': 'vidmoly'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Erreur extraction: {str(e)}',
                'extractor': 'vidmoly'
            }

class DirectExtractor(BaseExtractor):
    """Extracteur pour liens directs (pas besoin d'extraction)"""
    
    def can_extract(self, url):
        # Accepte tout, utilisé en dernier recours
        return True
    
    def extract(self, url):
        # Si c'est déjà un lien direct vidéo
        if any(ext in url for ext in ['.mp4', '.m3u8', '.mkv', '.webm']):
            return {
                'success': True,
                'url': url,
                'method': 'already_direct',
                'extractor': 'direct'
            }
        
        # Sinon, on ne peut rien faire
        return {
            'success': False,
            'error': 'URL non reconnue comme lien vidéo direct',
            'extractor': 'direct'
        }

class ExtractorFactory:
    """Factory pour gérer les extracteurs"""
    
    def __init__(self):
        self.extractors = [
            VidmolyExtractor(),
            DirectExtractor()  # Toujours en dernier
        ]
    
    def get_extractor(self, url):
        """Retourne le premier extracteur qui peut gérer cette URL"""
        for extractor in self.extractors:
            if extractor.can_extract(url):
                return extractor
        return DirectExtractor()  # Fallback
    
    def extract(self, url):
        """Extrait le lien vidéo en utilisant l'extracteur approprié"""
        extractor = self.get_extractor(url)
        print(f"[ExtractorFactory] Utilisation de: {extractor.__class__.__name__}")
        return extractor.extract(url)

# Fonction utilitaire simple pour l'API
def extract_video_url(url):
    """Fonction principale d'extraction"""
    factory = ExtractorFactory()
    return factory.extract(url)
