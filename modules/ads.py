import pyautogui

def check_and_watch(path, confidence):
    try:
        ad_button = pyautogui.locateOnScreen(path + "ad_button.png", confidence=confidence)
        if ad_button:
            pyautogui.click(ad_button)
            print("Reklama uruchomiona")
    except Exception as e:
        print("Błąd w ads:", e)
