import ffmpeg
import os
import threading
from scanner_de_projetos import DavinciMonitor
from conversor_de_video import inspecao_de_pasta

# Configurações de Caminho
caminho_proxies_base = '/media/user/Data/Edicoes/Davinci_Resolve/ProxyMedia'
VIDEO_EXTENSIONS = ('.mp4', '.mkv', '.mov', '.webm')

def get_video_info(path):
    """Extrai FPS e Timecode com fallback para erros de leitura."""
    try:
        probe = ffmpeg.probe(path)
        video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
        
        if not video_stream:
            return 24, '00:00:00:00'

        fps_eval = video_stream.get('avg_frame_rate', '24/1')
        n, d = map(int, fps_eval.split('/'))
        fps = n / d if d != 0 else 24
        
        tags = video_stream.get('tags', {})
        tmcd = tags.get('timecode', '00:00:00:00')
        return fps, tmcd
    except Exception:
        return 24, '00:00:00:00'

def generate_proxy(input_path):
    """Pipeline: Valida entrada -> Valida existência de Proxy -> Gera Proxy."""
    
    # 1. Validação de Entrada: Ignora se o arquivo original sumiu do disco
    if not input_path or not os.path.exists(input_path):
        return

    # 2. Filtro de Extensão
    if not input_path.lower().endswith(VIDEO_EXTENSIONS):
        return

    # --- LÓGICA DE CAMINHOS CORRIGIDA ---
    file_name = os.path.basename(input_path)
    file_name_no_ext = os.path.splitext(file_name)[0]
    
    # Remove a primeira barra do caminho original para concatenar corretamente
    # Ex: /home/user/video.mp4 vira home/user/video.mp4
    relative_path = input_path.lstrip('/') 
    
    # Define o diretório de saída espelhando a estrutura original dentro da base de proxies
    output_dir = os.path.join(caminho_proxies_base, os.path.dirname(relative_path))
    output_path = os.path.join(output_dir, f"{file_name_no_ext}.mov")

    # 3. Checagem de Existência do Proxy (Onde estava falhando)
    if os.path.exists(output_path):
        # Opcional: print(f"[SKIP] Proxy já existe para: {file_name}")
        return

    # 4. Preparação para Geração
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    fps, tmcd = get_video_info(input_path)
    target_fps = 24 if fps < 23.9 else fps

    print(f"-> Gerando proxy: {file_name} ({target_fps} fps)")

    try:
        (
            ffmpeg
            .input(input_path)
            .output(
                output_path,
                vcodec='prores_ks',
                profile=0, # Proxy
                pix_fmt='yuv422p',
                vf='scale=-2:480', 
                r=str(target_fps),
                acodec='pcm_s16le',
                ar='48000',
                timecode=tmcd,
                metadata='write_tmcd=1',
                movflags='faststart'
            )
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        print(f"   [OK] {file_name}")
    except ffmpeg.Error as e:
        err_msg = e.stderr.decode() if e.stderr else str(e)
        print(f"   [ERRO] Falha no FFmpeg para {file_name}: {err_msg[:100]}...")

if __name__ == "__main__":
    monitor = DavinciMonitor()

    # Inicia thread de inspeção
    threading.Thread(target=inspecao_de_pasta, daemon=True).start()
    print("[THREAD] Monitor de pastas ativo.")

    nome_projeto = monitor.find_active_project()
    print(f"Projeto: {nome_projeto}")

    # Processamento Inicial
    iniciais = monitor.get_initial_queue()
    if iniciais:
        # Filtra apenas o que realmente existe antes de processar
        existentes = [f for f in iniciais if os.path.exists(f)]
        print(f"Sincronizando {len(existentes)} arquivos da timeline...")
        for arquivo in existentes:
            generate_proxy(arquivo)

    monitor.start_watching()
    print("\n--- Aguardando novos clipes ---")

    try:
        while True:
            novo_arquivo = monitor.get_next_new()
            if novo_arquivo:
                generate_proxy(novo_arquivo)
    except KeyboardInterrupt:
        print("\nEncerrando...")
        monitor.stop()