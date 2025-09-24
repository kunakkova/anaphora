from anaphora.resolver import resolve_pronouns

def main():
    while True:
        text_example = input("Введите текст для разрешения местоимений (или 'exit' для выхода): ")
        if text_example.lower() == 'exit':
            break
        resolved_text = resolve_pronouns(text_example)
        print("Результат:", resolved_text)

if __name__ == '__main__':
    main()

