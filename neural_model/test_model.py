import torch
from transformers import (T5ForConditionalGeneration, T5Tokenizer, Trainer, TrainingArguments, DataCollatorForSeq2Seq)
from datasets import Dataset, load_dataset
from tqdm.auto import tqdm


device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Используемое устройство: {device}")

OUTPUT_DIR = "/anaphora_resolution_model"

loaded_model = T5ForConditionalGeneration.from_pretrained(OUTPUT_DIR)
loaded_tokenizer = T5Tokenizer.from_pretrained(OUTPUT_DIR, legacy=False)
loaded_model.to(device)
loaded_model.eval()


def resolve_anaphora(text, model, tokenizer, max_length=128):
    prompt = text.strip()
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=max_length).to(device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_length=max_length,
            num_beams=4,
            early_stopping=True,
            no_repeat_ngram_size=3,
            repetition_penalty=1.2
        )
    resolved_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return resolved_text


test_examples = [
    "Маша купила телефон. Он был новый.",
    "Учёные исследовали образцы грунта, доставленные с Луны. Они надеялись найти следы воды или органических веществ.",
    "Решение, что было принято на собрании, удивило всех.",
    "Это был разговор, что они откладывали целый год."
]

print("Проверка модели на примерах:")
for i, example in enumerate(test_examples, 1):
    result = resolve_anaphora(example, loaded_model, loaded_tokenizer)
    print(f"{i}. Вход: {example}")
    print(f"   Выход: {result}")


while True:
    print("\nВведите текст (на русском) для разрешения анафоры или \"выход\" для завершения")
    user_text = input("Введите текст: ")
    if user_text:
        if user_text.lower() == "выход":
            print("Обработка завершена")
            break
        result = resolve_anaphora(user_text, loaded_model, loaded_tokenizer)
        print(f"Результат: {result}")
    else:
        print("Пустой ввод")
