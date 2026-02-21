# RPG Transcription & Chronicle Generator

Este projeto automatiza a transcrição de sessões de RPG utilizando **WhisperX** para conversão de áudio em texto e **Gemini API** para a criação de crônicas narrativas épicas.

---

## Preparação Local (Pré-processamento)

Antes de subir o áudio para o Google Drive, é necessário garantir que ele esteja no formato ideal para o processador de áudio.

### 1. Navegar até a pasta de áudios
Abra o seu terminal (Git Bash recomendado) e utilize o comando abaixo para acessar sua pasta de músicas:

```bash
cd "C:\Users\thais\Music\Mesas de RPG\"
```

### 2. Conversão para WAV (FFmpeg)
O Whisper processa melhor arquivos .wav mono de 16kHz. Utilize o comando abaixo para converter seu arquivo original:

```bash
# Substitua 'ID56' pelo código da sua sessão
ffmpeg -i ID56.mp3 -ac 1 -ar 16000 -c:a pcm_s16le ID56w.wav
```

## Execução no Google Colab
Para rodar os notebooks, siga estas configurações críticas para garantir o uso da GPU e evitar erros de memória.

### 1. Configuração do Ambiente
Ativar GPU: Vá no menu Runtime (Ambiente de execução) > Change runtime type (Alterar tipo de ambiente de execução) e selecione T4 GPU.

### 2. Limpeza de Cache: Se encontrar erros estranhos de biblioteca, use Runtime > Disconnect and delete runtime para limpar a máquina virtual e começar do zero.

### 3. Fluxo de Execução Crítico
O processo de instalação de dependências exige um reinício do ambiente para que as versões das bibliotecas (como o Numpy) sejam aplicadas corretamente.

> [!CAUTION]
> AÇÃO CRÍTICA: Após a execução dos Blocos 1 e 2 (Instalações Iniciais), você deve clicar no botão "RESTART SESSION" que aparecerá no log ou ir em Runtime > Restart session.
> Não execute esses blocos novamente após o reset. Siga diretamente para o Bloco 3.

## Estrutura de Arquivos Gerados
* IDxxw.wav: Áudio convertido (Entrada).
* IDxx_transcricao_final.txt: Texto bruto gerado pelo Whisper.
* IDxx_cronica.md: Texto narrativo final gerado pelo Gemini.