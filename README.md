#DaVinci Boladão

Solução para deixar o davinci resolve linux mais leve em pc fraco e aumentar compatibilidade

##Uso

Substitua os caminhos nos scripts para os caminhos do seu PC e altere as configurações

####VIDEO_EXTENSIONS ou EXTENSOES_VIDEO

Extensões de arquivos que serão tratadas pelo programa


####MONITORAR_SUBPASTAS

Checa alterações em todos os diretórios dentro da pasta escolhida

####SUBSTITUIR_ORIGINAL

Apaga o arquivo original antes da checagem. Recomendado desabilitar e checar pra ver se o resultado ficou bom antes de apagar o arquivo (dependendo do codec. Pra alguns tipos não tem perigo e pode habilitar)

####PROCESSAR_EXISTENTES

Converte tudo o que tem não pasta previamente e não só os arquivos novos

### --- CONFIGURAÇÕES DE VÍDEO ---
####PERFIL_VIDEO_ESCOLHIDO

Qual setup de codec de video ou audio e qual container

####PERFIS_VIDEO

#####vp9_mkv

Codec vp9 opensource e compatível, mas pesado. Audio puro. Container matroska porque tem compatibilidade pra várias combinações

#####av1_mkv

Codec av1 opensource e compatível, mas pesado (menos que o vp9). Audio puro. Container matroska porque tem compatibilidade pra várias combinações

#####h264_mov

Codec h264 proprietário e incompatível, pesado (menos que o av1). Audio puro. Container quicktime (não lembro o motivo). Reza a lenda que funciona instalando o plugin FFMPEG no DaVinci

#####mpeg4_mov

O mais delicinha de todos, leve, compatível e não deixa os arquivos grandes demais, Codec MPEG4. Audio puro. Container quicktime.
(!!!!Aviso, por algum motivo alguns dos vídeos convertidos apresentam glitches visuais, se for usar faça a conferência depois)
(Quem souber qual é o problema avise por favor)

#####copy_remux

Mantém o Codec e só converte o audio e muda o container

#####Outras opções

Você também pode usar o Codec prores_ks, ele é compatível e o mais leve de todos, porém consome muito armazenamento
Não disponível nas opções por padrão


### --- CONFIGURAÇÕES DE ÁUDIO ---

####EXTENSOES_AUDIO

Quais exensões são tratadas pelo programa

####PERFIL_AUDIO_ALVO

Por padrão vem:
{'ext': '.wav', 'acodec': 'pcm_s16le', 'ar': '48000'}

você pode alterar principalmente o parâmetro 'ar': '48000', padrão 48 kHz

### --- CONFIGURAÇÕES DE IMAGEM ---

####EXTENSOES_IMAGEM

Quais extensões são tratadas pelo programa

####PERFIL_IMAGEM_ALVO

Pra qual formato é convertido

### Proxies

Coloque o caminho de geração no mesmo diretório configurado no DaVinci. As vezes ele vincula automaticamente, mas caso não aconteça vincule manualmente clicando com o botão direito na midia em Media Pool e relink proxy media

Não esqueça de escolher a opção prefer camera originals antes de renderizar

