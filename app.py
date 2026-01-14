# ============ ROUTES KODI (ajoutées) ============

@app.route('/check-kodi')
def check_kodi():
    import os
    path = os.path.join(os.path.dirname(__file__), 'kodi-addons')
    exists = os.path.exists(path)
    return {
        'kodi_addons_exists': exists,
        'path': path,
        'files': os.listdir(path) if exists else []
    }

@app.route('/api/extract/kodi-direct', methods=['GET'])
def api_extract_kodi_direct():
    """
    Nouvelle route : utilise Kodi si disponible
    """
    url = request.args.get('url', '')
    
    if not url:
        return jsonify({'success': False, 'error': 'URL manquante'}), 400
    
    # Pour l'instant, utiliser ton extracteur actuel
    from extractors import extract_video_url
    result = extract_video_url(url)
    result['note'] = 'Kodi pas encore chargé - utilisant extracteur actuel'
    
    return jsonify(result)
