# RPG Transcription & Chronicle Generator

Este projeto automatiza a transcrição de sessões de RPG utilizando **WhisperX** para conversão de áudio em texto e **Gemini API** para a criação de crônicas narrativas épicas.

---

## Preparação Local (Pré-processamento)

Antes de subir o áudio para o Google Drive, é necessário garantir que ele esteja no formato ideal para o processador de áudio.

### Conversão para WAV (FFmpeg) para Arquivo Único
O Whisper processa melhor arquivos .wav mono de 16kHz. Utilize o comando abaixo para converter seu arquivo original:

**No Git Bash:**
```bash
cd "<CAMINHO_DA_PASTA_DO_ARQUIVO>"
NOME="ID56"; ffmpeg -i "$NOME.mp3" -ac 1 -ar 16000 -c:a pcm_s16le "${NOME}w.wav"
```

**No Powershell:**
```PowerShell
cd "<CAMINHO_DA_PASTA_DO_ARQUIVO>"
$nome = "<NOME_DO_ARQUIVO>"; ffmpeg -i "$nome.mp3" -ac 1 -ar 16000 -c:a pcm_s16le "$($nome)w.wav"
```

### Conversão para WAV (FFmpeg) para Múltiplos Arquivos
Para converter todos os arquivos MP3 da pasta, utilize o seguinte comando:

**No Git Bash:**
```bash
cd "<CAMINHO_DA_PASTA_DOS_ARQUIVOS>"
for f in *.mp3; do ffmpeg -i "$f" -ac 1 -ar 16000 -c:a pcm_s16le "${f%.mp3}w.wav"; done
```

**No Powershell:**
```PowerShell
cd "<CAMINHO_DA_PASTA_DOS_ARQUIVOS>"
Get-ChildItem *.mp3 | ForEach-Object { ffmpeg -i $_.Name -ac 1 -ar 16000 -c:a pcm_s16le "$($_.BaseName)w.wav" }
```

### Conversão para WAV (FFmpeg) para Arquivos Grandes
Algumas vezes o Colab falha no plano gratuito (GPU T4) ao tentar processar arquivos muito grandes (maiores do que 3 horas). Para cortar os arquivos em partes de 150 minutos, utilize o seguinte comando:

**No Git Bash:**
```bash
cd "<CAMINHO_DA_PASTA_DOS_ARQUIVOS>"
NOME="ID54"; ffmpeg -i "$NOME.mp3" -f segment -segment_time 02:30:00 -ac 1 -ar 16000 -c:a pcm_s16le "${NOME}_parte_%03d.wav"
```

**No Powershell:**
```PowerShell
cd "<CAMINHO_DA_PASTA_DO_ARQUIVO>"
$nome = "<NOME_DO_ARQUIVO>"; ffmpeg -i "$nome.mp3" -f segment -segment_time 02:30:00 -ac 1 -ar 16000 -c:a pcm_s16le "$($nome)_parte_%03d.wav"
```

Note que com arquivos divididos em partes será necessário ajustar a montagem da variável ARQUIVO_ENTRADA de acordo no Bloco 3.

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