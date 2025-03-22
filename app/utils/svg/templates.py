"""SVG visualization templates and processors."""

import re
from typing import Dict, Any, Tuple, Optional


def extract_svg_from_text(text: str) -> Tuple[Optional[str], str]:
    """Extract SVG content from text and return cleaned text.
    
    Args:
        text: Text containing potential SVG content
        
    Returns:
        Tuple of (svg_content, text_without_svg)
    """
    svg_pattern = r'<svg.*?</svg>'
    svg_matches = re.findall(svg_pattern, text, re.DOTALL)

    if not svg_matches:
        return None, text

    # Get the first SVG content
    svg_content = svg_matches[0]

    # Remove SVG from text
    text_without_svg = re.sub(svg_pattern, '', text, flags=re.DOTALL).strip()

    return svg_content, text_without_svg


def service_status_template(data: Dict[str, Any]) -> str:
    """Generate SVG for service status visualization.
    
    Args:
        data: Dictionary containing service status data
        
    Returns:
        SVG content as string
    """
    services = data.get('services', {})

    # SVG dimensions and styles
    width = 800
    height = 100 + (len(services) * 80)

    svg = f'''<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">
    <style>
        .title {{ font-size: 24px; font-weight: bold; }}
        .service {{ font-size: 18px; }}
        .status {{ font-size: 16px; }}
        .metric {{ font-size: 14px; fill: #666; }}
        .online {{ fill: #34a853; }}
        .offline {{ fill: #ea4335; }}
        .degraded {{ fill: #fbbc05; }}
    </style>
    
    <text x="50" y="50" class="title">Service Status</text>
    '''

    y = 100
    for name, info in services.items():
        status = info.get('status', 'unknown')
        response_time = info.get('response_time', 0)
        availability = info.get('availability', 0)

        svg += f'''
        <g transform="translate(50,{y})">
            <text x="0" y="0" class="service">{name}</text>
            <text x="200" y="0" class="status {status}">{status}</text>
            <text x="350" y="0" class="metric">{response_time}ms</text>
            <text x="500" y="0" class="metric">{availability}% uptime</text>
        </g>
        '''
        y += 80

    svg += '</svg>'
    return svg


def failover_process_template() -> str:
    """Generate SVG for failover process visualization."""
    return '''<svg width="800" height="400" xmlns="http://www.w3.org/2000/svg">
    <style>
        .service { font-size: 18px; font-weight: bold; }
        .arrow { fill: none; stroke: #666; stroke-width: 2; }
        .label { font-size: 14px; fill: #666; }
    </style>
    
    <!-- Primary Service -->
    <rect x="50" y="50" width="200" height="80" rx="10" fill="#34a853"/>
    <text x="150" y="95" text-anchor="middle" class="service" fill="white">Gemini API</text>
    
    <!-- Secondary Service -->
    <rect x="300" y="50" width="200" height="80" rx="10" fill="#fbbc05"/>
    <text x="400" y="95" text-anchor="middle" class="service" fill="white">Ollama</text>
    
    <!-- Tertiary Service -->
    <rect x="550" y="50" width="200" height="80" rx="10" fill="#ea4335"/>
    <text x="650" y="95" text-anchor="middle" class="service" fill="white">Transformers</text>
    
    <!-- Arrows -->
    <path d="M 250 90 L 300 90" class="arrow" marker-end="url(#arrow)"/>
    <path d="M 500 90 L 550 90" class="arrow" marker-end="url(#arrow)"/>
    
    <!-- Arrow Marker -->
    <defs>
        <marker id="arrow" viewBox="0 0 10 10" refX="5" refY="5"
                markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#666"/>
        </marker>
    </defs>
    
    <!-- Labels -->
    <text x="275" y="70" text-anchor="middle" class="label">Failover</text>
    <text x="525" y="70" text-anchor="middle" class="label">Failover</text>
    </svg>'''


def capability_degradation_template(data: Optional[Dict[str, Any]] = None) -> str:
    """Generate SVG for capability degradation visualization."""
    return '''<svg width="800" height="400" xmlns="http://www.w3.org/2000/svg">
    <style>
        .title { font-size: 24px; font-weight: bold; }
        .label { font-size: 16px; }
        .metric { font-size: 14px; fill: #666; }
        .bar { opacity: 0.8; }
    </style>
    
    <text x="400" y="50" text-anchor="middle" class="title">Service Capabilities</text>
    
    <!-- Gemini API -->
    <rect x="100" y="100" width="150" height="200" class="bar" fill="#34a853"/>
    <text x="175" y="320" text-anchor="middle" class="label">Gemini API</text>
    <text x="175" y="340" text-anchor="middle" class="metric">Full Capabilities</text>
    
    <!-- Ollama -->
    <rect x="325" y="140" width="150" height="160" class="bar" fill="#fbbc05"/>
    <text x="400" y="320" text-anchor="middle" class="label">Ollama</text>
    <text x="400" y="340" text-anchor="middle" class="metric">High Capabilities</text>
    
    <!-- Transformers -->
    <rect x="550" y="180" width="150" height="120" class="bar" fill="#ea4335"/>
    <text x="625" y="320" text-anchor="middle" class="label">Transformers</text>
    <text x="625" y="340" text-anchor="middle" class="metric">Basic Capabilities</text>
    </svg>'''
