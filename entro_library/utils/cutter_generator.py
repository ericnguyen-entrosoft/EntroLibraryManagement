import unicodedata
import re
from typing import Dict, List, Tuple, Optional

class CutterGenerator:
    """
    Tạo mã Cutter-Sanborn chỉ dựa trên tiêu đề sách
    Không cần thông tin tác giả
    """
    
    def __init__(self):
        self.cutter_table = self._create_cutter_table()
        
        # Mạo từ cần bỏ qua
        self.articles = [
            # Tiếng Việt
            'các', 'những', 'mọi', 'một', 'hai', 'ba', 'bốn', 'năm',
            'cuốn', 'quyển', 'tập', 'bộ', 'bản', 'tuyển',
            # Tiếng Anh
            'the', 'a', 'an'
        ]
        
    def _create_cutter_table(self) -> Dict[str, int]:
        """
        Tạo bảng tra cứu Cutter-Sanborn
        """
        base_values = {
            'a': 10, 'b': 100, 'c': 200, 'd': 300, 'e': 400,
            'f': 500, 'g': 600, 'h': 700, 'i': 800, 'j': 900,
            'k': 10, 'l': 110, 'm': 210, 'n': 310, 'o': 410,
            'p': 510, 'q': 610, 'r': 710, 's': 810, 't': 910,
            'u': 20, 'v': 120, 'w': 220, 'x': 320, 'y': 420,
            'z': 520
        }
        
        secondary_values = {
            'a': 0, 'e': 1, 'i': 2, 'o': 3, 'u': 4,
            'b': 5, 'c': 6, 'd': 7, 'f': 8, 'g': 9,
            'h': 10, 'k': 11, 'l': 12, 'm': 13, 'n': 14,
            'p': 15, 'q': 16, 'r': 17, 's': 18, 't': 19,
            'v': 20, 'w': 21, 'x': 22, 'y': 23, 'z': 24
        }
        
        return {
            'base': base_values,
            'secondary': secondary_values
        }
    
    def remove_vietnamese_accents(self, text: str) -> str:
        """
        Bỏ dấu tiếng Việt
        """
        nfd = unicodedata.normalize('NFD', text)
        without_accents = ''.join([c for c in nfd if not unicodedata.combining(c)])
        
        replacements = {
            'đ': 'd', 'Đ': 'D',
            'ă': 'a', 'Ă': 'A',
            'â': 'a', 'Â': 'A',
            'ê': 'e', 'Ê': 'E',
            'ô': 'o', 'Ô': 'O',
            'ơ': 'o', 'Ơ': 'O',
            'ư': 'u', 'Ư': 'U'
        }
        
        for vn_char, latin_char in replacements.items():
            without_accents = without_accents.replace(vn_char, latin_char)
        
        return without_accents
    
    def normalize_title(self, title: str) -> str:
        """
        Chuẩn hóa tiêu đề
        """
        # Bỏ dấu
        title = self.remove_vietnamese_accents(title)
        # Chuyển thành chữ thường
        title = title.lower()
        # Bỏ các ký tự không phải chữ cái và số
        title = re.sub(r'[^a-z0-9\s]', '', title)
        # Bỏ số ở đầu
        title = re.sub(r'^\d+\s*', '', title)
        # Chuẩn hóa khoảng trắng
        title = ' '.join(title.split())
        
        return title
    
    def get_main_word(self, title: str) -> str:
        """
        Lấy từ chính từ tiêu đề (sau khi bỏ mạo từ)
        """
        normalized = self.normalize_title(title)
        words = normalized.split()
        
        # Bỏ mạo từ ở đầu
        while words and words[0] in self.articles:
            words.pop(0)
        
        # Trả về từ đầu tiên
        return words[0] if words else ""
    
    def calculate_cutter_number(self, word: str) -> int:
        """
        Tính số Cutter dựa trên từ chính
        """
        if not word:
            return 0
        
        # Lấy 3 ký tự đầu
        first = word[0] if len(word) > 0 else 'a'
        second = word[1] if len(word) > 1 else 'a'
        third = word[2] if len(word) > 2 else 'a'
        
        # Tính giá trị cơ bản
        base = self.cutter_table['base'].get(first, 0)
        
        # Tính modifier từ chữ thứ 2
        secondary = self.cutter_table['secondary'].get(second, 0)
        
        # Tính fine-tuning từ chữ thứ 3
        tertiary = ord(third) - ord('a') if third.isalpha() else 0
        
        # Công thức tính
        cutter_num = base + (secondary * 3) + tertiary
        
        # Đảm bảo trong khoảng 0-999
        cutter_num = cutter_num % 1000
        
        return cutter_num
    
    def generate_cutter_code(self, title: str, include_second_letter: bool = True) -> str:
        """
        Tạo mã Cutter từ tiêu đề
        
        Args:
            title: Tiêu đề sách
            include_second_letter: Có thêm chữ cái thứ 2 của tiêu đề không
            
        Returns:
            Mã Cutter (ví dụ: S810, D300c, T910k)
        """
        # Lấy từ chính
        main_word = self.get_main_word(title)
        
        if not main_word:
            return ""
        
        # Chữ cái đầu (viết hoa)
        first_letter = main_word[0].upper()
        
        # Số Cutter
        cutter_number = self.calculate_cutter_number(main_word)
        
        # Tạo mã Cutter cơ bản
        cutter_code = f"{first_letter}{cutter_number}"
        
        # Thêm chữ cái thứ 2 nếu cần (để phân biệt các sách có cùng từ đầu)
        if include_second_letter and len(main_word) > 1:
            second_letter = main_word[1].lower()
            cutter_code += second_letter
        
        return cutter_code
    