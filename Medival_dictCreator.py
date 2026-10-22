import io
import time
import os
import csv
import re
import keyboard
from PIL import ImageGrab, Image
import pytesseract
from deep_translator import GoogleTranslator
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


pytesseract.pytesseract.tesseract_cmd = r'C:\Users\kmois\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'

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


def process_clipboard_image():
    print("\n[Анализ буфера обмена...]")
    try:
        img = ImageGrab.grabclipboard()
        
        if isinstance(img, Image.Image):
            
            img = img.resize((img.width * 2, img.height * 2), Image.Resampling.LANCZOS)
            
            text = pytesseract.image_to_string(img, lang='eng').strip()
            
            if not text and not bool(re.search(r'[а-яА-ЯёЁ]', clean_text)):
                print("Не вдалося розпізнати текст")
                return None

            print(f"Знайдено слово/фраза: {text}")

           
            translated = GoogleTranslator(source='en', target='uk').translate(text)
            print(f"Переклад: {translated}")

            file_path = "medieval_dict.csv"
            known_texts = ensure_csv_file(file_path)

            clean_text = text.replace('\n', ' ').strip()
            normalized = normalize_text(clean_text)
            if normalized in known_texts:
                print("Слово вже є в словнику, пропускаю.")
                return True

            with open(file_path, "a", encoding="utf-8", newline="") as f:
                writer = csv.writer(f, delimiter=';')
                writer.writerow([clean_text, translated])

            print("💾 Збережено в medieval_dict.csv")
            return True
        else:
            print("В буфері обміну немає нової картинки.")
            return False
            
    except Exception as e:
        print(f"Помилка при обробці: {e}")
        return False

print("Скрипт запущен і чекає скриншотів (Win + Shift + S)...")

last_image = None
while True:

    if keyboard.is_pressed('esc'):
        print("Вихід із програми.")
        break
    if keyboard.is_pressed('q'):
        target = "forest"
        print(f"\nСлова, схожі на '{target}':")
        words, model, embeddings = words_dw()
        sorted_result = sort_words_by_similarity(target, words, embeddings, model)

        print(f"\nСлова, схожі на '{target}':")
        print(sorted_result[[ 'Translation' ]].head(5))
        break

    try:
        
        current_item = ImageGrab.grabclipboard()
        
        
        if isinstance(current_item, Image.Image) and current_item != last_image:
            
            time.sleep(0.5) 
            
            if process_clipboard_image():
                
                last_image = ImageGrab.grabclipboard() 
                
    except KeyboardInterrupt:
        print("\nСкрипт остановлен.")
        break
    except Exception as e:
        pass
        
    time.sleep(0.5)

