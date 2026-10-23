import os
import sys
import time
import json
import base64
import random
import requests
import hashlib
import urllib.parse

# Ensure parent directory is in sys.path in case this is called directly or imported from subpackages
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import config as cfg

class ProviderManager:
    _session = None
    _ocr_cache = {}
    _chat_cache = {}
    _gemini_client = None
    _gemini_configured = False

    @classmethod
    def _get_session(cls) -> requests.Session:
        """
        Returns a cached requests.Session for connection reuse and request pooling.
        Mounts a shared HTTPAdapter for both HTTP and HTTPS to allow connection pooling.
        """
        if cls._session is None:
            cls._session = requests.Session()
            # Configure a connection pool with reasonable limits
            adapter = requests.adapters.HTTPAdapter(
                pool_connections=10,
                pool_maxsize=20,
                max_retries=1
            )
            cls._session.mount("http://", adapter)
            cls._session.mount("https://", adapter)
        return cls._session

    @classmethod
    def _build_messages(
        cls,
        system_prompt: str | None,
        messages_history: list,
        user_prompt: str | None,
    ) -> list:
        """Assembles the OpenAI-compatible messages list from components.

        Extracted to eliminate the identical 4-line pattern that previously
        appeared in both chat() and nvidia_instruct().
        """
        messages: list = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if messages_history:
            messages.extend(messages_history)
        if user_prompt:
            messages.append({"role": "user", "content": user_prompt})
        return messages

    @classmethod
    def _make_cache_key(cls, data: dict) -> str:
        """Produces a stable MD5 hex-digest cache key from an arbitrary dict.

        Extracted to eliminate the identical json.dumps + hashlib.md5 pattern
        that previously appeared in five separate methods.
        """
        serialized = json.dumps(data, sort_keys=True)
        return hashlib.md5(serialized.encode("utf-8")).hexdigest()


    @classmethod
    def chat(
        cls,
        system_prompt: str,
        messages_history: list,
        user_prompt: str,
        response_format_json: bool = False,
    ) -> str:
        """
        Executes a chat LLM query with retry, rate-limit handling, automatic
        fallback, and response caching.

        Provider chain: Groq Llama 3.3 → NVIDIA Nemotron 3 Ultra → Google Gemma 4.
        Returns the raw text content string from whichever provider succeeds.
        Raises ValueError if all providers fail.
        """
        cache_hash = cls._make_cache_key({
            "system_prompt": system_prompt,
            "history": messages_history,
            "user_prompt": user_prompt,
            "json_format": response_format_json,
        })
        if cache_hash in cls._chat_cache:
            return cls._chat_cache[cache_hash]

        messages = cls._build_messages(system_prompt, messages_history, user_prompt)
        session = cls._get_session()

        # --- 1. Primary: Gemini 2.5 Flash ---
        if cfg.LLMConfig.GEMINI_API_KEY:
            try:
                full_prompt = ""
                if system_prompt:
                    full_prompt += f"[System Instructions]\n{system_prompt}\n\n"
                if messages_history:
                    for m in messages_history:
                        role = m.get("role", "user")
                        content = m.get("content", "")
                        full_prompt += f"{role.capitalize()}: {content}\n"
                full_prompt += f"User: {user_prompt}\n"
                if response_format_json:
                    full_prompt += "\nOutput ONLY valid, raw JSON."

                content = cls.gemini(prompt=full_prompt, system_prompt=system_prompt)
                if content:
                    cls._chat_cache[cache_hash] = content
                    return content
            except Exception:
                pass

        # --- 2. Groq (High-Speed LPU Inference: GPT-OSS 120B / Qwen 27B) ---
        if cfg.LLMConfig.GROQ_API_KEY:
            groq_models = ["openai/gpt-oss-120b", "qwen/qwen3.6-27b", "openai/gpt-oss-20b"]
            for model_name in groq_models:
                try:
                    url = "https://api.groq.com/openai/v1/chat/completions"
                    headers = {
                        "Authorization": f"Bearer {cfg.LLMConfig.GROQ_API_KEY}",
                        "Content-Type": "application/json",
                    }
                    payload = {
                        "model": model_name,
                        "messages": messages,
                        "temperature": 0.3,
                        "max_tokens": 4096
                    }
                    if response_format_json:
                        payload["response_format"] = {"type": "json_object"}

                    response = session.post(url, headers=headers, json=payload, timeout=12)
                    if response.status_code == 200:
                        content = response.json()["choices"][0]["message"]["content"].strip()
                        if content:
                            cls._chat_cache[cache_hash] = content
                            return content
                    elif response.status_code == 429:
                        continue
                except Exception as e:
                    pass

        # --- 3. NVIDIA NIM (Nemotron Nano Omni) ---
        nvidia_keys = [
            cfg.VisionConfig.NVIDIA_VISION_API_KEY,
            cfg.SearchConfig.NVIDIA_API_KEY,
            cfg.LLMConfig.NVIDIA_NEMOTRON_API_KEY,
            cfg.LLMConfig.NVIDIA_MISTRAL_API_KEY
        ]
        valid_nvidia_keys = [k for k in nvidia_keys if k]
        
        if valid_nvidia_keys:
            n_key = valid_nvidia_keys[0]
            headers = {
                "Authorization": f"Bearer {n_key}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            try:
                payload = {
                    "model": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
                    "messages": messages,
                    "temperature": 0.4,
                    "max_tokens": 4096
                }
                url = "https://integrate.api.nvidia.com/v1/chat/completions"
                response = session.post(url, headers=headers, json=payload, timeout=8)
                if response.status_code == 200:
                    content = response.json()["choices"][0]["message"]["content"].strip()
                    if content:
                        cls._chat_cache[cache_hash] = content
                        return content
            except Exception as e:
                print(f"[ProviderManager Warning] NVIDIA attempt failed: {e}")

        # --- 4. OpenRouter Fallback ---
        if cfg.LLMConfig.OPENROUTER_API_KEY:
            try:
                url = "https://openrouter.ai/api/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {cfg.LLMConfig.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": "meta-llama/llama-3.3-70b-instruct",
                    "messages": messages,
                    "temperature": 0.5
                }
                response = session.post(url, headers=headers, json=payload, timeout=15)
                if response.status_code == 200:
                    content = response.json()["choices"][0]["message"]["content"].strip()
                    if content:
                        cls._chat_cache[cache_hash] = content
                        return content
            except Exception as e:
                print(f"[ProviderManager Warning] OpenRouter failed: {e}")

        raise ValueError("All configured chat LLM providers failed to respond.")

    @classmethod
    def code(cls, prompt: str, language: str, is_api_call: bool = True) -> str:
        """
        Generates production-grade code using the fast LLM provider chain.
        When is_api_call=True the response is a JSON string {"code": "..."}.
        When is_api_call=False the response is plain code text.
        """
        if is_api_call:
            system_prompt = (
                "You are J.A.R.V.I.S., a master software architect and coding co-pilot.\n"
                f"Write high quality, robust, complete, and runnable code in the following target language: {language}.\n"
                "CRITICAL REQUIREMENTS:\n"
                "1. If creating interactive console programs (e.g. calculator, menu, text game), ensure input handling is intuitive, robust, and handles errors gracefully without infinite hanging.\n"
                "2. Include clear comments explaining key logic.\n"
                "3. Respond ONLY with a valid JSON object matching the key 'code':\n"
                "{\"code\": \"<pure runnable code with standard newlines>\"}\n"
                "Do not include markdown code fence wrappers inside the JSON string."
            )
            user_prompt = (
                f"Task: Generate {language} code for: \"{prompt}\"\n\n"
                "Respond ONLY with a valid JSON object with key 'code'."
            )
        else:
            system_prompt = (
                "You are J.A.R.V.I.S., a master software architect and developer assistant. "
                f"Write high quality, robust, complete, and runnable code in the target language: {language}."
            )
            user_prompt = (
                f"Generate {language} code for: {prompt}\n"
                "Requirements:\n"
                "- Only provide the code, no explanations\n"
                "- Make sure the code is complete and runnable\n"
                "- Include necessary imports/dependencies\n"
                f"- Use {language} best practices and conventions\n"
                "- Add basic error handling where appropriate\n"
                "- Add comments to explain complex logic"
            )

        # Check cache first
        cache_hash = cls._make_cache_key({
            "prompt": prompt,
            "language": language,
            "is_api_call": is_api_call,
        })
        if cache_hash in cls._chat_cache:
            return cls._chat_cache[cache_hash]

        # Use the fast, resilient chat provider chain (Groq / Gemini / NVIDIA Nemotron)
        res = cls.chat(system_prompt, [], user_prompt, response_format_json=is_api_call)
        cls._chat_cache[cache_hash] = res
        return res

    @classmethod
    def compress_image_to_b64(cls, img, max_size=180000) -> str:
        """
        Takes a PIL Image object, compresses it to JPEG (quality 80),
        and downscales it to fit within max_size (chars/bytes) if needed,
        returning the base64 string.
        """
        import io
        from PIL import Image
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=80)
        image_b64 = base64.b64encode(buf.getvalue()).decode()
        
        if len(image_b64) >= max_size:
            w, h = img.size
            target_w = 1280 if w > 1280 else w
            target_h = int(h * (target_w / w))
            img_resized = img.resize((target_w, target_h))
            buf = io.BytesIO()
            img_resized.save(buf, format='JPEG', quality=75)
            image_b64 = base64.b64encode(buf.getvalue()).decode()
            
        return image_b64

    @classmethod
    def ocr(cls, image_b64):
        """
        Performs OCR using NVIDIA Nemotron OCR v2 with MD5 caching to avoid duplicate remote calls.
        """
        if not cfg.OCRConfig.NVIDIA_OCR_API_KEY:
            raise ValueError("NVIDIA OCR API key is not configured.")

        img_hash = hashlib.md5(image_b64.encode('utf-8')).hexdigest()
        if img_hash in cls._ocr_cache:
            return cls._ocr_cache[img_hash]

        url = "https://ai.api.nvidia.com/v1/cv/nvidia/nemotron-ocr-v2"
        headers = {
            "Authorization": f"Bearer {cfg.OCRConfig.NVIDIA_OCR_API_KEY}",
            "Accept": "application/json"
        }
        payload = {
            "input": [
                {
                    "type": "image_url",
                    "url": f"data:image/png;base64,{image_b64}"
                }
            ]
        }

        session = cls._get_session()
        for attempt in range(3):
            try:
                response = session.post(url, headers=headers, json=payload, timeout=30)
                if response.status_code == 200:
                    res_json = response.json()
                    cls._ocr_cache[img_hash] = res_json
                    return res_json
                elif response.status_code == 429:
                    print(f"[ProviderManager] NVIDIA OCR rate limited. Retrying in 2 seconds...")
                    time.sleep(2)
                    continue
                else:
                    print(f"[ProviderManager Warning] NVIDIA OCR returned status {response.status_code}")
            except Exception as e:
                print(f"[ProviderManager Warning] NVIDIA OCR attempt {attempt+1} failed: {e}")
                time.sleep(1)

        raise ValueError("NVIDIA OCR provider failed to respond.")

    @classmethod
    def vision(
        cls,
        image_input: str,
        prompt: str = "Describe what is in this image, including visible text, active windows, and UI controls.",
        system_prompt: str | None = None
    ) -> str:
        """
        Multimodal visual perception using nvidia/nemotron-3-nano-omni-30b-a3b-reasoning.
        image_input can be a web URL, local image path, or raw base64 string.
        """
        api_key = cfg.VisionConfig.NVIDIA_VISION_API_KEY
        if not api_key:
            raise ValueError("NVIDIA Vision API key is not configured.")

        # Prepare image URL / data URI
        if image_input.startswith("http://") or image_input.startswith("https://") or image_input.startswith("data:image"):
            image_url = image_input
        elif os.path.exists(image_input):
            import mimetypes
            mime_type, _ = mimetypes.guess_type(image_input)
            mime_type = mime_type or "image/png"
            with open(image_input, "rb") as f:
                b64_data = base64.b64encode(f.read()).decode("utf-8")
            image_url = f"data:{mime_type};base64,{b64_data}"
        else:
            # Assume raw base64 string
            image_url = f"data:image/jpeg;base64,{image_input}"

        cache_hash = cls._make_cache_key({
            "prompt": prompt,
            "image_url_hash": hashlib.md5(image_url.encode("utf-8")).hexdigest(),
            "provider": "nvidia_vision_omni",
        })
        if cache_hash in cls._chat_cache:
            return cls._chat_cache[cache_hash]

        messages_list = []
        if system_prompt:
            messages_list.append({"role": "system", "content": system_prompt})

        messages_list.append({
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": prompt
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": image_url
                    }
                }
            ]
        })

        invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        payload = {
            "model": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
            "messages": messages_list,
            "max_tokens": 4096,
            "temperature": 0.6,
            "top_p": 0.95
        }

        session = cls._get_session()
        for attempt in range(3):
            try:
                response = session.post(invoke_url, headers=headers, json=payload, timeout=40)
                if response.status_code == 200:
                    res_json = response.json()
                    content = res_json["choices"][0]["message"]["content"].strip()
                    cls._chat_cache[cache_hash] = content
                    return content
                elif response.status_code == 429:
                    print(f"[ProviderManager] NVIDIA Vision rate limited. Retrying in 2 seconds...")
                    time.sleep(2)
                    continue
                else:
                    print(f"[ProviderManager Warning] NVIDIA Vision returned status {response.status_code}")
            except Exception as e:
                print(f"[ProviderManager Warning] NVIDIA Vision attempt {attempt+1} failed: {e}")
                time.sleep(1)

        raise ValueError("NVIDIA Vision provider failed to respond.")

    @classmethod
    def gemini(cls, prompt, system_prompt=None):
        """
        Generates content using Gemini (google.generativeai) with lazy initialization.
        """
        if not cfg.LLMConfig.GEMINI_API_KEY:
            raise ValueError("Gemini API key is not configured.")

        import google.generativeai as genai
        if not cls._gemini_configured:
            genai.configure(api_key=cfg.LLMConfig.GEMINI_API_KEY)
            cls._gemini_configured = True
        
        cache_hash = cls._make_cache_key({
            "prompt": prompt,
            "system_prompt": system_prompt,
            "provider": "gemini",
        })
        if cache_hash in cls._chat_cache:
            return cls._chat_cache[cache_hash]

        for attempt in range(2):
            try:
                model_name = "gemini-2.5-flash"
                if system_prompt:
                    model = genai.GenerativeModel(
                        model_name=model_name,
                        system_instruction=system_prompt
                    )
                else:
                    model = genai.GenerativeModel(model_name=model_name)
                    
                response = model.generate_content(prompt)
                res_text = response.text.strip()
                cls._chat_cache[cache_hash] = res_text
                return res_text
            except Exception as e:
                err_msg = str(e)
                if "429" in err_msg or "quota" in err_msg.lower() or "limit" in err_msg.lower():
                    print("[ProviderManager] Gemini free-tier daily limit reached (429). Switching to Groq LPU...")
                    break
                print(f"[ProviderManager Warning] Gemini attempt {attempt+1} failed: {err_msg[:120]}")
                time.sleep(0.5)
        raise ValueError("Gemini provider failed to respond.")

    @classmethod
    def gemini_grounding(cls, query):
        """
        Grounded search query using Gemini 2.5 Flash with search tool and lazy client initialization.
        """
        if not cfg.LLMConfig.GEMINI_API_KEY:
            raise ValueError("Gemini API key is not configured.")

        cache_hash = cls._make_cache_key({
            "query": query,
            "provider": "gemini_grounding",
        })
        if cache_hash in cls._chat_cache:
            return cls._chat_cache[cache_hash]

        if cls._gemini_client is None:
            from google import genai
            cls._gemini_client = genai.Client(api_key=cfg.LLMConfig.GEMINI_API_KEY)
        
        for attempt in range(3):
            try:
                response = cls._gemini_client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=query,
                    config={"tools": [{"google_search": {}}]}
                )
                res_text = response.text
                cls._chat_cache[cache_hash] = res_text
                return res_text
            except Exception as e:
                print(f"[ProviderManager Warning] Gemini grounding attempt {attempt+1} failed: {e}")
                time.sleep(1)
        raise ValueError("Gemini grounding provider failed to respond.")

    @classmethod
    def nvidia_instruct(
        cls,
        system_prompt: str,
        messages_history: list,
        user_prompt: str,
    ) -> str:
        """
        Queries meta/llama-3.3-70b-instruct via the NVIDIA NIM endpoint with
        retries and rate-limit handling.

        Falls back to the general chat() provider chain if NVIDIA fails.
        """
        if not cfg.SearchConfig.NVIDIA_API_KEY:
            fallback_res = cls.chat(system_prompt, messages_history, user_prompt)
            cls._chat_cache[cache_hash] = fallback_res
            return fallback_res

        cache_hash = cls._make_cache_key({
            "system_prompt": system_prompt,
            "history": messages_history,
            "user_prompt": user_prompt,
            "provider": "nvidia_instruct",
        })
        if cache_hash in cls._chat_cache:
            return cls._chat_cache[cache_hash]

        messages = cls._build_messages(system_prompt, messages_history, user_prompt)

        url = f"{cfg.SearchConfig.NVIDIA_BASE_URL.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {cfg.SearchConfig.NVIDIA_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "meta/llama-3.3-70b-instruct",
            "messages": messages,
            "temperature": 0.5,
            "top_p": 0.7,
            "max_tokens": 1024,
            "stream": False
        }

        session = cls._get_session()
        for attempt in range(1):
            try:
                response = session.post(url, headers=headers, json=payload, timeout=3.0)
                if response.status_code == 200:
                    content = response.json()["choices"][0]["message"]["content"].strip()
                    cls._chat_cache[cache_hash] = content
                    return content
            except Exception as e:
                pass

        fallback_res = cls.chat(system_prompt, messages_history, user_prompt)
        cls._chat_cache[cache_hash] = fallback_res
        return fallback_res
