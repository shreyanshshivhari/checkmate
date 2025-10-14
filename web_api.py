"""
Flask Web API for File Deduplication Agent
Provides REST API endpoints for the frontend
"""

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import yaml
import threading
from pathlib import Path

from src.permission_handler import PermissionHandler
from src.scanner import FileScanner
from src.reader import FileReader
from src.similarity import SimilarityEngine
from src.database import DatabaseManager
from src.file_ops import FileOperations
from src.logger import setup_logger

app = Flask(__name__)
CORS(app)

# Global state
scan_status = {
    'running': False,
    'progress': 0,
    'current_step': '',
    'files_found': 0,
    'duplicates_found': 0,
    'error': None
}

current_duplicates = []
config = None
agent_components = None


def load_config():
    """Load configuration"""
    global config, agent_components
    with open('config/settings.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Initialize components
    agent_components = {
        'scanner': FileScanner(config),
        'reader': FileReader(config),
        'similarity': SimilarityEngine(config),
        'db': DatabaseManager(),
        'file_ops': FileOperations(config),
        'logger': setup_logger(config)
    }


@app.route('/')
def index():
    """Serve the frontend HTML"""
    return render_template('index.html')


@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration"""
    return jsonify({
        'similarity_threshold': config['similarity']['threshold'],
        'max_file_size_mb': config['scanning']['max_file_size_mb'],
        'skip_folders': config['scanning']['skip_folders'][:10],  # First 10
        'quarantine_enabled': config['safety']['move_to_quarantine']
    })


@app.route('/api/scan', methods=['POST'])
def start_scan():
    """Start a new scan"""
    global scan_status, current_duplicates
    
    if scan_status['running']:
        return jsonify({'error': 'Scan already running'}), 400
    
    data = request.json
    paths = data.get('paths', [])
    
    if not paths:
        return jsonify({'error': 'No paths provided'}), 400
    
    # Reset status
    scan_status = {
        'running': True,
        'progress': 0,
        'current_step': 'Starting scan...',
        'files_found': 0,
        'duplicates_found': 0,
        'error': None
    }
    current_duplicates = []
    
    # Run scan in background thread
    thread = threading.Thread(target=run_scan, args=(paths,))
    thread.start()
    
    return jsonify({'status': 'started'})


def run_scan(paths):
    """Run the scan in background"""
    global scan_status, current_duplicates, agent_components
    
    try:
        # Step 1: Scan files
        scan_status['current_step'] = 'Scanning files...'
        scan_status['progress'] = 10
        
        files = agent_components['scanner'].scan_all(paths)
        scan_status['files_found'] = len(files)
        scan_status['progress'] = 30
        
        if len(files) == 0:
            scan_status['running'] = False
            scan_status['current_step'] = 'No files found'
            return
        
        # Step 2: Read contents
        scan_status['current_step'] = 'Reading file contents...'
        scan_status['progress'] = 40
        
        file_contents = []
        for f in files:
            content = agent_components['reader'].read_file(f['path'])
            file_contents.append((f, content))
        
        scan_status['progress'] = 60
        
        # Step 3: Compute similarities
        scan_status['current_step'] = 'Computing similarities...'
        duplicates = agent_components['similarity'].compute_similarity(file_contents)
        
        # Limit to 1000 for UI performance
        if len(duplicates) > 1000:
            duplicates = duplicates[:1000]
        
        current_duplicates = duplicates
        scan_status['duplicates_found'] = len(duplicates)
        scan_status['progress'] = 100
        scan_status['current_step'] = 'Complete'
        scan_status['running'] = False
        
    except Exception as e:
        scan_status['error'] = str(e)
        scan_status['running'] = False
        scan_status['current_step'] = 'Error'


@app.route('/api/status', methods=['GET'])
def get_status():
    """Get current scan status"""
    return jsonify(scan_status)


@app.route('/api/duplicates', methods=['GET'])
def get_duplicates():
    """Get found duplicates"""
    # Format for frontend
    formatted = []
    for idx, dup in enumerate(current_duplicates):
        formatted.append({
            'id': idx,
            'file1': {
                'path': dup['file1']['path'],
                'name': Path(dup['file1']['path']).name,
                'size': dup['file1']['size'],
                'modified': dup['file1']['modified']
            },
            'file2': {
                'path': dup['file2']['path'],
                'name': Path(dup['file2']['path']).name,
                'size': dup['file2']['size'],
                'modified': dup['file2']['modified']
            },
            'similarity': round(dup['similarity'] * 100, 1)
        })
    
    return jsonify(formatted)


@app.route('/api/delete', methods=['POST'])
def delete_files():
    """Delete selected files"""
    data = request.json
    file_paths = data.get('files', [])
    
    if not file_paths:
        return jsonify({'error': 'No files provided'}), 400
    
    success_count, failure_count, log = agent_components['file_ops'].bulk_delete(file_paths)
    
    return jsonify({
        'success': success_count,
        'failures': failure_count,
        'log': log
    })


@app.route('/api/folders/user', methods=['GET'])
def get_user_folders():
    """Get common user folders"""
    home = Path.home()
    folders = []
    
    for folder_name in ['Documents', 'Downloads', 'Desktop', 'Pictures', 'Videos', 'Music']:
        path = home / folder_name
        if path.exists():
            folders.append({
                'name': folder_name,
                'path': str(path)
            })
    
    return jsonify(folders)


if __name__ == '__main__':
    load_config()
    print("\n" + "="*50)
    print("🚀 File Deduplication Agent - Web Interface")
    print("="*50)
    print("\n📱 Open your browser and go to:")
    print("   http://localhost:5000")
    print("\n⏹️  Press Ctrl+C to stop the server\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
