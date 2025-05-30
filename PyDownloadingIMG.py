import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor

class WebsiteImageDownloader:
    def __init__(self, base_url, output_folder='downloaded_images', max_pages=1000, max_threads=5):
        self.base_url = base_url
        self.output_folder = output_folder
        self.max_pages = max_pages
        self.max_threads = max_threads
        self.visited_urls = set()
        self.downloaded_images = set()
        self.domain = urlparse(base_url).netloc
        
        # Создаем папку для сохранения
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
    
    def is_valid_url(self, url):
        """Проверяет, что URL принадлежит тому же домену и не посещался ранее"""
        parsed = urlparse(url)
        return (
            parsed.netloc == self.domain and
            url not in self.visited_urls and
            not url.startswith('javascript:') and
            not url.startswith('mailto:') and
            not url.startswith('#')
        )
    
    def get_all_links(self, url):
        """Получает все ссылки со страницы"""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Находим все ссылки на странице
            links = set()
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                absolute_url = urljoin(url, href)
                if self.is_valid_url(absolute_url):
                    links.add(absolute_url)
            
            return links
        except Exception as e:
            print(f"Ошибка при обработке {url}: {e}")
            return set()
    
    def download_image(self, img_url):
        """Скачивает одно изображение"""
        if img_url in self.downloaded_images:
            return
        
        try:
            img_name = os.path.basename(urlparse(img_url).path)
            if not img_name:
                img_name = f"image_{len(self.downloaded_images) + 1}.jpg"
            
            # Проверяем расширение файла
            valid_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.svg')
            if not img_name.lower().endswith(valid_extensions):
                img_name += '.jpg'
            
            # Проверяем, не скачивали ли уже это изображение
            save_path = os.path.join(self.output_folder, img_name)
            if os.path.exists(save_path):
                return
            
            img_data = requests.get(img_url, stream=True, timeout=10)
            img_data.raise_for_status()
            
            with open(save_path, 'wb') as f:
                for chunk in img_data.iter_content(1024):
                    f.write(chunk)
            
            self.downloaded_images.add(img_url)
            print(f"Скачано: {img_name}")
        except Exception as e:
            print(f"Ошибка при загрузке {img_url}: {e}")
    
    def process_page(self, url):
        """Обрабатывает одну страницу: скачивает изображения и находит новые ссылки"""
        if url in self.visited_urls or len(self.visited_urls) >= self.max_pages:
            return set()
        
        self.visited_urls.add(url)
        print(f"Обработка страницы: {url}")
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Скачиваем все изображения на странице
            img_urls = set()
            for img in soup.find_all('img', src=True):
                img_url = urljoin(url, img['src'])
                img_urls.add(img_url)
            
            # Многопоточная загрузка изображений
            with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
                executor.map(self.download_image, img_urls)
            
            # Возвращаем все ссылки на этой странице для дальнейшего обхода
            return self.get_all_links(url)
        except Exception as e:
            print(f"Ошибка при обработке {url}: {e}")
            return set()
    
    def crawl_website(self):
        """Рекурсивно обходит все страницы сайта"""
        from collections import deque
        
        queue = deque([self.base_url])
        
        while queue and len(self.visited_urls) < self.max_pages:
            current_url = queue.popleft()
            new_links = self.process_page(current_url)
            
            for link in new_links:
                if link not in self.visited_urls and link not in queue:
                    queue.append(link)
        
        print(f"\nЗавершено! Посещено {len(self.visited_urls)} страниц. Скачано {len(self.downloaded_images)} изображений.")

if __name__ == "__main__":
    website_url = input("Введите URL сайта (например, https://example.com): ").strip()
    
    downloader = WebsiteImageDownloader(
        base_url=website_url,
        output_folder='downloaded_images',
        max_pages=100,  # Максимальное количество страниц для обработки
        max_threads=5   # Количество потоков для загрузки изображений
    )
    
    downloader.crawl_website()
