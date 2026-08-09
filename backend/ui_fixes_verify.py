"""
One-off verification script for the UI/UX fixes against the local
wrangler pages dev server (http://127.0.0.1:8790). Checks:
1. No horizontal scroll at 3 viewport sizes across 3 screens.
2. Realm card shows its name once, not twice.
3. Answer buttons are styled (not native).
4. Focus trap: Tab stays inside quiz modal; Escape closes it.
5. Persistent nav bar with realm name visible in combat.
6. Math notation renders via KaTeX.
"""
from playwright.sync_api import sync_playwright
import os

BASE_URL = "http://127.0.0.1:8790"
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pw_screenshots", "ui_fixes")
os.makedirs(OUT_DIR, exist_ok=True)

VIEWPORTS = [
    ("mobile", 390, 844),
    ("tablet", 768, 1024),
    ("desktop", 1920, 1080),
]


def has_horizontal_scroll(page):
    return page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")


def main():
    console_errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for name, w, h in VIEWPORTS:
            print(f"\n=== Viewport: {name} ({w}x{h}) ===")
            page = browser.new_page(viewport={"width": w, "height": h})
            page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
            page.goto(BASE_URL)
            page.wait_for_selector("#deploy-btn")
            print("main-menu horizontal scroll:", has_horizontal_scroll(page))
            page.screenshot(path=f"{OUT_DIR}/{name}_01_main_menu.png")

            page.click("#deploy-btn")
            page.wait_for_selector(".syllabus-card")
            print("syllabus-screen horizontal scroll:", has_horizontal_scroll(page))
            page.screenshot(path=f"{OUT_DIR}/{name}_02_syllabus_select.png")

            # Check #2: realm card name appears once, not twice
            first_card = page.query_selector(".syllabus-card")
            card_text = first_card.inner_text()
            h3_text = first_card.query_selector("h3").inner_text()
            occurrences = card_text.count(h3_text)
            print(f"realm name '{h3_text}' appears {occurrences}x in card text (expect 1)")

            # Check #5 (partial): nav should be hidden on main menu, visible on syllabus screen
            nav_display = page.evaluate("getComputedStyle(document.getElementById('game-nav')).display")
            print("game-nav display on syllabus-screen:", nav_display)

            page.click(".syllabus-card")
            page.wait_for_selector("#combat-screen[style*='display: block']")
            print("combat-screen horizontal scroll:", has_horizontal_scroll(page))
            page.screenshot(path=f"{OUT_DIR}/{name}_03_combat_screen.png")

            realm_text = page.inner_text("#game-nav-realm")
            print("nav realm text in combat:", repr(realm_text))

            if name == "desktop":
                # Deep-dive interaction checks only once (desktop), not per-viewport
                page.click("#attack-btn")
                page.wait_for_selector("#quiz-modal.active")
                page.wait_for_timeout(100)  # let the deferred focus-trap rAF settle
                page.screenshot(path=f"{OUT_DIR}/{name}_04_quiz_modal.png")

                answer_btn = page.query_selector(".answer-btn")
                if answer_btn:
                    bg = answer_btn.evaluate("el => getComputedStyle(el).backgroundColor")
                    print("answer-btn background-color (should not be a native gray):", bg)
                else:
                    print("WARNING: no .answer-btn found (multi-select question?)")

                # Focus trap check: Tab many times, confirm focus stays inside #quiz-modal
                page.keyboard.press("Tab")
                escaped = False
                for _ in range(15):
                    page.keyboard.press("Tab")
                    inside = page.evaluate("document.getElementById('quiz-modal').contains(document.activeElement)")
                    if not inside:
                        escaped = True
                        break
                print("focus trap held (no escape after 15 tabs):", not escaped)

                # Escape closes modal
                page.keyboard.press("Escape")
                page.wait_for_timeout(500)
                still_active = "active" in (page.get_attribute("#quiz-modal", "class") or "")
                print("Escape closed quiz modal:", not still_active)

            page.close()

        # Math rendering check: hit a known math question directly via a fresh page + API
        print("\n=== Math rendering check ===")
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        page.goto(BASE_URL)
        page.click("#deploy-btn")
        page.wait_for_selector(".syllabus-card")
        # Click the "math" card specifically if present
        math_card = page.query_selector(".syllabus-card:has-text('Math')")
        if math_card:
            math_card.click()
        else:
            page.click(".syllabus-card")
        page.wait_for_selector("#combat-screen[style*='display: block']")
        # Rather than fight the combat loop's auto-advance-after-answering
        # structure to randomly stumble onto a math question, directly
        # exercise the same normalizeMathText()+renderMathIn() code path the
        # real game uses, with known math-notation strings pulled from the
        # actual corpus earlier in this session (caret exponents, fractions).
        page.click("#attack-btn")
        page.wait_for_selector("#quiz-modal.active")
        page.wait_for_timeout(150)
        test_strings = [
            "What is x^2 + y^2 when x=3 and y=4?",
            "What is the sum of 1/3 and 1/6?",
            "S_n = a * (1 - r^n) / (1 - r)",
        ]
        for s in test_strings:
            page.evaluate("""(text) => {
                const qEl = document.getElementById('quiz-question');
                qEl.innerHTML = normalizeMathText(text);
                renderMathIn(qEl);
            }""", s)
            page.wait_for_timeout(100)
            katex_present = page.query_selector("#quiz-question .katex") is not None
            rendered_html = page.eval_on_selector("#quiz-question", "el => el.innerHTML")
            print(f"input={s!r}\\n  katex_rendered={katex_present}\\n  html={rendered_html[:150]!r}")
        page.screenshot(path=f"{OUT_DIR}/desktop_05_katex_question.png")
        found_math = True
        print("KaTeX rendering path exercised directly:", found_math)
        page.close()

        browser.close()

    print("\n=== Console errors seen across all pages ===")
    for e in console_errors:
        print(" -", e)
    if not console_errors:
        print(" (none)")


if __name__ == "__main__":
    main()
