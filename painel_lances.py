"""
PAINEL DE CONTROLE E CONFIGURAÇÃO DO ROBÔ DE LANCES
Interface gráfica profissional e moderna com edição rápida de regras por lote.
"""

import os
import sys
import time
import re
import json
import threading
import subprocess
import socket
from decimal import Decimal, ROUND_DOWN
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

try:
    import selenium
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    import selenium.webdriver.chrome.webdriver
    import selenium.webdriver.chrome.service
except ImportError:
    messagebox.showerror("Erro", "Selenium não encontrado!\nExecute: pip install selenium")
    sys.exit(1)

ARQUIVO_REGRAS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "regras_lotes.json")


class PainelRoboLance(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("🎯 Painel de Controle de Lances - Licitações")
        self.geometry("940x740")
        self.minsize(840, 640)
        self.configure(bg="#181825")

        # Estado da Aplicação
        self.robo_ativo = False
        self.driver = None
        self.thread_robo = None
        self.total_lances_enviados = 0
        self.regras_lotes = {}

        # Inicialização dos Componentes Visuais
        self.configurar_estilos()
        self.criar_barra_superior()
        self.criar_card_controle_geral()
        self.criar_secao_edicao_regras()
        self.criar_secao_logs()

        # Carregar Regras Iniciais
        self.carregar_regras_do_arquivo()

        self.protocol("WM_DELETE_WINDOW", self.ao_fechar)

    def configurar_estilos(self):
        self.style = ttk.Style(self)
        self.style.theme_use("clam")

        self.BG_DARK = "#181825"
        self.BG_CARD = "#1e1e2e"
        self.BG_INPUT = "#313244"
        self.FG_TEXT = "#cdd6f4"
        self.COLOR_GREEN = "#a6e3a1"
        self.COLOR_RED = "#f38ba8"
        self.COLOR_YELLOW = "#f9e2af"
        self.COLOR_BLUE = "#89b4fa"
        self.COLOR_PURPLE = "#cba6f7"

        self.style.configure("Treeview",
                             background="#1e1e2e",
                             foreground="#cdd6f4",
                             fieldbackground="#1e1e2e",
                             rowheight=26,
                             font=("Segoe UI", 10))
        self.style.configure("Treeview.Heading",
                             background="#313244",
                             foreground="#ffffff",
                             font=("Segoe UI", 10, "bold"))
        self.style.map("Treeview",
                       background=[("selected", "#45475a")],
                       foreground=[("selected", "#a6e3a1")])

    def criar_barra_superior(self):
        top_bar = tk.Frame(self, bg=self.BG_DARK, pady=10, padx=15)
        top_bar.pack(fill="x")

        lbl_titulo = tk.Label(
            top_bar,
            text="⚡ ROBÔ DE LANCES AUTOMÁTICOS",
            font=("Segoe UI", 16, "bold"),
            bg=self.BG_DARK,
            fg=self.COLOR_BLUE
        )
        lbl_titulo.pack(side="left")

        btn_chrome = tk.Button(
            top_bar,
            text="🌐 Abrir Google Chrome (Depuração)",
            command=self.abrir_chrome_debug,
            bg="#313244",
            fg="#cdd6f4",
            activebackground="#45475a",
            activeforeground="#ffffff",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=14,
            pady=5,
            cursor="hand2"
        )
        btn_chrome.pack(side="right")

    def criar_card_controle_geral(self):
        card = tk.Frame(self, bg=self.BG_CARD, bd=1, relief="solid", highlightbackground="#45475a")
        card.pack(fill="x", padx=15, pady=(0, 10))

        inner = tk.Frame(card, bg=self.BG_CARD, padx=15, pady=12)
        inner.pack(fill="x")

        # Status
        self.lbl_status = tk.Label(
            inner,
            text="🔴 STATUS: DESLIGADO (PARADO)",
            font=("Segoe UI", 12, "bold"),
            bg=self.BG_CARD,
            fg=self.COLOR_RED
        )
        self.lbl_status.pack(side="left")

        # Contador de Lances
        self.lbl_contador = tk.Label(
            inner,
            text="Lances Enviados: 0",
            font=("Segoe UI", 10, "bold"),
            bg=self.BG_CARD,
            fg="#a6adc8"
        )
        self.lbl_contador.pack(side="left", padx=25)

        # Botão ON / OFF
        self.btn_toggle = tk.Button(
            inner,
            text="▶ LIGAR ROBÔ (ON)",
            command=self.toggle_robo,
            bg="#2e7d32",
            fg="#ffffff",
            activebackground="#388e3c",
            activeforeground="#ffffff",
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            padx=25,
            pady=6,
            cursor="hand2"
        )
        self.btn_toggle.pack(side="right")

    def criar_secao_edicao_regras(self):
        card_regras = tk.Frame(self, bg=self.BG_CARD, bd=1, relief="solid", highlightbackground="#45475a")
        card_regras.pack(fill="x", padx=15, pady=(0, 10))

        # Cabeçalho com Título e Botão de Puxar Lotes
        frame_header = tk.Frame(card_regras, bg=self.BG_CARD, padx=15, pady=10)
        frame_header.pack(fill="x")

        lbl_header = tk.Label(
            frame_header,
            text="📋 TABELA DE REGRAS E ALTERAÇÃO POR LOTE (STOP-LOSS)",
            font=("Segoe UI", 11, "bold"),
            bg=self.BG_CARD,
            fg=self.COLOR_YELLOW
        )
        lbl_header.pack(side="left")

        btn_puxar = tk.Button(
            frame_header,
            text="📥 Puxar Lotes Marcados do Portal",
            command=self.puxar_lotes_do_portal,
            bg="#b4befe",
            fg="#11111b",
            activebackground="#cdd6f4",
            activeforeground="#11111b",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=12,
            pady=4,
            cursor="hand2"
        )
        btn_puxar.pack(side="right")

        # Tabela Treeview
        frame_tabela = tk.Frame(card_regras, bg=self.BG_CARD, padx=15, pady=2)
        frame_tabela.pack(fill="x")

        colunas = ("lote", "minimo", "decremento", "status")
        self.tree_regras = ttk.Treeview(frame_tabela, columns=colunas, show="headings", height=5)
        self.tree_regras.heading("lote", text="Nº Lote")
        self.tree_regras.heading("minimo", text="Preço Mínimo (Stop-Loss)")
        self.tree_regras.heading("decremento", text="Diminuir por Lance")
        self.tree_regras.heading("status", text="Ação / Status")

        self.tree_regras.column("lote", width=100, anchor="center")
        self.tree_regras.column("minimo", width=240, anchor="center")
        self.tree_regras.column("decremento", width=200, anchor="center")
        self.tree_regras.column("status", width=180, anchor="center")
        self.tree_regras.pack(side="left", fill="x", expand=True)

        # Ao clicar numa linha, preenche os campos automaticamente para alteração rápida!
        self.tree_regras.bind("<<TreeviewSelect>>", self.ao_selecionar_linha_tabela)

        # Formulário de Alteração / Adição Rápida
        form_frame = tk.Frame(card_regras, bg=self.BG_CARD, padx=15, pady=8)
        form_frame.pack(fill="x")

        tk.Label(form_frame, text="Nº Lote:", bg=self.BG_CARD, fg=self.FG_TEXT, font=("Segoe UI", 9, "bold")).grid(row=0, column=0, padx=4)
        self.ent_lote = tk.Entry(form_frame, width=8, bg=self.BG_INPUT, fg="#ffffff", font=("Segoe UI", 10, "bold"), insertbackground="white", justify="center")
        self.ent_lote.grid(row=0, column=1, padx=4)

        tk.Label(form_frame, text="Preço Mínimo (R$):", bg=self.BG_CARD, fg=self.FG_TEXT, font=("Segoe UI", 9, "bold")).grid(row=0, column=2, padx=4)
        self.ent_minimo = tk.Entry(form_frame, width=12, bg=self.BG_INPUT, fg=self.COLOR_YELLOW, font=("Segoe UI", 10, "bold"), insertbackground="white", justify="center")
        self.ent_minimo.grid(row=0, column=3, padx=4)

        tk.Label(form_frame, text="Diminuir (R$):", bg=self.BG_CARD, fg=self.FG_TEXT, font=("Segoe UI", 9, "bold")).grid(row=0, column=4, padx=4)
        self.ent_decremento = tk.Entry(form_frame, width=10, bg=self.BG_INPUT, fg=self.COLOR_GREEN, font=("Segoe UI", 10, "bold"), insertbackground="white", justify="center")
        self.ent_decremento.insert(0, "1.00")
        self.ent_decremento.grid(row=0, column=5, padx=4)

        # Botão Salvar / Alterar Regra
        btn_salvar = tk.Button(
            form_frame,
            text="💾 Salvar / Alterar Regra",
            command=self.salvar_regra,
            bg="#1e66f5",
            fg="#ffffff",
            activebackground="#7287fd",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=12,
            pady=3,
            cursor="hand2"
        )
        btn_salvar.grid(row=0, column=6, padx=8)

        # Botão Remover Regra
        btn_remover = tk.Button(
            form_frame,
            text="🗑️ Excluir Regra",
            command=self.remover_regra,
            bg="#313244",
            fg=self.COLOR_RED,
            activebackground="#45475a",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=10,
            pady=3,
            cursor="hand2"
        )
        btn_remover.grid(row=0, column=7, padx=4)

        # Barra inferior de opções gerais
        opcoes_frame = tk.Frame(card_regras, bg=self.BG_CARD, padx=15, pady=6)
        opcoes_frame.pack(fill="x")

        tk.Label(opcoes_frame, text="Regra Geral (para lotes sem regra específica): Mínimo R$:", bg=self.BG_CARD, fg="#a6adc8", font=("Segoe UI", 9)).pack(side="left")
        self.ent_min_padrao = tk.Entry(opcoes_frame, width=8, bg=self.BG_INPUT, fg=self.COLOR_YELLOW, font=("Segoe UI", 9, "bold"), justify="center")
        self.ent_min_padrao.insert(0, "1.00")
        self.ent_min_padrao.pack(side="left", padx=4)

        tk.Label(opcoes_frame, text="Diminuir Padrão R$:", bg=self.BG_CARD, fg="#a6adc8", font=("Segoe UI", 9)).pack(side="left", padx=(10, 0))
        self.ent_dec_padrao = tk.Entry(opcoes_frame, width=8, bg=self.BG_INPUT, fg=self.COLOR_GREEN, font=("Segoe UI", 9, "bold"), justify="center")
        self.ent_dec_padrao.insert(0, "1.00")
        self.ent_dec_padrao.pack(side="left", padx=4)

        self.var_apenas_marcados = tk.BooleanVar(value=True)
        self.chk_marcados = tk.Checkbutton(
            opcoes_frame,
            text="Apenas caixas marcadas no portal (☑)",
            variable=self.var_apenas_marcados,
            bg=self.BG_CARD,
            fg=self.FG_TEXT,
            selectcolor=self.BG_INPUT,
            activebackground=self.BG_CARD,
            activeforeground=self.FG_TEXT,
            font=("Segoe UI", 9)
        )
        self.chk_marcados.pack(side="right")

    def criar_secao_logs(self):
        frame_log_header = tk.Frame(self, bg=self.BG_DARK, padx=18)
        frame_log_header.pack(fill="x", pady=(2, 2))

        lbl_log = tk.Label(frame_log_header, text="📡 Histórico de Lances em Tempo Real:", bg=self.BG_DARK, fg="#a6adc8", font=("Segoe UI", 10, "bold"))
        lbl_log.pack(side="left")

        btn_limpar_log = tk.Button(
            frame_log_header,
            text="🧹 Limpar Histórico",
            command=self.limpar_logs,
            bg="#313244",
            fg="#a6adc8",
            relief="flat",
            font=("Segoe UI", 8),
            padx=8,
            cursor="hand2"
        )
        btn_limpar_log.pack(side="right")

        frame_terminal = tk.Frame(self, bg="#11111b", padx=2, pady=2)
        frame_terminal.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        self.txt_log = scrolledtext.ScrolledText(
            frame_terminal,
            wrap="word",
            bg="#11111b",
            fg="#cdd6f4",
            insertbackground="white",
            font=("Consolas", 10),
            relief="flat"
        )
        self.txt_log.pack(fill="both", expand=True)

        self.txt_log.tag_config("INFO", foreground="#89b4fa")
        self.txt_log.tag_config("SUCCESS", foreground="#a6e3a1")
        self.txt_log.tag_config("WARNING", foreground="#f9e2af")
        self.txt_log.tag_config("DANGER", foreground="#f38ba8")
        self.txt_log.tag_config("TIMESTAMP", foreground="#6c7086")

    def log(self, mensagem, tipo="INFO"):
        timestamp = time.strftime("[%H:%M:%S]")
        self.txt_log.insert(tk.END, f"{timestamp} ", "TIMESTAMP")
        self.txt_log.insert(tk.END, f"{mensagem}\n", tipo)
        self.txt_log.see(tk.END)

    def limpar_logs(self):
        self.txt_log.delete("1.0", tk.END)

    def ao_selecionar_linha_tabela(self, event):
        selecionado = self.tree_regras.selection()
        if not selecionado:
            return
        item = self.tree_regras.item(selecionado[0])
        valores = item["values"]
        if valores:
            match = re.search(r'\d+', str(valores[0]))
            if match:
                self.ent_lote.delete(0, tk.END)
                self.ent_lote.insert(0, match.group(0))

            min_txt = str(valores[1]).replace("R$", "").strip()
            self.ent_minimo.delete(0, tk.END)
            self.ent_minimo.insert(0, min_txt)

            dec_txt = str(valores[2]).replace("R$", "").strip()
            self.ent_decremento.delete(0, tk.END)
            self.ent_decremento.insert(0, dec_txt)

    def carregar_regras_do_arquivo(self):
        if os.path.exists(ARQUIVO_REGRAS):
            try:
                with open(ARQUIVO_REGRAS, "r", encoding="utf-8") as f:
                    dados = json.load(f)
                    self.regras_lotes = {}
                    for lote_str, conf in dados.items():
                        minimo = Decimal(str(conf.get("minimo", "1.00")))
                        dec = Decimal(str(conf.get("decremento", "1.00")))
                        self.regras_lotes[str(lote_str)] = {"minimo": minimo, "decremento": dec}

                self.atualizar_tabela_regras()
            except Exception as e:
                self.log(f"[ERRO] Falha ao carregar regras: {e}", "DANGER")

    def salvar_regras_no_arquivo(self):
        try:
            dados = {}
            for lote_str, conf in self.regras_lotes.items():
                dados[lote_str] = {
                    "minimo": str(conf["minimo"]),
                    "decremento": str(conf["decremento"])
                }
            with open(ARQUIVO_REGRAS, "w", encoding="utf-8") as f:
                json.dump(dados, f, indent=2)
        except Exception as e:
            self.log(f"[ERRO] Falha ao salvar regras: {e}", "DANGER")

    def atualizar_tabela_regras(self):
        for item in self.tree_regras.get_children():
            self.tree_regras.delete(item)

        for lote in sorted(self.regras_lotes.keys(), key=lambda x: int(x) if x.isdigit() else x):
            regra = self.regras_lotes[lote]
            min_fmt = f"R$ {regra['minimo']:.4f}"
            dec_fmt = f"R$ {regra['decremento']:.4f}"
            self.tree_regras.insert("", "end", values=(f"Lote {lote}", min_fmt, dec_fmt, "Ativo (Personalizado)"))

    def salvar_regra(self):
        lote = self.ent_lote.get().strip()
        minimo_str = self.ent_minimo.get().strip().replace(",", ".")
        dec_str = self.ent_decremento.get().strip().replace(",", ".")

        if not lote:
            messagebox.showwarning("Aviso", "Por favor, digite o número do lote!")
            return

        try:
            minimo = Decimal(minimo_str)
            dec = Decimal(dec_str)
            if minimo <= 0 or dec <= 0:
                raise ValueError()
        except Exception:
            messagebox.showerror("Erro", "Valores inválidos para Preço Mínimo ou Diminuir!")
            return

        self.regras_lotes[str(lote)] = {"minimo": minimo, "decremento": dec}
        self.salvar_regras_no_arquivo()
        self.atualizar_tabela_regras()
        self.log(f"[REGRA SALVA] Lote {lote} -> Mínimo R$ {minimo:.4f} | Decremento R$ {dec:.4f}", "SUCCESS")

        self.ent_lote.delete(0, tk.END)
        self.ent_minimo.delete(0, tk.END)

    def remover_regra(self):
        lote = self.ent_lote.get().strip()
        if not lote:
            selecionado = self.tree_regras.selection()
            if selecionado:
                item = self.tree_regras.item(selecionado[0])
                match = re.search(r'\d+', str(item["values"][0]))
                if match:
                    lote = match.group(0)

        if lote and str(lote) in self.regras_lotes:
            del self.regras_lotes[str(lote)]
            self.salvar_regras_no_arquivo()
            self.atualizar_tabela_regras()
            self.log(f"[REGRA REMOVIDA] Lote {lote} voltará a usar as regras gerais.", "WARNING")
            self.ent_lote.delete(0, tk.END)
            self.ent_minimo.delete(0, tk.END)
        else:
            messagebox.showinfo("Informação", "Nenhuma regra selecionada para exclusão.")

    def verificar_porta_aberta(self, host="127.0.0.1", port=9222):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.5)
        try:
            s.connect((host, port))
            s.close()
            return True
        except Exception:
            return False

    def abrir_chrome_debug(self):
        self.log("[CHROME] Iniciando Google Chrome em modo de depuração (porta 9222)...", "INFO")
        caminhos = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")
        ]
        chrome_exe = "chrome.exe"
        for c in caminhos:
            if os.path.exists(c):
                chrome_exe = c
                break

        pasta_debug = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data Debug")
        cmd = [
            chrome_exe,
            "--remote-debugging-port=9222",
            f"--user-data-dir={pasta_debug}"
        ]
        try:
            subprocess.Popen(cmd)
            self.log("[CHROME] Chrome aberto! Faça login no portal e acesse a tela de lances.", "SUCCESS")
        except Exception as e:
            self.log(f"[ERRO] Falha ao abrir o Chrome: {e}", "DANGER")

    def conectar_driver(self):
        if self.driver:
            try:
                _ = self.driver.current_url
                return self.driver
            except Exception:
                self.driver = None

        options = Options()
        if self.verificar_porta_aberta():
            options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
            self.driver = webdriver.Chrome(options=options)
        else:
            self.log("[AVISO] Chrome na porta 9222 não detectado. Tentando abrir automaticamente...", "WARNING")
            self.abrir_chrome_debug()
            for _ in range(12):
                time.sleep(0.5)
                if self.verificar_porta_aberta():
                    break
            if self.verificar_porta_aberta():
                options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
                self.driver = webdriver.Chrome(options=options)
            else:
                raise Exception("Porta 9222 do Chrome não respondeu. Abra o Chrome pelo botão no topo.")
        return self.driver

    def linha_esta_marcada(self, linha):
        try:
            cbs = linha.find_elements(By.XPATH, ".//input[@type='checkbox']")
            if cbs:
                for cb in cbs:
                    try:
                        if cb.is_selected():
                            return True
                        if self.driver and self.driver.execute_script("return arguments[0].checked;", cb) is True:
                            return True
                        if cb.get_attribute("checked") in ["true", "checked", ""]:
                            return True
                        if cb.get_property("checked") is True:
                            return True
                        if cb.get_attribute("aria-checked") == "true":
                            return True
                    except Exception:
                        pass

            custom_cbs = linha.find_elements(By.XPATH, ".//*[contains(@class, 'checkbox') or contains(@class, 'check') or contains(@class, 'switch')]")
            for elem in custom_cbs:
                try:
                    classes = elem.get_attribute("class") or ""
                    aria = elem.get_attribute("aria-checked") or ""
                    if "checked" in classes.lower() or "active" in classes.lower() or "selected" in classes.lower() or aria == "true":
                        return True
                except Exception:
                    pass
        except Exception:
            pass
        return False

    def puxar_lotes_do_portal(self):
        """Varre a página aberta no Chrome e adiciona os lotes marcados na tabela de regras."""
        def _executar():
            try:
                self.log("[PORTAL] Conectando ao Chrome para escanear os lotes...", "INFO")
                driver = self.conectar_driver()
                if not driver:
                    self.log("[PORTAL] Falha ao conectar ao Chrome.", "DANGER")
                    return

                # Localiza linhas da tabela
                linhas = driver.find_elements(By.XPATH, "//table//tbody/tr[.//input[contains(@value, 'Enviar') or contains(@type, 'button') or contains(@type, 'submit') or @type='text']]")
                if not linhas:
                    linhas = driver.find_elements(By.XPATH, "//table//tbody/tr[.//input[@type='checkbox']]")
                if not linhas:
                    linhas = driver.find_elements(By.XPATH, "//tr[.//input[contains(@type, 'text')]]")

                if not linhas:
                    self.log("[PORTAL] Nenhuma tabela de lances encontrada na tela aberta do Chrome!", "WARNING")
                    return

                try:
                    minimo_padrao = Decimal(self.ent_min_padrao.get().replace(",", "."))
                except Exception:
                    minimo_padrao = Decimal("1.00")

                try:
                    dec_padrao = Decimal(self.ent_dec_padrao.get().replace(",", "."))
                except Exception:
                    dec_padrao = Decimal("1.00")

                lotes_encontrados = []
                novos_adicionados = 0

                for idx, linha in enumerate(linhas, start=1):
                    try:
                        # Se configurado para apenas marcados, verifica checkbox
                        if self.var_apenas_marcados.get():
                            if not self.linha_esta_marcada(linha):
                                continue

                        colunas = linha.find_elements(By.TAG_NAME, "td")
                        texto_linha = linha.text

                        match_lote = re.search(r'^\s*(\d+)', texto_linha)
                        if not match_lote and len(colunas) > 1:
                            match_lote = re.search(r'(\d+)', colunas[1].text)
                        if not match_lote:
                            match_lote = re.search(r'Lote\s*(\d+)', texto_linha, re.IGNORECASE)

                        lote_num = str(int(match_lote.group(1))) if match_lote else str(idx)
                        lotes_encontrados.append(lote_num)

                        if lote_num not in self.regras_lotes:
                            self.regras_lotes[lote_num] = {
                                "minimo": minimo_padrao,
                                "decremento": dec_padrao
                            }
                            novos_adicionados += 1
                    except Exception:
                        continue

                self.salvar_regras_no_arquivo()
                self.atualizar_tabela_regras()

                if lotes_encontrados:
                    lista_str = ", ".join(lotes_encontrados)
                    self.log(f"[PORTAL] ✅ Lotes detectados ({len(lotes_encontrados)}): {lista_str}", "SUCCESS")
                    if novos_adicionados > 0:
                        self.log(f"[PORTAL] 💾 {novos_adicionados} novos lote(s) inseridos na tabela de regras com sucesso!", "SUCCESS")
                else:
                    self.log("[PORTAL] ⚠️ Nenhum lote marcado foi encontrado. Marque as caixas de seleção na página do Compras BR e clique novamente.", "WARNING")

            except Exception as e:
                self.log(f"[PORTAL] Erro ao puxar lotes: {e}", "DANGER")

        threading.Thread(target=_executar, daemon=True).start()

    def toggle_robo(self):
        if not self.robo_ativo:
            self.iniciar_robo()
        else:
            self.parar_robo()

    def iniciar_robo(self):
        try:
            minimo_padrao = Decimal(self.ent_min_padrao.get().replace(",", "."))
            dec_padrao = Decimal(self.ent_dec_padrao.get().replace(",", "."))
        except Exception:
            messagebox.showerror("Erro", "Valores padrões de Mínimo ou Diminuir inválidos!")
            return

        self.robo_ativo = True
        self.lbl_status.config(text="🟢 STATUS: LIGADO (MONITORANDO LANCES)", fg=self.COLOR_GREEN)
        self.btn_toggle.config(text="⏹ DESLIGAR ROBÔ (OFF)", bg="#c62828", activebackground="#d32f2f")

        self.log(f"[ROBÔ LIGADO] Regras ativas para {len(self.regras_lotes)} lote(s).", "SUCCESS")

        self.thread_robo = threading.Thread(
            target=self.loop_monitoramento,
            args=(dec_padrao, minimo_padrao),
            daemon=True
        )
        self.thread_robo.start()

    def parar_robo(self):
        self.robo_ativo = False
        self.lbl_status.config(text="🔴 STATUS: DESLIGADO (PARADO)", fg=self.COLOR_RED)
        self.btn_toggle.config(text="▶ LIGAR ROBÔ (ON)", bg="#2e7d32", activebackground="#388e3c")
        self.log("[ROBÔ DESLIGADO] Monitoramento pausado.", "WARNING")

    def loop_monitoramento(self, dec_padrao, minimo_padrao):
        try:
            self.log("[CONEXÃO] Conectando ao Chrome...", "INFO")
            driver = self.conectar_driver()
            self.log("[CONEXÃO] Conectado ao Chrome com sucesso!", "SUCCESS")
        except Exception as e:
            self.log(f"[ERRO DE CONEXÃO] Falha ao conectar ao Chrome: {e}", "DANGER")
            self.after(0, self.parar_robo)
            return

        while self.robo_ativo:
            try:
                linhas = self.driver.find_elements(By.XPATH, "//table//tbody/tr[.//input[contains(@value, 'Enviar') or contains(@type, 'button') or contains(@type, 'submit') or @type='text']]")
                if not linhas:
                    linhas = self.driver.find_elements(By.XPATH, "//tr[.//input[contains(@type, 'text')]]")

                if not linhas:
                    time.sleep(1.0)
                    continue

                for idx, linha in enumerate(linhas, start=1):
                    if not self.robo_ativo:
                        break

                    try:
                        colunas = linha.find_elements(By.TAG_NAME, "td")
                        if not colunas:
                            continue

                        if self.var_apenas_marcados.get():
                            if not self.linha_esta_marcada(linha):
                                continue

                        texto_linha = linha.text
                        match_lote = re.search(r'^\s*(\d+)', texto_linha) or re.search(r'(\d+)', colunas[1].text if len(colunas) > 1 else "")
                        lote_num = str(int(match_lote.group(1))) if match_lote else str(idx)

                        # Carrega regra do lote
                        regra = self.regras_lotes.get(lote_num, {"minimo": minimo_padrao, "decremento": dec_padrao})
                        valor_minimo = regra["minimo"]
                        decremento = regra["decremento"]

                        valores = []
                        for td in colunas:
                            txt = td.text.strip()
                            if re.search(r'\d+[,\.]\d{2,4}', txt):
                                limpo = re.sub(r'[^\d,\.]', '', txt)
                                if ',' in limpo:
                                    limpo = limpo.replace('.', '').replace(',', '.')
                                try:
                                    valores.append(Decimal(limpo))
                                except Exception:
                                    pass

                        if len(valores) < 2:
                            continue

                        primeiro_lugar = valores[0]
                        meu_lance = valores[-1]

                        # Se não estiver em 1º lugar
                        if meu_lance > primeiro_lugar:
                            novo_lance = primeiro_lugar - decremento

                            # Trava de Segurança
                            if novo_lance < valor_minimo:
                                self.log(f"[LOTE {lote_num}] 🛑 Limite Mínimo Atingido! (Lance R$ {novo_lance:.4f} < Mínimo R$ {valor_minimo:.4f}). Lance protegido!", "DANGER")
                                continue

                            campo_lance = linha.find_element(By.XPATH, ".//input[@type='text']")
                            botao_enviar = linha.find_element(By.XPATH, ".//input[@value='Enviar Lance' or @value='Enviar' or contains(@type, 'button') or contains(@type, 'submit')] | .//button[contains(text(), 'Enviar')]")

                            campo_lance.click()
                            campo_lance.send_keys(Keys.CONTROL + "a")
                            campo_lance.send_keys(Keys.BACKSPACE)

                            valor_formatado = f"{novo_lance.quantize(Decimal('0.0001'), rounding=ROUND_DOWN):.4f}".replace('.', ',')
                            campo_lance.send_keys(valor_formatado)
                            time.sleep(0.05)
                            botao_enviar.click()

                            self.total_lances_enviados += 1
                            self.lbl_contador.config(text=f"Lances Enviados: {self.total_lances_enviados}")
                            self.log(f"[LOTE {lote_num}] ⚡ Lance R$ {valor_formatado} enviado com sucesso!", "SUCCESS")

                            try:
                                modal = WebDriverWait(self.driver, 1.0).until(
                                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Sim') or contains(text(), 'Confirmar') or contains(text(), 'OK')]"))
                                )
                                modal.click()
                            except Exception:
                                pass

                    except Exception:
                        continue

            except Exception:
                pass

            time.sleep(1.0)

    def ao_fechar(self):
        self.robo_ativo = False
        self.destroy()


if __name__ == "__main__":
    try:
        app = PainelRoboLance()
        app.mainloop()
    except Exception as e:
        import traceback
        erro_msg = traceback.format_exc()
        print(f"\n[ERRO CRÍTICO AO INICIAR O PAINEL]:\n{erro_msg}")
        try:
            import tkinter.messagebox as mb
            mb.showerror("Erro ao Iniciar Painel", f"Ocorreu um erro ao abrir o painel:\n\n{e}\n\nVerifique o console para mais detalhes.")
        except Exception:
            pass
        sys.exit(1)
