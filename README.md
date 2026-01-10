# API Scraper pour Animés Français

API Python/Flask qui extrait les animés depuis les sites de streaming français, basée sur l'addon Kodi French Animes.

## 🚀 Déploiement Rapide sur Render

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

### Prérequis
- Compte [Render.com](https://render.com) gratuit
- Compte [GitHub](https://github.com) gratuit

### Étapes
1. **Forkez** ce dépôt sur votre compte GitHub
2. **Rendez-vous sur Render.com** → New Web Service
3. **Lieez votre dépôt GitHub**
4. **Configurez** :
   - Name : `votre-api-animes`
   - Environment : `Python 3`
   - Build Command : `pip install -r requirements.txt`
   - Start Command : `gunicorn app:app`
5. **Cliquez sur Create Web Service**
6. **Attendez 2-3 minutes** pour le déploiement

## 📡 Endpoints API

### 1. Liste des animés
