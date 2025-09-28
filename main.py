# Самый простой файл, его единственная задача — импортировать класс приложения и запустить его.

# main.py
from app.application import Application

if __name__ == "__main__":
    app = Application()
    app.run()