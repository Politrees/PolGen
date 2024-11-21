<img src="https://raw.githubusercontent.com/Bebra777228/PolGen-RVC/refs/heads/PolGen/assets/logo.ico" width="100"/><img src="https://counter.seku.su/cmoe?name=PolGen&theme=r34"/><br>

# PolGen — Ваш инструмент для создания каверов и переозвучки

---

# 🚀 Установка и запуск

## `Запуск на Google Colab`

Если у вас нет мощной видеокарты, PolGen можно запустить с использованием Google Colab.

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1W39tbdYxR1NSVNHG6EDRiKkY4JM0f60B)

## `Запуск на ПК`

### Самостоятельная компиляция программы
> [!NOTE]
> 1. Скачайте ZIP-архив и распакуйте содержимое в любое удобное место - [Скачать](https://github.com/Bebra777228/PolGen-RVC/archive/refs/heads/PolGen.zip)
> 2. Запустите файл:
>    - **Windows**: `PolGen.exe`
>    - **Linux**: `install-run.sh`
> > Для Windows, возможно, придется установить **[Microsoft C++ Build Tools](https://visualstudio.microsoft.com/ru/visual-cpp-build-tools/)** с выбранной нагрузкой **«Desktop development with C++» (или «Разработка классических приложений на C++»)** во время установки.

### Скомпилированная программа
> [!TIP]
> Для лучшего опыта я настоятельно рекомендую использовать предварительно скомпилированную версию. Самостоятельная компиляция кода может привести к нестабильности.
> 1. Скачайте ZIP-архив и распакуйте содержимое в любое удобное место - [Репозиторий](https://huggingface.co/Politrees/PolGen/tree/main) / [Скачать](https://huggingface.co/Politrees/PolGen/resolve/main/PolGen-v1.2.0-FIX.zip?download=true)
> 2. Запустите файл:
        - **Windows**: `PolGen.exe`
        - **Linux**: `install-run.sh`

---

# 🚫 Условия использования

Использование преобразованного голоса для следующих целей **запрещено**:

- Критика или нападение на отдельных лиц.
- Поддержка или противодействие конкретным политическим позициям, религиям или идеологиям.
- Публичное отображение сильно стимулирующих выражений без соответствующего зонирования.
- Продажа голосовых моделей и сгенерированных голосовых клипов.
- Притворство оригинальным владельцем голоса с злонамеренными намерениями причинить вред/боль другим.
- Мошеннические цели, ведущие к краже личности или мошенническим телефонным звонкам.

---

# 🛡️ Отказ от ответственности

Я не несу ответственности за любые прямые, косвенные, последующие, случайные или специальные убытки, которые могут возникнуть в результате или в связи с использованием, неправильным использованием или невозможностью использования этого программного обеспечения.

---

# 📞 Контакты

Если у вас есть вопросы или предложения, пожалуйста, свяжитесь со мной через [Telegram](https://t.me/Politrees2) или [GitHub Issues](https://github.com/Bebra777228/Pol-Litres-RVC/issues).

---

# Структура проекта:
```
PolGen
├── .github
│   ├── ISSUE_TEMPLATE
│   │   ├── BUG_REPORT.yml
│   │   ├── FEATURE_REQUEST.yml
│   │   └── QUESTION_DISCUSSION.yml
│   ├── workflows
│   │   ├── code_formatter.yml
│   │   ├── code_linter.yml
│   │   ├── test_cli.yml
│   │   └── test_links.yml
│   └── CODE_OF_CONDUCT.md
├── assets
│   ├── i18n
│   │   ├── languages
│   │   │   └── en_US.json
│   │   ├── i18n.py
│   │   └── scan.py
│   └── logo.ico
├── models
│   └── .gitignore
├── output
│   ├── converted_audio
│   │   └── .gitignore
│   ├── separated_audio
│   │   └── .gitignore
│   └── .gitignore
├── rvc
│   ├── cli
│   │   ├── edge_tts_cli.py
│   │   └── rvc_cli.py
│   ├── infer
│   │   ├── config.py
│   │   ├── infer.py
│   │   └── pipeline.py
│   ├── lib
│   │   ├── algorithm
│   │   │   ├── __init__.py
│   │   │   ├── attentions.py
│   │   │   ├── commons.py
│   │   │   ├── discriminators.py
│   │   │   ├── encoders.py
│   │   │   ├── generators.py
│   │   │   ├── modules.py
│   │   │   ├── nsf.py
│   │   │   ├── normalization.py
│   │   │   ├── residuals.py
│   │   │   └── synthesizers.py
│   │   ├── predictors
│   │   │   ├── FCPE.py
│   │   │   └── RMVPE.py
│   │   └── my_utils.py
│   └── models
│       ├── embedders
│       │   └── .gitignore
│       └── predictors
│           └── .gitignore
├── tabs
│   ├── edge_tts
│   │   └── edge_tts.py
│   ├── inference
│   │   ├── inference_batch.py
│   │   └── inference_single.py
│   ├── install
│   │   └── install.py
│   ├── uvr
│   │   └── uvr.py
│   └── welcome.py
├── .gitignore
├── LICENSE
├── PolGen.exe
├── README.md
├── TODO.md
├── app.py
├── app_offline.py
├── download_models.py
├── requirements.txt
├── run-PolGen.bat
└── run-install.bat
```
---
