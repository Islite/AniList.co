# modules/manga.py
from typing import Any, List, Optional
import re

class MangaModule:
    def __init__(self, core):
        self.core = core  # ссылка на основной плагин
        self.register_commands()

    def register_commands(self):
        """Регистрация команд для манги"""
        # Здесь будем регистрировать команды в core
        pass

    def process_manga_search(self, account: int, base: dict, original_candidates: List[str]):
        """Основная логика поиска манги"""
        try:
            is_manga = True
            cache_key = f"data_{original_candidates[0] if original_candidates else ''}_manga"
            
            # Пока используем метод из core
            data, orig, shiki = self.core.get_data_by_id_or_search(
                original_candidates, 
                has_cyrillic=bool(re.search(r"[а-яА-ЯёЁ]", " ".join(original_candidates))), 
                cache_key=cache_key, 
                is_manga=True
            )
            
            if data or shiki:
                card_text = self.core.format_media_full(data or {}, 'manga', self.core.card_template, shiki)
                self.core.send_only_success(card_text, account, base)
            else:
                self.core.show_error_only("Манга не найдена")
                
        except Exception as e:
            self.core.log(f"[MangaModule] Ошибка: {e}")
            self.core.show_error_only("Ошибка поиска манги")

# Функция инициализации модуля (будет вызываться из Core)
def init_module(core):
    return MangaModule(core)
