import unittest
import os
import shutil
from unittest.mock import patch, MagicMock
from PyDownloadingIMG import WebsiteImageDownloader
from urllib.parse import urlparse

class TestWebsiteImageDownloader(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Создаем тестовую директорию
        cls.test_dir = "test_downloads"
        os.makedirs(cls.test_dir, exist_ok=True)
        
        # Тестовый URL
        cls.test_url = "http://example.com"
    
    @classmethod
    def tearDownClass(cls):
        # Удаляем тестовую директорию
        shutil.rmtree(cls.test_dir)
    
    def setUp(self):
        # Создаем экземпляр класса для каждого теста
        self.downloader = WebsiteImageDownloader(
            base_url=self.test_url,
            output_folder=self.test_dir,
            max_pages=10,
            max_threads=2
        )
    
    def test_init(self):
        """Тест инициализации класса"""
        self.assertEqual(self.downloader.base_url, self.test_url)
        self.assertEqual(self.downloader.output_folder, self.test_dir)
        self.assertEqual(self.downloader.max_pages, 10)
        self.assertEqual(self.downloader.max_threads, 2)
        self.assertEqual(urlparse(self.downloader.base_url).netloc, "example.com")
        self.assertTrue(os.path.exists(self.test_dir))
    
    def test_is_valid_url(self):
        """Тест проверки валидности URL"""
        # Валидные URL
        self.assertTrue(self.downloader.is_valid_url("http://example.com/page"))
        self.assertTrue(self.downloader.is_valid_url("https://example.com/page"))
        
        # Невалидные URL
        self.assertFalse(self.downloader.is_valid_url("http://other.com/page"))  # другой домен
        self.assertFalse(self.downloader.is_valid_url("javascript:void(0)"))     # javascript
        self.assertFalse(self.downloader.is_valid_url("mailto:test@example.com")) # mailto
        self.assertFalse(self.downloader.is_valid_url("#anchor"))                # якорь
        
        # После посещения URL должен стать невалидным
        test_url = "http://example.com/test"
        self.assertTrue(self.downloader.is_valid_url(test_url))
        self.downloader.visited_urls.add(test_url)
        self.assertFalse(self.downloader.is_valid_url(test_url))
    
    @patch('PyDownloadingIMG.requests.get')
    def test_get_all_links(self, mock_get):
        """Тест извлечения ссылок со страницы"""
        # Мокаем ответ сервера
        mock_response = MagicMock()
        mock_response.text = """
        <html>
            <body>
                <a href="/page1">Page 1</a>
                <a href="http://example.com/page2">Page 2</a>
                <a href="http://other.com/page3">Page 3</a>
                <a href="javascript:void(0)">JS Link</a>
            </body>
        </html>
        """
        mock_get.return_value = mock_response
        
        links = self.downloader.get_all_links("http://example.com")
        
        # Должны вернуться только ссылки на тот же домен
        expected_links = {
            "http://example.com/page1",
            "http://example.com/page2"
        }
        self.assertEqual(links, expected_links)
    
    @patch('PyDownloadingIMG.requests.get')
    def test_download_image(self, mock_get):
        """Тест загрузки изображения"""
        # Мокаем ответ сервера для изображения
        mock_response = MagicMock()
        mock_response.iter_content.return_value = [b'test', b'data']
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Тестируем загрузку
        img_url = "http://example.com/image.jpg"
        self.downloader.download_image(img_url)
        
        # Проверяем, что файл создан
        expected_file = os.path.join(self.test_dir, "image.jpg")
        self.assertTrue(os.path.exists(expected_file))
        self.assertIn(img_url, self.downloader.downloaded_images)
        
        # Проверяем, что повторная загрузка не происходит
        with patch('builtins.open') as mock_open:
            self.downloader.download_image(img_url)
            mock_open.assert_not_called()
    
    @patch('PyDownloadingIMG.requests.get')
    def test_process_page(self, mock_get):
        """Тест обработки страницы"""
        # Мокаем ответ сервера
        mock_response = MagicMock()
        mock_response.text = """
        <html>
            <body>
                <img src="/image1.jpg">
                <img src="http://example.com/image2.jpg">
                <a href="/page1">Page 1</a>
            </body>
        </html>
        """
        mock_get.return_value = mock_response
        
        # Мокаем download_image, чтобы не создавать реальные файлы
        with patch.object(self.downloader, 'download_image') as mock_download:
            new_links = self.downloader.process_page("http://example.com")
            
            # Проверяем, что изображения были обработаны
            expected_image_calls = [
                "http://example.com/image1.jpg",
                "http://example.com/image2.jpg"
            ]
            actual_image_calls = [args[0] for args in mock_download.call_args_list]
            self.assertCountEqual(actual_image_calls, expected_image_calls)
            
            # Проверяем, что ссылки были извлечены
            self.assertEqual(new_links, {"http://example.com/page1"})
            self.assertIn("http://example.com", self.downloader.visited_urls)
    
    @patch('PyDownloadingIMG.requests.get')
    @patch('PyDownloadingIMG.ThreadPoolExecutor')
    def test_crawl_website(self, mock_executor, mock_get):
        """Тест обхода сайта"""
        # Настраиваем моки
        mock_response = MagicMock()
        mock_response.text = """
        <html>
            <body>
                <img src="/image1.jpg">
                <a href="/page1">Page 1</a>
                <a href="/page2">Page 2</a>
            </body>
        </html>
        """
        mock_get.return_value = mock_response
        
        # Мокаем executor
        mock_executor.return_value.__enter__.return_value.map.return_value = None
        
        # Запускаем обход
        self.downloader.crawl_website()
        
        # Проверяем, что все страницы были посещены
        self.assertIn("http://example.com", self.downloader.visited_urls)
        self.assertIn("http://example.com/page1", self.downloader.visited_urls)
        self.assertIn("http://example.com/page2", self.downloader.visited_urls)

if __name__ == "__main__":
    unittest.main()