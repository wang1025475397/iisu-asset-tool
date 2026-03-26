"""
Internationalization (i18n) module for iiSU Asset Tool.
Supports multiple languages with JSON-based translation files.
"""
import json
import locale
import sys
from pathlib import Path
from typing import Any

# Current language code (default: en)
_current_lang: str = "en"
_translations: dict[str, str] = {}
_loaded: bool = False


def get_locales_dir() -> Path:
    """Get the locales directory path."""
    return Path(__file__).parent / "locales"


def get_available_languages() -> dict[str, str]:
    """Get available languages as {code: display_name}."""
    return {
        "auto": "Auto (System)",  # Will be translated dynamically
        "en": "English",
        "zh_CN": "简体中文",
    }


def load_translations(lang: str) -> bool:
    """Load translations for the specified language.
    
    Args:
        lang: Language code (e.g., 'en', 'zh_CN')
        
    Returns:
        True if translations loaded successfully, False otherwise
    """
    global _translations, _loaded, _current_lang
    
    if lang == "en":
        # English is the default, no translation needed
        _current_lang = "en"
        _translations = {}
        _loaded = True
        return True
    
    locales_dir = get_locales_dir()
    lang_file = locales_dir / f"{lang}.json"
    
    if not lang_file.exists():
        print(f"Translation file not found: {lang_file}")
        _current_lang = "en"
        _translations = {}
        _loaded = True
        return False
    
    try:
        with open(lang_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Ensure all values are strings
            _translations = {k: str(v) for k, v in data.items()}
        _current_lang = lang
        _loaded = True
        return True
    except Exception as e:
        print(f"Failed to load translations for {lang}: {e}")
        _current_lang = "en"
        _translations = {}
        _loaded = True
        return False


def set_language(lang: str) -> bool:
    """Set the current language.
    
    Args:
        lang: Language code (e.g., 'en', 'zh_CN')
        
    Returns:
        True if language was set successfully
    """
    global _current_lang
    
    if lang == _current_lang and _loaded:
        return True
    
    return load_translations(lang)


def get_language() -> str:
    """Get the current language code."""
    return _current_lang


def tr(key: str, default: str | None = None, **kwargs: Any) -> str:
    """Translate a key to the current language.
    
    Args:
        key: Translation key (usually the English text)
        default: Default value if translation not found (defaults to key)
        **kwargs: Format variables for string interpolation
        
    Returns:
        Translated string, or key/default if not found
    """
    if _current_lang == "en" or not _translations:
        text = default if default is not None else key
    else:
        text = _translations.get(key, default if default is not None else key)
    
    # Ensure text is a string
    if not isinstance(text, str):
        text = str(text)
    
    # Apply format variables if provided
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, ValueError):
            return text
    
    return text


def tr_fmt(key: str, *args: Any, **kwargs: Any) -> str:
    """Translate and format a string with positional or keyword arguments.
    
    Args:
        key: Translation key
        *args: Positional format arguments
        **kwargs: Keyword format arguments
        
    Returns:
        Formatted translated string
    """
    text = tr(key)
    
    if args:
        try:
            # Use tuple formatting for multiple args, single value for one arg
            if len(args) == 1:
                return text % args[0]
            else:
                return text % args
        except (TypeError, ValueError):
            return text
    
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, ValueError):
            return text
    
    return text


# Convenience alias
_ = tr


def detect_system_language() -> str:
    """Detect the system language.
    
    Returns:
        Language code based on system locale:
        - 'zh_CN' for Chinese systems
        - 'en' for all other systems
    """
    # Try multiple methods to detect system language
    lang_code = None
    
    # Method 1: Use locale module
    try:
        lang_code = locale.getdefaultlocale()[0]
    except Exception:
        pass
    
    # Method 2: Use system language on Windows/macOS/Linux
    if not lang_code:
        try:
            if sys.platform == "win32":
                import ctypes
                windll = ctypes.windll.kernel32
                lang_id = windll.GetUserDefaultUILanguage()
                # Map Windows language ID to locale code
                # 0x0804 = Chinese (Simplified)
                if lang_id in (0x0804, 0x0404):  # Simplified or Traditional Chinese
                    lang_code = "zh_CN"
        except Exception:
            pass
    
    # Method 3: Check environment variables
    if not lang_code:
        import os
        for env_var in ("LANG", "LC_ALL", "LC_MESSAGES", "LANGUAGE"):
            env_lang = os.environ.get(env_var, "")
            if env_lang:
                lang_code = env_lang.split(".")[0].split("_")[0]
                break
    
    # Check if the language is Chinese
    if lang_code:
        lang_lower = lang_code.lower()
        if lang_lower.startswith("zh") or "chinese" in lang_lower:
            return "zh_CN"
    
    return "en"


def init_from_config(config: dict[str, Any]) -> str:
    """Initialize language from config.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        The language code that was set
    """
    # Check if user has explicitly set a language in config
    user_lang = config.get("ui", {}).get("language", None)
    
    if user_lang and user_lang != "auto":
        # User has explicitly chosen a language
        lang = user_lang
    else:
        # Auto-detect from system language
        lang = detect_system_language()
    
    set_language(lang)
    return lang
