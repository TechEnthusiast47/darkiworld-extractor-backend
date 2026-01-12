# extractors.py - Extracteurs de liens vidéo (Version Kodi)
import requests
import re
import json
from urllib.parse import urlparse, urljoin
from abc import ABC, abstractmethod
import time

class BaseExtractor(ABC):
    """Classe de base pour tous les extracteurs"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:139.0) Gecko/20100101 Firefox/139.0',
            'Accept': '*/*',
            'Accept-Language': 'fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
        }
    
    @abstractmethod
    def can_extract(self, url):
        pass
    
    @abstractmethod
    def extract(self, url):
        pass
    
    def _fetch_page_kodi_style(self, url, referer=None):
        """Fetch exactement comme Kodi (cRequestHandler)"""
        headers = self.headers.copy()
        headers.update({
            'Referer': referer or url,
            'Sec-Fetch-Dest': 'iframe',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'cross-site',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        # Timeout comme Kodi
        response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        response.raise_for_status()
        return response.text

class VidmolyExtractor(BaseExtractor):
    """Extracteur Vidmoly 100% compatible Kodi"""
    
    def can_extract(self, url):
        url_lower = url.lower()
        return any(x in url_lower for x in ['vidmoly', 'vidmoly.to', 'vidmoly.net', '/embed-'])
    
    def extract(self, url):
        try:
            # 1. Normalisation exacte comme Kodi
            url = url.replace('vidmoly.to', 'vidmoly.net')
            print(f"[Vidmoly] Extraction Kodi-style: {url}")
            
            # 2. Fetch avec headers Kodi
            html = self._fetch_page_kodi_style(url, referer=url)
            
            # 3. Pattern EXACT de Kodi vidmoly.py
            # Pattern: sources: *[{file:"URL"
            sPattern = r'sources: *\[{file:"([^"]+)'
            match = re.search(sPattern, html, re.IGNORECASE)
            
            if match:
                api_call = match.group(1).strip()
                
                # Nettoyage optionnel (commenté dans Kodi)
                # api_call = api_call.replace(',', '').replace('.urlset', '')
                
                # Ajout du Referer comme Kodi
                parsed_url = urlparse(url)
                referer_host = f"{parsed_url.scheme}://{parsed_url.netloc}"
                full_url = api_call + '|Referer=' + referer_host
                
                print(f"[Vidmoly] SUCCÈS - Pattern Kodi trouvé")
                print(f"[Vidmoly] URL brute: {api_call}")
                print(f"[Vidmoly] URL avec Referer: {full_url}")
                
                return {
                    'success': True,
                    'url': api_call,  # URL directe pour le navigateur
                    'full_url': full_url,  # URL complète (comme Kodi)
                    'method': 'kodi_exact_pattern',
                    'extractor': 'vidmoly',
                    'headers': {
                        'Referer': referer_host,
                        'User-Agent': self.headers['User-Agent'],
                        'Origin': referer_host
                    },
                    'kodi_compatible': True
                }
            
            # 4. Fallback: chercher autres patterns
            fallback_patterns = [
                r'file\s*:\s*["\'](https?://[^"\']+)["\']',
                r'src\s*:\s*["\'](https?://[^"\']+)["\']',
                r'"file"\s*:\s*"([^"]+)"',
                r'"url"\s*:\s*"([^"]+)"',
                r'sources\s*:\s*\[\s*{\s*["\']?file["\']?\s*:\s*["\']([^"\']+)["\']',
            ]
            
            for i, pattern in enumerate(fallback_patterns):
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    video_url = match.group(1).strip()
                    print(f"[Vidmoly] SUCCÈS - Fallback pattern {i}: {video_url}")
                    
                    return {
                        'success': True,
                        'url': video_url,
                        'method': f'fallback_pattern_{i}',
                        'extractor': 'vidmoly',
                        'headers': {
                            'Referer': url,
                            'User-Agent': self.headers['User-Agent']
                        }
                    }
            
            # 5. Recherche agressive de liens vidéo
            video_extensions = ['.mp4', '.m3u8', '.mkv', '.webm', '.ts']
            all_links = re.findall(r'(https?://[^\s"\'>]+)', html)
            
            for link in all_links:
                link_lower = link.lower()
                if any(ext in link_lower for ext in video_extensions):
                    # Filtrer les faux positifs
                    if not any(bad in link_lower for bad in ['.css', '.js', '.png', '.jpg', '.ico', 'google', 'facebook']):
                        print(f"[Vidmoly] SUCCÈS - Lien vidéo trouvé: {link}")
                        
                        return {
                            'success': True,
                            'url': link,
                            'method': 'aggressive_scan',
                            'extractor': 'vidmoly',
                            'headers': {
                                'Referer': url,
                                'User-Agent': self.headers['User-Agent']
                            }
                        }
            
            # 6. Aucun lien trouvé
            print(f"[Vidmoly] ÉCHEC - Aucun pattern trouvé")
            print(f"[Vidmoly] HTML preview (500 chars): {html[:500]}")
            
            return {
                'success': False,
                'error': 'Aucun lien vidéo trouvé avec les patterns Kodi',
                'extractor': 'vidmoly',
                'debug_info': {
                    'url': url,
                    'html_length': len(html),
                    'patterns_tried': ['kodi_exact'] + [f'fallback_{i}' for i in range(len(fallback_patterns))],
                    'html_sample': html[:1000]
                }
            }
            
        except requests.RequestException as e:
            print(f"[Vidmoly] ERREUR réseau: {e}")
            return {
                'success': False,
                'error': f'Erreur réseau: {str(e)}',
                'extractor': 'vidmoly'
            }
        except Exception as e:
            print(f"[Vidmoly] ERREUR inattendue: {e}")
            return {
                'success': False,
                'error': f'Erreur: {str(e)}',
                'extractor': 'vidmoly'
            }

class DirectExtractor(BaseExtractor):
    """Pour liens directs"""
    
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
            VidmolyExtractor(),
            DirectExtractor()
        ]
        print(f"[Factory] Initialisée avec {len(self.extractors)} extracteurs")
    
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
    print(f"\n{'='*50}")
    print(f"EXTRACTION DÉMARRÉE: {url}")
    print(f"{'='*50}")
    
    factory = ExtractorFactory()
    result = factory.extract(url)
    
    print(f"{'='*50}")
    print(f"RÉSULTAT: {'SUCCÈS' if result.get('success') else 'ÉCHEC'}")
    if result.get('success'):
        print(f"URL: {result.get('url', 'N/A')[:100]}...")
    else:
        print(f"ERREUR: {result.get('error', 'Inconnue')}")
    print(f"{'='*50}\n")
    
    return result
