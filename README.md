# StudySpark — PDF to Quiz

> Turn course PDFs into quizzes you can check against the source.

[![CI](https://github.com/sahityadhiman/studyspark-pdf-to-quiz/actions/workflows/ci.yml/badge.svg)](https://github.com/sahityadhiman/studyspark-pdf-to-quiz/actions/workflows/ci.yml) ![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python) ![Flask](https://img.shields.io/badge/Flask-web%20app-000000?logo=flask)

StudySpark is a GenAI study app that extracts selectable text from a course PDF and asks Google Gemini to create multiple-choice questions. Each answer includes an explanation and a page reference. You can reveal answers while studying or download an answer key as CSV.

## Live demo

Coming soon. This project is being prepared for deployment.

## The problem and solution

Writing practice questions from long course notes takes time, and generic questions may not match the material. StudySpark uses the uploaded PDF as context so the questions stay tied to the document. Page references help you check each answer against the source.

## Workflow

1. Upload a text-based PDF (up to 10 MB and 80 pages).
2. Choose 3–10 questions.
3. Reveal answers and explanations as you study.
4. Check cited pages and export the answer key as CSV.

## Features

- Gemini structured output, validated with Pydantic.
- Explanations and source page numbers for each question.
- Fallback Gemini model for service-busy errors.
- CSRF protection, upload limits, and per-process generation limits.
- CSV formula escaping and a deployment health endpoint.

## Technology

Python · Flask · Jinja · Google Gemini API · pypdf · Pydantic · Gunicorn · Docker · Render

## Run locally on Windows

Use Python 3.10 or newer. In PowerShell, from the project folder:

    py -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install -r requirements.txt -r requirements-deploy.txt
    Copy-Item .env.example .env

Add your Gemini API key to the private .env file, then run:

    python app.py

Open http://127.0.0.1:5000. Keep the terminal open while using the app. The .env file is ignored by Git; never commit your API key.

## Tests

    python -m unittest discover -s tests -v

GitHub Actions runs the test suite on pushes and pull requests.

## Deployment

A Dockerfile and Render Blueprint are included. In Render, create a Blueprint from this repository and provide GOOGLE_API_KEY as a secret when prompted. Render uses /health for readiness checks. Add the deployed URL here when available.

## Limitations and privacy

Scanned PDFs are not supported because OCR is not included. Uploaded PDFs are processed in memory and are not saved; extracted text is sent to Gemini. Do not upload confidential files. Generated answers can be wrong, so review explanations and page references. This prototype has no accounts or persistent storage, and its in-memory request limit resets when the app restarts.

## Attribution and license

Selected from [Yash Kavaiya's GenAI Projects](https://github.com/Yash-Kavaiya/GenAI-Projects). MIT License; see LICENSE.

## Author

[Sahityadhiman](https://github.com/sahityadhiman)
