# -*- coding: utf-8 -*-
"""
Gamma Generate API (beta) lightweight client for creating PDF from report text.
"""
from __future__ import annotations

import os
import time
import re
from pathlib import Path
from typing import Optional, Dict, Any
import asyncio
import functools

import httpx
from core.logger import get_logger
logger = get_logger(__name__)

from settings import (
    GAMMA_API_BASE,
    GAMMA_API_KEY,
    GAMMA_NUM_CARDS,
    GAMMA_TEXT_MODE,
    GAMMA_LONG_INSTRUCTIONS,
    GAMMA_COMPACT_INSTRUCTIONS,
    GAMMA_POLL_TIMEOUT_SEC,
    GAMMA_POLL_INTERVAL_SEC,
)

# Python 3.8+ compatible to_thread polyfill
try:
    from asyncio import to_thread as asyncio_to_thread  # type: ignore
except Exception:  # ImportError on <3.9 or shadowing
    async def asyncio_to_thread(func, /, *args, **kwargs):  # type: ignore
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, functools.partial(func, *args, **kwargs))

# Selenium imports for web automation
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    logger.warning("Selenium not available - PDF extraction via web interface disabled")


class GammaError(Exception):
    pass


def _safe_filename(name: str, max_length: int = 50) -> str:
    """Создает безопасное имя файла из названия компании"""
    if not name:
        return "company"
    
    # Убираем недопустимые символы для имен файлов
    safe_name = re.sub(r'[<>:"/\\|?*]', '_', name)
    
    # Убираем лишние пробелы и заменяем на подчеркивания
    safe_name = re.sub(r'\s+', '_', safe_name.strip())
    
    # Ограничиваем длину
    if len(safe_name) > max_length:
        safe_name = safe_name[:max_length]
    
    # Убираем подчеркивания в начале и конце
    safe_name = safe_name.strip('_')
    
    return safe_name or "company"


def _headers() -> Dict[str, str]:
    return {
        "Content-Type": "application/json",
        "X-API-KEY": GAMMA_API_KEY or "",
    }


def create_generation(
    input_text: str,
    *,
    export_as: str = "pdf",
    format: str = "document",
    text_mode: str = None,
    language: str = "ru",
    theme_name: Optional[str] = None,
    card_split: str = "inputTextBreaks",
    num_cards: Optional[int] = None,
    additional_instructions: Optional[str] = None,
) -> str:
    """Create a generation and return generationId."""
    url = f"{GAMMA_API_BASE}/generations"
    # text_mode приоритет: аргумент -> настройка -> 'preserve'
    effective_text_mode = text_mode or GAMMA_TEXT_MODE or "preserve"
    # Enforce Gamma API limit: numCards <= 60
    if num_cards is not None and num_cards > 60:
        logger.warning("Gamma: numCards too large, capping to 60", requested=num_cards)
        num_cards = 60

    payload: Dict[str, Any] = {
        "inputText": input_text,
        "textMode": effective_text_mode,
        "format": format,
        "textOptions": {
            "language": language,
            "amount": "extensive",
            "tone": "analytical, formal",
        },
        "cardSplit": card_split,
        "exportAs": export_as,
    }
    if theme_name:
        payload["themeName"] = theme_name
    if num_cards is not None:
        payload["numCards"] = num_cards
    # Используем компактную инструкцию из настроек, игнорируя длинную
    compact = (additional_instructions or GAMMA_COMPACT_INSTRUCTIONS or "").strip()
    if compact:
        try:
            if len(compact) > 500:
                logger.warning("Gamma: compact instructions >500, truncating", length=len(compact))
                compact = compact[:500]
        except Exception:
            pass
        payload["additionalInstructions"] = compact

    logger.info(
        "Gamma: creating generation",
        has_theme=bool(theme_name),
        themeName=theme_name or None,
        numCards=num_cards,
        cardSplit=card_split,
        textMode=effective_text_mode,
        format=format,
        exportAs=export_as,
        language=language,
    )
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(url, headers=_headers(), json=payload)
    logger.info("Gamma: create response", status=resp.status_code)
    if resp.status_code == 401:
        logger.error("Gamma: 401 unauthorized — invalid API key?")
        raise GammaError("Unauthorized (401)")
    if resp.status_code == 403:
        logger.error("Gamma: 403 forbidden — access/plan issue")
        raise GammaError("Forbidden (403)")
    if resp.status_code == 429:
        logger.error("Gamma: 429 too many requests — rate limit")
        raise GammaError("Too Many Requests (429)")
    if resp.status_code >= 400:
        logger.error("Gamma: API error", status=resp.status_code, body=resp.text)
        raise GammaError(f"API error {resp.status_code}")

    data = resp.json()
    logger.info("Gamma: create response data", data_keys=list(data.keys()) if isinstance(data, dict) else "not_dict", full_response=data)
    generation_id = data.get("generationId") or data.get("id")
    if not generation_id:
        logger.error("Gamma: generationId missing in response", response_data=data)
        raise GammaError("generationId missing in response")
    logger.info("Gamma: generation created", generation_id=generation_id)
    return generation_id


def poll_generation(generation_id: str, *, interval_sec: float = None, timeout_sec: int = None, progress_callback=None) -> Dict[str, Any]:
    """Poll generation until completed or timeout; return JSON."""
    url = f"{GAMMA_API_BASE}/generations/{generation_id}"
    effective_interval = interval_sec if interval_sec is not None else float(GAMMA_POLL_INTERVAL_SEC)
    effective_timeout = timeout_sec if timeout_sec is not None else int(GAMMA_POLL_TIMEOUT_SEC)
    deadline = time.time() + effective_timeout
    start_time = time.time()
    with httpx.Client(timeout=20.0) as client:
        while time.time() < deadline:
            try:
                resp = client.get(url, headers=_headers())
            except httpx.ReadError as exc:
                logger.warning("Gamma: read error while polling, retrying", error=str(exc))
                time.sleep(effective_interval)
                continue
            if resp.status_code == 401:
                logger.error("Gamma: 401 unauthorized while polling")
                raise GammaError("Unauthorized (401)")
            if resp.status_code == 403:
                logger.error("Gamma: 403 forbidden while polling")
                raise GammaError("Forbidden (403)")
            if resp.status_code == 429:
                logger.warning("Gamma: 429 rate limit while polling; sleeping")
                time.sleep(interval_sec)
                continue
            if resp.status_code >= 400:
                logger.error("Gamma: error while polling", status=resp.status_code, body=resp.text)
                raise GammaError(f"API error {resp.status_code}")
            data = resp.json()
            status = data.get("status")
            elapsed = time.time() - start_time
            logger.info("Gamma: polling status", generation_id=generation_id, status=status, elapsed=elapsed)
            
            # Вызываем callback для обновления прогресса (только если это не асинхронная функция)
            if progress_callback:
                try:
                    # Проверяем, является ли callback асинхронным
                    if asyncio.iscoroutinefunction(progress_callback):
                        logger.debug("Gamma: skipping async progress_callback in sync context")
                    else:
                        progress_callback(status, elapsed, timeout_sec)
                except Exception as e:
                    logger.debug("Gamma: progress_callback failed", error=str(e))
            
            if status == "completed":
                logger.info("Gamma: generation completed", generation_id=generation_id, full_response=data)
                return data
            time.sleep(effective_interval)
    logger.warning("Gamma: polling timeout reached", timeout_sec=effective_timeout)
    raise GammaError("Polling timeout after 15 minutes")


def download_file(url: str, dest_path: str) -> str:
    """Download PDF file from Gamma API with proper redirect handling."""
    Path(os.path.dirname(dest_path) or ".").mkdir(parents=True, exist_ok=True)
    logger.info("Gamma: downloading", dest_path=dest_path)
    
    # Согласно документации, используем stream=True и follow_redirects=True
    with httpx.Client(timeout=120.0) as client:
        with client.stream("GET", url, follow_redirects=True) as resp:
            resp.raise_for_status()
            with open(dest_path, "wb") as f:
                for chunk in resp.iter_bytes():
                    f.write(chunk)
    
    file_size = os.path.getsize(dest_path)
    logger.info("Gamma: downloaded", dest_path=dest_path, file_size=file_size)
    return dest_path


def get_pdf_via_selenium(gamma_url: str, dest_path: str) -> str:
    """Get PDF from Gamma web interface using Selenium."""
    if not SELENIUM_AVAILABLE:
        raise GammaError("Selenium not available for web automation")
    
    logger.info("Gamma: starting Selenium PDF extraction", gamma_url=gamma_url)
    
    # Настройка Chrome
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Без GUI
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    driver = None
    try:
        # Установка ChromeDriver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Переход на страницу Gamma
        driver.get(gamma_url)
        logger.info("Gamma: page loaded", url=gamma_url)
        
        # Ждем загрузки страницы
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Ищем кнопку экспорта PDF
        try:
            # Сначала получим HTML страницы для анализа
            page_source = driver.page_source
            logger.info("Gamma: page source length", length=len(page_source))
            
            # Сохраним HTML для анализа (опционально)
            try:
                html_path = os.path.join(os.path.dirname(dest_path), f"gamma_page_{int(time.time())}.html")
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(page_source)
                logger.info("Gamma: HTML saved for analysis", html_path=html_path)
            except Exception as e:
                logger.warning("Gamma: failed to save HTML", error=str(e))
            
            # Найдем все кнопки на странице
            all_buttons = driver.find_elements(By.TAG_NAME, "button")
            logger.info("Gamma: found buttons on page", count=len(all_buttons))
            
            # Логируем информацию о кнопках
            for i, button in enumerate(all_buttons[:10]):  # Первые 10 кнопок
                try:
                    text = button.text
                    classes = button.get_attribute("class")
                    aria_label = button.get_attribute("aria-label")
                    data_testid = button.get_attribute("data-testid")
                    logger.info("Gamma: button info", 
                              index=i, text=text[:50], classes=classes, 
                              aria_label=aria_label, data_testid=data_testid)
                except:
                    pass
            
            # Попробуем найти кнопки по тексту
            text_selectors = [
                "//button[contains(text(), 'PDF')]",
                "//button[contains(text(), 'Export')]",
                "//button[contains(text(), 'Download')]",
                "//button[contains(text(), 'Скачать')]",
                "//button[contains(text(), 'Экспорт')]"
            ]
            
            export_button = None
            for xpath in text_selectors:
                try:
                    export_button = driver.find_element(By.XPATH, xpath)
                    logger.info("Gamma: found export button by text", xpath=xpath, text=export_button.text)
                    break
                except:
                    continue
            
            # Если не нашли по тексту, попробуем CSS селекторы
            if not export_button:
                export_selectors = [
                    "button[data-testid='export-pdf']",
                    "button[aria-label*='PDF']",
                    "button[aria-label*='Export']",
                    "button[aria-label*='Download']",
                    ".export-button",
                    ".pdf-button",
                    "[role='button']",
                    "button[type='button']"
                ]
                
                for selector in export_selectors:
                    try:
                        export_button = driver.find_element(By.CSS_SELECTOR, selector)
                        logger.info("Gamma: found export button", selector=selector)
                        break
                    except:
                        continue
            
            if export_button:
                # Кликаем на кнопку экспорта
                export_button.click()
                logger.info("Gamma: clicked export button")
                
                # Ждем загрузки PDF
                time.sleep(5)
                
                # Ищем ссылку на PDF или скачиваем напрямую
                try:
                    # Попробуем найти ссылку на PDF
                    pdf_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='.pdf']")
                    if pdf_links:
                        pdf_url = pdf_links[0].get_attribute("href")
                        logger.info("Gamma: found PDF link", pdf_url=pdf_url)
                        
                        # Скачиваем PDF
                        with httpx.Client(timeout=60.0) as client:
                            response = client.get(pdf_url)
                            response.raise_for_status()
                            
                            with open(dest_path, 'wb') as f:
                                f.write(response.content)
                        
                        file_size = os.path.getsize(dest_path)
                        logger.info("Gamma: PDF downloaded via Selenium", dest_path=dest_path, file_size=file_size)
                        return dest_path
                    else:
                        logger.warning("Gamma: no PDF links found")
                except Exception as e:
                    logger.error("Gamma: error downloading PDF", error=str(e))
            else:
                logger.warning("Gamma: no export button found")
                
                # Попробуем альтернативный подход - использовать JavaScript
                try:
                    logger.info("Gamma: trying JavaScript approach")
                    
                    # Попробуем найти элементы через JavaScript
                    js_script = """
                    var buttons = document.querySelectorAll('button');
                    var links = document.querySelectorAll('a');
                    var result = {
                        buttons: [],
                        links: []
                    };
                    
                    buttons.forEach(function(btn, i) {
                        if (i < 20) { // Первые 20 кнопок
                            result.buttons.push({
                                text: btn.textContent,
                                className: btn.className,
                                ariaLabel: btn.getAttribute('aria-label'),
                                dataTestId: btn.getAttribute('data-testid'),
                                id: btn.id
                            });
                        }
                    });
                    
                    links.forEach(function(link, i) {
                        if (i < 20) { // Первые 20 ссылок
                            result.links.push({
                                text: link.textContent,
                                href: link.href,
                                className: link.className
                            });
                        }
                    });
                    
                    return result;
                    """
                    
                    js_result = driver.execute_script(js_script)
                    logger.info("Gamma: JavaScript analysis", 
                              buttons_count=len(js_result.get('buttons', [])),
                              links_count=len(js_result.get('links', [])))
                    
                    # Логируем найденные элементы
                    for i, btn in enumerate(js_result.get('buttons', [])[:10]):
                        logger.info("Gamma: JS button", 
                                  index=i, text=btn.get('text', '')[:50], 
                                  className=btn.get('className', ''),
                                  ariaLabel=btn.get('ariaLabel', ''),
                                  dataTestId=btn.get('dataTestId', ''))
                    
                    for i, link in enumerate(js_result.get('links', [])[:10]):
                        logger.info("Gamma: JS link", 
                                  index=i, text=link.get('text', '')[:50], 
                                  href=link.get('href', '')[:100],
                                  className=link.get('className', ''))
                    
                except Exception as e:
                    logger.error("Gamma: JavaScript analysis failed", error=str(e))
                
        except Exception as e:
            logger.error("Gamma: error finding export button", error=str(e))
            
    except Exception as e:
        logger.error("Gamma: Selenium error", error=str(e))
        raise GammaError(f"Selenium PDF extraction failed: {e}")
    finally:
        if driver:
            driver.quit()
    
    raise GammaError("PDF extraction via Selenium failed")


def generate_pdf_from_report_text(
    report_text: str,
    *,
    out_dir: str = "reports",
    language: str = "ru",
    theme_name: Optional[str] = None,
    progress_callback=None,
    company_name: Optional[str] = None,
    company_inn: Optional[str] = None,
) -> Optional[str]:
    if not GAMMA_API_KEY:
        logger.warning("Gamma: no API key configured")
        return None
    # Разделяем секции визуальными разделителями для отдельных страниц в Gamma
    try:
        # Вставляем длинные инструкции в начало, затем визуальные разделители секций
        long_instr = (GAMMA_LONG_INSTRUCTIONS or "").strip()
        if long_instr:
            preface = long_instr + "\n\n---\n\n"
        else:
            preface = ""
        sectioned_text = preface + report_text.replace("\n\n", "\n\n---\n\n")
    except Exception:
        sectioned_text = report_text
    gen_id = create_generation(
        input_text=sectioned_text,
        export_as="pdf",
        format="document",
        text_mode="generate",
        language=language,
        theme_name=theme_name,
        card_split="inputTextBreaks",
        num_cards=GAMMA_NUM_CARDS if GAMMA_NUM_CARDS > 0 else None,
        additional_instructions=GAMMA_COMPACT_INSTRUCTIONS,
    )
    result = poll_generation(
        gen_id,
        interval_sec=GAMMA_POLL_INTERVAL_SEC,
        timeout_sec=GAMMA_POLL_TIMEOUT_SEC,
        progress_callback=progress_callback,
    )
    logger.info("Gamma: poll result", result_keys=list(result.keys()) if isinstance(result, dict) else "not_dict")
    
    # Формируем имя файла на основе названия компании и ИНН
    if company_name and company_inn:
        safe_name = _safe_filename(company_name)
        filename = f"{safe_name}_{company_inn}.pdf"
    else:
        filename = f"report_{gen_id}.pdf"
    
    # Согласно документации Gamma API, ищем PDF URL в правильных полях
    pdf_url = None
    
    # Согласно документации, ищем в следующих полях:
    # pdfUrl, fileUrl, exportUrl, urls.pdf, files.pdf
    pdf_url = (result.get("pdfUrl") or 
               result.get("fileUrl") or 
               result.get("exportUrl") or 
               result.get("urls", {}).get("pdf") or 
               result.get("files", {}).get("pdf"))
    
    logger.info("Gamma: PDF URL search", 
                pdfUrl=result.get("pdfUrl"),
                fileUrl=result.get("fileUrl"), 
                exportUrl=result.get("exportUrl"),
                urls_pdf=result.get("urls", {}).get("pdf"),
                files_pdf=result.get("files", {}).get("pdf"),
                found_pdf_url=pdf_url,
                full_result=result)
    
    # Вариант 2: gammaUrl (для редактирования) - попробуем разные варианты
    if not pdf_url:
        gamma_url = result.get("gammaUrl")
        logger.info("Gamma: no direct PDF URL found, trying gammaUrl", gamma_url=gamma_url)
        if gamma_url:
            # Попробуем разные варианты экспорта
            export_variants = [
                f"{gamma_url}?export=pdf",
                f"{gamma_url}?format=pdf", 
                f"{gamma_url}/export/pdf",
                f"{gamma_url}/pdf",
                gamma_url  # попробуем и без параметров
            ]
            logger.info("Gamma: trying export variants", variants=export_variants)
            
            for variant_url in export_variants:
                logger.info("Gamma: trying gammaUrl variant", pdf_url=variant_url)
                try:
                    # Проверим, доступен ли URL
                    logger.info("Gamma: checking URL accessibility", url=variant_url)
                    response = httpx.get(variant_url, timeout=30)
                    logger.info("Gamma: URL response", url=variant_url, status=response.status_code, content_type=response.headers.get("content-type"))
                    if response.status_code == 200:
                        logger.info("Gamma: PDF URL accessible", pdf_url=variant_url)
                        pdf_url = variant_url
                        break
                    else:
                        logger.warning("Gamma: PDF URL not accessible", status_code=response.status_code, pdf_url=variant_url)
                except Exception as e:
                    logger.warning("Gamma: error checking PDF URL", error=str(e), pdf_url=variant_url)
    
    # Вариант 3: прямой URL в результате
    if not pdf_url:
        pdf_url = result.get("pdfUrl") or result.get("downloadUrl") or result.get("url")
        logger.info("Gamma: direct PDF URL", pdf_url=pdf_url)
    
    # Вариант 4: попробуем использовать get-gamma-file-urls endpoint
    if not pdf_url:
        try:
            logger.info("Gamma: trying get-gamma-file-urls endpoint")
            files_url = f"{GAMMA_API_BASE}/files/{gen_id}"
            with httpx.Client(timeout=30.0) as client:
                files_resp = client.get(files_url, headers=_headers())
                logger.info("Gamma: files endpoint response", status=files_resp.status_code)
                if files_resp.status_code == 200:
                    files_data = files_resp.json()
                    logger.info("Gamma: files endpoint data", files_data_keys=list(files_data.keys()) if isinstance(files_data, dict) else "not_dict")
                    pdf_url = files_data.get("pdf") or files_data.get("PDF") or files_data.get("url")
                    if pdf_url:
                        logger.info("Gamma: PDF URL from files endpoint", pdf_url=pdf_url)
        except Exception as e:
            logger.warning("Gamma: files endpoint failed", error=str(e))
    
    # Вариант 5: попробуем другой endpoint для файлов
    if not pdf_url:
        try:
            logger.info("Gamma: trying alternative files endpoint")
            alt_files_url = f"{GAMMA_API_BASE}/generations/{gen_id}/files"
            with httpx.Client(timeout=30.0) as client:
                alt_resp = client.get(alt_files_url, headers=_headers())
                logger.info("Gamma: alt files endpoint response", status=alt_resp.status_code)
                if alt_resp.status_code == 200:
                    alt_data = alt_resp.json()
                    logger.info("Gamma: alt files endpoint data", alt_data_keys=list(alt_data.keys()) if isinstance(alt_data, dict) else "not_dict")
                    pdf_url = alt_data.get("pdf") or alt_data.get("PDF") or alt_data.get("url")
                    if pdf_url:
                        logger.info("Gamma: PDF URL from alt files endpoint", pdf_url=pdf_url)
        except Exception as e:
            logger.warning("Gamma: alt files endpoint failed", error=str(e))
    
    # Вариант 6: попробуем Selenium для получения PDF из веб-интерфейса
    if not pdf_url and SELENIUM_AVAILABLE:
        gamma_url = result.get("gammaUrl")
        if gamma_url:
            logger.info("Gamma: trying Selenium PDF extraction", gamma_url=gamma_url)
            try:
                Path(out_dir).mkdir(parents=True, exist_ok=True)
                dest = os.path.join(out_dir, filename)
                return get_pdf_via_selenium(gamma_url, dest)
            except Exception as e:
                logger.warning("Gamma: Selenium PDF extraction failed", error=str(e))
    
    if not pdf_url:
        gamma_url = result.get("gammaUrl")
        if gamma_url:
            logger.warning("Gamma: no PDF url found, returning edit link", gamma_url=gamma_url)
            return f"LINK:{gamma_url}"
        logger.warning("Gamma: no PDF url found in any format", result=result)
        return None
        
    logger.info("Gamma: PDF url found", pdf_url=pdf_url)
    logger.info("Gamma: starting PDF download", pdf_url=pdf_url)
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    dest = os.path.join(out_dir, filename)
    
    # Попробуем скачать PDF с обработкой истекших ссылок
    try:
        logger.info("Gamma: downloading PDF", pdf_url=pdf_url, dest=dest)
        result = download_file(pdf_url, dest)
        logger.info("Gamma: PDF download completed", result=result)
        return result
    except Exception as e:
        logger.warning("Gamma: PDF download failed, trying to get fresh URL", error=str(e))
        
        # Если ссылка истекла, попробуем получить новую
        try:
            logger.info("Gamma: getting fresh PDF URL")
            fresh_result = poll_generation(gen_id, timeout_sec=60)  # Короткий таймаут для быстрого получения
            
            # Ищем PDF URL в новом результате
            fresh_pdf_url = (fresh_result.get("pdfUrl") or 
                           fresh_result.get("fileUrl") or 
                           fresh_result.get("exportUrl") or 
                           fresh_result.get("urls", {}).get("pdf") or 
                           fresh_result.get("files", {}).get("pdf"))
            
            if fresh_pdf_url:
                logger.info("Gamma: fresh PDF URL found", pdf_url=fresh_pdf_url)
                return download_file(fresh_pdf_url, dest)
            else:
                logger.error("Gamma: no fresh PDF URL found")
                return None
                
        except Exception as fresh_error:
            logger.error("Gamma: failed to get fresh PDF URL", error=str(fresh_error))
            return None


def generate_pptx_from_report_text(
    report_text: str,
    *,
    out_dir: str = "reports",
    language: str = "ru",
    theme_name: Optional[str] = None,
    progress_callback=None,
    company_name: Optional[str] = None,
    company_inn: Optional[str] = None,
) -> Optional[str]:
    if not GAMMA_API_KEY:
        logger.warning("Gamma: no API key configured")
        return None
    # Разделяем секции визуальными разделителями для отдельных страниц в Gamma
    try:
        long_instr = (GAMMA_LONG_INSTRUCTIONS or "").strip()
        if long_instr:
            preface = long_instr + "\n\n---\n\n"
        else:
            preface = ""
        sectioned_text = preface + report_text.replace("\n\n", "\n\n---\n\n")
    except Exception:
        sectioned_text = report_text
    gen_id = create_generation(
        input_text=sectioned_text,
        export_as="pptx",
        format="document",
        text_mode="generate",
        language=language,
        theme_name=theme_name,
        card_split="inputTextBreaks",
        num_cards=GAMMA_NUM_CARDS if GAMMA_NUM_CARDS > 0 else None,
        additional_instructions=GAMMA_COMPACT_INSTRUCTIONS,
    )
    result = poll_generation(
        gen_id,
        interval_sec=GAMMA_POLL_INTERVAL_SEC,
        timeout_sec=GAMMA_POLL_TIMEOUT_SEC,
        progress_callback=progress_callback,
    )
    logger.info("Gamma: poll result", result_keys=list(result.keys()) if isinstance(result, dict) else "not_dict")

    # Имя файла
    if company_name and company_inn:
        safe_name = _safe_filename(company_name)
        filename = f"{safe_name}_{company_inn}.pptx"
    else:
        filename = f"report_{gen_id}.pptx"

    # Ищем PPTX URL
    pptx_url = (
        result.get("pptxUrl") or
        result.get("powerpointUrl") or
        result.get("fileUrl") or
        result.get("exportUrl") or
        result.get("urls", {}).get("pptx") or
        result.get("files", {}).get("pptx") or
        result.get("urls", {}).get("powerpoint") or
        result.get("files", {}).get("powerpoint")
    )
    logger.info(
        "Gamma: PPTX URL search",
        pptxUrl=result.get("pptxUrl"),
        powerPointUrl=result.get("powerpointUrl"),
        fileUrl=result.get("fileUrl"),
        exportUrl=result.get("exportUrl"),
        urls=result.get("urls", {}),
        files=result.get("files", {}),
        found_url=pptx_url,
    )

    # Попытка через gammaUrl
    if not pptx_url:
        gamma_url = result.get("gammaUrl")
        logger.info("Gamma: no direct PPTX URL found, trying gammaUrl", gamma_url=gamma_url)
        if gamma_url:
            export_variants = [
                f"{gamma_url}?export=pptx",
                f"{gamma_url}?format=pptx",
                f"{gamma_url}/export/pptx",
                f"{gamma_url}/pptx",
                gamma_url,
            ]
            logger.info("Gamma: trying export variants", variants=export_variants)
            for variant_url in export_variants:
                try:
                    response = httpx.get(variant_url, timeout=30)
                    logger.info("Gamma: URL response", url=variant_url, status=response.status_code, content_type=response.headers.get("content-type"))
                    if response.status_code == 200:
                        pptx_url = variant_url
                        break
                except Exception as e:
                    logger.warning("Gamma: error checking PPTX URL", error=str(e), url=variant_url)

    # files endpoints
    if not pptx_url:
        try:
            files_url = f"{GAMMA_API_BASE}/files/{gen_id}"
            with httpx.Client(timeout=30.0) as client:
                files_resp = client.get(files_url, headers=_headers())
            logger.info("Gamma: files endpoint response", status=files_resp.status_code)
            if files_resp.status_code == 200:
                files_data = files_resp.json()
                logger.info("Gamma: files endpoint data", files_data_keys=list(files_data.keys()) if isinstance(files_data, dict) else "not_dict")
                pptx_url = files_data.get("pptx") or files_data.get("PPTX") or files_data.get("url")
        except Exception as e:
            logger.warning("Gamma: files endpoint failed", error=str(e))

    if not pptx_url:
        try:
            alt_files_url = f"{GAMMA_API_BASE}/generations/{gen_id}/files"
            with httpx.Client(timeout=30.0) as client:
                alt_resp = client.get(alt_files_url, headers=_headers())
            logger.info("Gamma: alt files endpoint response", status=alt_resp.status_code)
            if alt_resp.status_code == 200:
                alt_data = alt_resp.json()
                logger.info("Gamma: alt files endpoint data", alt_data_keys=list(alt_data.keys()) if isinstance(alt_data, dict) else "not_dict")
                pptx_url = alt_data.get("pptx") or alt_data.get("PPTX") or alt_data.get("url")
        except Exception as e:
            logger.warning("Gamma: alt files endpoint failed", error=str(e))

    if not pptx_url:
        gamma_url = result.get("gammaUrl")
        if gamma_url:
            logger.warning("Gamma: no PPTX url found, returning edit link", gamma_url=gamma_url)
            return f"LINK:{gamma_url}"
        logger.warning("Gamma: no PPTX url found in any format", result=result)
        return None

    # Скачиваем
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    dest = os.path.join(out_dir, filename)
    try:
        logger.info("Gamma: downloading PPTX", url=pptx_url, dest=dest)
        result_path = download_file(pptx_url, dest)
        logger.info("Gamma: PPTX download completed", result=result_path)
        return result_path
    except Exception as e:
        logger.warning("Gamma: PPTX download failed, trying to get fresh URL", error=str(e))
        try:
            fresh_result = poll_generation(gen_id, timeout_sec=60)
            fresh_url = (
                fresh_result.get("pptxUrl") or fresh_result.get("powerpointUrl") or
                fresh_result.get("fileUrl") or fresh_result.get("exportUrl") or
                fresh_result.get("urls", {}).get("pptx") or fresh_result.get("files", {}).get("pptx")
            )
            if fresh_url:
                logger.info("Gamma: fresh PPTX URL found", url=fresh_url)
                return download_file(fresh_url, dest)
            else:
                logger.error("Gamma: no fresh PPTX URL found")
                return None
        except Exception as fresh_error:
            logger.error("Gamma: failed to get fresh PPTX URL", error=str(fresh_error))
            return None
