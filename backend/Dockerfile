FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .

RUN pip install --no-cache-dir --default-timeout=1000 -r requirements.txt

COPY backend/ .

# Copy ml package and make it importable
COPY ml/ /ml_pkg/ml/
ENV PYTHONPATH=/app:/ml_pkg

# Patch SHAP's bundled colorconv for NumPy 1.24+ compatibility at build time
RUN python3 -c "\
import pathlib; \
p = pathlib.Path('/usr/local/lib/python3.11/site-packages/shap/plots/colors/_colorconv.py'); \
c = p.read_text(); \
c = c.replace('return convert(image, np.floating, force_copy)', 'return convert(image, np.float64, force_copy)'); \
c = c.replace('if np.issubdtype(dtype_in, np.dtype(dtype).type):', 'if np.issubdtype(dtype_in, dtypeobj_out.type):'); \
p.write_text(c); \
print('SHAP patch applied')" \
    && python3 -c "import shap; print('SHAP OK:', shap.__version__)"

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
