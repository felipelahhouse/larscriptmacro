import win32api
import win32con
import win32gui
import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
import ultralytics
import threading
import math
import time
import cv2
import mss
import sys
import os
import torch
import colorsys
import hashlib
import subprocess
import requests
from datetime import datetime, timedelta
import tempfile
import shutil
import zipfile

# 🔄 SISTEMA DE ATUALIZAÇÃO AUTOMÁTICA
CURRENT_VERSION = "1.0.0"
GITHUB_REPO = "felipelahhouse/larscriptmacro"  # Seu repositório GitHub
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
UPDATE_CHECK_FILE = "last_update_check.txt"

# KEYAUTH IMPORTS E SETUP
try:
    from keyauth import api

    def getchecksum():
        try:
            return hashlib.md5(open(sys.executable, 'rb').read()).hexdigest()
        except Exception:
            return "debug_mode"

    # Inicializar KeyAuth com suas credenciais reais
    keyauthapp = api.Keyauth(
        name = "Lars Macro", # App name 
        owner_id = "MJybaINWSR", # Account ID
        secret = "633bd926e661b6167426af61c08fe7a6a8b399d09fab0fcca559d46d4f8db723", # App secret
        version = "1.0", # Application version
        file_hash = getchecksum()
    )
    
    KEYAUTH_ENABLED = True
    print("✅ KeyAuth carregado com sucesso!")
except ImportError as e:
    print("⚠️ KeyAuth não encontrado - modo desenvolvimento")
    print(f"Erro: {e}")
    KEYAUTH_ENABLED = False
    keyauthapp = None
except Exception as e:
    print("⚠️ KeyAuth em modo desenvolvimento (credenciais inválidas)")
    print(f"Detalhes: {e}")
    # Continuar em modo desenvolvimento
    KEYAUTH_ENABLED = False
    keyauthapp = None

# 🔄 SISTEMA DE ATUALIZAÇÃO AUTOMÁTICA
class AutoUpdater:
    def __init__(self):
        self.current_version = CURRENT_VERSION
        self.github_repo = GITHUB_REPO
        self.api_url = GITHUB_API_URL
        self.update_available = False
        self.latest_version = None
        self.download_url = None
        self.release_notes = None
        self.checking = False
        
    def check_for_updates(self, silent=False):
        """Verifica se há atualizações disponíveis no GitHub."""
        if self.checking:
            return False
            
        self.checking = True
        try:
            print(f"🔍 Verificando atualizações... (Versão atual: {self.current_version})")
            
            # Fazer requisição à API do GitHub
            headers = {'User-Agent': 'LarsAimbot-Updater'}
            response = requests.get(self.api_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                release_data = response.json()
                
                # Extrair informações da release
                self.latest_version = release_data.get('tag_name', '').replace('v', '')
                self.release_notes = release_data.get('body', 'Sem notas de atualização.')
                
                # Procurar asset .exe ou .zip
                assets = release_data.get('assets', [])
                for asset in assets:
                    name = asset.get('name', '').lower()
                    if name.endswith('.exe') or name.endswith('.zip'):
                        self.download_url = asset.get('browser_download_url')
                        break
                
                # Comparar versões
                if self._compare_versions(self.latest_version, self.current_version):
                    self.update_available = True
                    print(f"✅ Nova versão disponível: {self.latest_version}")
                    if not silent:
                        self._show_update_notification()
                    return True
                else:
                    self.update_available = False
                    print(f"✅ Você está na versão mais recente!")
                    if not silent:
                        messagebox.showinfo(
                            "Atualização",
                            f"✅ Você já está usando a versão mais recente!\n\nVersão atual: {self.current_version}"
                        )
                    return False
            else:
                print(f"⚠️ Erro ao verificar atualizações: HTTP {response.status_code}")
                if not silent:
                    messagebox.showwarning(
                        "Erro de Atualização",
                        "Não foi possível verificar atualizações.\nVerifique sua conexão com a internet."
                    )
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Erro de conexão ao verificar atualizações: {e}")
            if not silent:
                messagebox.showerror(
                    "Erro de Conexão",
                    "Não foi possível conectar ao servidor de atualizações.\nVerifique sua internet."
                )
            return False
        except Exception as e:
            print(f"❌ Erro inesperado ao verificar atualizações: {e}")
            if not silent:
                messagebox.showerror(
                    "Erro",
                    f"Erro inesperado ao verificar atualizações:\n{str(e)}"
                )
            return False
        finally:
            self.checking = False
    
    def _compare_versions(self, latest, current):
        """Compara duas versões (formato: x.y.z)."""
        try:
            latest_parts = [int(x) for x in latest.split('.')]
            current_parts = [int(x) for x in current.split('.')]
            
            # Preencher com zeros se necessário
            while len(latest_parts) < 3:
                latest_parts.append(0)
            while len(current_parts) < 3:
                current_parts.append(0)
            
            return latest_parts > current_parts
        except:
            return False
    
    def _show_update_notification(self):
        """Mostra notificação de atualização disponível."""
        message = f"🎉 Nova versão disponível!\n\n"
        message += f"Versão atual: {self.current_version}\n"
        message += f"Nova versão: {self.latest_version}\n\n"
        message += f"📝 Novidades:\n{self.release_notes[:200]}..."
        
        result = messagebox.askyesno(
            "Atualização Disponível",
            message + "\n\nDeseja atualizar agora?",
            icon='info'
        )
        
        if result:
            self.download_and_install_update()
    
    def download_and_install_update(self):
        """Baixa e instala a atualização."""
        if not self.download_url:
            messagebox.showerror(
                "Erro",
                "URL de download não encontrada."
            )
            return
        
        try:
            # Criar janela de progresso
            progress_window = tk.Toplevel()
            progress_window.title("Baixando Atualização")
            progress_window.geometry("400x150")
            progress_window.configure(bg=ModernTheme.BG_DARK)
            progress_window.resizable(False, False)
            
            # Centralizar janela
            progress_window.update_idletasks()
            x = (progress_window.winfo_screenwidth() // 2) - (400 // 2)
            y = (progress_window.winfo_screenheight() // 2) - (150 // 2)
            progress_window.geometry(f"+{x}+{y}")
            
            status_label = tk.Label(
                progress_window,
                text="Baixando atualização...",
                font=("Segoe UI", 10),
                fg=ModernTheme.TEXT_WHITE,
                bg=ModernTheme.BG_DARK
            )
            status_label.pack(pady=20)
            
            progress_bar = ttk.Progressbar(
                progress_window,
                mode='indeterminate',
                length=350
            )
            progress_bar.pack(pady=10)
            progress_bar.start(10)
            
            def download_thread():
                try:
                    # Baixar arquivo
                    response = requests.get(self.download_url, stream=True, timeout=30)
                    response.raise_for_status()
                    
                    # Salvar em arquivo temporário
                    temp_dir = tempfile.gettempdir()
                    file_ext = '.exe' if self.download_url.endswith('.exe') else '.zip'
                    temp_file = os.path.join(temp_dir, f'lars_update{file_ext}')
                    
                    with open(temp_file, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                    
                    progress_window.destroy()
                    
                    # Perguntar se quer instalar agora
                    result = messagebox.askyesno(
                        "Download Completo",
                        f"✅ Atualização baixada com sucesso!\n\n"
                        f"O programa será fechado e a atualização será instalada.\n\n"
                        f"Deseja continuar?",
                        icon='info'
                    )
                    
                    if result:
                        # Executar instalador e fechar programa
                        if file_ext == '.exe':
                            subprocess.Popen([temp_file])
                        else:
                            # Extrair ZIP e executar
                            extract_dir = os.path.join(temp_dir, 'lars_update_extracted')
                            with zipfile.ZipFile(temp_file, 'r') as zip_ref:
                                zip_ref.extractall(extract_dir)
                            
                            # Procurar .exe no diretório extraído
                            for file in os.listdir(extract_dir):
                                if file.endswith('.exe'):
                                    subprocess.Popen([os.path.join(extract_dir, file)])
                                    break
                        
                        # Fechar aplicação atual
                        sys.exit(0)
                    
                except Exception as e:
                    progress_window.destroy()
                    messagebox.showerror(
                        "Erro de Download",
                        f"Erro ao baixar atualização:\n{str(e)}"
                    )
            
            threading.Thread(target=download_thread, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror(
                "Erro",
                f"Erro ao preparar download:\n{str(e)}"
            )
    
    def check_on_startup(self):
        """Verifica atualizações no startup (máximo 1x por dia)."""
        try:
            # Verificar última verificação
            if os.path.exists(UPDATE_CHECK_FILE):
                with open(UPDATE_CHECK_FILE, 'r') as f:
                    last_check = f.read().strip()
                    last_check_date = datetime.fromisoformat(last_check)
                    
                    # Se já verificou hoje, não verificar novamente
                    if (datetime.now() - last_check_date).days < 1:
                        return
            
            # Verificar atualizações silenciosamente
            threading.Thread(target=lambda: self.check_for_updates(silent=True), daemon=True).start()
            
            # Salvar data da verificação
            with open(UPDATE_CHECK_FILE, 'w') as f:
                f.write(datetime.now().isoformat())
                
        except Exception as e:
            print(f"⚠️ Erro ao verificar atualizações no startup: {e}")

# Instância global do updater
auto_updater = AutoUpdater()

# 🌈 CLASSE PARA EFEITOS RGB MODERNOS (disponível sempre)
class RGBEffects:
    def __init__(self):
        self.hue = 0
        self.rgb_active = True

    def get_rgb_color(self):
        if not self.rgb_active:
            return "#9333ea"
        r, g, b = colorsys.hsv_to_rgb(self.hue / 360.0, 1.0, 1.0)
        return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"

    def update_hue(self):
        self.hue = (self.hue + 2) % 360

    def toggle_rgb(self):
        self.rgb_active = not self.rgb_active

# 🎨 TEMA PROFISSIONAL ROXO ESCURO E DOURADO
class ModernTheme:
    """🎨 TEMA ULTRA MODERNO V2 - CYBER NEON"""
    # Cores de fundo com gradiente cyberpunk
    BG_DARK = "#0d0d1a"      # Preto azulado profundo
    BG_MEDIUM = "#1a1a2e"    # Azul escuro
    BG_LIGHT = "#252545"     # Roxo escuro
    BG_CARD = "#16213e"      # Azul card
    
    # Cores de destaque neon
    NEON_PURPLE = "#a855f7"  # Roxo neon
    NEON_BLUE = "#3b82f6"    # Azul neon
    NEON_CYAN = "#22d3ee"    # Ciano neon
    NEON_PINK = "#ec4899"    # Rosa neon
    NEON_GREEN = "#10b981"   # Verde neon
    
    # Cores principais
    GOLD = "#fbbf24"         # Dourado moderno
    GOLD_DARK = "#d97706"    # Dourado escuro
    GOLD_LIGHT = "#fef3c7"   # Dourado claro
    
    # Texto
    TEXT_WHITE = "#f8fafc"
    TEXT_GRAY = "#94a3b8"
    TEXT_DARK = "#64748b"
    
    # Status
    SUCCESS = "#22c55e"      # Verde sucesso
    ERROR = "#ef4444"        # Vermelho erro
    WARNING = "#f59e0b"      # Laranja aviso
    INFO = "#06b6d4"         # Ciano info
    
    # Bordas e efeitos
    RGB_BORDER = "#8b5cf6"   # Roxo RGB
    GLOW = "#7c3aed"         # Brilho
    
    # Gradientes (para referência)
    GRADIENT_START = "#667eea"
    GRADIENT_END = "#764ba2"
    
    def __init__(self):
        self.hue = 0
        self.rgb_active = True
    def update_hue(self):
        self.hue = (self.hue + 2) % 360
    def toggle_rgb(self):
        self.rgb_active = not self.rgb_active
# from pubg_version.logic.config_watcher_pubg import cfg  # REMOVIDO
# from pubg_version.logic.pubg_hotkeys_watcher import pubgHotkeysWatcher  # REMOVIDO  
# from logic.checks import run_checks  # REMOVIDO

# 🔥 CONFIGURAÇÃO SIMPLES INTEGRADA
class SimpleConfig:
    def __init__(self):
        self.headshot_mode = True
        self.body_shot_mode = False
        self.activation_key = "Left Click"
        
cfg = SimpleConfig()  # Substituição simples

class PerfectAimbotConfig:
    def __init__(self):
        
        # ============================================
        # 🖥️ DETECÇÃO AUTOMÁTICA DE RESOLUÇÃO
        # ============================================
        try:
            import ctypes
            user32 = ctypes.windll.user32
            user32.SetProcessDPIAware()  # Para DPI scaling
            self.width = user32.GetSystemMetrics(0)  # Largura real da tela
            self.height = user32.GetSystemMetrics(1)  # Altura real da tela
            print(f"🖥️ Resolução detectada: {self.width}x{self.height}")
        except:
            # Fallback para 1920x1080 se falhar
            self.width = 1920
            self.height = 1080
            print("⚠️ Usando resolução padrão: 1920x1080")
        
        self.center_x = self.width // 2
        self.center_y = self.height // 2
        
        # 🔥 ÁREA DE CAPTURA PROPORCIONAL À RESOLUÇÃO
        # Captura ~25% da tela (proporcional para qualquer resolução)
        base_capture = min(self.width, self.height) // 4
        self.capture_width = max(400, min(600, base_capture + 200))
        self.capture_height = max(400, min(600, base_capture + 200))
        self.capture_left = self.center_x - self.capture_width // 2
        self.capture_top = self.center_y - self.capture_height // 2
        self.crosshairX = self.capture_width // 2  # Centro da captura
        self.crosshairY = self.capture_height // 2
        
        # 🎮 MULTIPLICADOR DE MOVIMENTO (para calibração por usuário)
        # Ajusta automaticamente baseado na resolução
        self.resolution_scale = self.width / 1920.0  # 1.0 para 1920x1080
        self.movement_multiplier = 1.0  # Usuário pode ajustar
        
        # 🔥 SISTEMA DE ARMAS E BOTÕES G4/G5
        self.current_weapon = "AR"  # AR ou DMR
        self.activation_button = "LEFT"  # LEFT ou RIGHT
        
        # 🔒 SISTEMA AIMLOCK - GRUDA NO ALVO
        self.aimlock_enabled = True  # Aimlock ativado por padrão
        self.aimlock_target = None  # Alvo travado atual
        self.aimlock_sticky = True  # Mantém no alvo mesmo se sair do FOV
        
        # 👁️ SISTEMA ESP - DESATIVADO (causava problemas visuais)
        self.esp_enabled = False  # ESP desativado
        self.esp_boxes = False  # Desativado
        self.esp_lines = False  # Desativado
        self.esp_distance = False  # Desativado
        self.esp_health = False  # Mostrar vida (se disponível)
        self.last_detections = []  # Últimas detecções para ESP
        
        # 🔥 CONFIGURAÇÕES AR V4 - SENSIBILIDADE BAIXA PARA PRECISÃO
        self.ar_config = {
            "sensitivity": 0.5,  # BAIXO - para grudar melhor
            "MovementCoefficientX": 0.6,  # Movimento suave
            "MovementCoefficientY": 0.5,  # Movimento suave vertical
            "movementSteps": 1,  # MOVIMENTO ÚNICO
            "delay": 0.0,  # SEM DELAY
            "radius": 400,  # FOV para detectar
            "confidence_threshold": 0.15,  # Detecção sensível
            "head_offset_factor": 0.18,  # Offset para pescoço/peito superior
            "target_body_part": "head",  # Parte do corpo alvo (head, chest, auto, etc)
            "recoil_control": True,
            "recoil_strength": 3.0,  # RECOIL FORTE para compensar subida
            "smooth_factor": 0.85,  # Smooth alto = mais grudado
            "acceleration": 1.2,  # Aceleração moderada
            "prediction_enabled": True,
            "aimlock_strength": 0.9  # Força do aimlock (0.0-1.0)
        }
        
        self.dmr_config = {
            "sensitivity": 0.4,  # BAIXO - para headshots precisos
            "MovementCoefficientX": 0.5,  # Movimento preciso
            "MovementCoefficientY": 0.45,  # Movimento preciso vertical
            "movementSteps": 1,  # MOVIMENTO ÚNICO
            "delay": 0.0,  # SEM DELAY
            "radius": 350,  # FOV para DMR
            "confidence_threshold": 0.18,  # Detecção precisa
            "head_offset_factor": 0.10,  # Offset para cabeça
            "target_body_part": "head",  # HEADSHOT
            "recoil_control": True,
            "recoil_strength": 1.5,  # Recoil para DMR
            "smooth_factor": 0.90,  # Smooth muito alto = super grudado
            "acceleration": 1.0,  # Sem aceleração para precisão
            "prediction_enabled": True,
            "aimlock_strength": 0.95  # Força do aimlock alta para DMR
        }
        
        # CONFIGURAÇÕES DE PARTES DO CORPO - OFFSETS PIXEL PERFECT V2
        # Offsets calculados para precisão máxima em cada parte do corpo
        # Valores baseados em proporções anatômicas típicas de personagens de jogos
        self.body_parts = {
            # offset = percentual da altura da bounding box (0.0 = topo, 1.0 = base)
            "auto": {"offset": 0.30, "name": "🎯 AUTO (Gruda Centro/Peito)", "pixel_adjust": 0},
            "head": {"offset": 0.08, "name": "🎯 Head (Instant Kill)", "pixel_adjust": -3},  # Centro da cabeça
            "neck": {"offset": 0.15, "name": "🔴 Neck (Critical)", "pixel_adjust": 0},  # Base da cabeça/pescoço
            "upper_chest": {"offset": 0.22, "name": "💥 Upper Chest (High Damage)", "pixel_adjust": 2},  # Peito superior
            "chest": {"offset": 0.35, "name": "🎮 Chest (Good Damage)", "pixel_adjust": 0},  # Centro do peito
            "stomach": {"offset": 0.50, "name": "🟡 Stomach (Medium Damage)", "pixel_adjust": 0},  # Estômago
            "pelvis": {"offset": 0.65, "name": "🟠 Pelvis (Low Damage)", "pixel_adjust": 0},  # Quadril
            "legs": {"offset": 0.80, "name": "🦵 Legs (Safe Target)", "pixel_adjust": 5}  # Pernas superiores
        }
        
        # CONFIGURAÇÃO DE PIXEL TARGETING (novo)
        self.pixel_targeting = {
            "enabled": True,
            "head_precision": 0.95,  # Precisão extra para headshots
            "body_precision": 0.85,  # Precisão para corpo
            "micro_adjust": True,    # Micro ajustes quando perto
            "center_weight": 0.6     # Peso do centro horizontal (0.5 = centro exato)
        }
        
        # REGIÃO DE CAPTURA MSS (muito mais rápido)
        self.region = {
            "top": self.capture_top,
            "left": self.capture_left,
            "width": self.capture_width,
            "height": self.capture_height
        }

        # CONFIGURAÇÕES DE AIMBOT ULTRA RÁPIDAS
        self.Running = True
        self.AimToggle = True
        self.aimbot_enabled = True  # Atributo que estava faltando
        
        # OFFSETS DA MIRA (inicializados aqui)
        self.offset_x = 0
        self.offset_y = 0
        
        # CONFIGURAÇÕES DINÂMICAS (serão atualizadas baseado na arma)
        self.update_weapon_settings()
        
        # AUTO-LOAD DAS CONFIGURAÇÕES
        self.auto_load_on_startup()
        
        # CONFIGURAÇÕES ESPECÍFICAS PUBG OTIMIZADAS
        self.max_detections = 15
        
        # ESTADO DOS BOTÕES G4/G5, Arrow Keys e G6 (para debounce)
        self.g4_pressed = False
        self.g5_pressed = False
        self.g6_pressed = False  # Para trocar body part
        self.up_pressed = False
        self.down_pressed = False
        self.left_pressed = False
        self.right_pressed = False
        
        # 🎯 SISTEMA DE TRACKING AVANÇADO V3 - PREDICTION ATIVO
        self.last_target_pos = None
        self.target_velocity = {'x': 0, 'y': 0}
        self.tracking_history = []
        self.max_history = 10  # Mais histórico para melhor predição
        self.prediction_factor = 18.0  # Fator de predição FORTE
        
        # 🔄 SISTEMA ANTI-JITTER (evita tremidas)
        self.last_aim_x = 0
        self.last_aim_y = 0
        self.aim_smoothing_buffer = []
        self.aim_buffer_size = 3  # Últimos 3 movimentos para suavização
        
        # Métrica de desempenho
        self.last_fps = 0.0
        
    def get_current_config(self):
        """Retorna configuração da arma atual"""
        return self.ar_config if self.current_weapon == "AR" else self.dmr_config
    
    def update_tracking(self, target_x, target_y):
        """Atualiza sistema de tracking com predição de movimento"""
        current_pos = {'x': target_x, 'y': target_y, 'time': time.time()}
        
        # Adicionar à história
        self.tracking_history.append(current_pos)
        if len(self.tracking_history) > self.max_history:
            self.tracking_history.pop(0)
        
        # Calcular velocidade média suavizada se temos histórico suficiente
        if len(self.tracking_history) >= 2:
            # Usar média ponderada das últimas velocidades (mais recentes têm mais peso)
            total_vx = 0
            total_vy = 0
            total_weight = 0
            
            for i in range(1, len(self.tracking_history)):
                curr = self.tracking_history[i]
                prev = self.tracking_history[i-1]
                
                time_diff = curr['time'] - prev['time']
                if time_diff > 0 and time_diff < 0.5:  # Ignorar gaps muito grandes
                    weight = i  # Peso maior para mais recentes
                    vx = (curr['x'] - prev['x']) / time_diff
                    vy = (curr['y'] - prev['y']) / time_diff
                    
                    total_vx += vx * weight
                    total_vy += vy * weight
                    total_weight += weight
            
            if total_weight > 0:
                self.target_velocity['x'] = total_vx / total_weight
                self.target_velocity['y'] = total_vy / total_weight
        
        self.last_target_pos = current_pos
    
    def predict_target_position(self, current_x, current_y):
        """Prediz próxima posição do alvo - VERSÃO AGRESSIVA V2"""
        if len(self.tracking_history) < 2:  # Precisa de pelo menos 2 pontos
            return current_x, current_y
        
        # Calcular velocidade média
        vel_x = self.target_velocity['x']
        vel_y = self.target_velocity['y']
        
        # Limitar velocidade de predição
        max_vel = 400  # pixels por segundo (aumentado)
        vel_x = max(-max_vel, min(max_vel, vel_x))
        vel_y = max(-max_vel, min(max_vel, vel_y))
        
        # Velocidade do alvo
        speed = math.sqrt(vel_x*vel_x + vel_y*vel_y)
        
        # Fator de predição ADAPTATIVO - mais agressivo para alvos rápidos
        if speed < 30:  # Alvo parado
            adaptive_factor = 0.0  # Sem predição
        elif speed < 80:  # Movimento lento
            adaptive_factor = self.prediction_factor * 0.4
        elif speed < 150:  # Movimento médio
            adaptive_factor = self.prediction_factor * 0.7
        elif speed < 250:  # Movimento rápido
            adaptive_factor = self.prediction_factor * 1.0
        else:  # Movimento muito rápido (correndo)
            adaptive_factor = self.prediction_factor * 1.3
        
        # Frame time (ajustado para ~60fps)
        frame_time = 0.018
        
        # Prever posição futura
        predicted_x = current_x + (vel_x * frame_time * adaptive_factor)
        predicted_y = current_y + (vel_y * frame_time * adaptive_factor)
        
        return int(predicted_x), int(predicted_y)
    
    def update_weapon_settings(self):
        """Atualiza configurações baseado na arma atual"""
        current_config = self.get_current_config()
        
        self.Sensitivity = current_config["sensitivity"]
        self.MovementCoefficientX = current_config["MovementCoefficientX"]
        self.MovementCoefficientY = current_config["MovementCoefficientY"]
        self.movementSteps = current_config["movementSteps"]
        self.delay = current_config["delay"]
        self.radius = current_config["radius"]
        self.confidence_threshold = current_config["confidence_threshold"]
        self.head_offset_factor = current_config["head_offset_factor"]
        
        # Notifica overlay para atualização instantânea
        self._notify_overlay_update()
        
    def _notify_overlay_update(self):
        """Força atualização imediata do overlay (se existir)."""
        try:
            # Será preenchido pela GUI quando overlay for criado
            if hasattr(self, '_overlay_update_callback') and self._overlay_update_callback:
                self._overlay_update_callback()
        except:
            pass
    
    def toggle_weapon(self):
        """G4: Alternar entre AR e DMR"""
        self.current_weapon = "DMR" if self.current_weapon == "AR" else "AR"
        self.update_weapon_settings()
        
        # ✅ ATUALIZA OVERLAY EM TEMPO REAL
        self._notify_overlay_update()
        
        # Auto-save após mudança
        self.auto_save_settings()
        
        # Mostrar informação detalhada
        if self.current_weapon == "DMR":
            current_part = self.dmr_config["target_body_part"]
            part_info = self.body_parts[current_part]["name"]
            offset_value = self.body_parts[current_part]["offset"]
            print(f"🔫 Arma alterada para: {self.current_weapon} - {part_info} (offset: {offset_value:.2f})")
        else:
            ar_offset = self.ar_config["head_offset_factor"]
            print(f"🔫 Arma alterada para: {self.current_weapon} - Head targeting (offset: {ar_offset:.2f})")
        
        print(f"💾 Configurações salvas automaticamente!")
        # Atualização imediata do overlay
        self._notify_overlay_update()
        
    def toggle_activation_button(self):
        """G5: Alternar entre botão esquerdo e direito"""
        self.activation_button = "RIGHT" if self.activation_button == "LEFT" else "LEFT"
        print(f"🖱️ Botão de ativação alterado para: {self.activation_button}")
        self._notify_overlay_update()
    
    def adjust_crosshair_offset(self, direction, amount=2):
        """Ajustar offset do crosshair com arrow keys"""
        if direction == "up":
            self.offset_y -= amount
        elif direction == "down":
            self.offset_y += amount
        elif direction == "left":
            self.offset_x -= amount
        elif direction == "right":
            self.offset_x += amount
        
        # Limitar offset para valores razoáveis
        self.offset_x = max(-50, min(50, self.offset_x))
        self.offset_y = max(-50, min(50, self.offset_y))
        
        print(f"🎯 Crosshair Offset: X={self.offset_x}, Y={self.offset_y}")
    
    def reset_crosshair_offset(self):
        """Resetar offset do crosshair"""
        self.offset_x = 0
        self.offset_y = 0
        print("🎯 Crosshair Offset resetado para (0, 0)")
    
    def change_dmr_target(self):
        """Trocar parte do corpo para DMR"""
        parts = list(self.body_parts.keys())
        current_index = parts.index(self.dmr_config["target_body_part"])
        next_index = (current_index + 1) % len(parts)
        self.dmr_config["target_body_part"] = parts[next_index]
        
        # NÃO atualizar head_offset_factor - deixar o algoritmo usar body_parts diretamente
        # self.dmr_config["head_offset_factor"] = self.body_parts[new_part]["offset"]  # REMOVIDO
        
        # FORÇAR ATUALIZAÇÃO E SALVAR
        self.save_settings()
        
        # FORÇAR ATUALIZAÇÃO DAS CONFIGURAÇÕES
        if self.current_weapon == "DMR":
            self.update_weapon_settings()
        
        new_part = self.dmr_config["target_body_part"]
        part_name = self.body_parts[new_part]["name"]
        offset_value = self.body_parts[new_part]["offset"]
        print(f"🎯 DMR Target ALTERADO para: {part_name} (offset: {offset_value:.2f})")
        print(f"🔄 Configuração salva e aplicada!")
        
        return True
        
        # Auto-save
        self.auto_save_settings()
        
    def is_activation_pressed(self):
        """Verifica se botão de ativação está pressionado - DETECÇÃO SIMPLIFICADA"""
        try:
            if self.activation_button == "LEFT":
                # DETECÇÃO SIMPLES PARA BOTÃO ESQUERDO
                return win32api.GetAsyncKeyState(win32con.VK_LBUTTON) & 0x8000
            else:
                # BOTÃO DIREITO
                return win32api.GetAsyncKeyState(win32con.VK_RBUTTON) & 0x8000
        except:
            return False

    def save_settings(self, filename="lars_settings.json"):
        """Salva todas as configurações em arquivo JSON"""
        import json
        try:
            settings = {
                "current_weapon": self.current_weapon,
                "activation_button": self.activation_button,
                "ar_config": self.ar_config,
                "dmr_config": self.dmr_config,
                "offset_x": self.offset_x,
                "offset_y": self.offset_y,
                "aimbot_enabled": self.AimToggle  # Usar AimToggle em vez de aimbot_enabled
            }
            with open(filename, 'w') as f:
                json.dump(settings, f, indent=4)
            print(f"💾 Configurações salvas em: {filename}")
            return True
        except Exception as e:
            print(f"❌ Erro ao salvar configurações: {e}")
            return False

    def auto_save_settings(self):
        """Auto-save das configurações (silencioso)"""
        try:
            success = self.save_settings()
            if success:
                print("💾 AUTO-SAVE: Configurações salvas automaticamente!")
            return success
        except:
            return False

    def load_settings(self, filename="lars_settings.json"):
        """Carrega configurações do arquivo JSON"""
        import json
        import os
        try:
            if not os.path.exists(filename):
                print(f"⚠️ Arquivo {filename} não encontrado")
                return False
                
            with open(filename, 'r') as f:
                settings = json.load(f)
            
            # Restaurar configurações
            self.current_weapon = settings.get("current_weapon", "AR")
            self.activation_button = settings.get("activation_button", "LEFT")
            self.ar_config.update(settings.get("ar_config", {}))
            self.dmr_config.update(settings.get("dmr_config", {}))
            self.offset_x = settings.get("offset_x", 0)
            self.offset_y = settings.get("offset_y", 0)
            self.aimbot_enabled = settings.get("aimbot_enabled", True)
            self.AimToggle = settings.get("aimbot_enabled", True)  # Sincronizar com AimToggle
            
            # Atualizar configurações atuais
            self.update_weapon_settings()  # Corrigido: usar função que existe
            print(f"✅ Configurações carregadas de: {filename}")
            return True
        except Exception as e:
            print(f"❌ Erro ao carregar configurações: {e}")
            return False

    def auto_load_on_startup(self):
        """Carrega automaticamente as configurações na inicialização"""
        import os
        if os.path.exists("lars_settings.json"):
            success = self.load_settings()
            if success:
                print("🚀 AUTO-LOAD: Configurações carregadas automaticamente!")
            else:
                print("⚠️ AUTO-LOAD: Falha ao carregar - usando configurações padrão")
        else:
            print("💡 AUTO-LOAD: Nenhum arquivo encontrado - usando configurações padrão")

config = PerfectAimbotConfig()

# ===========================================
# SISTEMA DE AUTENTICAÇÃO KEYAUTH
# ===========================================

class LoginInterface:
    def __init__(self):
        self.authenticated = False
        self.user_data = None
        self.login_window = None
        self.hue_offset = 0
        
    def calculate_expiry_info(self, user_info):
        """Calcula informações detalhadas sobre expiração da licença"""
        try:
            username = user_info.get('username', 'User')
            
            # Tentar obter timestamp de expiração de diferentes formas
            expiry_timestamp = None
            
            # Método 1: subscriptions array
            if 'subscriptions' in user_info and user_info['subscriptions']:
                sub = user_info['subscriptions'][0] if isinstance(user_info['subscriptions'], list) else user_info['subscriptions']
                expiry_timestamp = sub.get('expiry', 0)
            
            # Método 2: campo direto expiry
            if not expiry_timestamp and 'expiry' in user_info:
                expiry_timestamp = user_info.get('expiry', 0)
                
            # Método 3: subscription_expiry
            if not expiry_timestamp and 'subscription_expiry' in user_info:
                expiry_timestamp = user_info.get('subscription_expiry', 0)
            
            print(f"🔍 Debug - Expiry timestamp: {expiry_timestamp}")
            print(f"🔍 Debug - User info keys: {list(user_info.keys())}")
            
            if expiry_timestamp and str(expiry_timestamp) != "0":
                try:
                    # Converter para int se for string
                    if isinstance(expiry_timestamp, str):
                        expiry_timestamp = int(expiry_timestamp)
                    
                    # Criar datetime a partir do timestamp
                    expiry_date = datetime.fromtimestamp(expiry_timestamp)
                    current_date = datetime.now()
                    
                    # Calcular diferença
                    time_diff = expiry_date - current_date
                    days_left = time_diff.days
                    hours_left = time_diff.seconds // 3600
                    
                    # Verificar se expirou
                    if days_left < 0:
                        raise Exception("License has expired")
                    
                    # Determinar status da licença
                    if days_left > 30:
                        status = "🟢 ACTIVE"
                        status_color = "#4CAF50"
                    elif days_left > 7:
                        status = "🟡 EXPIRING SOON"
                        status_color = "#FF9800"
                    else:
                        status = "🔴 EXPIRES VERY SOON"
                        status_color = "#f44336"
                    
                    # Formato de expiração mais detalhado
                    expiry_str = expiry_date.strftime('%d/%m/%Y at %H:%M')
                    
                    return {
                        'username': username,
                        'expiry_date': expiry_str,
                        'expiry_timestamp': expiry_timestamp,
                        'days_left': days_left,
                        'hours_left': hours_left,
                        'status': status,
                        'status_color': status_color,
                        'is_lifetime': False
                    }
                    
                except Exception as e:
                    print(f"❌ Erro ao processar timestamp: {e}")
                    # Fallback para lifetime se erro
                    pass
            
            # Se chegou aqui, é lifetime ou não tem data de expiração
            return {
                'username': username,
                'expiry_date': 'Lifetime',
                'expiry_timestamp': 0,
                'days_left': 999999,
                'hours_left': 0,
                'status': '♾️ LIFETIME',
                'status_color': '#9C27B0',
                'is_lifetime': True
            }
            
        except Exception as e:
            print(f"❌ Erro em calculate_expiry_info: {e}")
            # Retorno de emergência
            return {
                'username': 'User',
                'expiry_date': 'Unknown',
                'expiry_timestamp': 0,
                'days_left': 0,
                'hours_left': 0,
                'status': '❓ UNKNOWN',
                'status_color': '#757575',
                'is_lifetime': False
            }
        
    def create_login_window(self):
        """Cria interface de login animada com RGB"""
        self.login_window = tk.Tk()
        self.login_window.title("🔐 LARS SERVICE AIM - Authentication")
        self.login_window.geometry("500x700")
        self.login_window.configure(bg='#0a0a0a')
        self.login_window.resizable(False, False)
        
        # Centralizar janela
        self.login_window.eval('tk::PlaceWindow . center')
        
        # Remover barra de título (opcional)
        # self.login_window.overrideredirect(True)
        
        # HEADER COM RGB ANIMADO
        header_frame = tk.Frame(self.login_window, bg='#1a1a2e', height=80)
        header_frame.pack(fill='x')
        header_frame.pack_propagate(False)
        
        # BORDAS RGB ANIMADAS
        rgb_border_top = tk.Frame(self.login_window, bg='#9333ea', height=4)
        rgb_border_top.pack(fill='x')
        
        # LOGO E TÍTULO
        logo_frame = tk.Frame(header_frame, bg='#1a1a2e')
        logo_frame.pack(expand=True, fill='both')
        
        title_label = tk.Label(logo_frame, text="🎯 LARS SERVICE AIM", 
                              font=("Segoe UI", 18, "bold"), 
                              fg='#ffd700', bg='#1a1a2e')
        title_label.pack(pady=10)
        
        subtitle_label = tk.Label(logo_frame, text="Professional Targeting System", 
                                 font=("Segoe UI", 10), 
                                 fg='#cccccc', bg='#1a1a2e')
        subtitle_label.pack()
        
        # CONTAINER PRINCIPAL
        main_frame = tk.Frame(self.login_window, bg='#0a0a0a')
        main_frame.pack(fill='both', expand=True, padx=30, pady=20)
        
        # STATUS DE CONEXÃO
        connection_frame = tk.Frame(main_frame, bg='#1a1a2e', relief='solid', bd=1)
        connection_frame.pack(fill='x', pady=(0, 20))
        
        tk.Label(connection_frame, text="🌐 CONNECTION STATUS", 
                font=("Segoe UI", 9, "bold"), fg='#ffd700', bg='#1a1a2e').pack(pady=5)
        
        self.connection_label = tk.Label(connection_frame, text="🔄 Connecting to KeyAuth servers...", 
                                        font=("Segoe UI", 8), fg='#ffaa00', bg='#1a1a2e')
        self.connection_label.pack(pady=5)
        
        # CAMPO DE LICENSE KEY
        key_frame = tk.Frame(main_frame, bg='#0a0a0a')
        key_frame.pack(fill='x', pady=10)
        
        tk.Label(key_frame, text="🔑 LICENSE KEY", 
                font=("Segoe UI", 12, "bold"), fg='#ffd700', bg='#0a0a0a').pack(anchor='w', pady=(0, 5))
        
        # Entry com estilo moderno
        entry_frame = tk.Frame(key_frame, bg='#2d2d4a', relief='solid', bd=1)
        entry_frame.pack(fill='x', pady=5)
        
        self.key_entry = tk.Entry(entry_frame, font=("Consolas", 11), 
                                 bg='#2d2d4a', fg='white', bd=0, 
                                 insertbackground='#ffd700')
        self.key_entry.pack(fill='x', padx=10, pady=8)
        self.key_entry.bind('<Return>', lambda e: self.authenticate())
        
        # INFORMAÇÕES DA KEY
        info_frame = tk.Frame(main_frame, bg='#1a1a2e', relief='solid', bd=1)
        info_frame.pack(fill='x', pady=10)
        
        tk.Label(info_frame, text="📊 KEY INFORMATION", 
                font=("Segoe UI", 9, "bold"), fg='#ffd700', bg='#1a1a2e').pack(pady=5)
        
        self.key_info_label = tk.Label(info_frame, text="Enter your license key to view information", 
                                      font=("Segoe UI", 8), fg='#cccccc', bg='#1a1a2e')
        self.key_info_label.pack(pady=5)
        
        self.expiry_label = tk.Label(info_frame, text="", 
                                    font=("Segoe UI", 8), fg='#cccccc', bg='#1a1a2e')
        self.expiry_label.pack(pady=2)
        
        # BOTÕES
        button_frame = tk.Frame(main_frame, bg='#0a0a0a')
        button_frame.pack(fill='x', pady=20)
        
        # Botão Authenticate
        self.auth_button = tk.Button(button_frame, text="🔐 AUTHENTICATE", 
                                    command=self.authenticate,
                                    bg='#4CAF50', fg='white', 
                                    font=("Segoe UI", 12, "bold"),
                                    relief='flat', bd=0, pady=12,
                                    activebackground='#45a049')
        self.auth_button.pack(fill='x', pady=5)
        
        # Botão Exit
        exit_button = tk.Button(button_frame, text="❌ EXIT", 
                               command=self.exit_application,
                               bg='#f44336', fg='white', 
                               font=("Segoe UI", 10, "bold"),
                               relief='flat', bd=0, pady=8,
                               activebackground='#d32f2f')
        exit_button.pack(fill='x', pady=5)
        
        # FOOTER
        footer_frame = tk.Frame(self.login_window, bg='#1a1a2e', height=50)
        footer_frame.pack(fill='x', side='bottom')
        footer_frame.pack_propagate(False)
        
        footer_text = tk.Label(footer_frame, text="Protected by KeyAuth™ | Lars Service Aim v1.0", 
                              font=("Segoe UI", 8), fg='#666666', bg='#1a1a2e')
        footer_text.pack(expand=True)
        
        # BORDA RGB INFERIOR
        rgb_border_bottom = tk.Frame(self.login_window, bg='#9333ea', height=4)
        rgb_border_bottom.pack(fill='x', side='bottom')
        
        # Armazenar referências para animação RGB
        self.rgb_borders = [rgb_border_top, rgb_border_bottom]
        
        # Inicializar conexão com KeyAuth
        self.check_keyauth_connection()
        
        # Iniciar animação RGB
        self.animate_rgb_login()
        
        # Focar no campo de entrada
        self.key_entry.focus()
        
        return self.login_window
    
    def animate_rgb_login(self):
        """Animação RGB para interface de login"""
        self.hue_offset += 0.01
        if self.hue_offset > 1:
            self.hue_offset = 0
            
        # Converter HSV para RGB
        r, g, b = colorsys.hsv_to_rgb(self.hue_offset, 0.8, 0.9)
        color = f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
        
        # Atualizar bordas RGB
        for border in self.rgb_borders:
            try:
                border.config(bg=color)
            except:
                return  # Janela foi fechada
                
        # Continuar animação se janela ainda existe
        if self.login_window and self.login_window.winfo_exists():
            self.login_window.after(50, self.animate_rgb_login)
    
    def check_keyauth_connection(self):
        """Verifica conexão com KeyAuth"""
        def check():
            try:
                if KEYAUTH_ENABLED and keyauthapp:
                    # Verificar se já foi inicializado
                    if not hasattr(keyauthapp, '_initialized') or not keyauthapp._initialized:
                        keyauthapp.init()
                        keyauthapp._initialized = True
                    self.connection_label.config(text="✅ Connected to KeyAuth servers", fg='#4CAF50')
                else:
                    self.connection_label.config(text="⚠️ Development mode - KeyAuth disabled", fg='#ffaa00')
            except Exception as e:
                error_msg = str(e)
                if "already initialized" in error_msg.lower():
                    self.connection_label.config(text="✅ Connected to KeyAuth servers", fg='#4CAF50')
                else:
                    self.connection_label.config(text=f"❌ Connection failed: {str(e)[:30]}...", fg='#f44336')
        
        # Executar verificação em thread separada
        threading.Thread(target=check, daemon=True).start()
    
    def authenticate(self):
        """Realiza autenticação com KeyAuth"""
        license_key = self.key_entry.get().strip()
        
        if not license_key:
            messagebox.showerror("Error", "Please enter your license key!")
            return
        
        # Desabilitar botão durante autenticação
        self.auth_button.config(state='disabled', text='🔄 AUTHENTICATING...')
        
        def auth_thread():
            try:
                # MODO BYPASS TEMPORÁRIO - ACEITA QUALQUER KEY
                # TODO: Configurar KeyAuth corretamente
                if len(license_key) > 5:  # Qualquer key com mais de 5 caracteres
                    self.user_data = {
                        'username': 'Licensed User',
                        'expiry_date': 'Lifetime',
                        'expiry_timestamp': 0,
                        'days_left': 999999,
                        'hours_left': 0,
                        'status': '✅ ACTIVE',
                        'status_color': '#00ff88',
                        'is_lifetime': True
                    }
                    self.authenticated = True
                    
                    # Atualizar interface com sucesso
                    self.login_window.after(0, self.authentication_success)
                    return
                
                if KEYAUTH_ENABLED and keyauthapp:
                    # Tentar autenticar com KeyAuth
                    keyauthapp.license(license_key)
                    
                    # Se chegou aqui, autenticação foi bem-sucedida
                    # Criar dados do usuário a partir do KeyAuth
                    user_info = {
                        'username': getattr(keyauthapp, 'username', 'User'),
                        'subscription': getattr(keyauthapp, 'subscription', 'Unknown'),
                        'expiry': getattr(keyauthapp, 'expiry', '2099-12-31')
                    }
                    
                    # SISTEMA DE EXPIRAÇÃO MELHORADO
                    self.user_data = self.calculate_expiry_info(user_info)
                    
                    self.authenticated = True
                    
                    # Atualizar interface com sucesso
                    self.login_window.after(0, self.authentication_success)
                    
                else:
                    # Modo desenvolvimento - sempre permitir
                    if license_key.lower() in ['dev', 'debug', 'test']:
                        self.user_data = {
                            'username': 'Developer',
                            'expiry_date': 'Development Mode',
                            'expiry_timestamp': 0,
                            'days_left': 999999,
                            'hours_left': 0,
                            'status': '🚀 DEV MODE',
                            'status_color': '#00BCD4',
                            'is_lifetime': True
                        }
                        self.authenticated = True
                        self.login_window.after(0, self.authentication_success)
                    else:
                        raise Exception("KeyAuth not available - use 'dev' for testing")
                    
            except Exception as e:
                error_msg = str(e)
                if "KeyAuth" in error_msg:
                    error_msg = "Invalid license key or expired subscription"
                
                # Atualizar interface com erro
                self.login_window.after(0, lambda: self.authentication_failed(error_msg))
        
        # Executar autenticação em thread separada
        threading.Thread(target=auth_thread, daemon=True).start()
    
    def authentication_success(self):
        """Chamado quando autenticação é bem-sucedida"""
        user_data = self.user_data
        
        # Atualizar informações do usuário
        welcome_text = f"✅ Welcome, {user_data['username']}! {user_data['status']}"
        self.key_info_label.config(text=welcome_text, fg=user_data['status_color'])
        
        # Mostrar informações de expiração detalhadas
        if user_data['is_lifetime']:
            expiry_text = "♾️ Lifetime License - Never Expires!"
        else:
            if user_data['days_left'] > 0:
                if user_data['days_left'] == 1:
                    expiry_text = f"⚠️ Expires: {user_data['expiry_date']} (TOMORROW - {user_data['hours_left']}h left!)"
                else:
                    expiry_text = f"⏰ Expires: {user_data['expiry_date']} ({user_data['days_left']} days left)"
            else:
                expiry_text = f"🔴 EXPIRED: {user_data['expiry_date']}"
        
        self.expiry_label.config(text=expiry_text, fg='#cccccc')
        
        # Atualizar botão baseado no status
        if user_data['days_left'] < 3 and not user_data['is_lifetime']:
            button_text = '⚠️ AUTHENTICATED - EXPIRES SOON!'
            button_color = '#FF9800'
        else:
            button_text = '✅ AUTHENTICATED - STARTING...'
            button_color = '#4CAF50'
            
        self.auth_button.config(state='normal', text=button_text, bg=button_color)
        
        # Aguardar um pouco e fechar janela
        self.login_window.after(2000, self.close_login)
    
    def authentication_failed(self, error_msg):
        """Chamado quando autenticação falha"""
        self.auth_button.config(state='normal', text='🔐 AUTHENTICATE', bg='#4CAF50')
        messagebox.showerror("Authentication Failed", f"❌ {error_msg}\n\nPlease check your license key and try again.")
        self.key_entry.delete(0, tk.END)
        self.key_entry.focus()
    
    def close_login(self):
        """Fecha janela de login"""
        if self.login_window:
            self.login_window.destroy()
    
    def exit_application(self):
        """Sai da aplicação"""
        self.authenticated = False
        if self.login_window:
            self.login_window.destroy()
        sys.exit(0)
    
    def show_login(self):
        """Mostra interface de login e aguarda autenticação"""
        self.create_login_window()
        self.login_window.mainloop()
        return self.authenticated, self.user_data

def CreateOverlay(user_info=None, on_close_callback=None):
    """Cria a interface principal SEM ser executada em thread secundária.
    user_info: dict com dados do usuário autenticado
    on_close_callback: função chamada ao fechar janela para encerrar loops
    """
    rgb_effects = RGBEffects()
    theme = ModernTheme()
    root = tk.Tk()
    root.title("⚡ LARS AIM PRO - Cyber Targeting System")
    root.geometry('950x650')  # Tamanho otimizado
    root.configure(bg=theme.BG_DARK)
    root.minsize(900, 600)
    root.resizable(True, True)
    
    # 🌈 BORDA RGB NEON SUPERIOR
    rgb_border_top = tk.Frame(root, bg=theme.NEON_PURPLE, height=3)
    rgb_border_top.pack(fill='x', side='top')
    
    # 🎨 HEADER CYBER MODERNO
    header_frame = tk.Frame(root, bg=theme.BG_CARD, height=70)
    header_frame.pack(fill='x', padx=10, pady=(5, 8))
    header_frame.pack_propagate(False)
    
    # CONTAINER HORIZONTAL PARA TÍTULO E INFORMAÇÕES DO USUÁRIO
    header_content = tk.Frame(header_frame, bg=theme.BG_CARD)
    header_content.pack(fill='both', expand=True, pady=8, padx=15)
    
    # TÍTULO À ESQUERDA COM EFEITO NEON
    title_frame = tk.Frame(header_content, bg=theme.BG_CARD)
    title_frame.pack(side='left', fill='y')
    
    title_label = tk.Label(title_frame, 
                          text="⚡ LARS AIM PRO", 
                          font=("Segoe UI", 18, "bold"), 
                          fg=theme.NEON_CYAN, 
                          bg=theme.BG_CARD)
    title_label.pack(anchor='w', pady=2)
    
    version_label = tk.Label(title_frame, 
                            text=f"🎮 Cyber Targeting System v{CURRENT_VERSION}", 
                            font=("Segoe UI", 9), 
                            fg=theme.TEXT_GRAY, 
                            bg=theme.BG_CARD)
    version_label.pack(anchor='w')
    
    # INFORMAÇÕES DO USUÁRIO À DIREITA
    # user_info já recebido como argumento (evita acessar main.user_data em outros threads)
    if user_info:
        # FRAME DO USUÁRIO À DIREITA COM BORDA NEON
        user_frame = tk.Frame(header_content, bg=theme.BG_CARD)
        user_frame.pack(side='right', fill='y', padx=(10, 0))
        
        # INFORMAÇÕES DO USUÁRIO (linha 1 - usuário e status)
        user_top_frame = tk.Frame(user_frame, bg=theme.BG_CARD)
        user_top_frame.pack(anchor='e', pady=1)
        
        username_label = tk.Label(user_top_frame, 
                                 text=f"👤 {user_info['username']} | {user_info['status']}", 
                                 font=("Segoe UI", 10, "bold"), 
                                 fg=user_info.get('status_color', theme.NEON_GREEN), 
                                 bg=theme.BG_CARD)
        username_label.pack(anchor='e')
        
        # INFORMAÇÕES DE EXPIRAÇÃO (linha 2 - mais detalhada)
        user_bottom_frame = tk.Frame(user_frame, bg=theme.BG_MEDIUM)
        user_bottom_frame.pack(anchor='e', pady=1)
        
        if user_info['is_lifetime']:
            expiry_text = "♾️ Lifetime License"
            expiry_color = '#9C27B0'
        else:
            if user_info['days_left'] > 0:
                if user_info['days_left'] == 1:
                    expiry_text = f"⚠️ EXPIRES TOMORROW ({user_info['hours_left']}h left)"
                    expiry_color = '#f44336'
                elif user_info['days_left'] <= 7:
                    expiry_text = f" {user_info['days_left']} days left"
                    expiry_color = '#f44336'
                elif user_info['days_left'] <= 30:
                    expiry_text = f"� {user_info['days_left']} days left"
                    expiry_color = '#FF9800'
                else:
                    expiry_text = f"📅 {user_info['days_left']} days left"
                    expiry_color = '#4CAF50'
            else:
                expiry_text = f"🔴 EXPIRED"
                expiry_color = '#f44336'
        
        expiry_label = tk.Label(user_bottom_frame, 
                               text=expiry_text, 
                               font=("Segoe UI", 9), 
                               fg=expiry_color, 
                               bg=theme.BG_MEDIUM)
        expiry_label.pack(anchor='e')
    
    # FRAME PRINCIPAL COM SISTEMA DE ABAS
    main_frame = tk.Frame(root, bg=theme.BG_DARK)
    main_frame.pack(fill='both', expand=True, padx=8, pady=4)
    
    # CRIANDO NOTEBOOK (SISTEMA DE ABAS)
    style = ttk.Style()
    style.theme_use('clam')
    # 🎨 ESTILO DAS ABAS CYBER NEON
    style.configure('TNotebook', background=theme.BG_DARK, borderwidth=0)
    style.configure('TNotebook.Tab', 
                   background=theme.BG_CARD, 
                   foreground=theme.NEON_CYAN, 
                   padding=[25, 12], 
                   focuscolor='none',
                   font=('Segoe UI', 10, 'bold'))
    style.map('TNotebook.Tab', 
              background=[('selected', theme.NEON_PURPLE)], 
              foreground=[('selected', '#ffffff')])
    
    notebook = ttk.Notebook(main_frame, style='TNotebook')
    notebook.pack(fill='both', expand=True, padx=8, pady=8)
    
    # ABA 1: ULTRA CONTROLS (AR) - Fundo escuro
    ar_tab = tk.Frame(notebook, bg=theme.BG_DARK)
    notebook.add(ar_tab, text='⚡ AR CONTROLS')
    
    # ABA 2: DMR SETTINGS  - Fundo escuro
    dmr_tab = tk.Frame(notebook, bg=theme.BG_DARK)
    notebook.add(dmr_tab, text='🎯 DMR SNIPER')
    
    # ABA 3: SYSTEM STATUS - Fundo escuro
    status_tab = tk.Frame(notebook, bg=theme.BG_DARK)
    notebook.add(status_tab, text='📊 STATUS')
    
    # ABA 4: SETTINGS MANAGER - Fundo escuro
    settings_tab = tk.Frame(notebook, bg=theme.BG_DARK)
    notebook.add(settings_tab, text='⚙️ CONFIG')
    
    # ABA 5: ESP - VISUAL HACK 👁️
    esp_tab = tk.Frame(notebook, bg=theme.BG_DARK)
    notebook.add(esp_tab, text='👁️ ESP')
    
    # ===========================================
    # CONFIGURANDO ABA AR (ULTRA CONTROLS)
    # ===========================================
    
    # Header AR com gradiente neon
    ar_header = tk.Frame(ar_tab, bg=theme.NEON_BLUE, height=45)
    ar_header.pack(fill='x', padx=8, pady=8)
    ar_header.pack_propagate(False)
    
    ar_title = tk.Label(ar_header, text="⚡ ASSAULT RIFLE - TRACKING SYSTEM", 
                       font=("Segoe UI", 13, "bold"), fg='#ffffff', bg=theme.NEON_BLUE)
    ar_title.pack(pady=12)
    
    # Canvas e Scrollbar para AR
    ar_canvas = tk.Canvas(ar_tab, bg=theme.BG_DARK, highlightthickness=0)
    ar_scrollbar = ttk.Scrollbar(ar_tab, orient="vertical", command=ar_canvas.yview)
    ar_frame = tk.Frame(ar_canvas, bg=theme.BG_DARK)
    
    ar_frame.bind(
        "<Configure>",
        lambda e: ar_canvas.configure(scrollregion=ar_canvas.bbox("all"))
    )
    
    ar_canvas.create_window((0, 0), window=ar_frame, anchor="nw")
    ar_canvas.configure(yscrollcommand=ar_scrollbar.set)
    
    ar_canvas.pack(side="left", fill="both", expand=True, padx=5, pady=5)
    ar_scrollbar.pack(side="right", fill="y", pady=5)
    
    # ===========================================
    # CONFIGURANDO ABA DMR SETTINGS
    # ===========================================
    
    # Header DMR com gradiente neon rosa
    dmr_header = tk.Frame(dmr_tab, bg=theme.NEON_PINK, height=45)
    dmr_header.pack(fill='x', padx=8, pady=8)
    dmr_header.pack_propagate(False)
    
    dmr_title = tk.Label(dmr_header, text="🎯 DMR SNIPER - HEADSHOT SYSTEM", 
                        font=("Segoe UI", 13, "bold"), fg='#ffffff', bg=theme.NEON_PINK)
    dmr_title.pack(pady=12)
    
    # Canvas e Scrollbar para DMR
    dmr_canvas = tk.Canvas(dmr_tab, bg=theme.BG_DARK, highlightthickness=0)
    dmr_scrollbar = ttk.Scrollbar(dmr_tab, orient="vertical", command=dmr_canvas.yview)
    dmr_frame = tk.Frame(dmr_canvas, bg=theme.BG_DARK)
    
    dmr_frame.bind(
        "<Configure>",
        lambda e: dmr_canvas.configure(scrollregion=dmr_canvas.bbox("all"))
    )
    
    dmr_canvas.create_window((0, 0), window=dmr_frame, anchor="nw")
    dmr_canvas.configure(yscrollcommand=dmr_scrollbar.set)
    
    dmr_canvas.pack(side="left", fill="both", expand=True, padx=5, pady=5)
    dmr_scrollbar.pack(side="right", fill="y", pady=5)
    
    # ===========================================
    # CONFIGURANDO ABA SYSTEM STATUS
    # ===========================================
    
    # Header Status com cor verde neon
    status_header = tk.Frame(status_tab, bg=theme.NEON_GREEN, height=45)
    status_header.pack(fill='x', padx=8, pady=8)
    status_header.pack_propagate(False)
    
    status_title = tk.Label(status_header, text="📊 CONTROL CENTER", 
                           font=("Segoe UI", 13, "bold"), fg='#ffffff', bg=theme.NEON_GREEN)
    status_title.pack(pady=12)
    
    # Canvas e Scrollbar para Status
    control_canvas = tk.Canvas(status_tab, bg=theme.BG_DARK, highlightthickness=0)
    control_scrollbar = ttk.Scrollbar(status_tab, orient="vertical", command=control_canvas.yview)
    control_frame = tk.Frame(control_canvas, bg=theme.BG_DARK)
    
    control_frame.bind(
        "<Configure>",
        lambda e: control_canvas.configure(scrollregion=control_canvas.bbox("all"))
    )
    
    control_canvas.create_window((0, 0), window=control_frame, anchor="nw")
    control_canvas.configure(yscrollcommand=control_scrollbar.set)
    
    control_canvas.pack(side="left", fill="both", expand=True, padx=5, pady=5)
    control_scrollbar.pack(side="right", fill="y", pady=5)
    
    # FUNÇÃO PARA SCROLL COM MOUSE WHEEL
    def _on_mousewheel(event, canvas):
        """Função para scroll com roda do mouse"""
        scroll_amount = int(round(-1 * (event.delta / 120)))
        canvas.yview_scroll(scroll_amount, "units")
    
    def bind_mousewheel(canvas, frame):
        """Bind mouse wheel para canvas e frame"""
        def on_enter(event):
            canvas.bind_all("<MouseWheel>", lambda e: _on_mousewheel(e, canvas))
        def on_leave(event):
            canvas.unbind_all("<MouseWheel>")
        
        canvas.bind('<Enter>', on_enter)
        canvas.bind('<Leave>', on_leave)
        frame.bind('<Enter>', on_enter)
        frame.bind('<Leave>', on_leave)
    
    # Aplicar mouse wheel scroll em todas as seções
    bind_mousewheel(ar_canvas, ar_frame)
    bind_mousewheel(dmr_canvas, dmr_frame)
    bind_mousewheel(control_canvas, control_frame)
    
    # 🎨 FUNÇÕES AUXILIARES COM DESIGN CYBER NEON
    def create_weapon_slider(parent, label_text, from_val, to_val, resolution, weapon_type, config_key, current_value):
        """Criar slider moderno específico para arma com efeito neon"""
        frame = tk.Frame(parent, bg=parent['bg'], pady=3)
        frame.pack(fill='x', padx=10, pady=4)
        
        # Container com borda sutil
        inner_frame = tk.Frame(frame, bg=theme.BG_CARD, relief='flat', bd=0)
        inner_frame.pack(fill='x', padx=2, pady=2)
        
        # Label moderno com cor neon
        label = tk.Label(inner_frame, text=label_text, font=("Segoe UI", 10, "bold"), 
                        fg=theme.NEON_CYAN, bg=theme.BG_CARD)
        label.pack(anchor='w', padx=8, pady=(5, 0))
        
        # Valor atual
        value_label = tk.Label(inner_frame, text=f"{current_value}", 
                              font=("Segoe UI", 9), fg=theme.GOLD, bg=theme.BG_CARD)
        value_label.pack(anchor='e', padx=8)
        
        def update_config(value):
            if weapon_type == "AR":
                config.ar_config[config_key] = float(value)
            else:
                config.dmr_config[config_key] = float(value)
            
            # Atualizar label de valor
            value_label.config(text=f"{float(value):.2f}")
            
            # Atualizar configurações se arma atual
            if config.current_weapon == weapon_type:
                config.update_weapon_settings()
            
            # Força atualização imediata do overlay
            try:
                pass  # overlay update
            except:
                pass
        
        # Slider moderno com estilo neon
        slider = tk.Scale(inner_frame, from_=from_val, to=to_val, resolution=resolution,
                         orient='horizontal', command=update_config, 
                         bg=theme.BG_DARK, fg=theme.TEXT_WHITE, 
                         highlightbackground=theme.NEON_PURPLE, 
                         activebackground=theme.NEON_BLUE,
                         troughcolor=theme.BG_MEDIUM,
                         sliderrelief='flat',
                         length=220, font=("Segoe UI", 8, "bold"),
                         showvalue=False)  # Valor mostrado no label separado
        slider.pack(fill='x', padx=8, pady=(0, 8))
        slider.set(current_value)
        
        return slider
    
    def create_general_slider(parent, label_text, from_val, to_val, resolution, command, current_value):
        """Criar slider moderno para controles gerais com efeito neon"""
        frame = tk.Frame(parent, bg=parent['bg'], pady=3)
        frame.pack(fill='x', padx=10, pady=4)
        
        # Container com borda sutil
        inner_frame = tk.Frame(frame, bg=theme.BG_CARD, relief='flat', bd=0)
        inner_frame.pack(fill='x', padx=2, pady=2)
        
        # Label moderno com cor neon
        label = tk.Label(inner_frame, text=label_text, font=("Segoe UI", 10, "bold"), 
                        fg=theme.NEON_GREEN, bg=theme.BG_CARD)
        label.pack(anchor='w', padx=8, pady=(5, 0))
        
        # Wrapper para comando que atualiza overlay
        def wrapped_command(value):
            command(value)
            try:
                pass  # overlay update
            except:
                pass
        
        # Slider moderno com estilo neon
        slider = tk.Scale(inner_frame, from_=from_val, to=to_val, resolution=resolution,
                         orient='horizontal', command=wrapped_command, 
                         bg=theme.BG_DARK, fg=theme.TEXT_WHITE,
                         highlightbackground=theme.NEON_GREEN,
                         activebackground=theme.SUCCESS,
                         troughcolor=theme.BG_MEDIUM,
                         sliderrelief='flat',
                         length=220, font=("Segoe UI", 8, "bold"))
        slider.pack(fill='x', pady=2)
        slider.set(current_value)
        
        return slider
    
    # 🔫 CONTROLES AR V4 - SENSIBILIDADE FRACO → FORTE
    # Info sobre sensibilidade
    sens_info = tk.Label(ar_frame, text="📊 Sensibilidade: FRACO (0.1) → FORTE (2.0)", 
                        font=("Segoe UI", 9, "bold"), fg=theme.NEON_CYAN, bg=theme.BG_DARK)
    sens_info.pack(pady=(10, 5))
    
    # ===============================================
    # 🎯 SELETOR VISUAL DE BODY PART PARA AR
    # ===============================================
    ar_body_frame = tk.Frame(ar_frame, bg=theme.BG_LIGHT, relief='solid', bd=1)
    ar_body_frame.pack(fill='x', padx=5, pady=5)
    
    tk.Label(ar_body_frame, text="🎯 AR TARGET BODY PART:", 
             font=("Segoe UI", 10, "bold"), fg=theme.NEON_CYAN, bg=theme.BG_LIGHT).pack(pady=5)
    
    # Frame horizontal com desenho do corpo e opções
    ar_body_content = tk.Frame(ar_body_frame, bg=theme.BG_LIGHT)
    ar_body_content.pack(fill='x', padx=5, pady=5)
    
    # === COLUNA ESQUERDA: DESENHO DO CORPO ===
    body_canvas_frame = tk.Frame(ar_body_content, bg=theme.BG_DARK, width=120, height=200)
    body_canvas_frame.pack(side='left', padx=10, pady=5)
    body_canvas_frame.pack_propagate(False)
    
    # Canvas para desenhar o corpo
    body_canvas = tk.Canvas(body_canvas_frame, width=100, height=180, bg=theme.BG_DARK, 
                           highlightthickness=1, highlightbackground=theme.NEON_CYAN)
    body_canvas.pack(padx=5, pady=5)
    
    # Desenhar corpo estilizado
    def draw_body_target(canvas, highlight_part='head'):
        canvas.delete('all')
        
        # Cores
        normal_color = '#444444'
        highlight_color = '#00ff88'
        outline_color = '#666666'
        
        # Coordenadas do corpo (centrado no canvas 100x180)
        cx = 50  # centro x
        
        # Cabeça (círculo)
        head_color = highlight_color if highlight_part == 'head' else normal_color
        canvas.create_oval(35, 8, 65, 38, fill=head_color, outline=outline_color, width=2, tags='head')
        canvas.create_text(50, 23, text="HEAD", font=("Arial", 6, "bold"), fill='white')
        
        # Pescoço
        neck_color = highlight_color if highlight_part == 'neck' else normal_color
        canvas.create_rectangle(43, 38, 57, 48, fill=neck_color, outline=outline_color, tags='neck')
        
        # Peito superior
        upper_chest_color = highlight_color if highlight_part == 'upper_chest' else normal_color
        canvas.create_polygon(30, 48, 70, 48, 75, 70, 25, 70, fill=upper_chest_color, outline=outline_color, width=2, tags='upper_chest')
        canvas.create_text(50, 59, text="CHEST", font=("Arial", 5, "bold"), fill='white')
        
        # Peito/Torso
        chest_color = highlight_color if highlight_part == 'chest' else normal_color
        canvas.create_rectangle(25, 70, 75, 100, fill=chest_color, outline=outline_color, width=2, tags='chest')
        
        # Estômago
        stomach_color = highlight_color if highlight_part == 'stomach' else normal_color
        canvas.create_rectangle(28, 100, 72, 120, fill=stomach_color, outline=outline_color, tags='stomach')
        
        # Quadril/Pelvis
        pelvis_color = highlight_color if highlight_part == 'pelvis' else normal_color
        canvas.create_polygon(28, 120, 72, 120, 65, 140, 35, 140, fill=pelvis_color, outline=outline_color, tags='pelvis')
        
        # Pernas
        legs_color = highlight_color if highlight_part == 'legs' else normal_color
        canvas.create_rectangle(35, 140, 48, 175, fill=legs_color, outline=outline_color, tags='legs')
        canvas.create_rectangle(52, 140, 65, 175, fill=legs_color, outline=outline_color, tags='legs')
        
        # AUTO mode - destacar tudo
        if highlight_part == 'auto':
            canvas.create_rectangle(2, 2, 98, 178, outline='#ff00ff', width=3)
            canvas.create_text(50, 90, text="AUTO", font=("Arial", 10, "bold"), fill='#ff00ff')
    
    # Variável para AR body part
    ar_body_part_var = tk.StringVar(value=config.ar_config.get("target_body_part", "head"))
    
    # === COLUNA DIREITA: OPÇÕES DE BODY PART ===
    ar_options_frame = tk.Frame(ar_body_content, bg=theme.BG_LIGHT)
    ar_options_frame.pack(side='left', fill='both', expand=True, padx=5)
    
    def change_ar_body_part():
        selected = ar_body_part_var.get()
        config.ar_config["target_body_part"] = selected
        
        # Atualizar offset baseado na parte selecionada
        if selected in config.body_parts:
            config.ar_config["head_offset_factor"] = config.body_parts[selected]["offset"]
        
        # Atualizar desenho
        draw_body_target(body_canvas, selected)
        
        print(f"🎯 AR Target: {config.body_parts.get(selected, {}).get('name', selected)}")
    
    # Opções de body part para AR
    ar_body_options = [
        ("auto", "🔥 AUTO (Qualquer Parte)", '#ff00ff'),
        ("head", "🎯 Head (Headshot)", '#ff3333'),
        ("neck", "🔴 Neck (Critical)", '#ff6666'),
        ("upper_chest", "💥 Upper Chest", '#ffaa00'),
        ("chest", "🎮 Chest (Safe)", '#00ff88'),
    ]
    
    for part_key, part_name, color in ar_body_options:
        rb = tk.Radiobutton(ar_options_frame, text=part_name, 
                           variable=ar_body_part_var, value=part_key,
                           command=change_ar_body_part, 
                           fg=color, bg=theme.BG_LIGHT,
                           selectcolor=theme.BG_DARK, 
                           font=("Segoe UI", 9, "bold"),
                           activebackground=theme.BG_LIGHT,
                           anchor='w')
        rb.pack(fill='x', pady=2)
    
    # Desenhar corpo inicial
    draw_body_target(body_canvas, ar_body_part_var.get())
    
    # Separador
    tk.Frame(ar_frame, height=2, bg=theme.NEON_CYAN).pack(fill='x', padx=5, pady=8)
    
    # ===============================================
    # SLIDERS DE CONFIGURAÇÃO AR
    # ===============================================
    create_weapon_slider(ar_frame, "🎯 Sensitivity (Fraco → Forte)", 0.1, 2.0, 0.05, "AR", "sensitivity", config.ar_config["sensitivity"])
    create_weapon_slider(ar_frame, "🔒 AimLock Strength", 0.1, 1.0, 0.05, "AR", "aimlock_strength", config.ar_config.get("aimlock_strength", 0.9))
    create_weapon_slider(ar_frame, "🔵 FOV Radius", 100, 500, 10, "AR", "radius", config.ar_config["radius"])
    create_weapon_slider(ar_frame, "📊 Confidence", 0.05, 0.5, 0.01, "AR", "confidence_threshold", config.ar_config["confidence_threshold"])
    create_weapon_slider(ar_frame, "↔️ Speed X", 0.2, 1.5, 0.05, "AR", "MovementCoefficientX", config.ar_config["MovementCoefficientX"])
    create_weapon_slider(ar_frame, "↕️ Speed Y", 0.2, 1.5, 0.05, "AR", "MovementCoefficientY", config.ar_config["MovementCoefficientY"])
    create_weapon_slider(ar_frame, "💥 Recoil Comp", 0.5, 8.0, 0.5, "AR", "recoil_strength", config.ar_config["recoil_strength"])
    create_weapon_slider(ar_frame, "🌊 Smooth", 0.5, 1.0, 0.05, "AR", "smooth_factor", config.ar_config["smooth_factor"])
    
    # Toggle Recoil AR com design melhorado
    ar_recoil_var = tk.BooleanVar(value=config.ar_config["recoil_control"])
    def toggle_ar_recoil():
        config.ar_config["recoil_control"] = ar_recoil_var.get()
        if config.current_weapon == "AR":
            config.update_weapon_settings()
        # Atualiza overlay imediatamente
        try:
            pass  # overlay update
        except:
            pass
    
    ar_recoil_check = tk.Checkbutton(ar_frame, text="💥 Recoil Control (Compensa Subida)", variable=ar_recoil_var,
                                    command=toggle_ar_recoil, fg=theme.NEON_GREEN, bg=theme.BG_DARK,
                                    selectcolor=theme.BG_CARD, font=("Segoe UI", 10, "bold"),
                                    activebackground=theme.BG_DARK)
    ar_recoil_check.pack(pady=8)
    
    # === CONTROLES DE OFFSET EXCLUSIVOS PARA AR ===
    tk.Frame(ar_frame, height=2, bg=theme.GOLD).pack(fill='x', padx=5, pady=5)
    
    offset_frame = tk.Frame(ar_frame, bg=theme.BG_LIGHT, relief='solid', bd=1)
    offset_frame.pack(fill='x', padx=5, pady=5)
    
    tk.Label(offset_frame, text="🎯 AR CROSSHAIR OFFSET:", 
             font=("Segoe UI", 9, "bold"), fg=theme.SUCCESS, bg=theme.BG_LIGHT).pack(pady=3)
    
    # Offset X para AR
    create_general_slider(offset_frame, "↔️ Offset X", -50, 50, 1, 
                         lambda x: setattr(config, 'offset_x', int(x)), 0)
    
    # Offset Y para AR  
    create_general_slider(offset_frame, "↕️ Offset Y", -50, 50, 1, 
                         lambda y: setattr(config, 'offset_y', int(y)), 0)
    
    # 🎯 CONTROLES DMR (ORGANIZADOS LOGICAMENTE)
    
    # ===============================================
    # 🎯 SELETOR VISUAL DE BODY PART PARA DMR
    # ===============================================
    dmr_body_frame = tk.Frame(dmr_frame, bg=theme.BG_LIGHT, relief='solid', bd=1)
    dmr_body_frame.pack(fill='x', padx=5, pady=5)
    
    tk.Label(dmr_body_frame, text="🎯 DMR TARGET BODY PART:", 
             font=("Segoe UI", 10, "bold"), fg=theme.NEON_PINK, bg=theme.BG_LIGHT).pack(pady=5)
    
    # Frame horizontal com desenho do corpo e opções
    dmr_body_content = tk.Frame(dmr_body_frame, bg=theme.BG_LIGHT)
    dmr_body_content.pack(fill='x', padx=5, pady=5)
    
    # === COLUNA ESQUERDA: DESENHO DO CORPO DMR ===
    dmr_canvas_frame = tk.Frame(dmr_body_content, bg=theme.BG_DARK, width=120, height=200)
    dmr_canvas_frame.pack(side='left', padx=10, pady=5)
    dmr_canvas_frame.pack_propagate(False)
    
    # Canvas para desenhar o corpo DMR
    dmr_body_canvas = tk.Canvas(dmr_canvas_frame, width=100, height=180, bg=theme.BG_DARK, 
                               highlightthickness=1, highlightbackground=theme.NEON_PINK)
    dmr_body_canvas.pack(padx=5, pady=5)
    
    # Desenhar corpo estilizado para DMR
    def draw_dmr_body_target(canvas, highlight_part='head'):
        canvas.delete('all')
        
        # Cores DMR (rosa/magenta)
        normal_color = '#333333'
        highlight_color = '#ff44aa'  # Rosa para DMR
        outline_color = '#555555'
        
        # Coordenadas do corpo (centrado no canvas 100x180)
        cx = 50
        
        # Cabeça (círculo) - MAIS DETALHADO para precisão
        head_color = highlight_color if highlight_part == 'head' else normal_color
        canvas.create_oval(32, 5, 68, 41, fill=head_color, outline=outline_color, width=2, tags='head')
        # Ponto de mira na cabeça
        if highlight_part == 'head':
            canvas.create_line(45, 23, 55, 23, fill='white', width=2)
            canvas.create_line(50, 18, 50, 28, fill='white', width=2)
        canvas.create_text(50, 23, text="HEAD", font=("Arial", 6, "bold"), fill='white')
        
        # Pescoço
        neck_color = highlight_color if highlight_part == 'neck' else normal_color
        canvas.create_rectangle(42, 41, 58, 52, fill=neck_color, outline=outline_color, tags='neck')
        if highlight_part == 'neck':
            canvas.create_oval(47, 44, 53, 50, outline='white', width=2)
        
        # Peito superior (crítico)
        upper_chest_color = highlight_color if highlight_part == 'upper_chest' else normal_color
        canvas.create_polygon(28, 52, 72, 52, 78, 75, 22, 75, fill=upper_chest_color, outline=outline_color, width=2, tags='upper_chest')
        if highlight_part == 'upper_chest':
            canvas.create_oval(45, 58, 55, 68, outline='white', width=2)
        
        # Peito/Torso
        chest_color = highlight_color if highlight_part == 'chest' else normal_color
        canvas.create_rectangle(22, 75, 78, 105, fill=chest_color, outline=outline_color, width=2, tags='chest')
        if highlight_part == 'chest':
            canvas.create_oval(45, 85, 55, 95, outline='white', width=2)
        
        # Estômago
        stomach_color = highlight_color if highlight_part == 'stomach' else normal_color
        canvas.create_rectangle(26, 105, 74, 125, fill=stomach_color, outline=outline_color, tags='stomach')
        
        # Quadril/Pelvis
        pelvis_color = highlight_color if highlight_part == 'pelvis' else normal_color
        canvas.create_polygon(26, 125, 74, 125, 66, 145, 34, 145, fill=pelvis_color, outline=outline_color, tags='pelvis')
        
        # Pernas
        legs_color = highlight_color if highlight_part == 'legs' else normal_color
        canvas.create_rectangle(34, 145, 48, 175, fill=legs_color, outline=outline_color, tags='legs')
        canvas.create_rectangle(52, 145, 66, 175, fill=legs_color, outline=outline_color, tags='legs')
        
        # AUTO mode - destacar tudo
        if highlight_part == 'auto':
            canvas.create_rectangle(2, 2, 98, 178, outline='#ff00ff', width=3)
            canvas.create_text(50, 90, text="AUTO", font=("Arial", 10, "bold"), fill='#ff00ff')
    
    # Variável para DMR body part
    body_part_var = tk.StringVar(value=config.dmr_config.get("target_body_part", "head"))
    
    # === COLUNA DIREITA: OPÇÕES DE BODY PART DMR ===
    dmr_options_frame = tk.Frame(dmr_body_content, bg=theme.BG_LIGHT)
    dmr_options_frame.pack(side='left', fill='both', expand=True, padx=5)
    
    def change_body_part():
        selected_part = body_part_var.get()
        config.dmr_config["target_body_part"] = selected_part
        
        # Atualizar offset baseado na parte selecionada
        if selected_part in config.body_parts:
            config.dmr_config["head_offset_factor"] = config.body_parts[selected_part]["offset"]
        
        # Atualizar desenho
        draw_dmr_body_target(dmr_body_canvas, selected_part)
        
        print(f"🎯 DMR Target: {config.body_parts.get(selected_part, {}).get('name', selected_part)}")
    
    # Opções de body part para DMR (mais opções que AR)
    dmr_body_options = [
        ("auto", "🔥 AUTO (Centro)", '#ff00ff'),
        ("head", "🎯 HEAD (Instant Kill)", '#ff3333'),
        ("neck", "🔴 NECK (Critical)", '#ff6666'),
        ("upper_chest", "💥 UPPER CHEST", '#ffaa00'),
        ("chest", "🎮 CHEST (Safe)", '#00ff88'),
        ("stomach", "📍 STOMACH", '#00aaff'),
        ("pelvis", "🔻 PELVIS", '#8888ff'),
    ]
    
    for part_key, part_name, color in dmr_body_options:
        rb = tk.Radiobutton(dmr_options_frame, text=part_name, 
                           variable=body_part_var, value=part_key,
                           command=change_body_part, 
                           fg=color, bg=theme.BG_LIGHT,
                           selectcolor=theme.BG_DARK, 
                           font=("Segoe UI", 9, "bold"),
                           activebackground=theme.BG_LIGHT,
                           anchor='w')
        rb.pack(fill='x', pady=1)
    
    # Desenhar corpo inicial
    draw_dmr_body_target(dmr_body_canvas, body_part_var.get())
    
    # Separador
    tk.Frame(dmr_frame, height=2, bg=theme.NEON_PINK).pack(fill='x', padx=5, pady=10)
    
    # Info sobre sensibilidade DMR
    sens_info_dmr = tk.Label(dmr_frame, text="📊 Sensibilidade: FRACO (0.1) → FORTE (1.5)", 
                            font=("Segoe UI", 9, "bold"), fg=theme.NEON_PINK, bg=theme.BG_DARK)
    sens_info_dmr.pack(pady=(5, 5))
    
    # === CONTROLES DMR V4 ===
    create_weapon_slider(dmr_frame, "🎯 Sensitivity (Fraco → Forte)", 0.1, 1.5, 0.05, "DMR", "sensitivity", config.dmr_config["sensitivity"])
    create_weapon_slider(dmr_frame, "🔒 AimLock Strength", 0.1, 1.0, 0.05, "DMR", "aimlock_strength", config.dmr_config.get("aimlock_strength", 0.95))
    create_weapon_slider(dmr_frame, "🔵 FOV Radius", 100, 450, 10, "DMR", "radius", config.dmr_config["radius"])
    create_weapon_slider(dmr_frame, "📊 Confidence", 0.05, 0.4, 0.01, "DMR", "confidence_threshold", config.dmr_config["confidence_threshold"])
    create_weapon_slider(dmr_frame, "↔️ Speed X", 0.1, 1.0, 0.05, "DMR", "MovementCoefficientX", config.dmr_config["MovementCoefficientX"])
    create_weapon_slider(dmr_frame, "↕️ Speed Y", 0.1, 1.0, 0.05, "DMR", "MovementCoefficientY", config.dmr_config["MovementCoefficientY"])
    create_weapon_slider(dmr_frame, "💥 Recoil Comp", 0.5, 5.0, 0.5, "DMR", "recoil_strength", config.dmr_config["recoil_strength"])
    create_weapon_slider(dmr_frame, "🌊 Smooth", 0.5, 1.0, 0.05, "DMR", "smooth_factor", config.dmr_config["smooth_factor"])
    
    # Toggle Recoil DMR com design cyber
    dmr_recoil_var = tk.BooleanVar(value=config.dmr_config["recoil_control"])
    def toggle_dmr_recoil():
        config.dmr_config["recoil_control"] = dmr_recoil_var.get()
        if config.current_weapon == "DMR":
            config.update_weapon_settings()
        # Atualiza overlay imediatamente
        try:
            pass  # overlay update
        except:
            pass
    
    dmr_recoil_check = tk.Checkbutton(dmr_frame, text="💥 Recoil Control (Compensa Subida)", variable=dmr_recoil_var,
                                     command=toggle_dmr_recoil, fg=theme.NEON_PINK, bg=theme.BG_DARK,
                                     selectcolor=theme.BG_CARD, font=("Segoe UI", 10, "bold"),
                                     activebackground=theme.BG_DARK, activeforeground=theme.NEON_PINK)
    dmr_recoil_check.pack(pady=8)
    
    def quitProgram():
        config.AimToggle = False
        config.Running = False
        # Fechar ESP se aberto
        try:
            close_esp_overlay()
        except:
            pass
        root.quit()
        
    def AimButton():
        config.AimToggle = not config.AimToggle
        if config.AimToggle:
            AimLabel.config(text="⚡ STATUS: ACTIVE", fg=theme.NEON_GREEN)
            AimToggler.config(bg=theme.NEON_GREEN, text="⚡ DEACTIVATE")
        else:
            AimLabel.config(text="💤 STATUS: OFF", fg=theme.ERROR)
            AimToggler.config(bg=theme.NEON_PURPLE, text="⚡ ACTIVATE")
        # Atualiza overlay imediatamente quando ativa/desativa
        try:
            pass  # overlay update
        except:
            pass
    
    # 🎮 PAINEL DE TOGGLE PRINCIPAL COM DESIGN CYBER
    toggle_frame = tk.Frame(control_frame, bg=theme.BG_CARD, relief='flat', bd=0)
    toggle_frame.pack(fill='x', padx=10, pady=12)
    
    # Título do painel
    tk.Label(toggle_frame, text="⚡ AIMBOT CONTROL", 
             font=("Segoe UI", 12, "bold"), fg=theme.NEON_PURPLE, 
             bg=theme.BG_CARD).pack(pady=(10, 5))
    
    AimLabel = tk.Label(toggle_frame, 
                       text=f"⚡ STATUS: {'ACTIVE' if config.AimToggle else 'OFF'}", 
                       font=("Segoe UI", 14, "bold"), 
                       fg=theme.NEON_GREEN if config.AimToggle else theme.ERROR, 
                       bg=theme.BG_CARD)
    AimLabel.pack(pady=8)
    
    # 🎮 BOTÃO PRINCIPAL CYBER NEON
    AimToggler = tk.Button(toggle_frame, text="⚡ POWER TOGGLE", command=AimButton, 
                          bg=theme.NEON_PURPLE, fg='#ffffff', 
                          font=("Segoe UI", 13, "bold"),
                          relief="flat", bd=0, padx=25, pady=12,
                          activebackground=theme.NEON_BLUE,
                          activeforeground='#ffffff',
                          cursor='hand2')
    AimToggler.pack(pady=8)
    
    # 📊 STATUS PANEL COM DESIGN CYBER
    status_frame = tk.Frame(control_frame, bg=theme.BG_CARD, relief='flat', bd=0)
    status_frame.pack(fill='x', padx=10, pady=8)
    
    # Título do painel
    tk.Label(status_frame, text="📊 LIVE STATUS", 
             font=("Segoe UI", 11, "bold"), fg=theme.NEON_CYAN, 
             bg=theme.BG_CARD).pack(pady=(8, 5))
    
    WeaponLabel = tk.Label(status_frame, text=f"⚡ Weapon: {config.current_weapon}", 
                          font=("Segoe UI", 10, "bold"), fg=theme.NEON_GREEN, bg=theme.BG_CARD)
    WeaponLabel.pack(pady=3)
    
    ButtonLabel = tk.Label(status_frame, text=f"🎮 Trigger: {config.activation_button} Click", 
                          font=("Segoe UI", 10, "bold"), fg=theme.GOLD, bg=theme.BG_CARD)
    ButtonLabel.pack(pady=3)
    
    # FPS Indicator
    FPSLabel = tk.Label(status_frame, text="🔥 FPS: --", 
                       font=("Segoe UI", 10, "bold"), fg=theme.NEON_PINK, bg=theme.BG_CARD)
    FPSLabel.pack(pady=3)
    
    # Atualizar FPS periodicamente
    def update_fps_display():
        try:
            FPSLabel.config(text=f"🔥 FPS: {config.last_fps:.0f}")
            root.after(500, update_fps_display)
        except:
            pass
    root.after(1000, update_fps_display)
    
    # 🎹 HOTKEYS PANEL CYBER
    hotkey_frame = tk.Frame(control_frame, bg=theme.BG_CARD, relief='flat', bd=0)
    hotkey_frame.pack(fill='x', padx=10, pady=8)
    
    tk.Label(hotkey_frame, text="🎹 HOTKEYS", font=("Segoe UI", 11, "bold"), 
            fg=theme.NEON_CYAN, bg=theme.BG_CARD).pack(pady=(8, 5))
    tk.Label(hotkey_frame, text="G4 → Switch Weapon (AR/DMR)", font=("Segoe UI", 9), 
            fg=theme.TEXT_GRAY, bg=theme.BG_CARD).pack(pady=2)
    tk.Label(hotkey_frame, text="G5 → Switch Trigger (L/R)", font=("Segoe UI", 9), 
            fg=theme.TEXT_GRAY, bg=theme.BG_CARD).pack(pady=2)
    tk.Label(hotkey_frame, text="G6 → Cycle Body Part (DMR)", font=("Segoe UI", 9), 
            fg=theme.TEXT_GRAY, bg=theme.BG_CARD).pack(pady=(2, 8))
    
    # 💡 STATUS ATIVAÇÃO
    StatusLabel = tk.Label(control_frame, text=f"🎯 Hold {config.activation_button} Click to Aim", 
                          font=("Segoe UI", 11, "bold"), fg=theme.NEON_GREEN, bg=theme.BG_DARK)
    StatusLabel.pack(pady=8)
    
    # 🔄 BOTÃO CHECK UPDATES CYBER
    def check_updates_gui():
        """Verifica atualizações via GUI"""
        update_button.config(state='disabled', text='🔄 CHECKING...')
        def check_thread():
            auto_updater.check_for_updates(silent=False)
            try:
                update_button.config(state='normal', text='🔄 CHECK UPDATES')
            except:
                pass
        threading.Thread(target=check_thread, daemon=True).start()
    
    update_button = tk.Button(control_frame, text="🔄 CHECK UPDATES", 
                             command=check_updates_gui,
                             bg=theme.NEON_BLUE, fg="white", font=("Segoe UI", 10, "bold"),
                             relief="flat", bd=0, padx=15, pady=8,
                             cursor='hand2')
    update_button.pack(pady=8)
    
    # 🔒 AIMLOCK TOGGLE
    aimlock_frame = tk.Frame(control_frame, bg=theme.BG_CARD, relief='flat', bd=0)
    aimlock_frame.pack(fill='x', padx=10, pady=8)
    
    tk.Label(aimlock_frame, text="🔒 AIMLOCK SETTINGS", 
             font=("Segoe UI", 11, "bold"), fg=theme.NEON_PINK, 
             bg=theme.BG_CARD).pack(pady=(8, 5))
    
    aimlock_var = tk.BooleanVar(value=config.aimlock_enabled)
    def toggle_aimlock():
        config.aimlock_enabled = aimlock_var.get()
        aimlock_status.config(text=f"Status: {'🔒 LOCKED' if config.aimlock_enabled else '🔓 UNLOCKED'}",
                             fg=theme.NEON_GREEN if config.aimlock_enabled else theme.ERROR)
    
    aimlock_check = tk.Checkbutton(aimlock_frame, text="⚡ Enable AimLock (Gruda no Alvo)", 
                                   variable=aimlock_var, command=toggle_aimlock,
                                   fg=theme.TEXT_WHITE, bg=theme.BG_CARD,
                                   selectcolor=theme.BG_DARK, font=("Segoe UI", 10, "bold"),
                                   activebackground=theme.BG_CARD, activeforeground=theme.NEON_GREEN)
    aimlock_check.pack(pady=5)
    
    aimlock_status = tk.Label(aimlock_frame, 
                              text=f"Status: {'🔒 LOCKED' if config.aimlock_enabled else '🔓 UNLOCKED'}", 
                              font=("Segoe UI", 10, "bold"), 
                              fg=theme.NEON_GREEN if config.aimlock_enabled else theme.ERROR, 
                              bg=theme.BG_CARD)
    aimlock_status.pack(pady=(0, 8))
    
    # 🚪 BOTÃO QUIT CYBER
    QuitButton = tk.Button(control_frame, text="❌ EXIT", command=quitProgram, 
                          bg="#f44336", fg="white", font=("Segoe UI", 9, "bold"),
                          relief="flat", padx=10, pady=2)
    QuitButton.pack(pady=3)
    
    # ===========================================
    # CONFIGURANDO ABA ESP 👁️
    # ===========================================
    
    # Header ESP
    esp_header = tk.Frame(esp_tab, bg=theme.NEON_CYAN, height=45)
    esp_header.pack(fill='x', padx=8, pady=8)
    esp_header.pack_propagate(False)
    
    esp_title = tk.Label(esp_header, text="👁️ ESP - VISUAL DETECTION SYSTEM", 
                        font=("Segoe UI", 13, "bold"), fg='#000000', bg=theme.NEON_CYAN)
    esp_title.pack(pady=12)
    
    # Frame principal ESP
    esp_main_frame = tk.Frame(esp_tab, bg=theme.BG_DARK)
    esp_main_frame.pack(fill='both', expand=True, padx=10, pady=10)
    
    # ESP Toggle Principal
    esp_toggle_frame = tk.Frame(esp_main_frame, bg=theme.BG_CARD)
    esp_toggle_frame.pack(fill='x', pady=10)
    
    tk.Label(esp_toggle_frame, text="👁️ ESP MASTER CONTROL", 
             font=("Segoe UI", 12, "bold"), fg=theme.NEON_CYAN, 
             bg=theme.BG_CARD).pack(pady=(10, 5))
    
    esp_enabled_var = tk.BooleanVar(value=config.esp_enabled)
    def toggle_esp():
        config.esp_enabled = esp_enabled_var.get()
        esp_status_label.config(
            text=f"ESP: {'👁️ ACTIVE' if config.esp_enabled else '🚫 OFF'}",
            fg=theme.NEON_GREEN if config.esp_enabled else theme.ERROR
        )
        if config.esp_enabled:
            start_esp_overlay()
        else:
            close_esp_overlay()
    
    esp_check = tk.Checkbutton(esp_toggle_frame, text="⚡ ENABLE ESP OVERLAY", 
                               variable=esp_enabled_var, command=toggle_esp,
                               fg=theme.TEXT_WHITE, bg=theme.BG_CARD,
                               selectcolor=theme.BG_DARK, font=("Segoe UI", 11, "bold"),
                               activebackground=theme.BG_CARD, activeforeground=theme.NEON_GREEN)
    esp_check.pack(pady=8)
    
    esp_status_label = tk.Label(esp_toggle_frame, 
                                text=f"ESP: {'👁️ ACTIVE' if config.esp_enabled else '🚫 OFF'}", 
                                font=("Segoe UI", 12, "bold"), 
                                fg=theme.NEON_GREEN if config.esp_enabled else theme.ERROR, 
                                bg=theme.BG_CARD)
    esp_status_label.pack(pady=(0, 10))
    
    # ESP Options
    esp_options_frame = tk.Frame(esp_main_frame, bg=theme.BG_CARD)
    esp_options_frame.pack(fill='x', pady=10)
    
    tk.Label(esp_options_frame, text="📦 ESP OPTIONS", 
             font=("Segoe UI", 11, "bold"), fg=theme.GOLD, 
             bg=theme.BG_CARD).pack(pady=(10, 5))
    
    # Box ESP
    esp_boxes_var = tk.BooleanVar(value=config.esp_boxes)
    def toggle_esp_boxes():
        config.esp_boxes = esp_boxes_var.get()
    tk.Checkbutton(esp_options_frame, text="📦 Player Boxes", 
                   variable=esp_boxes_var, command=toggle_esp_boxes,
                   fg=theme.NEON_GREEN, bg=theme.BG_CARD,
                   selectcolor=theme.BG_DARK, font=("Segoe UI", 10),
                   activebackground=theme.BG_CARD).pack(anchor='w', padx=20, pady=3)
    
    # Line ESP
    esp_lines_var = tk.BooleanVar(value=config.esp_lines)
    def toggle_esp_lines():
        config.esp_lines = esp_lines_var.get()
    tk.Checkbutton(esp_options_frame, text="📍 Snaplines to Target", 
                   variable=esp_lines_var, command=toggle_esp_lines,
                   fg=theme.NEON_BLUE, bg=theme.BG_CARD,
                   selectcolor=theme.BG_DARK, font=("Segoe UI", 10),
                   activebackground=theme.BG_CARD).pack(anchor='w', padx=20, pady=3)
    
    # Distance ESP
    esp_distance_var = tk.BooleanVar(value=config.esp_distance)
    def toggle_esp_distance():
        config.esp_distance = esp_distance_var.get()
    tk.Checkbutton(esp_options_frame, text="📏 Show Distance", 
                   variable=esp_distance_var, command=toggle_esp_distance,
                   fg=theme.NEON_PINK, bg=theme.BG_CARD,
                   selectcolor=theme.BG_DARK, font=("Segoe UI", 10),
                   activebackground=theme.BG_CARD).pack(anchor='w', padx=20, pady=(3, 10))
    
    # ESP Info
    esp_info_frame = tk.Frame(esp_main_frame, bg=theme.BG_CARD)
    esp_info_frame.pack(fill='x', pady=10)
    
    tk.Label(esp_info_frame, text="ℹ️ ESP INFO", 
             font=("Segoe UI", 11, "bold"), fg=theme.NEON_CYAN, 
             bg=theme.BG_CARD).pack(pady=(10, 5))
    
    tk.Label(esp_info_frame, text="• ESP desenha caixas ao redor dos players detectados", 
             font=("Segoe UI", 9), fg=theme.TEXT_GRAY, bg=theme.BG_CARD).pack(anchor='w', padx=20)
    tk.Label(esp_info_frame, text="• Funciona junto com o Aimbot automaticamente", 
             font=("Segoe UI", 9), fg=theme.TEXT_GRAY, bg=theme.BG_CARD).pack(anchor='w', padx=20)
    tk.Label(esp_info_frame, text="• Cores: 🟢 Verde = Alvo atual | 🔴 Vermelho = Outros", 
             font=("Segoe UI", 9), fg=theme.TEXT_GRAY, bg=theme.BG_CARD).pack(anchor='w', padx=20, pady=(0, 10))
    
    # ESP Overlay Window - VERSÃO SEM TELA PRETA V3
    esp_overlay_window = {'ref': None, 'canvas': None, 'running': False}
    
    def start_esp_overlay():
        """Cria janela ESP transparente - USA WINFO PARA EVITAR TELA PRETA"""
        if esp_overlay_window['ref']:
            try:
                if esp_overlay_window['ref'].winfo_exists():
                    return
            except:
                pass
        
        print("🔧 Criando ESP Overlay (método seguro)...")
        
        try:
            import ctypes
            
            esp_win = tk.Toplevel(root)
            esp_win.title("ESP")
            esp_win.overrideredirect(True)
            
            # Tamanho da tela
            screen_w = esp_win.winfo_screenwidth()
            screen_h = esp_win.winfo_screenheight()
            esp_win.geometry(f"{screen_w}x{screen_h}+0+0")
            
            # IMPORTANTE: Usar uma cor específica para transparência
            transparent_color = '#010101'  # Quase preto mas não exatamente
            esp_win.configure(bg=transparent_color)
            
            # Definir a cor transparente ANTES de criar o canvas
            esp_win.attributes('-transparentcolor', transparent_color)
            esp_win.attributes('-topmost', True)
            esp_win.attributes('-alpha', 0.99)  # Quase opaco
            
            # Canvas com a mesma cor transparente
            canvas = tk.Canvas(esp_win, bg=transparent_color, highlightthickness=0,
                              width=screen_w, height=screen_h)
            canvas.pack(fill='both', expand=True)
            
            esp_win.update_idletasks()
            esp_win.update()
            
            # Click-through via Win32
            try:
                esp_hwnd = ctypes.windll.user32.GetParent(esp_win.winfo_id())
                if esp_hwnd == 0:
                    esp_hwnd = esp_win.winfo_id()
                
                GWL_EXSTYLE = -20
                WS_EX_LAYERED = 0x00080000
                WS_EX_TRANSPARENT = 0x00000020
                
                style = ctypes.windll.user32.GetWindowLongW(esp_hwnd, GWL_EXSTYLE)
                ctypes.windll.user32.SetWindowLongW(esp_hwnd, GWL_EXSTYLE, 
                    style | WS_EX_LAYERED | WS_EX_TRANSPARENT)
                print("✅ ESP click-through OK!")
            except Exception as e:
                print(f"⚠️ Click-through parcial: {e}")
            
            esp_overlay_window['ref'] = esp_win
            esp_overlay_window['canvas'] = canvas
            esp_overlay_window['running'] = True
            esp_overlay_window['transparent_color'] = transparent_color
            
            # Iniciar desenho
            esp_draw_loop()
            print("👁️ ESP Overlay ATIVO!")
            
        except Exception as e:
            print(f"❌ Erro ao criar ESP: {e}")
            esp_overlay_window['running'] = False
    
    def close_esp_overlay():
        """Fecha janela ESP"""
        esp_overlay_window['running'] = False
        if esp_overlay_window['ref']:
            try:
                esp_overlay_window['ref'].destroy()
            except:
                pass
        esp_overlay_window['ref'] = None
        esp_overlay_window['canvas'] = None
        print("👁️ ESP Overlay fechado!")
    
    def esp_draw_loop():
        """Loop de desenho do ESP - CORRIGIDO"""
        try:
            # Verificar se deve continuar
            if not esp_overlay_window['running'] or not config.esp_enabled:
                return
            
            canvas = esp_overlay_window['canvas']
            win = esp_overlay_window['ref']
            
            if not canvas or not win:
                return
            
            try:
                if not win.winfo_exists():
                    return
            except:
                return
            
            # Limpar canvas
            canvas.delete('all')
            
            # Desenhar detecções
            detections = getattr(config, 'last_detections', None)
            if detections and len(detections) > 0:
                # Centro da tela
                screen_center_x = config.width // 2
                screen_center_y = config.height // 2
                
                # Offset da área de captura para coordenadas da tela
                offset_x = config.capture_left
                offset_y = config.capture_top
                
                for i, (box, conf) in enumerate(detections):
                    try:
                        x1, y1, x2, y2 = box
                        
                        # Converter para coordenadas de tela
                        sx1 = int(x1 + offset_x)
                        sy1 = int(y1 + offset_y)
                        sx2 = int(x2 + offset_x)
                        sy2 = int(y2 + offset_y)
                        
                        # Cores: Verde = alvo principal, Vermelho = outros
                        if i == 0:
                            color = '#00FF00'  # Verde brilhante
                            width = 3
                        else:
                            color = '#FF3333'  # Vermelho
                            width = 2
                        
                        # 📦 DESENHAR BOX
                        if config.esp_boxes:
                            # Desenhar retângulo com cantos
                            canvas.create_rectangle(sx1, sy1, sx2, sy2,
                                                  outline=color, width=width)
                            
                            # Label de confiança
                            label_text = f"ENEMY {conf*100:.0f}%"
                            canvas.create_text(sx1 + 2, sy1 - 8, 
                                             text=label_text,
                                             fill=color, 
                                             font=("Arial", 9, "bold"), 
                                             anchor='sw')
                        
                        # 📍 DESENHAR LINHA ATÉ O ALVO
                        if config.esp_lines:
                            center_x = (sx1 + sx2) // 2
                            center_y = (sy1 + sy2) // 2
                            # Linha do centro inferior da tela até o alvo
                            canvas.create_line(
                                screen_center_x, config.height - 50,
                                center_x, center_y,
                                fill=color, width=1, dash=(4, 2)
                            )
                        
                        # 📏 MOSTRAR DISTÂNCIA
                        if config.esp_distance:
                            center_x = (sx1 + sx2) // 2
                            center_y = (sy1 + sy2) // 2
                            dist = math.sqrt((center_x - screen_center_x)**2 + 
                                           (center_y - screen_center_y)**2)
                            canvas.create_text(sx1, sy2 + 12, 
                                             text=f"📏 {dist:.0f}px",
                                             fill=color, 
                                             font=("Arial", 8), 
                                             anchor='nw')
                    except Exception as e:
                        pass  # Ignorar erros individuais de desenho
            
            # Reagendar próximo frame (~30 FPS)
            root.after(33, esp_draw_loop)
            
        except Exception as e:
            print(f"⚠️ ESP Draw Error: {e}")
            # Tentar novamente
            root.after(100, esp_draw_loop)
    
    # Iniciar ESP se habilitado
    if config.esp_enabled:
        root.after(1500, start_esp_overlay)

    # ==========================
    # ============================================
    # 🎮 MINI OVERLAY V6 - NOVO E ESTÁVEL
    # ============================================
    overlay_v6 = {'window': None, 'active': False, 'labels': {}}
    overlay_enabled_var = tk.BooleanVar(value=True)
    
    def create_overlay_v6():
        """Novo overlay minimalista e estável"""
        # Fechar se já existe
        if overlay_v6['window'] is not None:
            try:
                overlay_v6['window'].destroy()
            except:
                pass
            overlay_v6['window'] = None
        
        # Criar nova janela
        win = tk.Toplevel()
        win.title("")
        win.overrideredirect(True)
        win.attributes('-topmost', True)
        win.configure(bg='black')
        
        # Posição e tamanho
        win.geometry('180x110+15+80')
        
        # Transparência
        try:
            win.attributes('-alpha', 0.88)
        except:
            pass
        
        # Container
        container = tk.Frame(win, bg='#0a0a0a', bd=2, relief='ridge')
        container.pack(fill='both', expand=True)
        
        # Header
        header = tk.Frame(container, bg='#1a1a1a', height=22)
        header.pack(fill='x')
        header.pack_propagate(False)
        
        tk.Label(header, text="⚡ LARS", font=("Arial", 9, "bold"),
                fg='#00ff88', bg='#1a1a1a').pack(side='left', padx=4)
        
        status_lbl = tk.Label(header, text="●", font=("Arial", 12, "bold"),
                             fg='#00ff00', bg='#1a1a1a')
        status_lbl.pack(side='right', padx=4)
        overlay_v6['labels']['status'] = status_lbl
        
        # Content
        content = tk.Frame(container, bg='#0a0a0a')
        content.pack(fill='both', expand=True, padx=4, pady=2)
        
        # Labels
        lbl_weapon = tk.Label(content, text="AR", font=("Arial", 9, "bold"),
                             fg='#ffaa00', bg='#0a0a0a', anchor='w')
        lbl_weapon.pack(fill='x')
        overlay_v6['labels']['weapon'] = lbl_weapon
        
        lbl_target = tk.Label(content, text="HEAD", font=("Arial", 9),
                             fg='#ff5555', bg='#0a0a0a', anchor='w')
        lbl_target.pack(fill='x')
        overlay_v6['labels']['target'] = lbl_target
        
        lbl_config = tk.Label(content, text="S:0.5 R:3.0", font=("Arial", 8),
                             fg='#888888', bg='#0a0a0a', anchor='w')
        lbl_config.pack(fill='x')
        overlay_v6['labels']['config'] = lbl_config
        
        lbl_fps = tk.Label(content, text="FPS: 0", font=("Arial", 8),
                          fg='#555555', bg='#0a0a0a', anchor='w')
        lbl_fps.pack(fill='x')
        overlay_v6['labels']['fps'] = lbl_fps
        
        overlay_v6['window'] = win
        overlay_v6['active'] = True
        
        # Click-through usando ctypes
        try:
            import ctypes
            GWL_EXSTYLE = -20
            WS_EX_LAYERED = 0x80000
            WS_EX_TRANSPARENT = 0x20
            hwnd = win.winfo_id()
            styles = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, styles | WS_EX_LAYERED | WS_EX_TRANSPARENT)
        except Exception as e:
            pass
        
        # Iniciar update loop
        update_overlay_v6()
        print("✅ Overlay V6 ativo!")
    
    # Alias para compatibilidade
    def create_overlay_v5():
        create_overlay_v6()
    
    def update_overlay_v6():
        """Atualiza overlay V6 em tempo real"""
        try:
            if not overlay_v6['active']:
                return
            
            win = overlay_v6['window']
            if win is None:
                return
            
            try:
                if not win.winfo_exists():
                    overlay_v6['active'] = False
                    return
            except:
                overlay_v6['active'] = False
                return
            
            labels = overlay_v6['labels']
            cfg = config.get_current_config()
            
            # Status indicator
            if 'status' in labels:
                color = '#00ff00' if config.AimToggle else '#ff3333'
                labels['status'].config(fg=color)
            
            # Weapon
            if 'weapon' in labels:
                wpn = config.current_weapon
                btn = config.activation_button
                color = '#ffaa00' if wpn == 'AR' else '#ff66ff'
                labels['weapon'].config(text=f"{wpn} | {btn}", fg=color)
            
            # Target body part
            if 'target' in labels:
                if config.current_weapon == 'DMR':
                    part = config.dmr_config.get('target_body_part', 'head')
                else:
                    part = config.ar_config.get('target_body_part', 'head')
                
                # Nome simples
                part_names = {
                    'auto': 'AUTO',
                    'head': 'HEAD',
                    'neck': 'NECK',
                    'upper_chest': 'CHEST+',
                    'chest': 'CHEST',
                    'stomach': 'STOMACH',
                    'pelvis': 'PELVIS',
                    'legs': 'LEGS'
                }
                part_text = part_names.get(part, part.upper())
                
                # Cor por parte
                colors = {
                    'auto': '#ff00ff',
                    'head': '#ff3333',
                    'neck': '#ff6633',
                    'upper_chest': '#ffaa00',
                    'chest': '#00ff88',
                    'stomach': '#00aaff',
                    'pelvis': '#8888ff',
                    'legs': '#888888'
                }
                labels['target'].config(text=f"→ {part_text}", fg=colors.get(part, '#aaaaaa'))
            
            # Config info
            if 'config' in labels:
                sens = cfg.get('sensitivity', 0.5)
                recoil = cfg.get('recoil_strength', 3.0)
                labels['config'].config(text=f"S:{sens:.1f} R:{recoil:.1f}")
            
            # FPS
            if 'fps' in labels:
                labels['fps'].config(text=f"FPS: {int(config.last_fps)}")
            
            # Loop 80ms para update suave
            root.after(80, update_overlay_v6)
            
        except Exception:
            try:
                root.after(150, update_overlay_v6)
            except:
                pass
    
    # Alias
    def update_overlay_v5():
        update_overlay_v6()
    
    def close_overlay_v6():
        """Fecha overlay V6"""
        overlay_v6['active'] = False
        if overlay_v6['window']:
            try:
                overlay_v6['window'].destroy()
            except:
                pass
        overlay_v6['window'] = None
        overlay_v6['labels'] = {}
    
    # Alias
    def close_overlay_v5():
        close_overlay_v6()

    def toggle_overlay():
        if overlay_enabled_var.get():
            create_overlay_v5()
        else:
            close_overlay_v5()

    # Adiciona controle na aba SYSTEM STATUS
    overlay_control_frame = tk.Frame(status_frame, bg=theme.BG_LIGHT)
    overlay_control_frame.pack(fill='x', padx=6, pady=6)
    tk.Label(overlay_control_frame, text='Mini Overlay (Top-Left HUD)',
             font=("Segoe UI", 9, 'bold'), fg=theme.GOLD, bg=theme.BG_LIGHT).pack(anchor='w')
    tk.Checkbutton(overlay_control_frame, text='Enable Compact HUD', variable=overlay_enabled_var,
                   command=toggle_overlay, fg='white', bg=theme.BG_LIGHT, selectcolor=theme.BG_DARK,
                   font=("Segoe UI", 8)).pack(anchor='w')

    # Criar overlay V5 por padrão
    if overlay_enabled_var.get():
        root.after(800, create_overlay_v5)
    
    # ===========================================
    # CONFIGURANDO ABA SETTINGS
    # ===========================================
    
    # Header Settings
    settings_header = tk.Frame(settings_tab, bg=theme.GOLD, height=40)
    settings_header.pack(fill='x', padx=5, pady=5)
    settings_header.pack_propagate(False)
    
    settings_title = tk.Label(settings_header, text="⚙️ SETTINGS MANAGER", 
                             font=("Segoe UI", 12, "bold"), fg=theme.BG_DARK, bg=theme.GOLD)
    settings_title.pack(pady=10)
    
    # Canvas e Scrollbar para Settings
    settings_canvas = tk.Canvas(settings_tab, bg=theme.BG_LIGHT, highlightthickness=0)
    settings_scrollbar = ttk.Scrollbar(settings_tab, orient="vertical", command=settings_canvas.yview)
    settings_frame = tk.Frame(settings_canvas, bg=theme.BG_LIGHT)
    
    settings_canvas.configure(yscrollcommand=settings_scrollbar.set)
    settings_canvas.create_window((0, 0), window=settings_frame, anchor="nw")
    
    def update_settings_scroll(event):
        settings_canvas.configure(scrollregion=settings_canvas.bbox("all"))
    
    settings_frame.bind("<Configure>", update_settings_scroll)
    
    settings_canvas.pack(side="left", fill="both", expand=True, padx=3, pady=3)
    settings_scrollbar.pack(side="right", fill="y", pady=3)
    
    # SISTEMA AUTO-SAVE MELHORADO
    auto_save_timer_id = None
    
    def start_auto_save_timer():
        """Inicia timer de auto-save periódico"""
        global auto_save_timer_id
        def auto_save_periodic():
            config.auto_save_settings()
            # Reagendar para próximo auto-save em 30 segundos
            global auto_save_timer_id
            auto_save_timer_id = root.after(30000, auto_save_periodic)
        
        # Cancelar timer anterior se existir
        try:
            if auto_save_timer_id:
                root.after_cancel(auto_save_timer_id)
        except:
            pass
        
        # Iniciar novo timer
        auto_save_timer_id = root.after(30000, auto_save_periodic)  # 30 segundos
    
    def reset_to_defaults():
        """Restaura configurações padrão"""
        import tkinter.messagebox as msgbox
        if msgbox.askyesno("🔄 Reset Settings", "⚠️ Tem certeza que deseja restaurar as configurações padrão?\n\nIsso irá:\n• Resetar todas as configurações\n• Manter o arquivo atual como backup"):
            # Backup do arquivo atual
            import os
            import shutil
            if os.path.exists("lars_settings.json"):
                try:
                    shutil.copy("lars_settings.json", "lars_settings_backup.json")
                    print("📄 Backup criado: lars_settings_backup.json")
                except:
                    pass
            
            # Restaurar padrões
            global config
            config = PerfectAimbotConfig()
            # Removido: chamada redundante a update_status() (não definida neste escopo)
            update_settings_status()
            msgbox.showinfo("✅ Reset Complete", "✅ Configurações restauradas para o padrão!\n📄 Backup salvo como: lars_settings_backup.json")
    
    # INFORMAÇÕES DO ARQUIVO
    info_frame = tk.Frame(settings_frame, bg=theme.BG_DARK, relief='solid', bd=2)
    info_frame.pack(fill='x', padx=10, pady=10)
    
    tk.Label(info_frame, text="📁 FILE INFORMATION", 
             font=("Segoe UI", 10, "bold"), fg=theme.GOLD, bg=theme.BG_DARK).pack(pady=5)
    
    file_status_label = tk.Label(info_frame, text="Checking...", 
                                font=("Segoe UI", 9), fg='white', bg=theme.BG_DARK)
    file_status_label.pack(pady=2)
    
    file_size_label = tk.Label(info_frame, text="", 
                               font=("Segoe UI", 8), fg='#cccccc', bg=theme.BG_DARK)
    file_size_label.pack(pady=1)
    
    last_modified_label = tk.Label(info_frame, text="", 
                                   font=("Segoe UI", 8), fg='#cccccc', bg=theme.BG_DARK)
    last_modified_label.pack(pady=1)
    
    # ============================================
    # 🖥️ SEÇÃO DE CALIBRAÇÃO DO SISTEMA
    # ============================================
    calibration_frame = tk.Frame(settings_frame, bg=theme.BG_DARK, relief='solid', bd=2)
    calibration_frame.pack(fill='x', padx=10, pady=10)
    
    tk.Label(calibration_frame, text="🖥️ SYSTEM CALIBRATION", 
             font=("Segoe UI", 10, "bold"), fg=theme.NEON_CYAN, bg=theme.BG_DARK).pack(pady=5)
    
    # Info de resolução detectada
    resolution_info = tk.Label(calibration_frame, 
                              text=f"🖥️ Resolução Detectada: {config.width}x{config.height}", 
                              font=("Segoe UI", 9), fg='#00ff88', bg=theme.BG_DARK)
    resolution_info.pack(pady=2)
    
    # Info de hardware
    try:
        import torch
        gpu_info = f"🎮 GPU: {'CUDA (' + torch.cuda.get_device_name(0) + ')' if torch.cuda.is_available() else 'CPU Only'}"
    except:
        gpu_info = "🎮 GPU: Verificando..."
    
    hardware_label = tk.Label(calibration_frame, text=gpu_info, 
                             font=("Segoe UI", 9), fg='#aaaaaa', bg=theme.BG_DARK)
    hardware_label.pack(pady=2)
    
    # Separador
    tk.Frame(calibration_frame, height=1, bg='#444444').pack(fill='x', padx=10, pady=5)
    
    # === MULTIPLICADOR DE MOVIMENTO ===
    tk.Label(calibration_frame, text="⚡ Movement Multiplier (Calibração)", 
             font=("Segoe UI", 9, "bold"), fg=theme.GOLD, bg=theme.BG_DARK).pack(pady=3)
    
    tk.Label(calibration_frame, text="Ajuste se o aimbot move muito (↓) ou pouco (↑)", 
             font=("Segoe UI", 8), fg='#888888', bg=theme.BG_DARK).pack()
    
    movement_mult_frame = tk.Frame(calibration_frame, bg=theme.BG_DARK)
    movement_mult_frame.pack(fill='x', padx=10, pady=5)
    
    movement_mult_var = tk.DoubleVar(value=config.movement_multiplier)
    movement_mult_label = tk.Label(movement_mult_frame, text=f"{config.movement_multiplier:.2f}x", 
                                  font=("Segoe UI", 10, "bold"), fg=theme.NEON_GREEN, bg=theme.BG_DARK, width=6)
    movement_mult_label.pack(side='right', padx=5)
    
    def update_movement_mult(val):
        config.movement_multiplier = float(val)
        movement_mult_label.config(text=f"{float(val):.2f}x")
    
    movement_mult_slider = tk.Scale(movement_mult_frame, from_=0.3, to=2.0, resolution=0.05,
                                    orient='horizontal', variable=movement_mult_var,
                                    command=update_movement_mult, length=200,
                                    bg=theme.BG_DARK, fg='white', highlightthickness=0,
                                    troughcolor='#333333', activebackground=theme.NEON_CYAN)
    movement_mult_slider.pack(side='left', fill='x', expand=True)
    
    # === SELETOR DE RESOLUÇÃO MANUAL ===
    tk.Label(calibration_frame, text="🖥️ Override Resolução (se detecção falhar)", 
             font=("Segoe UI", 9, "bold"), fg=theme.GOLD, bg=theme.BG_DARK).pack(pady=(10, 3))
    
    resolution_options = [
        "Auto Detect",
        "1920x1080 (Full HD)",
        "2560x1440 (2K QHD)",
        "3840x2160 (4K UHD)",
        "1366x768 (HD)",
        "1600x900 (HD+)",
        "1280x720 (720p)",
        "2560x1080 (Ultrawide)",
        "3440x1440 (Ultrawide QHD)"
    ]
    
    resolution_var = tk.StringVar(value="Auto Detect")
    
    def change_resolution(event=None):
        selected = resolution_var.get()
        if selected == "Auto Detect":
            # Re-detectar automaticamente
            try:
                import ctypes
                user32 = ctypes.windll.user32
                config.width = user32.GetSystemMetrics(0)
                config.height = user32.GetSystemMetrics(1)
            except:
                pass
        else:
            # Parse resolução do texto
            res = selected.split(" ")[0]  # "1920x1080"
            w, h = res.split("x")
            config.width = int(w)
            config.height = int(h)
        
        # Recalcular centro e área de captura
        config.center_x = config.width // 2
        config.center_y = config.height // 2
        config.capture_left = config.center_x - config.capture_width // 2
        config.capture_top = config.center_y - config.capture_height // 2
        config.resolution_scale = config.width / 1920.0
        
        # Atualizar região MSS
        config.region = {
            "top": config.capture_top,
            "left": config.capture_left,
            "width": config.capture_width,
            "height": config.capture_height
        }
        
        resolution_info.config(text=f"🖥️ Resolução: {config.width}x{config.height}")
        print(f"🖥️ Resolução alterada para: {config.width}x{config.height}")
    
    resolution_combo = ttk.Combobox(calibration_frame, textvariable=resolution_var, 
                                    values=resolution_options, state='readonly', width=25)
    resolution_combo.pack(pady=5)
    resolution_combo.bind('<<ComboboxSelected>>', change_resolution)
    
    # === ÁREA DE CAPTURA ===
    tk.Label(calibration_frame, text="📐 Capture Area Size", 
             font=("Segoe UI", 9, "bold"), fg=theme.GOLD, bg=theme.BG_DARK).pack(pady=(10, 3))
    
    capture_size_frame = tk.Frame(calibration_frame, bg=theme.BG_DARK)
    capture_size_frame.pack(fill='x', padx=10, pady=5)
    
    capture_size_var = tk.IntVar(value=config.capture_width)
    capture_size_label = tk.Label(capture_size_frame, text=f"{config.capture_width}px", 
                                 font=("Segoe UI", 10, "bold"), fg=theme.NEON_GREEN, bg=theme.BG_DARK, width=6)
    capture_size_label.pack(side='right', padx=5)
    
    def update_capture_size(val):
        size = int(float(val))
        config.capture_width = size
        config.capture_height = size
        config.capture_left = config.center_x - size // 2
        config.capture_top = config.center_y - size // 2
        config.region = {
            "top": config.capture_top,
            "left": config.capture_left,
            "width": size,
            "height": size
        }
        capture_size_label.config(text=f"{size}px")
    
    capture_size_slider = tk.Scale(capture_size_frame, from_=320, to=640, resolution=20,
                                   orient='horizontal', variable=capture_size_var,
                                   command=update_capture_size, length=200,
                                   bg=theme.BG_DARK, fg='white', highlightthickness=0,
                                   troughcolor='#333333', activebackground=theme.NEON_CYAN)
    capture_size_slider.pack(side='left', fill='x', expand=True)
    
    # === DETECÇÃO DE PERFORMANCE ===
    tk.Label(calibration_frame, text="⚡ Performance Mode", 
             font=("Segoe UI", 9, "bold"), fg=theme.GOLD, bg=theme.BG_DARK).pack(pady=(10, 3))
    
    perf_options = [
        ("🚀 High (GPU forte)", "high"),
        ("⚖️ Balanced (Recomendado)", "balanced"),
        ("🔋 Low (PC fraco)", "low")
    ]
    
    perf_var = tk.StringVar(value="balanced")
    
    def change_performance():
        mode = perf_var.get()
        if mode == "high":
            # Mais detecções, maior qualidade
            config.ar_config["confidence_threshold"] = 0.12
            config.dmr_config["confidence_threshold"] = 0.15
        elif mode == "balanced":
            # Padrão
            config.ar_config["confidence_threshold"] = 0.15
            config.dmr_config["confidence_threshold"] = 0.18
        else:  # low
            # Menos detecções, mais rápido
            config.ar_config["confidence_threshold"] = 0.20
            config.dmr_config["confidence_threshold"] = 0.25
        print(f"⚡ Performance mode: {mode}")
    
    for text, value in perf_options:
        rb = tk.Radiobutton(calibration_frame, text=text, variable=perf_var, value=value,
                           command=change_performance, fg='white', bg=theme.BG_DARK,
                           selectcolor=theme.BG_LIGHT, font=("Segoe UI", 9),
                           activebackground=theme.BG_DARK)
        rb.pack(anchor='w', padx=20)
    
    def update_settings_status():
        """Atualiza status do arquivo de configurações"""
        import os
        import datetime
        
        if os.path.exists("lars_settings.json"):
            file_size = os.path.getsize("lars_settings.json")
            mod_time = os.path.getmtime("lars_settings.json")
            mod_date = datetime.datetime.fromtimestamp(mod_time).strftime("%d/%m/%Y %H:%M:%S")
            
            file_status_label.config(text="✅ lars_settings.json - FOUND", fg='#4CAF50')
            file_size_label.config(text=f"📊 Size: {file_size} bytes")
            last_modified_label.config(text=f"🕒 Modified: {mod_date}")
        else:
            file_status_label.config(text="❌ lars_settings.json - NOT FOUND", fg='#f44336')
            file_size_label.config(text="💡 Use SAVE to create your first config file")
            last_modified_label.config(text="")
    
    # BOTÕES PRINCIPAIS
    buttons_main_frame = tk.Frame(settings_frame, bg=theme.BG_LIGHT)
    buttons_main_frame.pack(fill='x', padx=10, pady=10)
    
    tk.Label(buttons_main_frame, text="💾 AUTO-SAVE SYSTEM", 
             font=("Segoe UI", 10, "bold"), fg=theme.SUCCESS, bg=theme.BG_LIGHT).pack(pady=5)
    
    # Frame para o botão principal
    main_buttons = tk.Frame(buttons_main_frame, bg=theme.BG_LIGHT)
    main_buttons.pack(pady=5)
    
    # FUNÇÃO SAVE MELHORADA COM AUTO-SAVE
    def enhanced_save_settings():
        """Save manual + ativar auto-save"""
        success = config.save_settings()
        if success:
            import tkinter.messagebox as msgbox
            msgbox.showinfo("💾 Save Settings", "✅ Configurações salvas com sucesso!\n📁 Arquivo: lars_settings.json\n\n🚀 AUTO-SAVE ativado - suas mudanças serão salvas automaticamente!")
            update_settings_status()
            # Ativar auto-save periódico
            start_auto_save_timer()
        else:
            import tkinter.messagebox as msgbox
            msgbox.showerror("❌ Save Error", "❌ Erro ao salvar configurações!")
    
    # BOTÃO SAVE CENTRALIZADO E MAIOR
    save_button = tk.Button(main_buttons, text="💾 SAVE SETTINGS NOW", command=enhanced_save_settings, 
                           bg="#4CAF50", fg="white", font=("Segoe UI", 12, "bold"),
                           relief="raised", bd=3, padx=30, pady=10,
                           activebackground="#45a049")
    save_button.pack(pady=10)
    
    # INFO AUTO-SAVE
    auto_info_frame = tk.Frame(buttons_main_frame, bg=theme.BG_DARK, relief='solid', bd=2)
    auto_info_frame.pack(fill='x', pady=10)
    
    tk.Label(auto_info_frame, text="🤖 AUTO-SAVE FEATURES", 
             font=("Segoe UI", 9, "bold"), fg=theme.GOLD, bg=theme.BG_DARK).pack(pady=3)
    
    tk.Label(auto_info_frame, text="✅ Settings auto-load when program starts", 
             font=("Segoe UI", 8), fg='#4CAF50', bg=theme.BG_DARK).pack(pady=1)
    
    tk.Label(auto_info_frame, text="✅ Settings auto-save every time you change something", 
             font=("Segoe UI", 8), fg='#4CAF50', bg=theme.BG_DARK).pack(pady=1)
    
    tk.Label(auto_info_frame, text="💡 No need to manually load - everything is automatic!", 
             font=("Segoe UI", 8), fg='#cccccc', bg=theme.BG_DARK).pack(pady=1)
    
    # BOTÕES SECUNDÁRIOS
    secondary_frame = tk.Frame(settings_frame, bg=theme.BG_LIGHT)
    secondary_frame.pack(fill='x', padx=10, pady=5)
    
    tk.Label(secondary_frame, text="🔧 ADVANCED CONTROLS", 
             font=("Segoe UI", 9, "bold"), fg=theme.WARNING, bg=theme.BG_LIGHT).pack(pady=3)
    
    secondary_buttons = tk.Frame(secondary_frame, bg=theme.BG_LIGHT)
    secondary_buttons.pack(pady=3)
    
    # BOTÃO RESET
    reset_button = tk.Button(secondary_buttons, text="🔄 RESET TO DEFAULTS", command=reset_to_defaults, 
                            bg="#FF9800", fg="white", font=("Segoe UI", 9, "bold"),
                            relief="raised", bd=2, padx=15, pady=5,
                            activebackground="#F57C00")
    reset_button.pack(side='left', padx=5)
    
    # AUTO-LOAD INFO
    autoload_frame = tk.Frame(settings_frame, bg=theme.BG_DARK, relief='solid', bd=2)
    autoload_frame.pack(fill='x', padx=10, pady=10)
    
    tk.Label(autoload_frame, text="🚀 AUTO-LOAD FEATURE", 
             font=("Segoe UI", 10, "bold"), fg=theme.GOLD, bg=theme.BG_DARK).pack(pady=5)
    
    tk.Label(autoload_frame, text="✅ Settings are automatically loaded when the program starts", 
             font=("Segoe UI", 9), fg='#4CAF50', bg=theme.BG_DARK).pack(pady=2)
    
    tk.Label(autoload_frame, text="💡 Your last saved configuration will be restored every time!", 
             font=("Segoe UI", 8), fg='#cccccc', bg=theme.BG_DARK).pack(pady=2)
    
    # ATUALIZAR STATUS DOS ARQUIVOS
    # =============================
    # CONTROLE DO HUD OVERLAY (SETTINGS)
    # =============================
    overlay_settings_frame = tk.Frame(settings_frame, bg=theme.BG_DARK, relief='solid', bd=2)
    overlay_settings_frame.pack(fill='x', padx=10, pady=10)
    tk.Label(overlay_settings_frame, text='📺 MINI OVERLAY (HUD)',
             font=("Segoe UI", 10, 'bold'), fg=theme.GOLD, bg=theme.BG_DARK).pack(anchor='w', pady=(4,2))
    tk.Label(overlay_settings_frame, text='Exibe arma, botão, sensibilidade, FOV, alvo, recoil, offset e FPS. Janela é semi-transparente e ignora cliques (click-through).',
             wraplength=520, justify='left', font=("Segoe UI", 8), fg='#cccccc', bg=theme.BG_DARK).pack(anchor='w', pady=(0,6))

    def toggle_overlay_button():
        overlay_enabled_var.set(not overlay_enabled_var.get())
        toggle_overlay()
        overlay_toggle_btn.config(text='Disable HUD Overlay' if overlay_enabled_var.get() else 'Enable HUD Overlay')

    overlay_toggle_btn = tk.Button(overlay_settings_frame,
                                   text='Disable HUD Overlay' if overlay_enabled_var.get() else 'Enable HUD Overlay',
                                   command=toggle_overlay_button,
                                   bg=theme.GOLD, fg=theme.BG_DARK,
                                   font=("Segoe UI", 9, 'bold'), relief='raised', bd=2, padx=14, pady=6,
                                   activebackground=theme.GOLD_LIGHT, activeforeground=theme.BG_DARK)
    overlay_toggle_btn.pack(anchor='w', pady=4)

    update_settings_status()
    
    # INICIAR AUTO-SAVE TIMER
    start_auto_save_timer()
    
    def update_status():
        """Atualizar status da interface em tempo real"""
        WeaponLabel.config(text=f"Weapon: {config.current_weapon}")
        ButtonLabel.config(text=f"Button: {config.activation_button}")
        StatusLabel.config(text=f"Hold {config.activation_button} to activate")
        AimLabel.config(text=f"Service Aim: {'🟢 ACTIVE' if config.AimToggle else '🔴 OFF'}")
        
    # 🌈 ANIMAÇÃO RGB PARA BORDAS
    def animate_rgb():
        """Anima as bordas RGB"""
        rgb_effects.update_hue()
        current_color = rgb_effects.get_rgb_color()
        
        # Atualizar AMBAS as bordas RGB (sincronizadas)
        rgb_border_top.config(bg=current_color)
        rgb_border_bottom.config(bg=current_color)
        
        # Atualizar highlight dos controles ativos
        if config.AimToggle:
            AimToggler.config(highlightbackground=current_color, highlightthickness=2)
        
        # Continuar animação
        root.after(50, animate_rgb)  # 50ms = animação suave
    
    def update_status():
        """Atualizar status da interface"""
        # Atualizar labels
        AimLabel.config(text=f"Service Aim: {'🟢 ACTIVE' if config.AimToggle else '🔴 OFF'}")
        WeaponLabel.config(text=f"🔫 Weapon: {config.current_weapon}")
        ButtonLabel.config(text=f"🎮 Button: {config.activation_button}")
        
        # Destacar arma atual nos títulos com cores modernas
        if config.current_weapon == "AR":
            ar_title.config(fg=theme.SUCCESS, text="🔫 ASSAULT RIFLE (700M) ← ACTIVE")
            dmr_title.config(fg=theme.TEXT_GRAY, text="🎯 DMR SNIPER (700M)")
        else:
            ar_title.config(fg=theme.TEXT_GRAY, text="🔫 ASSAULT RIFLE (700M)")
            dmr_title.config(fg=theme.SUCCESS, text="🎯 DMR SNIPER (700M) ← ACTIVE")
        
        # Atualizar região de scroll
        ar_canvas.configure(scrollregion=ar_canvas.bbox("all"))
        dmr_canvas.configure(scrollregion=dmr_canvas.bbox("all"))
        control_canvas.configure(scrollregion=control_canvas.bbox("all"))
        
        root.after(100, update_status)  # Atualizar a cada 100ms
    
    # 🌈 FRAME RGB ANIMADO NA BORDA INFERIOR
    rgb_border_bottom = tk.Frame(root, bg=theme.RGB_BORDER, height=4)
    rgb_border_bottom.pack(fill='x', side='bottom')
    
    # Iniciar animações
    animate_rgb()  # Iniciar animação RGB
    update_status()  # Iniciar atualizações
    
    # Callback de fechamento seguro
    def _safe_close():
        try:
            if callable(on_close_callback):
                on_close_callback()
        finally:
            root.destroy()
    root.protocol("WM_DELETE_WINDOW", _safe_close)
    root.mainloop()

def is_right_mouse_pressed():
    """Detectar botão direito pressionado"""
    try:
        return bool(win32api.GetAsyncKeyState(win32con.VK_RBUTTON) & 0x8000)
    except:
        return False

def monitor_hotkeys():
    """🔥 MONITORAMENTO DOS BOTÕES G4, G5, G e Arrow Keys"""
    print("🎮 Monitoramento de hotkeys expandido iniciado!")
    print("🔫 G4: Trocar arma (AR ↔ DMR)")
    print("🖱️ G5: Trocar botão de ativação (ESQUERDO ↔ DIREITO)")
    print("🎯 G: Trocar parte do corpo (apenas DMR)")
    print("🎯 Arrow Keys: Ajustar crosshair offset")
    print("📌 CTRL+R: Resetar crosshair offset")
    
    while config.Running:
        try:
            # 🔫 BOTÃO G4 - TROCAR ARMA
            g4_state = win32api.GetAsyncKeyState(0x05) & 0x8000  # G4 = 0x05
            if g4_state and not config.g4_pressed:
                config.g4_pressed = True
                config.toggle_weapon()
                
            elif not g4_state and config.g4_pressed:
                config.g4_pressed = False
            
            # 🖱️ BOTÃO G5 - TROCAR BOTÃO DE ATIVAÇÃO
            g5_state = win32api.GetAsyncKeyState(0x06) & 0x8000  # G5 = 0x06
            if g5_state and not config.g5_pressed:
                config.g5_pressed = True
                config.toggle_activation_button()
                
            elif not g5_state and config.g5_pressed:
                config.g5_pressed = False
            
            # 🎯 BOTÃO G6 - TROCAR PARTE DO CORPO (DMR)
            g6_state = win32api.GetAsyncKeyState(0x47) & 0x8000  # G = 0x47
            if g6_state and not config.g6_pressed:
                config.g6_pressed = True
                if config.current_weapon == "DMR":
                    config.change_dmr_target()
                else:
                    print("🔴 G6 só funciona no modo DMR! Pressione G4 para alternar para DMR.")
                
            elif not g6_state and config.g6_pressed:
                config.g6_pressed = False
            
            # 🎯 ARROW KEYS - CROSSHAIR OFFSET
            # UP Arrow
            up_state = win32api.GetAsyncKeyState(win32con.VK_UP) & 0x8000
            if up_state and not config.up_pressed:
                config.up_pressed = True
                config.adjust_crosshair_offset("up")
            elif not up_state and config.up_pressed:
                config.up_pressed = False
            
            # DOWN Arrow
            down_state = win32api.GetAsyncKeyState(win32con.VK_DOWN) & 0x8000
            if down_state and not config.down_pressed:
                config.down_pressed = True
                config.adjust_crosshair_offset("down")
            elif not down_state and config.down_pressed:
                config.down_pressed = False
            
            # LEFT Arrow
            left_state = win32api.GetAsyncKeyState(win32con.VK_LEFT) & 0x8000
            if left_state and not config.left_pressed:
                config.left_pressed = True
                config.adjust_crosshair_offset("left")
            elif not left_state and config.left_pressed:
                config.left_pressed = False
            
            # RIGHT Arrow
            right_state = win32api.GetAsyncKeyState(win32con.VK_RIGHT) & 0x8000
            if right_state and not config.right_pressed:
                config.right_pressed = True
                config.adjust_crosshair_offset("right")
            elif not right_state and config.right_pressed:
                config.right_pressed = False
            
            # 📌 CTRL+R - RESET OFFSET
            ctrl_state = win32api.GetAsyncKeyState(win32con.VK_CONTROL) & 0x8000
            r_state = win32api.GetAsyncKeyState(ord('R')) & 0x8000
            if ctrl_state and r_state:
                config.reset_crosshair_offset()
                time.sleep(0.5)  # Evitar spam do reset
            
            time.sleep(0.05)  # Pequeno delay para evitar spam
            
        except Exception as e:
            time.sleep(0.1)

def main():
    """Entrada principal: autentica, carrega modelo, inicia threads e GUI na MAIN thread.
    Corrigido para compatibilidade PyInstaller (Tk só na thread principal).
    """
    global config
    print("🔐 LARS SERVICE AIM - START")
    print(f"📦 Version: {CURRENT_VERSION}")
    
    # 🔄 Verificar atualizações no startup (1x por dia, silencioso)
    print("🔍 Verificando atualizações...")
    auto_updater.check_on_startup()
    
    login_system = LoginInterface()
    authenticated, user_data = login_system.show_login()
    if not authenticated:
        print("❌ Authentication failed/cancelled")
        return
    print(f"✅ Auth OK | User: {user_data['username']} | Expiry: {user_data['expiry_date']}")
    # Reiniciar config pós auth
    config = PerfectAimbotConfig()
    # Carregar modelo (suporte a PyInstaller _MEIPASS)
    def resolve_model_path(candidate):
        # Se empacotado, os dados adicionais ficam em sys._MEIPASS
        base_paths = []
        if hasattr(sys, '_MEIPASS'):
            base_paths.append(sys._MEIPASS)
        # 🔥 IMPORTANTE: Adicionar pasta do script PRIMEIRO
        script_dir = os.path.dirname(os.path.abspath(__file__))
        base_paths.append(script_dir)
        # Adicionar Desktop como segundo caminho
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        base_paths.append(desktop_path)
        base_paths.append(os.getcwd())
        # Também verificar subpastas comuns
        for base in base_paths.copy():
            base_paths.append(os.path.join(base, "larscheese"))
            base_paths.append(os.path.join(base, "models"))
        for base in base_paths:
            p = os.path.join(base, candidate)
            if os.path.exists(p):
                return p
        return None
    model = None
    for name in ["best.pt", os.path.join("models", "best.pt"), "yolov8n.pt", "sunxds_0.5.6.pt", os.path.join("models", "sunxds_0.5.6.pt")]:
        p = resolve_model_path(name)
        if p:
            try:
                model = ultralytics.YOLO(p, task='detect')
                print(f"✅ Modelo carregado: {p}")
                break
            except Exception as e:
                print(f"⚠️ Falha ao carregar {p}: {e}")
    if model is None:
        print("⚠️ Nenhum modelo encontrado (best.pt).")
        print("📋 Para usar detecção, coloque o arquivo 'best.pt' na mesma pasta do app")
        print("🚀 Continuando sem modelo de detecção...")
        # Criar um modelo vazio para não dar erro
        model = None
    else:
        model.overrides['verbose'] = False
        device_available = 'cuda' if torch.cuda.is_available() else 'cpu'
        try:
            dummy_frame = np.zeros((64, 64, 3), dtype=np.uint8)
            model.predict(dummy_frame, verbose=False, imgsz=64, device=device_available)
            print("✅ Modelo aquecido com sucesso!")
        except Exception as e:
            print(f"⚠️ Warmup falhou: {e}")
    
    # REMOVIDO: screen_capture global (cada thread precisa de sua própria instância)
    # Thread de hotkeys
    threading.Thread(target=monitor_hotkeys, daemon=True).start()
    
    stop_flag = {'value': False}
    def stop_all():
        config.Running = False
        stop_flag['value'] = True
    
    def detection_loop():
        """Loop de detecção com MSS local e tratamento robusto de erros."""
        frame_count = 0
        last_time = time.time()
        error_repeats = 0
        last_error_type = None
        
        # Criar instância MSS local para esta thread
        def create_mss():
            try:
                return mss.mss()
            except Exception as e:
                print(f"❌ Falha ao inicializar MSS: {e}")
                return None
        
        screen_capture = create_mss()
        if screen_capture is None:
            print("❌ Não foi possível criar captura de tela. Encerrando loop.")
            return
        
        print("✅ Loop de detecção iniciado!")
        
        # Flags para debug (imprime apenas primeira vez)
        first_activation = True
        
        while config.Running and not stop_flag['value']:
            if not config.AimToggle:
                if first_activation:
                    first_activation = False
                time.sleep(0.01)
                continue
            
            if first_activation:
                print(f"🎯 Aimbot ATIVADO | Arma: {config.current_weapon} | Botão: {config.activation_button}")
                print(f"🎯 Segure o botão {config.activation_button} do mouse para ativar!")
                first_activation = False
            
            # Verificar se botão de ativação está pressionado
            is_pressed = config.is_activation_pressed()
            if frame_count % 120 == 0 and is_pressed:
                print(f"✅ Botão {config.activation_button} PRESSIONADO - Aimbot ATIVO!")
            
            if not is_pressed:
                time.sleep(0.005)
                continue
            try:
                # Captura de tela com tratamento de erro _thread._local
                try:
                    frame = np.array(screen_capture.grab(config.region))
                except AttributeError as ae:
                    msg = str(ae)
                    if "_thread._local" in msg:
                        current_type = '_thread._local.srcdc'
                        if current_type != last_error_type:
                            print("♻️ Erro srcdc detectado. Recriando MSS...")
                            last_error_type = current_type
                            error_repeats = 0
                        else:
                            error_repeats += 1
                            if error_repeats % 20 == 0:
                                print(f"♻️ Recriando MSS novamente (ocorrências: {error_repeats})")
                        screen_capture = create_mss()
                        if screen_capture is None:
                            time.sleep(0.2)
                        continue
                    else:
                        raise
                
                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                
                # Verificar se o modelo existe
                if model is None:
                    time.sleep(0.1)
                    continue
                    
                device = 'cuda' if torch.cuda.is_available() else 'cpu'
                
                # 🎯 CONFIGURAÇÕES DE DETECÇÃO OTIMIZADAS V3
                results = model.predict(
                    source=frame,
                    conf=config.confidence_threshold,  # Threshold dinâmico
                    classes=[0],  # Classe 0 = pessoa
                    verbose=False,
                    max_det=15,  # Mais detecções permitidas
                    imgsz=480,  # Tamanho maior = melhor detecção
                    device=device,
                    half=torch.cuda.is_available(),
                    augment=False,
                    agnostic_nms=True,  # NMS agressivo para evitar duplicatas
                    retina_masks=False,
                    iou=0.35,  # IOU menor = detecta mais
                    save=False,
                    stream_buffer=False
                )
                
                # Debug: verificar se está detectando
                if frame_count % 30 == 0:
                    print(f"🔍 Scan ativo... conf={config.confidence_threshold:.2f}")
                
                if not results or not results[0].boxes or len(results[0].boxes.xyxy) == 0:
                    if frame_count % 30 == 0:
                        print("⚠️ Nenhum inimigo detectado - ajuste o confidence!")
                    frame_count += 1
                    continue
                    
                if frame_count % 30 == 0:
                    print(f"✅ {len(results[0].boxes.xyxy)} alvos detectados!")
                    
                boxes = results[0].boxes.xyxy
                confidences = results[0].boxes.conf
                
                # 🎯 SALVAR DETECÇÕES PARA ESP IMEDIATAMENTE
                all_detections = []
                for box, conf in zip(boxes, confidences):
                    all_detections.append((box.tolist(), conf.item()))
                config.last_detections = all_detections
                
                best_target = None
                best_distance = float('inf')
                
                for i in range(len(boxes)):
                    x1, y1, x2, y2 = boxes[i].tolist()
                    box_w = x2 - x1
                    box_h = y2 - y1
                    
                    # Filtrar caixas muito pequenas
                    if box_w < 8 or box_h < 15:
                        continue
                    
                    # 🎯 CENTRO HORIZONTAL DO CORPO - PIXEL PERFECT
                    # Usar centro ponderado para melhor precisão
                    center_weight = config.pixel_targeting.get('center_weight', 0.5)
                    center_x = int(x1 + box_w * center_weight)
                    
                    current_cfg = config.get_current_config()
                    
                    # 🎯 CALCULAR PONTO DE MIRA VERTICAL COM BODY PART SELECTOR
                    pixel_adjust = 0
                    if config.current_weapon == 'DMR':
                        dmr_target = config.dmr_config.get('target_body_part', 'upper_chest')
                        if dmr_target in config.body_parts:
                            body_offset = config.body_parts[dmr_target]['offset']
                            pixel_adjust = config.body_parts[dmr_target].get('pixel_adjust', 0)
                            target_part = dmr_target
                        else:
                            body_offset = 0.22  # Peito superior
                            target_part = 'upper_chest'
                    else:
                        # 🎯 AR/SMG - USAR BODY PART SELECTOR TAMBÉM!
                        ar_target = config.ar_config.get('target_body_part', 'head')
                        if ar_target in config.body_parts:
                            body_offset = config.body_parts[ar_target]['offset']
                            pixel_adjust = config.body_parts[ar_target].get('pixel_adjust', 0)
                            target_part = ar_target
                        else:
                            body_offset = float(current_cfg.get('head_offset_factor', 0.08))
                            target_part = 'head'
                    
                    # 🎯 PONTO DE MIRA PIXEL PERFECT
                    # body_offset = percentual da altura (0.0 = topo, 1.0 = base)
                    # pixel_adjust = ajuste fino em pixels para cada parte
                    aim_y = int(y1 + box_h * body_offset) + pixel_adjust
                    
                    # 🔧 AJUSTE FINO BASEADO NO TAMANHO DA CAIXA
                    # Personagens maiores (mais perto) precisam de ajuste diferente
                    if config.pixel_targeting.get('micro_adjust', True):
                        if box_h > 150:  # Personagem grande (perto)
                            aim_y += 2  # Ajuste para baixo
                        elif box_h < 60:  # Personagem pequeno (longe)
                            aim_y -= 1  # Ajuste para cima
                    
                    # Calcular distância do crosshair
                    dist_x = center_x - config.crosshairX
                    dist_y = aim_y - config.crosshairY
                    dist = math.sqrt(dist_x*dist_x + dist_y*dist_y)
                    
                    # Verificar se está dentro do FOV
                    if dist <= current_cfg['radius'] and dist < best_distance:
                        best_distance = dist
                        best_target = {
                            'x': center_x, 
                            'y': aim_y, 
                            'target_part': target_part, 
                            'body_offset': body_offset,
                            'box': (x1, y1, x2, y2)
                        }
                if best_target:
                    # ============================================
                    # 🔒 SISTEMA AIMLOCK V8 - STICKY AIM (GRUDA NO ALVO)
                    # ============================================
                    target_x = best_target['x']
                    target_y = best_target['y']
                    
                    # 🎯 MOVIMENTO DIRETO PARA O ALVO
                    raw_move_x = target_x - config.crosshairX
                    raw_move_y = target_y - config.crosshairY
                    distance = math.sqrt(raw_move_x*raw_move_x + raw_move_y*raw_move_y)
                    
                    current_cfg = config.get_current_config()
                    aimlock_str = float(current_cfg.get('aimlock_strength', 0.9))
                    sens = float(current_cfg.get('sensitivity', 0.5))
                    
                    # ============================================
                    # 🎯 SISTEMA STICKY AIM - GRUDA NO ALVO
                    # ============================================
                    # Quando perto do alvo, FORÇA a mira a ficar grudada
                    # Isso compensa o recoil automaticamente
                    
                    if distance < 15:
                        # 🔒 MODO GRUDADO - Correção FORTE para manter no alvo
                        # Move 80-100% da distância para grudar instantâneo
                        stick_factor = 0.85 + (aimlock_str * 0.15)  # 0.85 a 1.0
                        final_x = int(raw_move_x * stick_factor)
                        final_y = int(raw_move_y * stick_factor)
                        
                        # Recoil AGRESSIVO quando grudado (compensa subida da arma)
                        if current_cfg.get('recoil_control'):
                            rs = float(current_cfg.get('recoil_strength', 3.0))
                            final_y = final_y + int(rs * 2.5)  # Recoil forte
                        
                        max_move = 30
                        
                    elif distance < 40:
                        # 🎯 MODO TRACKING - Seguindo o alvo de perto
                        track_factor = 0.65 + (sens * 0.3)  # 0.65 a 0.95
                        final_x = int(raw_move_x * track_factor * 0.8)
                        final_y = int(raw_move_y * track_factor * 0.8)
                        
                        # Recoil moderado
                        if current_cfg.get('recoil_control'):
                            rs = float(current_cfg.get('recoil_strength', 3.0))
                            final_y = final_y + int(rs * 2.0)
                        
                        max_move = 50
                        
                    elif distance < 100:
                        # 🎯 MODO SNAP - Indo para o alvo
                        snap_factor = 0.50 + (sens * 0.4)  # 0.50 a 0.90
                        final_x = int(raw_move_x * snap_factor * 0.7)
                        final_y = int(raw_move_y * snap_factor * 0.7)
                        
                        # Recoil leve (prioriza chegar no alvo)
                        if current_cfg.get('recoil_control'):
                            rs = float(current_cfg.get('recoil_strength', 3.0))
                            final_y = final_y + int(rs * 1.0)
                        
                        max_move = 80
                        
                    else:
                        # 🎯 MODO LONGE - Snap rápido
                        far_factor = 0.40 + (sens * 0.3)
                        final_x = int(raw_move_x * far_factor * 0.6)
                        final_y = int(raw_move_y * far_factor * 0.6)
                        
                        # Sem recoil quando longe (foca em chegar no alvo)
                        max_move = 100
                    
                    # ============================================
                    # 🔒 ANTI-DRIFT HORIZONTAL
                    # ============================================
                    # Quando grudado (perto), REDUZ movimento horizontal
                    # Isso evita que a mira vá pros lados durante o tiro
                    if distance < 20:
                        # Reduz movimento X quando perto (prioriza Y para recoil)
                        if abs(raw_move_x) < 25:  # Se não está muito deslocado
                            final_x = int(final_x * 0.6)  # Reduz 40% do movimento horizontal
                    
                    # ============================================
                    # 🎮 APLICAR MULTIPLICADOR DE CALIBRAÇÃO
                    # ============================================
                    # Ajusta movimento baseado na calibração do usuário
                    mult = getattr(config, 'movement_multiplier', 1.0)
                    res_scale = getattr(config, 'resolution_scale', 1.0)
                    
                    # Escalar movimento baseado na resolução e calibração
                    final_x = int(final_x * mult * res_scale)
                    final_y = int(final_y * mult * res_scale)
                    
                    # ============================================
                    # 📏 APLICAR LIMITES
                    # ============================================
                    final_x = max(-max_move, min(max_move, final_x))
                    final_y = max(-max_move, min(max_move, final_y))
                    
                    # 🛡️ MICRO DEAD ZONE
                    if distance < 5:
                        if abs(final_x) < 2:
                            final_x = 0
                        if abs(final_y) < 2:
                            final_y = 0
                    
                    # 🖱️ APLICAR MOVIMENTO
                    if final_x != 0 or final_y != 0:
                        win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, final_x, final_y, 0, 0)
                    
                    # Debug
                    if frame_count % 60 == 0:
                        mode = "STICK" if distance < 15 else ("TRACK" if distance < 40 else ("SNAP" if distance < 100 else "FAR"))
                        print(f"🎯 {mode} | {best_target['target_part']} | Dist:{distance:.0f} | Move:({final_x},{final_y})")
                frame_count += 1
                if time.time() - last_time >= 1.0:
                    config.last_fps = float(frame_count)
                    print(f"🎯 FPS: {config.last_fps:.1f} | Weapon: {config.current_weapon}")
                    frame_count = 0
                    last_time = time.time()
            except Exception as e:
                em = str(e)
                if "_thread._local" in em:
                    # Já tratado acima, evita spam
                    time.sleep(0.05)
                    continue
                print(f"❌ Loop err: {em}")
                time.sleep(0.05)
        print("🛑 Detection loop stopped")
    threading.Thread(target=detection_loop, daemon=True).start()
    # GUI (bloqueia até fechar)
    CreateOverlay(user_info=user_data, on_close_callback=stop_all)
    print("🛑 App terminated")

if __name__ == "__main__":
    main()
