import io
import time
import os
import csv
import re
import keyboard
from PIL import ImageGrab, Image
import pytesseract
from deep_translator import GoogleTranslator, MyMemoryTranslator
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import hashlib
import shutil
import pytesseract

if shutil.which("tesseract") is None:
    default_win = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    pytesseract.pytesseract.tesseract_cmd = default_win

def words_dw():
    df = pd.read_csv("medieval_dict.csv", sep=';')
  
    words = df['Original'].tolist()
    model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')

    embeddings = model.encode(words)

    return df, model, embeddings

def sort_words_by_similarity(target_word, words_list, embeddings_matrix, model):
    target_embedding = model.encode([target_word])
    
    similarities = cosine_similarity(target_embedding, embeddings_matrix)[0]
    
    result_df = pd.DataFrame({
        'Original': words_list['Original'].tolist(),
        'Translation': words_list['Translation'].tolist(),
        'Similarity': similarities
    })
    
    return result_df.sort_values(by='Similarity', ascending=False)

def normalize_text(text):
    return " ".join(text.strip().split()).lower()


def ensure_csv_file(file_path):
    if not os.path.isfile(file_path):
        with open(file_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow(["Original", "Translation"])
        return set()

    with open(file_path, "rb") as f:
        content = f.read()
    if content and not content.startswith(b"\xef\xbb\xbf"): 
        try:
            decoded = content.decode("utf-8")
        except UnicodeDecodeError:
            decoded = content.decode("utf-8", errors="replace")
        with open(file_path, "w", encoding="utf-8-sig", newline="") as f:
            f.write(decoded)

    known = set()
    with open(file_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f, delimiter=';')
        next(reader, None)
        for row in reader:
            if row:
                known.add(normalize_text(row[0]))
    return known


def translate_with_retry(text, retries=3):
    for attempt in range(retries):
        try:
            return MyMemoryTranslator(source='en-GB', target='uk-UA').translate(text)
        except Exception as e:
            wait = 5 * (attempt + 1)
            print(f"Помилка при перекладі ({e.__class__.__name__}), чекаю {wait} с...")
            time.sleep(wait)
    return None


def process_clipboard_image(img):
    print("\n[Анализ буфера обмена...]")
    try:
        img = img.resize((img.width * 2, img.height * 2), Image.Resampling.LANCZOS)
        text = pytesseract.image_to_string(img, lang='eng').strip()

        if not text:
            print("Не вдалося розпізнати текст")
            return

        clean_text = text.replace('\n', ' ').strip()
        print(f"Знайдено слово/фраза: {clean_text}")

        file_path = "medieval_dict.csv"
        known_texts = ensure_csv_file(file_path)

        # Сначала проверяем словарь, чтобы не делать лишний запрос
        if normalize_text(clean_text) in known_texts:
            print("Слово вже є в словнику, пропускаю.")
            return

        translated = translate_with_retry(clean_text)
        if translated is None:
            print("Не вдалося перекласти, пропускаю.")
            return
        print(f"Переклад: {translated}")

        with open(file_path, "a", encoding="utf-8-sig", newline="") as f:
            csv.writer(f, delimiter=';').writerow([clean_text, translated])

        print("💾 Збережено в medieval_dict.csv")
    except Exception as e:
        print(f"Помилка при обробці: {e}")


print("Скрипт запущен і чекає скриншотів (Win + Shift + S)...")

last_hash = None
while True:
    if keyboard.is_pressed('esc'):
        print("Вихід із програми.")
        break
    if keyboard.is_pressed('q'):
        # ... ваш блок с поиском похожих слов без изменений ...
        break

    try:
        item = ImageGrab.grabclipboard()
        if isinstance(item, Image.Image):
            h = hashlib.md5(item.tobytes()).hexdigest()
            if h != last_hash:
                last_hash = h          # помечаем СРАЗУ, независимо от результата
                time.sleep(0.5)
                process_clipboard_image(item)
    except KeyboardInterrupt:
        print("\nСкрипт остановлен.")
        break
    except Exception:
        pass

    time.sleep(2)

