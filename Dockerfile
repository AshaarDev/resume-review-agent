FROM node:22-alpine AS frontend-build

WORKDIR /frontend

COPY frontend/frontend-app/package.json frontend/frontend-app/package-lock.json ./
RUN npm ci

COPY frontend/frontend-app ./
RUN npm run build


FROM python:3.10-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8001

# Runtime dependencies:
# - TeX Live compiles generated resumes.
# - LibreOffice converts DOCX files for visual review.
# - Tesseract extracts text from uploaded resume images.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libreoffice-writer \
        fonts-liberation2 \
        tesseract-ocr \
        texlive-fonts-recommended \
        texlive-latex-base \
        texlive-latex-extra \
        texlive-latex-recommended \
        texlive-plain-generic \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install -r backend/requirements.txt

COPY backend backend
COPY frontend frontend
COPY --from=frontend-build /frontend/dist frontend/frontend-app/dist

# Validate the exact production template during image construction. A missing
# TeX package makes the build fail instead of disabling PDF generation at runtime.
RUN mkdir -p /tmp/resume-template-check \
    && cp backend/templates/resumes/harshibar/template.tex \
        /tmp/resume-template-check/resume.tex \
    && cd /tmp/resume-template-check \
    && sed -i 's/%%__HEADER__%%/Template runtime check/' resume.tex \
    && pdflatex -no-shell-escape -interaction=nonstopmode -halt-on-error resume.tex \
    && test -s resume.pdf \
    && rm -rf /tmp/resume-template-check

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p backend/artifacts backend/temp backend/uploads \
    && chown -R appuser:appuser /app

USER appuser
WORKDIR /app/backend

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.getenv('PORT','8001')+'/api/health',timeout=4)" || exit 1

CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port \"${PORT:-8001}\""]
