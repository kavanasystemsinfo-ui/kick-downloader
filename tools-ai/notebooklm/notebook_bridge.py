#!/usr/bin/env python3
"""
Universal NotebookLM CDP bridge.

Local automation layer for an AI-assisted TDD workflow. It connects to an
already running Chrome instance on localhost:9222, reuses or searches for a
permanent NotebookLM notebook, can add temporary external sources, triggers
chat/artifacts, extracts visible text to Markdown, and supports teardown of
temporary sources.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from playwright.sync_api import Locator, Page, TimeoutError as PlaywrightTimeoutError, sync_playwright

CDP_DEFAULT = "http://localhost:9222"
NOTEBOOKLM_DEFAULT = "https://notebooklm.google.com/"
ACTION_TIMEOUT_MS = 4000
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "docs" / "ai" / "outputs"
LOADING_LABELS = ["processing", "loading", "cargando", "añadiendo", "agregando", "adding source"]
LOADING_SELECTORS = [
    "[role='progressbar']",
    "[aria-busy='true']",
    "[data-progress]",
    "[data-loading='true']",
    ".mat-progress-bar",
    "mat-progress-bar",
]
RESEARCH_MODES = {"fast", "deep"}
MANUAL_CLEANUP_STATUSES = {
    "not_found_already_clean_or_text_truncated",
    "menu_button_not_found",
    "menu_click_failed",
    "remove_action_not_found",
    "removed_but_text_still_visible_manual_cleanup_required",
}


def requires_manual_cleanup(step: dict[str, Any]) -> bool:
    return step.get("status") in MANUAL_CLEANUP_STATUSES


def research_directive(research_mode: str) -> str:
    if research_mode == "deep":
        return (
            "Research mode: Deep Research. Explore multiple sources and synthesize "
            "a deep report; use only when explicitly requested."
        )

    return (
        "Research mode: Fast Research by default. Prefer official documentation, "
        "first-class technical sources, and concrete answers. Avoid Deep Research "
        "to preserve daily quota."
    )


def build_chat_prompt(args: argparse.Namespace) -> str:
    if not args.chat_prompt:
        return ""

    return f"{args.chat_prompt}\n\n{research_directive(args.research_mode)}"


def slugify(value: str, max_length: int = 80) -> str:
    slug = re.sub(r"[^a-zA-Z0-9À-ÿ_-]+", "-", value.strip().lower()).strip("-")
    return slug[:max_length] or "notebooklm"


def default_output_dir() -> Path:
    override = os.environ.get("NOTEBOOKLM_OUTPUT_DIR")
    if override:
        return Path(override).expanduser()

    return DEFAULT_OUTPUT_DIR


def parse_args() -> argparse.Namespace:
    default_cdp_endpoint = os.environ.get("NOTEBOOKLM_CDP_ENDPOINT", CDP_DEFAULT)
    default_notebook_url = os.environ.get("NOTEBOOKLM_NOTEBOOK_URL", "")
    default_notebook_title = os.environ.get("NOTEBOOKLM_NOTEBOOK_TITLE", "Project Notebook")
    default_session_file = os.environ.get(
        "NOTEBOOKLM_SESSION_FILE",
        str(default_output_dir() / "notebooklm_session_latest.json"),
    )

    parser = argparse.ArgumentParser(
        description="Orchestrate NotebookLM through a local Chrome DevTools Protocol endpoint."
    )
    parser.add_argument("--cdp-endpoint", default=default_cdp_endpoint, help="Chrome CDP endpoint, usually http://localhost:9222")
    parser.add_argument("--notebook-url", default=default_notebook_url, help="Direct URL of the permanent NotebookLM notebook")
    parser.add_argument("--notebook-title", default=default_notebook_title, help="Notebook title to search when --notebook-url is not set")
    parser.add_argument("--add-source-url", action="append", default=[], help="Temporary external URL to add to the notebook. Repeatable.")
    parser.add_argument("--source-mode", choices=["website", "pasted"], default="website", help="Ingestion mode: website or pasted. Default: website.")
    parser.add_argument("--research-mode", choices=sorted(RESEARCH_MODES), default="fast", help="NotebookLM research mode. Use deep only for explicit deep research.")
    parser.add_argument("--chat-prompt", help="Prompt to send to the NotebookLM chat")
    parser.add_argument(
        "--audio-prompt",
        default="Generate an audio guide focused on the main concepts, trade-offs, and practical next steps for this project.",
        help="Instruction used to customize the NotebookLM audio guide.",
    )
    parser.add_argument(
        "--artifact",
        action="append",
        choices=["chat", "flashcards", "quiz", "audio", "all"],
        help="Artifact to execute. Repeatable. Default: all.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(default_output_dir()),
        help="Markdown output directory. Default: docs/ai/outputs inside the template root.",
    )
    parser.add_argument("--session-file", default=default_session_file, help="JSON session manifest path")
    parser.add_argument("--navigation-timeout-ms", type=int, default=ACTION_TIMEOUT_MS, help="Strict UI action timeout in milliseconds. Default: 4000.")
    parser.add_argument("--notebook-wait-ms", type=int, default=3000, help="Pause after opening NotebookLM or the notebook")
    parser.add_argument("--artifact-wait-ms", type=int, default=12000, help="Observation pause after requesting Flashcards or Quiz")
    parser.add_argument("--audio-wait-ms", type=int, default=15000, help="Observation pause after requesting audio")
    parser.add_argument("--source-wait-ms", type=int, default=12000, help="Observation pause after adding a temporary source")
    parser.add_argument("--clean-temp-sources", action="store_true", help="Clean registered temporary sources and skip new extraction")
    parser.add_argument("--cleanup-urls", action="append", default=[], help="Specific temporary URL to clean. Repeatable.")
    return parser.parse_args()


def assert_local_cdp(endpoint: str) -> None:
    parsed = urlparse(endpoint)
    if parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("For safety, the CDP endpoint must be localhost or 127.0.0.1.")


def validate_external_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def derive_notebook_name(notebook_url: str | None, notebook_title: str) -> str:
    if notebook_title:
        return notebook_title
    if notebook_url:
        parsed = urlparse(notebook_url)
        return Path(parsed.path).name.strip("/") or "notebooklm"
    return "notebooklm"


def goto_url(page: Page, url: str, timeout_ms: int) -> None:
    if not urlparse(url).scheme:
        url = f"https://{url}"
    page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
    page.wait_for_load_state("domcontentloaded", timeout=timeout_ms)


def click_matching_title(page: Page, title: str, timeout_ms: int) -> bool:
    pattern = re.compile(re.escape(title), re.IGNORECASE)
    candidates = [
        page.get_by_role("link", name=pattern),
        page.get_by_role("button", name=pattern),
        page.get_by_text(pattern),
    ]
    for locator in candidates:
        try:
            if locator.count() > 0:
                locator.first.click(timeout=timeout_ms)
                return True
        except PlaywrightTimeoutError:
            continue
        except Exception:
            continue
    return False


def search_notebook(page: Page, title: str, timeout_ms: int) -> None:
    search = page.get_by_placeholder(re.compile(r"search|buscar|notebook", re.IGNORECASE)).first
    try:
        if search.count() > 0:
            search.fill(title, timeout=timeout_ms)
            page.keyboard.press("Enter", timeout=timeout_ms)
            page.wait_for_timeout(timeout_ms)
            return
    except PlaywrightTimeoutError:
        pass
    except Exception:
        pass
    print(f"[WARN] No search field found for '{title}'. Continuing from the current page.")


def open_permanent_notebook(page: Page, notebook_url: str | None, notebook_title: str, navigation_timeout_ms: int, notebook_wait_ms: int) -> dict[str, Any]:
    if notebook_url:
        goto_url(page, notebook_url, navigation_timeout_ms)
        page.wait_for_timeout(notebook_wait_ms)
        return {"notebook_opened": "direct_url", "url": notebook_url}

    print("[WARN] --notebook-url not provided. Falling back to --notebook-title.")
    goto_url(page, NOTEBOOKLM_DEFAULT, navigation_timeout_ms)
    page.wait_for_timeout(notebook_wait_ms)

    if notebook_title and not click_matching_title(page, notebook_title, navigation_timeout_ms):
        search_notebook(page, notebook_title, navigation_timeout_ms)
        click_matching_title(page, notebook_title, navigation_timeout_ms)

    page.wait_for_timeout(notebook_wait_ms)
    return {"notebook_opened": "title_fallback", "title": notebook_title}


def click_semantic(page: Page, labels: list[str], timeout_ms: int) -> bool:
    for label in labels:
        pattern = re.compile(re.escape(label), re.IGNORECASE)
        candidates = [
            page.get_by_role("button", name=pattern),
            page.get_by_role("link", name=pattern),
            page.get_by_role("menuitem", name=pattern),
            page.get_by_text(pattern),
        ]
        for locator in candidates:
            try:
                if locator.count() > 0:
                    locator.first.click(timeout=timeout_ms)
                    return True
            except PlaywrightTimeoutError:
                continue
            except Exception:
                continue
    return False


def click_semantic_in_parent(parent: Locator, labels: list[str], timeout_ms: int) -> bool:
    for label in labels:
        pattern = re.compile(re.escape(label), re.IGNORECASE)
        candidates = [
            parent.get_by_role("button", name=pattern),
            parent.get_by_role("link", name=pattern),
            parent.get_by_role("menuitem", name=pattern),
            parent.get_by_text(pattern),
        ]
        for locator in candidates:
            try:
                if locator.count() > 0:
                    locator.first.click(timeout=timeout_ms)
                    return True
            except PlaywrightTimeoutError:
                continue
            except Exception:
                continue
    return False


def has_visible_text(page: Page, text: str, timeout_ms: int) -> bool:
    locator = page.get_by_text(re.compile(re.escape(text), re.IGNORECASE)).first
    try:
        return locator.is_visible(timeout=timeout_ms)
    except Exception:
        return False


def has_loading_text(page: Page) -> bool:
    for label in LOADING_LABELS:
        if has_visible_text(page, label, 500):
            return True
    return False


def has_loading_indicator(page: Page, timeout_ms: int = 500) -> bool:
    if has_loading_text(page):
        return True

    for selector in LOADING_SELECTORS:
        try:
            if page.locator(selector).first.is_visible(timeout=timeout_ms):
                return True
        except Exception:
            continue
    return False


def wait_for_processing_to_finish(page: Page, timeout_ms: int) -> bool:
    end = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < end:
        if not has_loading_indicator(page):
            return True
        time.sleep(0.5)
    return not has_loading_indicator(page)


def wait_until_text_absent(page: Page, text: str, timeout_ms: int) -> bool:
    end = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < end:
        if not has_visible_text(page, text, 500):
            return True
        time.sleep(0.5)
    return not has_visible_text(page, text, 500)


def dispatch_input_event(locator: Locator, timeout_ms: int) -> None:
    try:
        locator.evaluate(
            "(el) => {"
            "el.dispatchEvent(new InputEvent('input', {bubbles: true}));"
            "el.dispatchEvent(new Event('change', {bubbles: true}));"
            "}",
            timeout=timeout_ms,
        )
    except Exception:
        pass


def fill_any_textbox(page: Page, text: str, timeout_ms: int, prefer_type: bool = False) -> bool:
    textboxes = list(page.get_by_role("textbox").all()) + list(page.locator("[contenteditable='true']").all())
    for textbox in textboxes:
        try:
            if prefer_type:
                textbox.press("Control+A", timeout=timeout_ms)
                textbox.press("Backspace", timeout=timeout_ms)
                textbox.type(text, delay=0, timeout=timeout_ms)
            else:
                textbox.fill(text, timeout=timeout_ms)
            dispatch_input_event(textbox, timeout_ms)
            return True
        except PlaywrightTimeoutError:
            continue
        except Exception:
            continue
    return False


def open_study_interface(page: Page, timeout_ms: int) -> list[dict[str, str]]:
    opened = click_semantic(
        page,
        ["Study guide", "Study Guide", "Study", "Estudiar", "Guia de estudio", "Guía de estudio"],
        timeout_ms,
    )
    return [{"artifact": "study_guide", "status": "opened" if opened else "not_found_continue"}]


def request_flashcards(page: Page, timeout_ms: int, wait_ms: int) -> list[dict[str, str]]:
    requested = click_semantic(
        page,
        ["Flashcards", "Flash cards", "Tarjetas", "Tarjetas didacticas", "Tarjetas didácticas"],
        timeout_ms,
    )
    if requested:
        page.wait_for_timeout(wait_ms)
    return [{"artifact": "flashcards", "status": "requested" if requested else "not_found_continue"}]


def request_quiz(page: Page, timeout_ms: int, wait_ms: int) -> list[dict[str, str]]:
    requested = click_semantic(
        page,
        ["Quiz", "Quizzes", "Question", "Questions", "Cuestionario", "Cuestionarios", "Preguntas"],
        timeout_ms,
    )
    if requested:
        page.wait_for_timeout(wait_ms)
    return [{"artifact": "quiz", "status": "requested" if requested else "not_found_continue"}]


def fill_audio_prompt(page: Page, prompt: str, timeout_ms: int) -> bool:
    textboxes = list(page.get_by_role("textbox").all()) + list(page.locator("[contenteditable='true']").all())
    for textbox in textboxes:
        try:
            textbox.fill(prompt, timeout=timeout_ms)
            try:
                textbox.press("Control+Enter", timeout=timeout_ms)
            except Exception:
                pass
            return True
        except PlaywrightTimeoutError:
            continue
        except Exception:
            continue
    return False


def customize_audio(page: Page, prompt: str, timeout_ms: int, wait_ms: int) -> list[dict[str, str]]:
    customized = click_semantic(
        page,
        [
            "Customize",
            "Customize guide",
            "Customize audio",
            "Audio Overview",
            "Audio guide",
            "Personalizar",
            "Personalizar guia",
            "Personalizar guía",
            "Guia de audio",
            "Guía de audio",
        ],
        timeout_ms,
    )
    if not customized:
        return [{"artifact": "audio", "status": "customize_button_not_found_continue"}]

    filled = fill_audio_prompt(page, prompt, timeout_ms)
    if filled:
        click_semantic(
            page,
            ["Generate", "Save", "Apply", "Customize", "Generar", "Guardar", "Aplicar", "Personalizar"],
            timeout_ms,
        )
        page.wait_for_timeout(wait_ms)
        return [{"artifact": "audio", "status": "prompt_submitted"}]
    return [{"artifact": "audio", "status": "prompt_field_not_found_continue"}]


def open_chat_interface(page: Page, timeout_ms: int) -> bool:
    return click_semantic(
        page,
        ["Chat", "Ask", "Ask a question", "Preguntar", "Chatear", "Consulta"],
        timeout_ms,
    )


def send_chat_prompt(page: Page, prompt: str, timeout_ms: int, wait_ms: int) -> list[dict[str, str]]:
    opened = open_chat_interface(page, timeout_ms)
    filled = fill_any_textbox(page, prompt, timeout_ms)
    if not filled:
        return [{"artifact": "chat", "status": "composer_not_found_continue"}]

    try:
        page.keyboard.press("Enter", timeout=timeout_ms)
    except Exception:
        click_semantic(page, ["Send", "Enviar"], timeout_ms)
    page.wait_for_timeout(wait_ms)
    return [{"artifact": "chat", "status": "prompt_submitted", "chat_opened": str(opened)}]


def add_external_source(page: Page, url: str, mode: str, timeout_ms: int, wait_ms: int) -> dict[str, Any]:
    if not validate_external_url(url):
        return {"url": url, "mode": mode, "status": "invalid_url"}

    opened = click_semantic(
        page,
        ["Add source", "Add sources", "Añadir fuente", "Agregar fuente", "Fuentes", "Sources"],
        timeout_ms,
    )
    if not opened:
        return {"url": url, "mode": mode, "status": "add_source_button_not_found_continue"}

    if mode == "website":
        source_option_opened = click_semantic(
            page,
            ["Website", "Web link", "Link", "URL", "Enlace web", "Añadir enlace"],
            timeout_ms,
        )
    else:
        source_option_opened = click_semantic(
            page,
            ["Pasted text", "Paste text", "Texto copiado", "Pegar texto", "Pasted"],
            timeout_ms,
        )

    filled = fill_any_textbox(page, url, timeout_ms, prefer_type=mode == "pasted")
    if filled:
        try:
            page.keyboard.press("Enter", timeout=timeout_ms)
        except Exception:
            pass
        click_semantic(
            page,
            ["Add", "Confirm", "Continue", "Añadir", "Agregar", "Confirmar", "Continuar"],
            timeout_ms,
        )
        wait_for_processing_to_finish(page, wait_ms)
        return {
            "url": url,
            "mode": mode,
            "status": "added",
            "source_option_opened": source_option_opened,
            "processing_wait_ms": wait_ms,
        }

    return {
        "url": url,
        "mode": mode,
        "status": "source_field_not_found_continue",
        "source_option_opened": source_option_opened,
        "processing_wait_ms": wait_ms,
    }


def run_requested_artifacts(page: Page, args: argparse.Namespace) -> list[dict[str, Any]]:
    selected = args.artifact or ["all"]
    steps: list[dict[str, Any]] = []
    chat_prompt = build_chat_prompt(args)

    if "all" in selected or "chat" in selected:
        if chat_prompt:
            steps.extend(send_chat_prompt(page, chat_prompt, args.navigation_timeout_ms, args.artifact_wait_ms))
        else:
            steps.append({"artifact": "chat", "status": "skipped_no_chat_prompt"})

    if "all" in selected or "flashcards" in selected:
        steps.extend(open_study_interface(page, args.navigation_timeout_ms))
        steps.extend(request_flashcards(page, args.navigation_timeout_ms, args.artifact_wait_ms))

    if "all" in selected or "quiz" in selected:
        steps.extend(request_quiz(page, args.navigation_timeout_ms, args.artifact_wait_ms))

    if "all" in selected or "audio" in selected:
        steps.extend(customize_audio(page, args.audio_prompt, args.navigation_timeout_ms, args.audio_wait_ms))

    return steps


def extract_markdown(page: Page, notebook_name: str, output_dir: Path, session_state: dict[str, Any], timeout_ms: int) -> tuple[Path, int]:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    generated_at = datetime.now().isoformat(timespec="seconds")
    filename = f"{timestamp}_{slugify(notebook_name)}.md"
    output_path = output_dir / filename

    try:
        captured_text = page.locator("body").inner_text(timeout=timeout_ms)
    except Exception:
        captured_text = page.content()

    if not captured_text.strip():
        raise RuntimeError("Could not extract visible text from the NotebookLM page.")

    temporary_sources = session_state.get("temporary_sources", [])
    markdown = f"""---
title: "NotebookLM extraction: {notebook_name}"
generated_at: "{generated_at}"
source: "tools-ai/notebooklm/notebook_bridge.py"
notebooklm_url: "{session_state.get('notebook_url') or NOTEBOOKLM_DEFAULT}"
research_mode: "{session_state.get('research_mode') or 'fast'}"
temporary_sources: {json.dumps(temporary_sources, ensure_ascii=False)}
human_in_the_loop: true
requires_confirmation_before_code_changes: true
---

# NotebookLM extraction: {notebook_name}

> Local extraction from an automated NotebookLM session. Review before using as source of truth.
> The AI assistant must present a concise plan and wait for explicit developer confirmation before modifying code.

## Captured screen text

{captured_text}
"""
    output_path.write_text(markdown, encoding="utf-8")
    return output_path, len(captured_text)


def write_session_manifest(session_file: Path, state: dict[str, Any]) -> None:
    session_file.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = datetime.now().isoformat(timespec="seconds")
    session_file.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def load_session_manifest(session_file: Path) -> dict[str, Any]:
    if not session_file.exists():
        return {}
    try:
        return json.loads(session_file.read_text(encoding="utf-8"))
    except Exception:
        return {}


def cleanup_urls_from_args_or_manifest(args: argparse.Namespace) -> list[str]:
    if args.cleanup_urls:
        return args.cleanup_urls
    manifest = load_session_manifest(Path(args.session_file))
    urls: list[str] = []
    for source in manifest.get("temporary_sources", []):
        if isinstance(source, dict) and source.get("status") == "added" and source.get("url"):
            urls.append(source["url"])
        elif isinstance(source, str):
            urls.append(source)
    return urls


def source_text_variants(url: str) -> list[str]:
    parsed = urlparse(url)
    variants = [url.rstrip("/")]
    if parsed.netloc:
        variants.append(parsed.netloc)
    if parsed.path and parsed.path != "/":
        variants.append(Path(parsed.path).name)
    return variants


def find_source_locator(page: Page, url: str) -> Locator | None:
    for text in source_text_variants(url):
        locator = page.get_by_text(re.compile(re.escape(text), re.IGNORECASE)).first
        try:
            if locator.count() > 0 and locator.is_visible(timeout=500):
                return locator
        except Exception:
            continue
    return None


def find_menu_button(source: Locator, timeout_ms: int) -> Locator | None:
    for selector in ["xpath=..", "xpath=../..", "xpath=../../.."]:
        parent = source.locator(selector)
        try:
            buttons = parent.locator("button, [role='button']").all()
        except Exception:
            continue
        for button in buttons:
            try:
                aria = button.get_attribute("aria-label", timeout=timeout_ms) or ""
                title = button.get_attribute("title", timeout=timeout_ms) or ""
                text = button.text_content(timeout=timeout_ms) or ""
            except Exception:
                continue
            haystack = f"{aria} {title} {text}"
            if re.search(r"more|menu|options|mas|más|opciones|three|tres|more_vert", haystack, re.IGNORECASE):
                return button
    return None


def clean_one_temporary_source(page: Page, url: str, timeout_ms: int, wait_ms: int) -> dict[str, Any]:
    source = find_source_locator(page, url)
    if source is None:
        return {"url": url, "status": "not_found_already_clean_or_text_truncated"}

    try:
        source.scroll_into_view_if_needed(timeout=timeout_ms)
    except Exception:
        pass

    menu = find_menu_button(source, timeout_ms)
    if menu is None:
        return {"url": url, "status": "menu_button_not_found"}

    try:
        menu.click(timeout=timeout_ms)
    except Exception as exc:
        return {"url": url, "status": "menu_click_failed", "error": str(exc)}

    removed = click_semantic_in_parent(
        source.locator("xpath=../.."),
        ["Remove", "Delete", "Eliminar", "Quitar", "Borrar"],
        timeout_ms,
    )
    if not removed:
        removed = click_semantic(
            page,
            ["Remove", "Delete", "Eliminar", "Quitar", "Borrar"],
            timeout_ms,
        )

    if removed:
        click_semantic(
            page,
            ["Remove", "Delete", "Confirm", "Eliminar", "Quitar", "Borrar", "Confirmar", "Aceptar", "OK"],
            timeout_ms,
        )
        absent = wait_until_text_absent(page, url, wait_ms)
        return {
            "url": url,
            "status": "removed" if absent else "removed_but_text_still_visible_manual_cleanup_required",
        }

    return {"url": url, "status": "remove_action_not_found"}


def open_sources_panel(page: Page, timeout_ms: int) -> bool:
    return click_semantic(
        page,
        ["Sources", "Source panel", "Fuentes", "Panel de fuentes"],
        timeout_ms,
    )


def clean_temporary_sources(page: Page, args: argparse.Namespace) -> list[dict[str, Any]]:
    opened = open_sources_panel(page, args.navigation_timeout_ms)
    steps: list[dict[str, Any]] = [{"artifact": "sources_panel", "status": "opened" if opened else "not_found_continue"}]
    urls = cleanup_urls_from_args_or_manifest(args)
    if not urls:
        steps.append({"artifact": "sources_cleanup", "status": "skipped_no_temporary_sources"})
        return steps

    for url in urls:
        if not validate_external_url(url):
            steps.append({"url": url, "status": "skipped_invalid_url"})
            continue
        steps.append(clean_one_temporary_source(page, url, args.navigation_timeout_ms, args.source_wait_ms))
        page.wait_for_timeout(500)
    return steps


def cleanup_confirmation_status(steps: list[dict[str, Any]]) -> str:
    if any(requires_manual_cleanup(step) for step in steps):
        return "manual_cleanup_required"
    return "cleaned"


def build_initial_session_state(args: argparse.Namespace, notebook_name: str) -> dict[str, Any]:
    return {
        "notebook_url": args.notebook_url,
        "notebook_title": args.notebook_title,
        "notebook_name": notebook_name,
        "research_mode": args.research_mode,
        "temporary_sources": [],
        "successful_temporary_sources": [],
        "output_path": None,
        "confirmation_status": "pending",
        "human_in_the_loop": True,
        "requires_confirmation_before_code_changes": True,
    }


def main() -> int:
    args = parse_args()
    assert_local_cdp(args.cdp_endpoint)
    output_dir = Path(args.output_dir)
    session_file = Path(args.session_file)
    notebook_name = derive_notebook_name(args.notebook_url, args.notebook_title)
    session_state = build_initial_session_state(args, notebook_name)

    with sync_playwright() as playwright:
        browser = playwright.chromium.connect_over_cdp(args.cdp_endpoint)
        try:
            context = browser.contexts[0] if browser.contexts else browser.new_context()
            page = context.pages[0] if context.pages else context.new_page()
            page.set_default_timeout(args.navigation_timeout_ms)

            open_result = open_permanent_notebook(
                page,
                args.notebook_url,
                args.notebook_title,
                args.navigation_timeout_ms,
                args.notebook_wait_ms,
            )
            session_state["open_result"] = open_result

            if args.clean_temp_sources:
                steps = clean_temporary_sources(page, args)
                session_state["steps"] = steps
                session_state["confirmation_status"] = cleanup_confirmation_status(steps)
                write_session_manifest(session_file, session_state)
                print(
                    json.dumps(
                        {
                            "status": "ok",
                            "action": "clean_temp_sources",
                            "steps": steps,
                            "manifest": str(session_file),
                            "research_mode": session_state.get("research_mode", "fast"),
                            "human_in_the_loop": {
                                "requires_confirmation_before_code_changes": True,
                                "confirmation_command": "proceed",
                            },
                            "cleanup_status": session_state["confirmation_status"],
                            "manual_cleanup_required": session_state["confirmation_status"] == "manual_cleanup_required",
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                )
                return 0

            for url in args.add_source_url:
                step = add_external_source(page, url, args.source_mode, args.navigation_timeout_ms, args.source_wait_ms)
                session_state["temporary_sources"].append(step)
                if step.get("status") == "added":
                    session_state["successful_temporary_sources"].append(url)

            steps = run_requested_artifacts(page, args)
            session_state["steps"] = steps

            output_path, char_count = extract_markdown(page, notebook_name, output_dir, session_state, args.navigation_timeout_ms)
            session_state["output_path"] = str(output_path)
            session_state["characters"] = char_count
            session_state["confirmation_status"] = "pending_developer_confirmation"
            write_session_manifest(session_file, session_state)

            print(
                json.dumps(
                    {
                        "status": "ok",
                        "action": "extract",
                        "output": str(output_path),
                        "characters": char_count,
                        "steps": steps,
                        "temporary_sources": session_state["temporary_sources"],
                        "manifest": str(session_file),
                        "research_mode": session_state.get("research_mode", "fast"),
                        "human_in_the_loop": {
                            "requires_confirmation_before_code_changes": True,
                            "confirmation_command": "proceed",
                            "next_action": "present_plan_and_wait_for_explicit_confirmation",
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0
        finally:
            browser.close()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
