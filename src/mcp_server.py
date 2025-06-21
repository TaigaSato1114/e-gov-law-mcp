#!/usr/bin/env python3
"""
e-Gov Law MCP Server v2 - Ultra Smart & Efficient

A highly optimized Model Context Protocol server for Japanese e-Gov Law API.
Drastically simplified from 1000+ lines to <500 lines while adding more functionality.

Key Improvements:
- Direct mapping for 16+ major laws (六法 + key legislation)
- Smart Base64/XML text extraction 
- Efficient article search with intelligent pattern matching
- Minimal API calls with maximum accuracy
- Clean, maintainable code architecture
"""

import os
import argparse
import logging
import base64
import xml.etree.ElementTree as ET
import re
import json
from typing import Dict, List, Any, Optional
import httpx
from fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# API configuration
API_URL = os.environ.get("EGOV_API_URL", "https://laws.e-gov.go.jp/api/2")
API_TOKEN = os.environ.get("EGOV_API_TOKEN", "")

# Create MCP server
mcp = FastMCP(
    name=os.environ.get("MCP_SERVER_NAME", "e-Gov Law API Server v2"),
    on_duplicate_tools="warn"
)

# COMPREHENSIVE BASIC LAWS MAPPING (16 major laws)
BASIC_LAWS = {
    # 六法 (Six Codes)
    "民法": "明治二十九年法律第八十九号",
    "憲法": "昭和二十一年憲法",
    "日本国憲法": "昭和二十一年憲法",
    "刑法": "令和四年法律第六十八号",
    "商法": "昭和二十三年法律第二十五号",
    "民事訴訟法": "平成八年法律第百九号",
    "刑事訴訟法": "昭和二十三年法律第百三十一号",
    
    # 現代重要法 (Modern Key Laws)
    "会社法": "平成十七年法律第八十六号",
    "労働基準法": "昭和二十二年法律第四十九号",
    "所得税法": "令和六年法律第一号",
    "法人税法": "平成二十六年法律第十一号",
    "著作権法": "昭和三十一年法律第八十六号",
    "特許法": "昭和三十四年法律第百二十一号",
    "道路交通法": "昭和三十五年法律第百五号",
    "建築基準法": "昭和二十五年法律第二百一号",
    "独占禁止法": "昭和二十二年法律第五十四号",
    "消費者契約法": "平成十二年法律第六十一号",
}

async def get_http_client() -> httpx.AsyncClient:
    """Create HTTP client for e-Gov API."""
    headers = {
        "User-Agent": "e-Gov-Law-MCP-v2/2.0",
        "Accept": "application/json"
    }
    if API_TOKEN:
        headers["Authorization"] = f"Bearer {API_TOKEN}"
    
    return httpx.AsyncClient(
        base_url=API_URL,
        headers=headers,
        timeout=30.0,
        follow_redirects=True
    )

def extract_text_from_xml(obj) -> str:
    """
    Smart text extraction from e-Gov API response.
    Handles both Base64-encoded XML and structured JSON.
    """
    if isinstance(obj, str):
        # Handle Base64-encoded XML (XML format response)
        try:
            xml_bytes = base64.b64decode(obj)
            xml_string = xml_bytes.decode('utf-8')
            root = ET.fromstring(xml_string)
            
            def extract_xml_text(element):
                text = element.text or ''
                for child in element:
                    text += extract_xml_text(child)
                text += element.tail or ''
                return text
            
            return extract_xml_text(root)
        except Exception as e:
            logger.warning(f"XML decode failed: {e}")
            return str(obj)
    
    elif isinstance(obj, dict):
        # Handle structured JSON response
        if 'children' in obj:
            return ''.join(extract_text_from_xml(child) for child in obj['children'])
        elif 'text' in obj:
            return obj['text']
        return str(obj)
    
    elif isinstance(obj, list):
        return ''.join(extract_text_from_xml(item) for item in obj)
    
    return str(obj)

def arabic_to_kanji(num_str: str) -> str:
    """Convert Arabic numbers to Kanji for Japanese legal text."""
    if not num_str.isdigit():
        return num_str
    
    num = int(num_str)
    if num == 0: return '〇'
    if 1 <= num <= 9: return '一二三四五六七八九'[num-1]
    if 10 <= num <= 19:
        return '十' if num == 10 else '十' + '一二三四五六七八九'[num%10-1]
    if 20 <= num <= 99:
        tens = '二三四五六七八九'[num//10-2] + '十'
        ones = '' if num % 10 == 0 else '一二三四五六七八九'[num%10-1]
        return tens + ones
    if 100 <= num <= 999:
        hundreds = '百' if num // 100 == 1 else '一二三四五六七八九'[num//100-1] + '百'
        remainder = num % 100
        if remainder == 0: return hundreds
        if remainder < 10: return hundreds + '一二三四五六七八九'[remainder-1]
        return hundreds + arabic_to_kanji(str(remainder))
    
    return num_str  # Fallback for large numbers

def generate_search_patterns(article_input: str) -> List[str]:
    """Generate comprehensive search patterns for article numbers."""
    # Extract main number and patterns
    main_match = re.search(r'(\d+)', article_input)
    if not main_match:
        return [article_input]
    
    main_num = main_match.group(1)
    kanji_num = arabic_to_kanji(main_num)
    
    patterns = [
        f"第{kanji_num}条",     # e.g., 第百九十二条
        f"{kanji_num}条",      # e.g., 百九十二条
        f"第{main_num}条",     # e.g., 第192条
    ]
    
    # Handle 条の2 patterns
    if 'の' in article_input:
        no_match = re.search(r'の(\d+)', article_input)
        if no_match:
            no_num = no_match.group(1)
            no_kanji = arabic_to_kanji(no_num)
            patterns.extend([
                f"第{kanji_num}条の{no_kanji}",  # e.g., 第三百二十五条の三
                f"{kanji_num}条の{no_kanji}",   # e.g., 三百二十五条の三
                f"第{main_num}条の{no_num}",    # e.g., 第325条の3
            ])
    
    # Handle 項・号 patterns
    if '項' in article_input:
        kou_match = re.search(r'第(\d+)項', article_input)
        if kou_match:
            kou_num = kou_match.group(1)
            kou_kanji = arabic_to_kanji(kou_num)
            patterns.extend([
                f"第{kanji_num}条第{kou_kanji}項",
                f"第{main_num}条第{kou_num}項",
            ])
    
    if '号' in article_input:
        gou_match = re.search(r'第(\d+)号', article_input)
        if gou_match:
            gou_num = gou_match.group(1)
            gou_kanji = arabic_to_kanji(gou_num)
            patterns.extend([
                f"第{kanji_num}条第{gou_kanji}号",
                f"第{main_num}条第{gou_num}号",
            ])
    
    # Add original patterns
    patterns.extend([
        f"第{article_input}条",
        f"{article_input}条",
        article_input
    ])
    
    # Remove duplicates while preserving order
    return list(dict.fromkeys(patterns))

async def smart_law_lookup(law_name: str) -> Optional[str]:
    """Smart law lookup with direct mapping fallback to search."""
    law_name_clean = law_name.strip()
    
    # Step 1: Check direct mapping
    if law_name_clean in BASIC_LAWS:
        logger.info(f"Direct mapping: {law_name_clean} -> {BASIC_LAWS[law_name_clean]}")
        return BASIC_LAWS[law_name_clean]
    
    # Step 2: Intelligent search for unknown laws
    async with await get_http_client() as client:
        response = await client.get("/laws", params={
            "law_title": law_name_clean,
            "law_type": "Act",
            "limit": 20
        })
        response.raise_for_status()
        
        data = json.loads(response.text)
        laws = data.get("laws", [])
        
        if not laws:
            return None
        
        # Smart scoring for best law selection
        def score_law(law_info):
            law_num = law_info.get("law_num", "")
            score = 0
            
            # Era preference (modern laws preferred)
            if "令和" in law_num: score += 3000
            elif "平成" in law_num: score += 2000
            elif "昭和" in law_num: score += 1000
            elif "明治" in law_num: score += 500
            
            # Prefer shorter law numbers (basic laws)
            if len(law_num) < 25: score += 100
            
            # Year extraction for tie-breaking
            year_match = re.search(r'([元一二三四五六七八九十]+)年', law_num)
            if year_match:
                year_str = year_match.group(1)
                if year_str == "元": score += 1
                else:
                    # Simple kanji to number conversion
                    kanji_map = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
                               "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
                    if "十" in year_str:
                        parts = year_str.split("十")
                        tens = kanji_map.get(parts[0], 1) if parts[0] else 1
                        ones = kanji_map.get(parts[1], 0) if parts[1] else 0
                        score += tens * 10 + ones
                    else:
                        score += kanji_map.get(year_str, 0)
            
            return score
        
        best_law = max(laws, key=lambda law: score_law(law.get("law_info", {})))
        return best_law.get("law_info", {}).get("law_num")

@mcp.tool
async def find_law_article(law_name: str, article_number: str) -> str:
    """
    Find a specific article in Japanese law (ULTRA SMART & FAST)
    
    Supports 16+ major laws with direct mapping for instant access.
    Handles complex patterns like 条の2, 項, 号 automatically.
    
    Args:
        law_name: Law name (e.g., "民法", "会社法", "憲法")
        article_number: Article number (e.g., "192", "325条の3", "第9条第2項")
    
    Returns:
        JSON with found article content and metadata
    """
    if not law_name or not law_name.strip():
        return "Error: law_name is required"
    if not article_number or not article_number.strip():
        return "Error: article_number is required"
    
    try:
        # Step 1: Smart law lookup
        law_num = await smart_law_lookup(law_name)
        if not law_num:
            return f"Error: Law '{law_name}' not found"
        
        # Step 2: Get complete law text (XML format for full content)
        async with await get_http_client() as client:
            response = await client.get(f"/law_data/{law_num}", params={
                "law_full_text_format": "xml"
            })
            response.raise_for_status()
            
            data = json.loads(response.text)
            law_full_text = data.get('law_full_text', {})
            extracted_text = extract_text_from_xml(law_full_text)
            
            # Step 3: Smart article search
            patterns = generate_search_patterns(article_number)
            matches = []
            
            for pattern in patterns:
                regex_pattern = f".{{0,100}}{re.escape(pattern)}.{{0,500}}"
                found = re.findall(regex_pattern, extracted_text, re.DOTALL)
                for match in found:
                    clean_match = match.strip()
                    if clean_match and clean_match not in matches:
                        matches.append(clean_match)
            
            # Format result
            law_info_data = data.get('law_info', {})
            result = {
                "law_info": law_info_data,
                "search_law_name": law_name,
                "search_article": article_number,
                "found_law": law_info_data.get('law_title', law_name),
                "law_number": law_num,
                "matches_found": len(matches),
                "articles": matches[:3] if matches else [],
                "note": f"Searched for article '{article_number}' in '{law_name}'"
            }
            
            if not matches:
                # Smart suggestions for missing articles
                main_num = re.search(r'(\d+)', article_number)
                if main_num:
                    article_num = main_num.group(1)
                    kanji_num = arabic_to_kanji(article_num)
                    basic_patterns = [f"第{kanji_num}条", f"第{article_num}条"]
                    
                    basic_found = any(re.search(re.escape(p), extracted_text) for p in basic_patterns)
                    
                    if basic_found:
                        if 'の' in article_number:
                            result["suggestion"] = f"Article {article_num} exists, but the specified 'の' variation may not exist."
                        elif '項' in article_number or '号' in article_number:
                            result["suggestion"] = f"Article {article_num} exists, but the specified paragraph/item may not exist."
                        else:
                            result["suggestion"] = f"Article found with different formatting. Try searching for just '{article_num}'."
                    else:
                        result["suggestion"] = f"Article {article_number} not found in {law_name}. Please verify the article number."
                
                result["search_patterns_used"] = patterns[:5]
            
            return json.dumps(result, ensure_ascii=False, indent=2)
            
    except Exception as e:
        logger.error(f"Find law article error: {e}")
        return f"Find Law Article Error: {str(e)}"

@mcp.tool
async def search_laws(
    law_title: str = "",
    law_type: str = "",
    law_num: str = "",
    limit: int = 10,
    offset: int = 0
) -> str:
    """
    Search Japanese laws with smart filtering
    
    Args:
        law_title: Law title (partial match)
        law_type: Law type (Act, CabinetOrder, etc.)
        law_num: Law number (partial match)
        limit: Maximum results (1-500)
        offset: Starting position
    
    Returns:
        JSON with search results
    """
    # Input validation
    if limit < 1 or limit > 500:
        return "Error: limit must be between 1 and 500"
    if offset < 0:
        return "Error: offset must be 0 or greater"
    
    params = {"limit": limit, "offset": offset}
    if law_title: params["law_title"] = law_title
    if law_type: params["law_type"] = law_type
    if law_num: params["law_num"] = law_num
    
    try:
        async with await get_http_client() as client:
            response = await client.get("/laws", params=params)
            response.raise_for_status()
            return response.text
    except Exception as e:
        logger.error(f"Search laws error: {e}")
        return f"Search Laws Error: {str(e)}"

@mcp.tool
async def search_laws_by_keyword(keyword: str, law_type: str = "", limit: int = 5) -> str:
    """
    Full-text keyword search in Japanese laws
    
    Args:
        keyword: Search keyword (required)
        law_type: Law type filter (optional)
        limit: Maximum results (1-20)
    
    Returns:
        JSON with search results
    """
    if not keyword or not keyword.strip():
        return "Error: keyword is required"
    if limit < 1 or limit > 20:
        return "Error: limit must be between 1 and 20"
    
    params = {"keyword": keyword.strip(), "limit": limit}
    if law_type: params["law_type"] = law_type
    
    try:
        async with await get_http_client() as client:
            response = await client.get("/keyword", params=params)
            response.raise_for_status()
            return response.text
    except Exception as e:
        logger.error(f"Keyword search error: {e}")
        return f"Keyword Search Error: {str(e)}"

@mcp.tool
async def get_law_content(law_id: str = "", law_num: str = "", response_format: str = "json") -> str:
    """
    Get complete law content
    
    Args:
        law_id: Law ID
        law_num: Law number
        response_format: "json" or "xml"
    
    Returns:
        Complete law content in specified format
    """
    if not law_id and not law_num:
        return "Error: Either law_id or law_num must be specified"
    if response_format not in ["json", "xml"]:
        return "Error: response_format must be 'json' or 'xml'"
    
    law_identifier = law_id if law_id else law_num
    params = {}
    if response_format == "xml":
        params["law_full_text_format"] = "xml"
    
    try:
        async with await get_http_client() as client:
            response = await client.get(f"/law_data/{law_identifier}", params=params)
            response.raise_for_status()
            
            if response_format == "json":
                # Format JSON response for better readability
                data = json.loads(response.text)
                law_full_text = data.get('law_full_text', {})
                if isinstance(law_full_text, str):
                    # Extract readable text from XML
                    data['law_full_text_readable'] = extract_text_from_xml(law_full_text)
                
                return json.dumps(data, ensure_ascii=False, indent=2)
            else:
                return response.text
                
    except Exception as e:
        logger.error(f"Get law content error: {e}")
        return f"Get Law Content Error: {str(e)}"

# Resources
@mcp.resource("api://info")
def get_api_info() -> dict:
    """e-Gov Law API v2 information"""
    return {
        "name": "e-Gov Law API v2 - Ultra Smart Edition",
        "version": "2.0",
        "description": "Optimized Japanese law search with 16+ basic laws direct mapping",
        "features": [
            "🚀 Ultra-fast article search with direct law mapping",
            "🎯 16+ major laws (六法 + key legislation) instant access",
            "🧠 Smart XML/Base64 text extraction",
            "⚡ Efficient pattern matching for complex articles (条の2, 項, 号)",
            "📊 Intelligent law selection with era-based scoring",
            "🔍 Full-text keyword search with smart filtering"
        ],
        "basic_laws_supported": len(BASIC_LAWS),
        "optimization": "Reduced from 1000+ to <500 lines while adding functionality"
    }

@mcp.resource("schema://law_types")
def get_law_types() -> dict:
    """Supported Japanese law types"""
    return {
        "law_types": {
            "Constitution": "憲法",
            "Act": "法律", 
            "CabinetOrder": "政令",
            "MinisterialOrdinance": "省令",
            "Rule": "規則"
        },
        "basic_laws": BASIC_LAWS
    }

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="e-Gov Law MCP Server v2")
    parser.add_argument("--transport", choices=["stdio", "streamable-http"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    
    if args.transport == "stdio":
        # Use FastMCP's built-in stdio support
        mcp.run()
    else:
        # Use FastMCP's built-in streamable-http transport
        mcp.run(
            transport="streamable-http",
            host=args.host,
            port=args.port
        )