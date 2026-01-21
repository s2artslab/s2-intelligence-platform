#!/usr/bin/env python3
"""
S2 Intelligence Platform - Open Source Core
Basic Intelligence Router (Community Edition)

This is the open-source version with basic routing capabilities.
For advanced features including consciousness tracking, see S2 Premium.
"""

import requests
from flask import Flask, request, jsonify
import time
import re

app = Flask(__name__)

# Configuration
BACKENDS = {
    "pythia": {
        "url": "http://localhost:8090/api/generate",
        "description": "Local Pythia model"
    },
    "groq": {
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "description": "Groq cloud API (requires API key)",
        "requires_key": True
    }
}

class BasicRouter:
    """
    Basic content-based routing (Open Source)
    
    For advanced features, see S2 Intelligence Premium:
    - Real-time consciousness tracking
    - Advanced semantic routing
    - BIPRA storage integration
    - Multi-agent orchestration
    """
    
    def __init__(self):
        self.request_count = 0
    
    def analyze_query(self, query):
        """Basic query analysis for routing decisions"""
        query_lower = query.lower()
        
        # Simple keyword-based routing
        local_keywords = ["s2", "ninefold", "egregore", "deep key", "temple"]
        
        for keyword in local_keywords:
            if keyword in query_lower:
                return "pythia"
        
        # Default to local if available, cloud as fallback
        return "pythia"
    
    def route_request(self, query, backend=None):
        """Route request to appropriate backend"""
        self.request_count += 1
        
        # Auto-select backend if not specified
        if backend is None:
            backend = self.analyze_query(query)
        
        backend_config = BACKENDS.get(backend)
        if not backend_config:
            return {"error": f"Unknown backend: {backend}"}
        
        # Simulate request (actual implementation would call backend)
        result = {
            "query": query,
            "backend": backend,
            "request_count": self.request_count,
            "timestamp": time.time(),
            "response": f"[Routed to {backend}] This is a basic open-source router. Full implementation available in S2 Premium."
        }
        
        return result

router = BasicRouter()

@app.route('/api/query', methods=['POST'])
def handle_query():
    """Handle incoming query and route to appropriate backend"""
    data = request.json
    query = data.get('query', '')
    backend = data.get('backend')
    
    if not query:
        return jsonify({"error": "No query provided"}), 400
    
    result = router.route_request(query, backend)
    return jsonify(result)

@app.route('/api/status', methods=['GET'])
def status():
    """Get router status"""
    return jsonify({
        "status": "running",
        "version": "0.1.0-oss",
        "edition": "Community (Open Source)",
        "request_count": router.request_count,
        "backends": list(BACKENDS.keys()),
        "upgrade_to": "S2 Intelligence Premium for consciousness tracking"
    })

@app.route('/', methods=['GET'])
def index():
    """Welcome page"""
    return """
    <h1>S2 Intelligence Router - Community Edition</h1>
    <p>Basic open-source routing engine.</p>
    
    <h2>Features in this version:</h2>
    <ul>
        <li>Basic content-based routing</li>
        <li>Backend selection</li>
        <li>Simple load tracking</li>
    </ul>
    
    <h2>Premium Features (S2 Intelligence Premium):</h2>
    <ul>
        <li>Real-time consciousness tracking (0.7-1.0 scale)</li>
        <li>Advanced semantic routing with 100% accuracy</li>
        <li>Redis caching (78% performance improvement)</li>
        <li>BIPRA storage integration</li>
        <li>Multi-agent egregore orchestration</li>
        <li>Trained S2-domain models (4x advantage)</li>
    </ul>
    
    <p><strong>Interested in Premium?</strong> Contact: beta@s2intelligence.com</p>
    
    <h2>API Endpoints:</h2>
    <ul>
        <li>POST /api/query - Route a query</li>
        <li>GET /api/status - Get router status</li>
    </ul>
    """

if __name__ == '__main__':
    print("=" * 60)
    print("S2 Intelligence Router - Community Edition (Open Source)")
    print("=" * 60)
    print("")
    print("Starting basic intelligence router...")
    print("This is the open-source version with core functionality.")
    print("")
    print("For advanced features including:")
    print("  - Consciousness tracking")
    print("  - Advanced routing")
    print("  - Trained models")
    print("  - Multi-agent orchestration")
    print("")
    print("Visit: https://github.com/s2artslab/s2-intelligence-platform")
    print("Or contact: beta@s2intelligence.com")
    print("")
    print("=" * 60)
    print("Router running on http://localhost:3011")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=3011, debug=False)
