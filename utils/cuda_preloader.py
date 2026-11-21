import ctypes
import glob
import os


def preload_cuda_libraries():
    """
    Pré-carrega as bibliotecas CUDA 12 (cuBLAS e cuDNN 9) instaladas via pip
    (pacotes nvidia-cublas-cu12 e nvidia-cudnn-cu12), para que o ctranslate2 /
    faster-whisper as encontre.

    O pré-carregamento vale só para o processo atual: precisa rodar de novo após
    cada reinício da sessão e ANTES de importar o faster-whisper.
    """
    try:
        import nvidia.cublas.lib as cublas_lib
        import nvidia.cudnn.lib as cudnn_lib
    except ImportError:
        print(
            "⚠️ Pacotes nvidia-cublas-cu12 / nvidia-cudnn-cu12 não encontrados. "
            "Rode o Bloco 1 (instalação). Seguindo sem pré-carregar as bibliotecas CUDA 12."
        )
        return

    loaded = 0
    for pkg in (cublas_lib, cudnn_lib):
        folder = os.path.dirname(pkg.__file__) if pkg.__file__ else list(pkg.__path__)[0]
        for so_file in sorted(glob.glob(os.path.join(folder, "lib*.so*"))):
            try:
                ctypes.CDLL(so_file, mode=ctypes.RTLD_GLOBAL)
                loaded += 1
            except OSError:
                pass

    print(f"✅ Bibliotecas CUDA 12 pré-carregadas ({loaded} arquivos .so)")