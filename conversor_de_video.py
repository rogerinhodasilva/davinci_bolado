import ffmpeg
import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from PIL import Image

# Para garantir suporte a .avif no Pillow, instale: pip install pillow-avif-plugin
try:
    import pillow_avif
except ImportError:
    pass

# --- CONFIGURAÇÕES ---
PASTA_MONITORADA = '/media/user/SSD/Edicoes/Trabalhos/Expense Ratio/'
MONITORAR_SUBPASTAS = True
SUBSTITUIR_ORIGINAL = True
PROCESSAR_EXISTENTES = False  # Converte o que já estava na pasta ao iniciar

# --- CONFIGURAÇÕES DE VÍDEO ---
PERFIL_VIDEO_ESCOLHIDO = 'av1_mkv'
EXTENSOES_VIDEO = ('.webm', '.mp4', '.mov', '.mkv')#
PERFIS_VIDEO = {
    'vp9_mkv': {'ext': '.mkv', 'vcodec': 'libvpx-vp9', 'acodec': 'pcm_s16le', 'crf': '30'},
    'av1_mkv': {'ext': '.mkv', 'vcodec': 'libsvtav1', 'acodec': 'pcm_s16le', 'preset': '8'},
    'h264_mov': {'ext': '.mov', 'vcodec': 'h264', 'acodec': 'pcm_s16le', 'crf': '28'},
    'mpeg4_mov': {'ext': '.mov', 'vcodec': 'mpeg4', 'acodec': 'pcm_s16le'},
    'copy_remux': {'ext': '.mkv', 'vcodec': 'copy', 'acodec': 'copy'}
}

# --- CONFIGURAÇÕES DE ÁUDIO ---
EXTENSOES_AUDIO = ('.mp3', '.m4a', '.aac', '.ogg', '.flac', '.opus')
PERFIL_AUDIO_ALVO = {'ext': '.wav', 'acodec': 'pcm_s16le', 'ar': '48000'}

# --- CONFIGURAÇÕES DE IMAGEM ---
EXTENSOES_IMAGEM = ('.webp', '.avif', '.heic', '.tiff', '.bmp', '.jpeg', '.jpg')
PERFIL_IMAGEM_ALVO = {'ext': '.png'}


class MidiaHandler(FileSystemEventHandler):
    def __init__(self):
        self.p_video = PERFIS_VIDEO[PERFIL_VIDEO_ESCOLHIDO]
        self.processando = set()

    def _precisa_converter_video(self, path):
        """Verifica se os codecs de vídeo/áudio atuais batem com o perfil."""
        if not path.lower().endswith(self.p_video['ext']):
            return True
        try:
            probe = ffmpeg.probe(path)
            v_stream = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)
            a_stream = next((s for s in probe['streams'] if s['codec_type'] == 'audio'), None)

            # Normaliza nomes de codecs para checagem
            v_codec_alvo = self.p_video['vcodec'].replace('libx264', 'h264').replace('libvpx-vp9', 'vp9').replace('libsvtav1', 'av1')
            
            v_match = v_stream and v_stream['codec_name'] == v_codec_alvo
            a_match = a_stream and a_stream['codec_name'] == self.p_video['acodec']

            return not (v_match and a_match)
        except Exception:
            return True

    def _precisa_converter_audio(self, path):
        """Verifica se o áudio já está no formato WAV PCM 16-bit desejado."""
        if not path.lower().endswith(PERFIL_AUDIO_ALVO['ext']):
            return True
        try:
            probe = ffmpeg.probe(path)
            a_stream = next((s for s in probe['streams'] if s['codec_type'] == 'audio'), None)
            
            a_match = a_stream and a_stream['codec_name'] == PERFIL_AUDIO_ALVO['acodec']
            r_match = a_stream and int(a_stream.get('sample_rate', 0)) == int(PERFIL_AUDIO_ALVO['ar'])
            
            return not (a_match and r_match)
        except Exception:
            return True

    def _precisa_converter_imagem(self, path):
        """Imagens que não sejam PNG nativo precisam ser convertidas."""
        return not path.lower().endswith(PERFIL_IMAGEM_ALVO['ext'])

    def esperar_conclusao_arquivo(self, path, timeout=600):
        tamanho_anterior = -1
        inicio = time.time()
        while time.time() - inicio < timeout:
            if not os.path.exists(path): 
                return False
            try:
                tamanho_atual = os.path.getsize(path)
                if tamanho_atual == tamanho_anterior and tamanho_atual > 0:
                    try:
                        with open(path, 'ab'): 
                            return True
                    except IOError: 
                        pass
                tamanho_anterior = tamanho_atual
            except (OSError, IOError): 
                pass
            time.sleep(1.5)
        return False

    def gerenciar_substituicao(self, input_path, output_path, ext_alvo):
        """Garante a deleção segura do original e renomeia o arquivo temporário."""
        if SUBSTITUIR_ORIGINAL:
            final_path = os.path.splitext(input_path)[0] + ext_alvo
            if os.path.exists(input_path) and input_path != final_path:
                os.remove(input_path)
            
            if os.path.exists(output_path):
                if os.path.exists(final_path) and final_path != output_path:
                    os.remove(final_path)
                os.rename(output_path, final_path)

    def converter_video(self, input_path):
        if not self._precisa_converter_video(input_path):
            print(f"Ignorando Vídeo (Codecs já compatíveis): {os.path.basename(input_path)}")
            return

        output_path = os.path.splitext(input_path)[0] + "_temp_v" + self.p_video['ext']
        try:
            print(f"\n--- Convertendo Vídeo: {os.path.basename(input_path)} ---")
            params = {'ar': '48000', 'af': 'aresample=async=1'}
            for k, v in self.p_video.items():
                if k != 'ext': 
                    params[k] = v

            ffmpeg.input(input_path).output(output_path, **params).overwrite_output().run(quiet=True)
            self.gerenciar_substituicao(input_path, output_path, self.p_video['ext'])
            print(f"Vídeo Concluído: {os.path.basename(input_path)}")
        except ffmpeg.Error as e:
            print(f"Erro no vídeo {os.path.basename(input_path)}: {e.stderr.decode() if e.stderr else e}")

    def converter_audio(self, input_path):
        if not self._precisa_converter_audio(input_path):
            print(f"Ignorando Áudio (Já está em WAV PCM 16bit): {os.path.basename(input_path)}")
            return

        output_path = os.path.splitext(input_path)[0] + "_temp_a" + PERFIL_AUDIO_ALVO['ext']
        try:
            print(f"\n--- Convertendo Áudio: {os.path.basename(input_path)} ---")
            params = {
                'acodec': PERFIL_AUDIO_ALVO['acodec'],
                'ar': PERFIL_AUDIO_ALVO['ar']
            }
            ffmpeg.input(input_path).output(output_path, **params).overwrite_output().run(quiet=True)
            self.gerenciar_substituicao(input_path, output_path, PERFIL_AUDIO_ALVO['ext'])
            print(f"Áudio Concluído: {os.path.basename(input_path)}")
        except ffmpeg.Error as e:
            print(f"Erro no áudio {os.path.basename(input_path)}: {e.stderr.decode() if e.stderr else e}")

    def converter_imagem(self, input_path):
        if not self._precisa_converter_imagem(input_path):
            return

        output_path = os.path.splitext(input_path)[0] + "_temp_i" + PERFIL_IMAGEM_ALVO['ext']
        try:
            print(f"\n--- Convertendo Imagem: {os.path.basename(input_path)} ---")
            with Image.open(input_path) as img:
                # Garante conversão para RGBA caso venha com canais complexos ou indexados
                if img.mode not in ('RGB', 'RGBA'):
                    img = img.convert('RGBA')
                img.save(output_path, 'PNG')
            
            self.gerenciar_substituicao(input_path, output_path, PERFIL_IMAGEM_ALVO['ext'])
            print(f"Imagem Concluída: {os.path.basename(input_path)}")
        except Exception as e:
            print(f"Erro na imagem {os.path.basename(input_path)}: {e}")

    def processar_arquivo(self, input_path):
        filename = os.path.basename(input_path)
        
        # Ignora arquivos temporários criados pelo próprio script
        if "_temp_" in filename:
            return

        path_lower = input_path.lower()
        
        # Identifica o tipo de mídia
        if path_lower.endswith(EXTENSOES_VIDEO):
            tipo = 'video'
        elif path_lower.endswith(EXTENSOES_AUDIO):
            tipo = 'audio'
        elif path_lower.endswith(EXTENSOES_IMAGEM):
            tipo = 'imagem'
        else:
            return

        if input_path in self.processando:
            return

        if not self.esperar_conclusao_arquivo(input_path):
            return

        self.processando.add(input_path)

        try:
            if tipo == 'video':
                self.converter_video(input_path)
            elif tipo == 'audio':
                self.converter_audio(input_path)
            elif tipo == 'imagem':
                self.converter_imagem(input_path)
        finally:
            if input_path in self.processando:
                self.processando.remove(input_path)

    def on_created(self, event):
        if event.is_directory:
            for root, _, files in os.walk(event.src_path):
                for f in files:
                    self.processar_arquivo(os.path.join(root, f))
        else:
            self.processar_arquivo(event.src_path)

    def on_moved(self, event):
        if event.is_directory:
            for root, _, files in os.walk(event.dest_path):
                for f in files:
                    self.processar_arquivo(os.path.join(root, f))
        else:
            self.processar_arquivo(event.dest_path)


def scan_inicial(handler):
    print("Efetuando varredura inicial...")
    for root, _, files in os.walk(PASTA_MONITORADA):
        for f in files:
            handler.processar_arquivo(os.path.join(root, f))
    print("Varredura inicial concluída.\n")

def inspecao_de_pasta():
    handler = MidiaHandler()
    if PROCESSAR_EXISTENTES:
        scan_inicial(handler)

    observer = Observer()
    observer.schedule(handler, PASTA_MONITORADA, recursive=MONITORAR_SUBPASTAS)
    observer.start()
    print(f"Monitorando mídias (Vídeos, Áudios e Imagens) em: {PASTA_MONITORADA}")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    inspecao_de_pasta()