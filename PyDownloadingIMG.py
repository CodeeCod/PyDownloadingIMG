import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

def download_images_from_website(url, output_folder='downloaded_images'):
    """
    Скачивает все изображения с указанного веб-сайта
    
    :param url: URL веб-сайта
    :param output_folder: Папка для сохранения изображений
    """
    # Создаем папку для сохранения, если ее нет
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    # Получаем HTML-код страницы
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при загрузке страницы: {e}")
        return
    
    # Парсим HTML с помощью BeautifulSoup
    soup = BeautifulSoup(response.text, 'html.parser')
    img_tags = soup.find_all('img')
    
    if not img_tags:
        print("На странице не найдено изображений.")
        return
    
    print(f"Найдено {len(img_tags)} изображений. Начинаю загрузку...")
    
    downloaded_count = 0
    for img in img_tags:
        img_url = img.get('src')
        if not img_url:
            continue
        
        # Преобразуем относительный URL в абсолютный
        img_url = urljoin(url, img_url)
        
        # Получаем имя файла из URL
        img_name = os.path.basename(urlparse(img_url).path)
        if not img_name:
            img_name = f"image_{downloaded_count + 1}.jpg"
        
        # Проверяем расширение файла
        if not img_name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')):
            img_name += '.jpg'
        
        # Скачиваем изображение
        try:
            img_data = requests.get(img_url, stream=True)
            img_data.raise_for_status()
            
            # Сохраняем изображение
            save_path = os.path.join(output_folder, img_name)
            with open(save_path, 'wb') as f:
                for chunk in img_data.iter_content(1024):
                    f.write(chunk)
            
            downloaded_count += 1
            print(f"Скачано: {img_name}")
        except Exception as e:
            print(f"Ошибка при загрузке {img_url}: {e}")
    
    print(f"\nЗавершено! Успешно скачано {downloaded_count} из {len(img_tags)} изображений.")

if __name__ == "__main__":
    website_url = input("Введите URL сайта: ").strip()
    download_images_from_website(website_url)