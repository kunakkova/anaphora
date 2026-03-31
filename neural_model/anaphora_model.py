import os
import json
import torch
from transformers import (T5ForConditionalGeneration, T5Tokenizer, Trainer, TrainingArguments, DataCollatorForSeq2Seq)
from datasets import Dataset, load_dataset
from tqdm.auto import tqdm
import numpy as np
import random
import shutil


def set_seed(seed=42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


set_seed(42)


device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Используемое устройство: {device}")


OUTPUT_DIR = "/anaphora_resolution_model"

TRAIN_FILE = "./train.jsonl"
VALID_FILE = "./valid.jsonl"
TEST_FILE = "./test.jsonl"

train_dataset = load_dataset('json', data_files=TRAIN_FILE, split='train')
valid_dataset = load_dataset('json', data_files=VALID_FILE, split='train')
test_dataset = load_dataset('json', data_files=TEST_FILE, split='train')

print(f"Размер обучающей выборки: {len(train_dataset)}")
print(f"Размер валидационной выборки: {len(valid_dataset)}")
print(f"Размер тестовой выборки: {len(test_dataset)}")

print("Пример из train:")
print(train_dataset[0])

MODEL_NAME = "ai-forever/ruT5-base"

tokenizer = T5Tokenizer.from_pretrained(MODEL_NAME, legacy=False)
model = T5ForConditionalGeneration.from_pretrained(MODEL_NAME)

example_input = train_dataset[0]['input_text']
example_target = train_dataset[0]['target_text']
print("Пример входного текста:", example_input)
print("Пример целевого текста:", example_target)

input_ids = tokenizer(example_input, return_tensors='pt').input_ids


MAX_INPUT_LEN = 128
MAX_TARGET_LEN = 128


def preprocess_function(examples):
    inputs = examples['input_text']
    targets = examples['target_text']

    model_inputs = tokenizer(
        inputs,
        max_length=MAX_INPUT_LEN,
        truncation=True,
        padding=False,
        return_tensors=None
    )

    labels = tokenizer(
        targets,
        max_length=MAX_TARGET_LEN,
        truncation=True,
        padding=False,
        return_tensors=None
    )

    model_inputs['labels'] = labels['input_ids']
    return model_inputs


train_dataset = train_dataset.map(preprocess_function, batched=True, remove_columns=['input_text', 'target_text'])
valid_dataset = valid_dataset.map(preprocess_function, batched=True, remove_columns=['input_text', 'target_text'])
test_dataset = test_dataset.map(preprocess_function, batched=True, remove_columns=['input_text', 'target_text'])

train_dataset.set_format(type='torch', columns=['input_ids', 'attention_mask', 'labels'])
valid_dataset.set_format(type='torch', columns=['input_ids', 'attention_mask', 'labels'])
test_dataset.set_format(type='torch', columns=['input_ids', 'attention_mask', 'labels'])

data_collator = DataCollatorForSeq2Seq(
    tokenizer,
    model=model,
    padding=True,
    label_pad_token_id=tokenizer.pad_token_id
)

if os.path.exists(OUTPUT_DIR):
    shutil.rmtree(OUTPUT_DIR)

training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    num_train_epochs=5,
    per_device_train_batch_size=8,
    per_device_eval_batch_size=8,
    gradient_accumulation_steps=1,
    eval_strategy="epoch",
    save_strategy="no",
    logging_steps=100,
    learning_rate=3e-5,
    weight_decay=0.01,
    warmup_steps=500,
    fp16=torch.cuda.is_available(),
    report_to="none",
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=valid_dataset,
    data_collator=data_collator
)


print("Начинаем обучение")
trainer.train()


model.save_pretrained(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)
print(f"Модель сохранена в {OUTPUT_DIR}")

print("Оценка на тестовой выборке:")
test_results = trainer.evaluate(test_dataset)
print(test_results)
