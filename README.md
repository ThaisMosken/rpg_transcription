# RPG Transcription & Chronicle Generator

Este projeto automatiza a transcrição de sessões de RPG utilizando **faster-whisper** para conversão de áudio em texto e **Gemini API** para a criação de crônicas narrativas épicas.

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
Algumas vezes o Colab falha no plano gratuito (GPU T4) ao tentar processar arquivos muito grandes (maiores do que 3 horas). Para cortar os arquivos em partes de 120 minutos, utilize o seguinte comando:

**No Git Bash:**
```bash
cd "<CAMINHO_DA_PASTA_DOS_ARQUIVOS>"
NOME="ID54"; ffmpeg -i "$NOME.mp3" -f segment -segment_time 02:00:00 -ac 1 -ar 16000 -c:a pcm_s16le "${NOME}_parte_%03d.wav"
```

**No Powershell:**
```PowerShell
cd "<CAMINHO_DA_PASTA_DO_ARQUIVO>"
$nome = "<NOME_DO_ARQUIVO>"; ffmpeg -i "$nome.mp3" -f segment -segment_time 02:30:00 -ac 1 -ar 16000 -c:a pcm_s16le "$($nome)_parte_%03d.wav"
```

Os arquivos divididos em partes (IDxx_parte_000.wav, IDxx_parte_001.wav, ...) são detectados automaticamente no Bloco 3: cada parte é transcrita (as que já têm transcrição são puladas) e os textos são consolidados em IDxx_transcricao_final.txt.

## Execução no Google Colab
Para rodar os notebooks, siga estas configurações críticas para garantir o uso da GPU e evitar erros de memória.

### 1. Configuração do Ambiente
Ativar GPU (obrigatório): Vá no menu Runtime (Ambiente de execução) > Change runtime type (Alterar tipo de ambiente de execução) e selecione T4 GPU. A transcrição roda apenas em GPU (CUDA); não há suporte a CPU, e o código interrompe com uma mensagem de erro se nenhuma GPU for detectada.

### 2. Limpeza de Cache: Se encontrar erros estranhos de biblioteca, use Runtime > Disconnect and delete runtime para limpar a máquina virtual e começar do zero.

### 3. Fluxo de Execução
Execute o Bloco 1 (instalação) uma vez por runtime e siga direto para o Bloco 2. Não é necessário reiniciar a sessão.

> [!NOTE]
> Não instale numpy, torch nem WhisperX manualmente: o Colab já traz o que é preciso, e esses pacotes entram em conflito. O pacote `av` tem teto de versão (`av<19`) por incompatibilidade com o faster-whisper 1.2.1; veja o comentário no Bloco 1.

## Publicação em lote no Notion (backlog)
Para publicar no Notion as crônicas de sessões antigas, use `notebooks/backlog_notion.ipynb`.
O lote lê os arquivos `{ID_MESA}<num>_cronica.md` da pasta do projeto no Drive, pula as sessões que já existem no Notion (sem sobrescrever) e aplica `DEFAULT_DATE` a todas as publicadas. Se a consulta ao Notion falhar, nada é publicado.

## Estrutura de Arquivos Gerados
* IDxxw.wav: Áudio convertido (Entrada).
* IDxx_transcricao_final_parte_NNN.txt: Transcrição de cada parte (mantida após a consolidação)
* IDxx_transcricao_final.txt: Texto bruto gerado pelo Whisper.
* IDxx_cronica.md: Texto narrativo final gerado pelo Gemini.