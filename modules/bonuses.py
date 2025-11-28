import pyautogui

def collect(path, confidence):
    try:
        gold_popup = pyautogui.locateOnScreen(path + "gold_popup.png", confidence=confidence)
        if gold_popup:
            pyautogui.click(gold_popup)
            print("Bonus zebrany")
    except Exception as e:
        print("Błąd w bonuses:", e)
