# my_scraper.py - Fonctions de scraping extraites de l'addon Kodi
import requests
import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse

def get_animes_from_page(page_url, max_results=30):
    """
    Récupère la liste des animés depuis une page
    Remplace la fonction showAnimes() de l'addon Kodi
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3',
        'Accept-Encoding': 'gzip, deflate',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    try:
        # 1. Récupération de la page
        response = requests.get(page_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # Forcer l'encodage UTF-8
        response.encoding = 'utf-8'
        html_content = response.text
        
        # 2. Utiliser BeautifulSoup pour parser
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 3. Chercher les animés
        anime_containers = soup.find_all('div', class_=re.compile(r'mov\s+clearfix'))
        
        # Si pas trouvé avec classe, chercher par structure
        if not anime_containers:
            anime_containers = soup.find_all('div', {'class': re.compile(r'.*mov.*')})
        
        animes_list = []
        
        # 4. Extraire les données pour chaque animé
        for container in anime_containers[:max_results]:
            try:
                anime_data = {}
                
                # Image et titre
                img_tag = container.find('img')
                if img_tag:
                    anime_data['thumbnail'] = img_tag.get('src', '')
                    anime_data['title'] = img_tag.get('alt', '')
                else:
                    anime_data['thumbnail'] = ''
                    anime_data['title'] = ''
                
                # Lien vers la page de l'animé
                link_tag = container.find('a', href=True)
                if link_tag:
                    anime_data['url'] = link_tag['href']
                else:
                    anime_data['url'] = ''
                
                # Saison (nettoyée des tabulations)
                season_tag = container.find(class_=re.compile(r'sai'))
                if season_tag:
                    # Nettoyer les tabulations et sauts de ligne
                    season_text = season_tag.get_text()
                    season_text = re.sub(r'[\t\n]+', ' ', season_text)
                    season_text = re.sub(r'\s+', ' ', season_text)
                    anime_data['season'] = season_text.strip()
                else:
                    anime_data['season'] = ''
                
                # Version (VF/VOSTFR)
                version_match = re.search(r'Version[^>]*>([^<]+)', str(container))
                anime_data['version'] = version_match.group(1).strip() if version_match else ''
                
                # Description et année
                desc_tag = container.find(class_=re.compile(r'desc'))
                if desc_tag:
                    full_text = desc_tag.get_text(strip=True)
                    
                    # Extraire l'année
                    year_match = re.search(r'\b(19|20)\d{2}\b', full_text)
                    anime_data['year'] = year_match.group(0) if year_match else ''
                    
                    # Extraire la vraie description
                    synopsis_match = re.search(r'Synopsis[:\s]*(.+)', full_text, re.IGNORECASE)
                    if synopsis_match:
                        anime_data['description'] = synopsis_match.group(1).strip()
                    else:
                        # Enlever l'année au début si présente
                        cleaned_text = re.sub(r'^\s*(19|20)\d{2}\s*[-:]?\s*', '', full_text)
                        if cleaned_text and len(cleaned_text) > 10:
                            anime_data['description'] = cleaned_text[:100] + '...' if len(cleaned_text) > 100 else cleaned_text
                        else:
                            anime_data['description'] = 'Description non disponible'
                else:
                    anime_data['description'] = ''
                    anime_data['year'] = ''
                
                # Nettoyer et compléter les URLs
                if anime_data['thumbnail'] and anime_data['thumbnail'].startswith('/'):
                    anime_data['thumbnail'] = 'https://www.frenchanime.com' + anime_data['thumbnail']
                
                if anime_data['url'] and anime_data['url'].startswith('/'):
                    anime_data['url'] = 'https://www.frenchanime.com' + anime_data['url']
                
                # Nettoyer le titre
                if anime_data['title']:
                    anime_data['title'] = anime_data['title'].replace(' wiflix', '').strip()
                
                # Déterminer le type (film ou série)
                anime_data['type'] = 'film' if 'films-vf-vostfr' in anime_data['url'] else 'serie'
                
                # Ajouter seulement si on a au moins un titre
                if anime_data['title']:
                    animes_list.append(anime_data)
                    
            except Exception as e:
                # Ignorer les erreurs sur un animé spécifique
                continue
        
        return {
            'success': True,
            'source_url': page_url,
            'count': len(animes_list),
            'results': animes_list,
            'next_page': _find_next_page(html_content, page_url)
        }
        
    except requests.RequestException as e:
        return {
            'success': False,
            'error': f'Erreur réseau: {str(e)}',
            'source_url': page_url,
            'results': []
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Erreur de scraping: {str(e)}',
            'source_url': page_url,
            'results': []
        }

def get_episodes_from_anime(anime_url):
    """
    Récupère tous les épisodes d'un animé
    Version améliorée avec détection de qualité
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(anime_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # Technique pour garder la structure
        html_content = response.text.replace('\n', '###NEWLINE###')
        
        # Chercher la section des épisodes
        start_marker = 'class="eps"'
        end_marker = '/div>'
        
        start_index = html_content.find(start_marker)
        if start_index == -1:
            return {
                'success': False,
                'error': 'Section des épisodes non trouvée',
                'episodes': []
            }
        
        # Trouver la fin de la section
        end_index = html_content.find(end_marker, start_index)
        if end_index == -1:
            eps_section = html_content[start_index:]
        else:
            eps_section = html_content[start_index:end_index]
        
        # Restaurer les sauts de ligne
        eps_section = eps_section.replace('###NEWLINE###', '\n')
        
        # Nettoyer les URLs
        eps_section = eps_section.replace('!//', '!https://').replace(',//', ',https://')
        
        # Chercher les épisodes avec regex
        episodes = []
        
        # Méthode 1: Chercher les paires numéro!url avec qualité
        pattern1 = r'(\d+)!([^\s,]+)'
        matches1 = re.findall(pattern1, eps_section)
        
        for episode_num, url in matches1:
            quality = _detect_video_quality(url, eps_section)
            host = _extract_host_from_url(url)
            
            episodes.append({
                'episode': episode_num,
                'url': url,
                'quality': quality,
                'host': host
            })
        
        # Méthode 2: Chercher les URLs seules
        if not episodes:
            pattern2 = r'(https?://[^\s,]+)'
            urls = re.findall(pattern2, eps_section)
            
            for i, url in enumerate(urls, 1):
                quality = _detect_video_quality(url, eps_section)
                host = _extract_host_from_url(url)
                
                episodes.append({
                    'episode': str(i),
                    'url': url,
                    'quality': quality,
                    'host': host
                })
        
        # Analyser les qualités disponibles
        qualities = list(set(ep['quality'] for ep in episodes))
        hosts = list(set(ep['host'] for ep in episodes))
        
        return {
            'success': True,
            'anime_url': anime_url,
            'episodes': episodes,
            'total_episodes': len(episodes),
            'qualities_available': qualities,
            'hosts_available': hosts
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'anime_url': anime_url,
            'episodes': []
        }

def get_genres_from_page(base_url):
    """
    Récupère la liste des genres disponibles
    """
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(base_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Chercher la section des genres
        genres_section = None
        
        for tag in soup.find_all(['div', 'section']):
            if 'genre' in str(tag).lower() or 'catégorie' in str(tag).lower():
                genres_section = tag
                break
        
        genres_list = []
        
        if genres_section:
            genre_links = genres_section.find_all('a', href=True)
            
            for link in genre_links:
                genre_name = link.get_text(strip=True)
                genre_url = link['href']
                
                if genre_name and len(genre_name) > 1:
                    if genre_url.startswith('/'):
                        genre_url = 'https://www.frenchanime.com' + genre_url
                    
                    genres_list.append({
                        'name': genre_name.capitalize(),
                        'url': genre_url,
                        'slug': genre_name.lower().replace(' ', '-')
                    })
        
        # Liste par défaut si rien trouvé
        if not genres_list:
            default_genres = ['Action', 'Aventure', 'Comédie', 'Drame', 'Fantaisie', 
                            'Horreur', 'Mystère', 'Romance', 'Sci-Fi', 'Sport']
            genres_list = [
                {'name': g, 'url': f'{base_url}/genre/{g.lower()}', 'slug': g.lower()}
                for g in default_genres
            ]
        
        return {
            'success': True,
            'genres': genres_list,
            'count': len(genres_list)
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'genres': []
        }

def _find_next_page(html_content, current_url):
    """
    Trouve l'URL de la page suivante
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        next_link = soup.find('a', class_=re.compile(r'next|suivant|>', re.I))
        
        if next_link and next_link.get('href'):
            next_url = next_link['href']
            if next_url.startswith('/'):
                parsed = urlparse(current_url)
                next_url = f"{parsed.scheme}://{parsed.netloc}{next_url}"
            return next_url
        
        pattern = r'page/(\d+)/'
        match = re.search(pattern, current_url)
        
        if match:
            current_page = int(match.group(1))
            return current_url.replace(f'page/{current_page}/', f'page/{current_page + 1}/')
        
        return None
        
    except:
        return None

def _detect_video_quality(url, context=''):
    """
    Détecte la qualité vidéo depuis l'URL et le contexte
    """
    url_lower = url.lower()
    
    # Recherche directe dans l'URL
    quality_keywords = [
        ('1080p', ['1080p', 'fullhd', 'fhd']),
        ('720p', ['720p', 'hdready', 'hd']),
        ('4K', ['4k', '2160p', 'uhd']),
        ('480p', ['480p', 'sd']),
        ('360p', ['360p', 'low']),
    ]
    
    for quality_name, keywords in quality_keywords:
        if any(keyword in url_lower for keyword in keywords):
            return quality_name
    
    # Recherche dans le contexte
    if context:
        url_index = context.find(url)
        if url_index != -1:
            # Regarder autour de l'URL
            start = max(0, url_index - 150)
            end = min(len(context), url_index + 150)
            surrounding = context[start:end].lower()
            
            for quality_name, keywords in quality_keywords:
                if any(keyword in surrounding for keyword in keywords):
                    return quality_name
    
    # Si aucun marqueur trouvé
    return 'Qualité variable'

def _extract_host_from_url(url):
    """
    Extrait le nom de l'hébergeur depuis l'URL
    """
    try:
        parsed = urlparse(url)
        hostname = parsed.netloc.lower()
        
        # Mapping des hébergeurs connus
        host_mapping = {
            'vidmoly': 'Vidmoly',
            'voe': 'Voe',
            'streamtape': 'Streamtape',
            'dood': 'DoodStream',
            'mp4upload': 'Mp4Upload',
            'okru': 'OK.ru',
            'youtube': 'YouTube',
            'vimeo': 'Vimeo',
            'uptostream': 'Uptostream',
            'mystream': 'MyStream'
        }
        
        for host_key, host_name in host_mapping.items():
            if host_key in hostname:
                return host_name
        
        # Extraire le nom de domaine principal
        parts = hostname.split('.')
        if len(parts) >= 2:
            return parts[-2].capitalize()
        
        return hostname
        
    except:
        return 'Hébergeur inconnu'
