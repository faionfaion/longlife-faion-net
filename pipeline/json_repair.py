"""JSON repair utilities for LLM structured output parsing."""

from __future__ import annotations

import json
import logging
import re

logger = logging.getLogger(__name__)


def safe_parse_json(raw: str, *, context: str = "") -> dict:
    """Parse JSON string with automatic repair for common LLM errors."""
    label = f"[{context}] " if context else ""

    # Step 0: try as-is
    try:
        return _clean_html_in_dict(json.loads(raw))
    except (json.JSONDecodeError, ValueError):
        pass

    # Step 1: basic cleanup
    text = _strip_wrapping(raw)

    # Step 2: extract JSON object
    match = re.search(r'\{[\s\S]*\}', text)
    if not match:
        brace_idx = text.find('{')
        if brace_idx >= 0:
            text = _close_truncated(text[brace_idx:])
        else:
            raise ValueError(
                f"{label}No JSON object found in response ({len(raw)} chars)"
            )
    else:
        text = match.group()

    # Step 3: try after extraction
    try:
        return _clean_html_in_dict(json.loads(text))
    except (json.JSONDecodeError, ValueError):
        pass

    # Step 4: unicode quotes
    text = _sanitize_unicode_quotes(text)
    try:
        return _clean_html_in_dict(json.loads(text))
    except (json.JSONDecodeError, ValueError):
        pass

    # Step 5: trailing commas
    text = _fix_trailing_commas(text)
    try:
        return _clean_html_in_dict(json.loads(text))
    except (json.JSONDecodeError, ValueError):
        pass

    # Step 6: control characters
    text = _fix_control_chars(text)
    try:
        return _clean_html_in_dict(json.loads(text))
    except (json.JSONDecodeError, ValueError):
        pass

    # Step 7: stray quotes
    text = _repair_json_quotes(text)
    try:
        return _clean_html_in_dict(json.loads(text))
    except (json.JSONDecodeError, ValueError):
        pass

    # Step 8: backslash sequences
    text = _fix_backslashes(text)
    try:
        return _clean_html_in_dict(json.loads(text))
    except (json.JSONDecodeError, ValueError):
        pass

    raise ValueError(f"{label}All JSON repair attempts failed ({len(raw)} chars)")


def _strip_wrapping(raw: str) -> str:
    text = raw.strip().lstrip('\ufeff')
    # Remove markdown fences
    if text.startswith("```"):
        lines = text.split('\n')
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = '\n'.join(lines)
    return text.strip()


def _sanitize_unicode_quotes(text: str) -> str:
    replacements = {
        '\u201c': '"', '\u201d': '"',  # smart double quotes
        '\u2018': "'", '\u2019': "'",  # smart single quotes
        '\u00ab': '"', '\u00bb': '"',  # guillemets
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def _fix_trailing_commas(text: str) -> str:
    return re.sub(r',\s*([}\]])', r'\1', text)


def _fix_control_chars(text: str) -> str:
    # Replace literal newlines/tabs inside JSON strings
    result = []
    in_string = False
    escape = False
    for ch in text:
        if escape:
            result.append(ch)
            escape = False
            continue
        if ch == '\\':
            escape = True
            result.append(ch)
            continue
        if ch == '"':
            in_string = not in_string
        if in_string:
            if ch == '\n':
                result.append('\\n')
                continue
            if ch == '\t':
                result.append('\\t')
                continue
            if ch == '\r':
                continue
        result.append(ch)
    return ''.join(result)


def _repair_json_quotes(text: str) -> str:
    # Simple heuristic: replace unescaped quotes inside string values
    return re.sub(
        r'(?<=: ")(.*?)(?="[,}\]])',
        lambda m: m.group().replace('"', '\\"'),
        text,
        flags=re.DOTALL,
    )


def _fix_backslashes(text: str) -> str:
    valid_escapes = set('"\\/bfnrtu')
    result = []
    i = 0
    while i < len(text):
        if text[i] == '\\' and i + 1 < len(text):
            if text[i + 1] in valid_escapes:
                result.append(text[i])
            else:
                result.append('\\\\')
            i += 1
            result.append(text[i])
        else:
            result.append(text[i])
        i += 1
    return ''.join(result)


def _close_truncated(text: str) -> str:
    opens = 0
    brackets = 0
    for ch in text:
        if ch == '{':
            opens += 1
        elif ch == '}':
            opens -= 1
        elif ch == '[':
            brackets += 1
        elif ch == ']':
            brackets -= 1
    # Close unclosed structures
    text = text.rstrip().rstrip(',')
    text += ']' * max(0, brackets) + '}' * max(0, opens)
    return text


def _clean_html_in_dict(data: dict) -> dict:
    """Strip HTML tags from non-tg string values."""
    cleaned = {}
    for key, value in data.items():
        if isinstance(value, str) and 'tg' not in key.lower():
            # Remove HTML tags but preserve content
            value = re.sub(r'<[^>]+>', '', value)
        elif isinstance(value, dict):
            value = _clean_html_in_dict(value)
        cleaned[key] = value
    return cleaned
