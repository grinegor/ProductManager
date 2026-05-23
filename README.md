# Senior Product Manager AI Agent (MVP)

Локальный облегченный MVP доменно-экспертного PM-ассистента для D2C/B2C продуктов с подпиской в нише снижения веса и telehealth.

## Стек
- Python
- LangGraph
- OpenAI API (`gpt-5.2` только для LLM-вызовов)
- OpenAI text embeddings (`text-embedding-3-small`)
- FAISS local vector store
- Streamlit UI

## Структура проекта
- `app.py` - чат-приложение Streamlit + debug-панель в сайдбаре.
- `src/pm_agent/config.py` - настройки окружения.
- `src/pm_agent/llm.py` - обертки для OpenAI chat и embeddings.
- `src/pm_agent/prompts.py` - системные промпты и ключевые слова роутинга.
- `src/pm_agent/rag.py` - загрузка документов, чанкинг, сборка/поиск в FAISS.
- `src/pm_agent/orchestrator.py` - последовательный оркестратор LangGraph + сабагенты.
- `src/pm_agent/memory.py` - summary-память диалога.
- `scripts/ingest_docs.py` - сборка FAISS-индекса из `/docs`.
- `docs/*` - стартовая база знаний.

## Quickstart
1. Создайте и активируйте виртуальное окружение.
2. Установите зависимости:
   ```bash
   python -m pip install -r requirements.txt
   ```
3. Настройте окружение:
   ```bash
   cp .env.example .env
   # укажите OPENAI_API_KEY
   ```
   Опционально: fallback-модель, если `gpt-5.2` недоступна для вашего ключа:
   ```bash
   # in .env
   OPENAI_MODEL=gpt-5.2
   OPENAI_FALLBACK_MODEL=gpt-5
   OPENAI_REASONING_EFFORT=high
   ```
4. Соберите локальный индекс:
   ```bash
   python scripts/ingest_docs.py
   ```
5. Запустите UI:
   ```bash
   streamlit run app.py
   ```

## Импорт внешних статей в базу знаний
Используйте это, чтобы импортировать выбранные URL в `docs/growth` и `docs/competitors`:

```bash
python scripts/import_external_articles.py
python scripts/ingest_docs.py
```

## Примечания
- Сабагенты роутятся промптом и вызываются оркестратором последовательно.
- Передача данных между сабагентами использует сжатый общий JSON-контракт (`agent`, `summary`, `key_findings`, `recommendations`, `assumptions`, `compliance_flags`, опционально `experiments`).
- Нет автономных циклов, внешней БД и enterprise-инфраструктуры.
- В debug-сайдбаре отображаются активные сабагенты, извлеченные чанки и расход токенов.
