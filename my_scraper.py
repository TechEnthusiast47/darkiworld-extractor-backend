# my_scraper.py - Fonctions de scraping extraites de l'addon Kodi
import requests
import re
from bs4 import BeautifulSoup

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
        
        # 3. Chercher les animés - ADAPTEZ CES SELECTORS SI BESOIN
        # Le pattern original Kodi cherchait: 'mov clearfix'
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
                
                # Saison (peut être absente)
                season_tag = container.find(class_=re.compile(r'sai'))
                anime_data['season'] = season_tag.text.strip() if season_tag else ''
                
                # Version (VF/VOSTFR)
                version_match = re.search(r'Version[^>]*>([^<]+)', str(container))
                anime_data['version'] = version_match.group(1).strip() if version_match else ''
                
                # Description
                desc_tag = container.find(class_=re.compile(r'desc'))
                if desc_tag:
                    full_text = desc_tag.get_text(strip=True)
                    # Essayer d'extraire le synopsis
                    synopsis_match = re.search(r'Synopsis[:\s]*(.+)', full_text, re.IGNORECASE)
                    anime_data['description'] = synopsis_match.group(1).strip() if synopsis_match else full_text[:150]
                else:
                    anime_data['description'] = ''
                
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
                
                # Ajouter seulement si on a au moins un titre et une URL
                if anime_data['title'] and anime_data['url']:
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
    Remplace la fonction showEpisodes() de l'addon Kodi
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(anime_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # Technique pour garder la structure (comme dans l'addon Kodi)
        html_content = response.text.replace('\n', '###NEWLINE###')
        
        # Chercher la section des épisodes
        # L'addon Kodi cherchait: 'class="eps" style="display: none">'
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
        
        # Nettoyer les URLs (identique à l'addon Kodi)
        eps_section = eps_section.replace('!//', '!https://').replace(',//', ',https://')
        
        # Chercher les épisodes avec regex (pattern de l'addon Kodi adapté)
        # Pattern original: '([0-9]+)!|(https:.+?)[,|@]'
        episodes = []
        
        # Méthode 1: Chercher les paires numéro!url
        pattern1 = r'(\d+)!([^\s,]+)'
        matches1 = re.findall(pattern1, eps_section)
        
        for episode_num, url in matches1:
            episodes.append({
                'episode': episode_num,
                'url': url,
                'quality': 'HD' if 'hd' in url.lower() else 'SD'
            })
        
        # Méthode 2: Chercher les URLs seules et deviner les numéros
        if not episodes:
            pattern2 = r'(https?://[^\s,]+)'
            urls = re.findall(pattern2, eps_section)
            
            for i, url in enumerate(urls, 1):
                episodes.append({
                    'episode': str(i),
                    'url': url,
                    'quality': 'HD' if 'hd' in url.lower() else 'SD'
                })
        
        return {
            'success': True,
            'anime_url': anime_url,
            'episodes': episodes,
            'total_episodes': len(episodes)
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
    Remplace la fonction showGenres() de l'addon Kodi
    """
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(base_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Chercher la section des genres (adapté de l'addon Kodi)
        # L'addon cherchait: '</span><b>Animes par genre</b></div>'
        genres_section = None
        
        # Essayer plusieurs méthodes pour trouver les genres
        for tag in soup.find_all(['div', 'section']):
            if 'genre' in str(tag).lower() or 'catégorie' in str(tag).lower():
                genres_section = tag
                break
        
        genres_list = []
        
        if genres_section:
            # Extraire tous les liens qui pourraient être des genres
            genre_links = genres_section.find_all('a', href=True)
            
            for link in genre_links:
                genre_name = link.get_text(strip=True)
                genre_url = link['href']
                
                if genre_name and len(genre_name) > 1:  # Éviter les liens vides
                    # Compléter l'URL si relative
                    if genre_url.startswith('/'):
                        genre_url = 'https://www.frenchanime.com' + genre_url
                    
                    genres_list.append({
                        'name': genre_name.capitalize(),
                        'url': genre_url,
                        'slug': genre_name.lower().replace(' ', '-')
                    })
        
        # Si pas trouvé, retourner une liste par défaut
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
    Trouve l'URL de la page suivante (pour la pagination)
    Similaire à __checkForNextPage() dans l'addon Kodi
    """
    try:
        # Chercher les liens de pagination
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Chercher les liens de page suivante
        next_link = soup.find('a', class_=re.compile(r'next|suivant|>', re.I))
        
        if next_link and next_link.get('href'):
            next_url = next_link['href']
            if next_url.startswith('/'):
                # Reconstruire l'URL complète
                from urllib.parse import urlparse
                parsed = urlparse(current_url)
                next_url = f"{parsed.scheme}://{parsed.netloc}{next_url}"
            return next_url
        
        # Chercher par pattern (méthode de l'addon Kodi)
        pattern = r'page/(\d+)/'
        match = re.search(pattern, current_url)
        
        if match:
            current_page = int(match.group(1))
            return current_url.replace(f'page/{current_page}/', f'page/{current_page + 1}/')
        
        return None
        
    except:
        return None
