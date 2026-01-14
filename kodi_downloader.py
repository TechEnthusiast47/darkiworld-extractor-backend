"""
kodi_downloader.py
Télécharge UNIQUEMENT les extracteurs Kodi depuis GitHub
Poids total : ~5-10 Mo (au lieu de 500 Mo)
"""
import os
import requests
import time
import threading
from urllib.parse import urljoin

class KodiDownloader:
    def __init__(self):
        self.base_url = "https://api.github.com/repos/Kodi-vStream/venom-xbmc-addons/contents/resources/hosters"
        self.raw_base_url = "https://raw.githubusercontent.com/Kodi-vStream/venom-xbmc-addons/master/resources/hosters"
        self.extractors_dir = os.path.join(os.path.dirname(__file__), "kodi_extractors")
        self.downloaded = []
        
    def ensure_directory(self):
        """Crée le dossier pour les extracteurs"""
        if not os.path.exists(self.extractors_dir):
            os.makedirs(self.extractors_dir)
            print(f"📁 Dossier créé: {self.extractors_dir}")
    
    def get_extractor_list(self):
        """Récupère la liste des extracteurs depuis GitHub API"""
        try:
            response = requests.get(self.base_url, timeout=10)
            if response.status_code == 200:
                files = response.json()
                # Filtrer seulement les fichiers .py (les extracteurs)
                extractors = [f['name'] for f in files if f['name'].endswith('.py')]
                return extractors
        except Exception as e:
            print(f"❌ Erreur liste extracteurs: {e}")
        
        # Liste de fallback (les plus importants)
        return [
            'vidmoly.py', 'voe.py', 'streamtape.py', 'dood.py',
            'mixdrop.py', 'filelions.py', 'netu.py', 'streamlare.py',
            'streamvid.py', 'vudeo.py', 'upstream.py', 'videobin.py'
        ]
    
    def download_extractor(self, extractor_name):
        """Télécharge un extracteur spécifique"""
        try:
            url = f"{self.raw_base_url}/{extractor_name}"
            response = requests.get(url, timeout=15)
            
            if response.status_code == 200:
                file_path = os.path.join(self.extractors_dir, extractor_name)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                
                self.downloaded.append(extractor_name)
                print(f"✅ {extractor_name}")
                return True
            else:
                print(f"❌ {extractor_name} (HTTP {response.status_code})")
                
        except Exception as e:
            print(f"❌ Erreur {extractor_name}: {e}")
        
        return False
    
    def download_all(self, limit=20):
        """Télécharge tous les extracteurs (limité pour éviter la surcharge)"""
        self.ensure_directory()
        
        print("📥 Téléchargement des extracteurs Kodi...")
        print("🔧 Seulement les fichiers .py (extracteurs)")
        
        extractors = self.get_extractor_list()
        print(f"📋 {len(extractors)} extracteurs trouvés")
        
        # Télécharger les plus importants d'abord
        priority_extractors = ['vidmoly.py', 'voe.py', 'streamtape.py', 'dood.py']
        
        success_count = 0
        for extractor in priority_extractors:
            if extractor in extractors:
                if self.download_extractor(extractor):
                    success_count += 1
                time.sleep(0.5)  # Éviter le rate limiting
        
        # Télécharger les autres (limit)
        others = [e for e in extractors if e not in priority_extractors]
        for extractor in others[:limit]:
            if self.download_extractor(extractor):
                success_count += 1
            time.sleep(0.3)
        
        print(f"🎯 {success_count} extracteurs téléchargés")
        return success_count
    
    def update_extractors(self):
        """Met à jour les extracteurs existants"""
        print("🔄 Vérification des mises à jour...")
        extractors = self.get_extractor_list()
        
        updated = 0
        for extractor in extractors:
            file_path = os.path.join(self.extractors_dir, extractor)
            if os.path.exists(file_path):
                # Vérifier si besoin de mise à jour (simplifié)
                url = f"{self.raw_base_url}/{extractor}"
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        current_content = f.read()
                    
                    if current_content != response.text:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(response.text)
                        print(f"🔄 {extractor} mis à jour")
                        updated += 1
        
        print(f"📦 {updated} extracteurs mis à jour")
        return updated

# Instance globale
kodi_downloader = KodiDownloader()

# Démarrer le téléchargement en arrière-plan
def start_background_download():
    print("🚀 Démarrage téléchargement extracteurs Kodi...")
    thread = threading.Thread(target=kodi_downloader.download_all, daemon=True)
    thread.start()

# Démarrer automatiquement
start_background_download()
