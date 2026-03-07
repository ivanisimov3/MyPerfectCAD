import ezdxf

class DxfImporter:
    """Импортирует данные из DXF файла во внутренние примитивы приложения."""

    def import_dxf(self, state, filepath, root):
        """
        Чтение DXF файла и заполнение списков примитивов в AppState.
        
        Args:
            state: объект AppState.
            filepath: путь к файлу .dxf.
            root: главное окно Tkinter для конвертации цветов (если потребуется).
        """
        try:
            doc = ezdxf.readfile(filepath)
            msp = doc.modelspace()
            
            # На Фазе 1 мы просто проверяем, что ezdxf.readfile отработал без ошибок.
            # Последующий код будет добавлен в Фазе 2 и далее.
            
            print(f"DXF успешно открыт. Версия: {doc.dxfversion}")
            
        except IOError:
            raise Exception(f"Невозможно прочитать файл: {filepath}")
        except ezdxf.DXFStructureError as e:
            raise Exception(f"Некорректная структура DXF: {e}")
