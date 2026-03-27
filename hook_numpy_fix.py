# Runtime hook to fix numpy 2.x compatibility with PyInstaller
# Fixes: RuntimeError: CPU dispatcher tracer already initialized

import os
import sys

# Set environment variables before numpy imports
os.environ.setdefault('NPY_DISABLE_CPU_FEATURES', 'AVX512F,AVX512CD,AVX512_SKX')
os.environ.setdefault('NPY_DISABLE_CPU_FEATURES_WARNINGS', '1')

# Workaround for numpy 2.x CPU dispatcher issue
if hasattr(sys, 'frozen'):
    # Running as PyInstaller bundle
    try:
        import numpy as np
        # Trigger numpy initialization early
        np.__config__.show()
    except Exception:
        pass
