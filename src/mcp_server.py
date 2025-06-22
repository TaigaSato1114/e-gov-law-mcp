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
        
        # Step 2: Get law text with XML format
        async with await get_http_client() as client:
            # Get law data with XML format (elm parameter removed due to API 400 errors)
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
                # Enhanced text extraction for complete articles
                article_pattern = re.escape(pattern)
                
                # Find all matches first and filter for actual content vs table of contents
                all_matches = []
                
                # Find all occurrences of the pattern
                for match in re.finditer(article_pattern, extracted_text):
                    pos = match.start()
                    
                    # Check if this is the START of an actual article (not a reference)
                    # Look at context before the match
                    context_before = extracted_text[max(0, pos-50):pos]
                    context_after = extracted_text[pos:pos+100]
                    
                    # Skip if this appears to be a reference within another article
                    if re.search(r'第\d+条.*第\d+条', context_before + context_after):
                        continue  # This is likely a reference, not the actual article start
                    
                    # Look for patterns that indicate this is an actual article start
                    is_actual_article = False
                    
                    # Pattern 1: Article number followed by title/content structure
                    if re.search(rf'{article_pattern}\s*\n\s*\n\s*\n\s*', extracted_text[pos:pos+200]):
                        is_actual_article = True
                    
                    # Pattern 2: Article number at start of line with proper indentation
                    if context_before.endswith('\n              ') or context_before.endswith('            '):
                        is_actual_article = True
                    
                    # Pattern 3: Article number followed by paragraph structure
                    if re.search(rf'{article_pattern}\s*\n.*?\n.*?\n.*?[あ-ん]', extracted_text[pos:pos+300], re.DOTALL):
                        is_actual_article = True
                        
                    if not is_actual_article:
                        continue
                    
                    # Try multiple extraction strategies for this position
                    strategies = [
                        # Strategy 1: Article to next kanji article number
                        f"{article_pattern}.*?(?=第[一二三四五六七八九十百千]+条)",
                        
                        # Strategy 2: Article excluding next "第" character  
                        f"{article_pattern}[^第]*",
                        
                        # Strategy 3: Article to title pattern + next article
                        f"{article_pattern}.*?(?=（[^）]*）\\s*第)",
                        
                        # Strategy 4: Fixed character limit
                        f"{article_pattern}.{{0,2000}}"
                    ]
                    
                    # Get context around this match
                    context_start = max(0, pos - 20)
                    context_end = min(len(extracted_text), pos + 3000)
                    context = extracted_text[context_start:context_end]
                    
                    for strategy in strategies:
                        matches_found = re.findall(strategy, context, re.DOTALL | re.MULTILINE)
                        if matches_found:
                            candidate = matches_found[0].strip()
                            if len(candidate) > 50:
                                # Score this candidate based on content quality
                                content_score = 0
                                
                                # Heavily favor actual article content patterns
                                content_score += 10  # Base score for being an actual article
                                
                                # Prefer longer content
                                if len(candidate) > 200: content_score += 3
                                elif len(candidate) > 100: content_score += 2
                                
                                # Prefer content with sentence endings
                                if '。' in candidate: content_score += 3
                                
                                # Prefer content with commas (actual text)
                                if '、' in candidate: content_score += 2
                                
                                # Prefer content with hiragana (actual content vs table)
                                if re.search(r'[あ-ん]+', candidate): content_score += 3
                                
                                # Penalize reference patterns
                                if '―' in candidate: content_score -= 5
                                if candidate.count('第') > 3: content_score -= 2  # Too many references
                                
                                all_matches.append((content_score, candidate, pos))
                                break
                
                # Sort by content score (highest first) and take best matches
                all_matches.sort(key=lambda x: x[0], reverse=True)
                
                # Process top scored matches
                for score, candidate, pos in all_matches[:3]:  # Take top 3 candidates
                    if score > 10:  # Only accept high-quality actual articles
                        clean_match = candidate.strip()
                        # Accept matches that look like complete articles
                        if len(clean_match) > 30 and clean_match not in matches:
                            # Ensure we have a complete sentence/clause ending
                            if clean_match.endswith(('。', '）', '）。', '号', '項', '条')):
                                matches.append(clean_match)
                            else:
                                # Try to find a good stopping point
                                for ending in ['。', '）。', '号。', '項。']:
                                    if ending in clean_match:
                                        last_pos = clean_match.rfind(ending)
                                        if last_pos > len(clean_match) * 0.7:  # Must be in latter part
                                            truncated = clean_match[:last_pos + len(ending)]
                                            matches.append(truncated)
                                            break
                                else:
                                    # If no good ending found, use as-is if substantial
                                    if len(clean_match) > 100:
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
                "note": f"Searched for article '{article_number}' in '{law_name}'",
                "legal_analysis_instruction": "【重要】日本の法律の専門家として、この条文について以下のように回答してください：\n\n■ 1. 条文の正確な全文引用（必須）\n検索結果の「articles」に含まれる条文テキストを、一字一句正確に引用してください。条文番号、項、号まで含めて完全に表示してください。\n\n例：\n「第百九十二条　取引行為によって、平穏に、かつ、公然と動産の占有を始めた者は、善意であり、かつ、過失がないときは、即時にその動産について行使する権利を取得する。」\n\n■ 2. 法的分析（条文を引用しながら説明）\n上記で引用した条文の重要な文言を「」で再度引用しながら、以下の観点から詳細に分析してください：\n・条文の趣旨（立法目的・背景）\n・要件（適用要件・前提条件）\n・法的効果（権利義務の発生・変更・消滅）\n・実務上の注意点・関連判例\n・他の条文との関係性\n\n例：「取引行為によって」という要件は有償取引を前提とし、「善意であり、かつ、過失がない」という要件は主観的要件を示します。\n\n条文の正確な引用と法的分析を組み合わせた専門的で実用的な回答をお願いします。"
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
async def get_law_content(law_id: str = "", law_num: str = "", response_format: str = "json", elm: str = "") -> str:
    """
    Get law content (optimized per API spec with size limits)
    
    Args:
        law_id: Law ID
        law_num: Law number
        response_format: "json" or "xml"
        elm: Element to retrieve (currently disabled due to API 400 errors)
    
    Returns:
        Law content in specified format. For large laws (>800KB), returns summary with recommendation to use find_law_article for specific articles.
        
    Note:
        - elm parameter is currently disabled due to e-Gov API 400 errors
        - Large laws like Company Law (会社法) will return a summary instead of full text
        - Use find_law_article tool for specific article searches in large laws
    """
    if not law_id and not law_num:
        return "Error: Either law_id or law_num must be specified"
    if response_format not in ["json", "xml"]:
        return "Error: response_format must be 'json' or 'xml'"
    
    law_identifier = law_id if law_id else law_num
    params = {}
    if response_format == "xml":
        params["law_full_text_format"] = "xml"
    
    # Note: elm parameter causes 400 errors with current e-Gov API
    # Commented out to avoid API errors
    # if elm:
    #     params["elm"] = elm
    
    try:
        async with await get_http_client() as client:
            response = await client.get(f"/law_data/{law_identifier}", params=params)
            response.raise_for_status()
            
            if response_format == "json":
                # Format JSON response for better readability
                data = json.loads(response.text)
                
                # Check response size and truncate if necessary
                response_str = json.dumps(data, ensure_ascii=False, indent=2)
                if len(response_str) > 800000:  # 800KB limit (留余裕給其他數據)
                    # Create summary instead of full text for large laws
                    law_info = data.get('law_info', {})
                    summary = {
                        "law_info": law_info,
                        "warning": "法令全文が長すぎるため、概要のみ表示しています。",
                        "recommendation": "特定の条文を検索する場合は find_law_article ツールを使用してください。",
                        "law_stats": {
                            "original_size_bytes": len(response_str),
                            "law_title": law_info.get('law_title', ''),
                            "law_num": law_info.get('law_num', ''),
                            "promulgation_date": law_info.get('promulgation_date', '')
                        }
                    }
                    
                    # Try to include table of contents if available
                    law_full_text = data.get('law_full_text', {})
                    if isinstance(law_full_text, dict):
                        # Extract structure information
                        if 'chapters' in str(law_full_text).lower() or '章' in str(law_full_text):
                            summary["structure_note"] = "この法令は章立て構造を持っています。"
                        if 'sections' in str(law_full_text).lower() or '節' in str(law_full_text):
                            summary["structure_note"] = summary.get("structure_note", "") + " 節による区分があります。"
                    
                    return json.dumps(summary, ensure_ascii=False, indent=2)
                
                # For smaller responses, add readable text
                law_full_text = data.get('law_full_text', {})
                if isinstance(law_full_text, str):
                    # Extract readable text from XML
                    data['law_full_text_readable'] = extract_text_from_xml(law_full_text)
                
                return json.dumps(data, ensure_ascii=False, indent=2)
            else:
                # For XML format, check size and truncate if needed
                if len(response.text) > 800000:
                    return f"""<?xml version="1.0" encoding="UTF-8"?>
<law_content_summary>
    <warning>法令全文が長すぎるため、概要のみ表示しています。</warning>
    <recommendation>特定の条文を検索する場合は find_law_article ツールを使用してください。</recommendation>
    <original_size_bytes>{len(response.text)}</original_size_bytes>
    <truncated_content>
        {response.text[:1000]}...
    </truncated_content>
</law_content_summary>"""
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
        "optimization": "Reduced from 1000+ to <500 lines while adding functionality",
        "legal_analysis_guidance": "日本の法律の専門家として、条文の趣旨と要件と効果に重点を置いて回答してください。単なる条文の引用ではなく、法的分析と実務的な解釈を含めてください。"
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

def main():
    """Entry point for direct uvx installation"""
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

if __name__ == "__main__":
    main()