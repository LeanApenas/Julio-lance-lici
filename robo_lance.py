"""
Robô de Lances Automáticos para Licitações / Portais de Compras
Funcionalidades:
- Compara a 1ª posição com o 'Meu Lance'.
- Se não estiver em 1º lugar, calcula (1º lugar - R$ 0,01).
- Possui Trava de Segurança (Stop-Loss / Preço Mínimo) para não enviar lances abaixo do custo.
- Preenche o campo de lance e clica em 'Enviar Lance'.
- Pode conectar diretamente ao seu Chrome já aberto e logado (via porta 9222) ou abrir uma nova sessão.
"""

import time
import re
from decimal import Decimal, ROUND_DOWN
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ==============================================================================
# CONFIGURAÇÕES GERAIS
# ==============================================================================
# Valor a subtrair do 1º colocado (R$ 1,00)
DECREMENTO = Decimal('1.00')

# Intervalo entre checagens (em segundos)
INTERVALO_LOOP = 1.0

# Se True, monitora apenas os lotes com checkbox marcado
APENAS_LOTES_SELECIONADOS = True

import os
import json

ARQUIVO_REGRAS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "regras_lotes.json")

def carregar_regras_lotes():
    regras = {}
    if os.path.exists(ARQUIVO_REGRAS):
        try:
            with open(ARQUIVO_REGRAS, "r", encoding="utf-8") as f:
                dados = json.load(f)
                for k, v in dados.items():
                    regras[str(k)] = {
                        "minimo": Decimal(str(v.get("minimo", "1.00"))),
                        "decremento": Decimal(str(v.get("decremento", "1.00")))
                    }
        except Exception:
            pass
    return regras


def converter_para_decimal(texto_valor: str) -> Decimal:
    """Converte '138,0000' ou 'R$ 138,00' para Decimal(138.0000)"""
    if not texto_valor:
        return Decimal('0.0000')
    # Remove tudo exceto dígitos, vírgula e ponto
    limpo = re.sub(r'[^\d,\.]', '', texto_valor.strip())
    # Se tiver vírgula como separador decimal, substitui por ponto
    if ',' in limpo:
        limpo = limpo.replace('.', '').replace(',', '.')
    try:
        return Decimal(limpo)
    except Exception:
        return Decimal('0.0000')


def formatar_para_lance(valor: Decimal) -> str:
    """Formata Decimal(137.99) para '137,9900' com 4 casas decimais padrão do portal."""
    valor_arredondado = valor.quantize(Decimal('0.0001'), rounding=ROUND_DOWN)
    return f"{valor_arredondado:.4f}".replace('.', ',')


def verificar_porta_aberta(host="127.0.0.1", port=9222):
    import socket
    try:
        with socket.create_connection((host, port), timeout=0.8):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def inicializar_driver():
    options = Options()
    if verificar_porta_aberta("127.0.0.1", 9222):
        print(f"[*] Conectando ao Chrome na porta de depuração 127.0.0.1:9222...")
        options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    else:
        print("[*] Porta 9222 não detectada. Iniciando uma nova janela do Chrome...")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-notifications")

    driver = webdriver.Chrome(options=options)
    return driver


def linha_esta_marcada(linha):
    """Verifica com precisão se a caixa de seleção (checkbox) da linha está marcada."""
    try:
        cbs = linha.find_elements(By.XPATH, ".//input[@type='checkbox']")
        if cbs:
            cb = cbs[0]
            if cb.is_selected():
                return True
            if cb.get_attribute("checked") in ["true", "checked", ""]:
                return True
            if cb.get_property("checked") is True:
                return True
            if cb.get_attribute("aria-checked") == "true":
                return True

        custom_cbs = linha.find_elements(By.XPATH, ".//*[contains(@class, 'checkbox') or contains(@class, 'check')]")
        for elem in custom_cbs:
            classes = elem.get_attribute("class") or ""
            aria = elem.get_attribute("aria-checked") or ""
            if "checked" in classes.lower() or "active" in classes.lower() or aria == "true":
                return True
    except Exception:
        pass
    return False


def monitorar_e_enviar_lances(driver):
    print("=" * 60)
    print("ROBÔ DE LANCES INICIADO")
    print(f"- Decremento: R$ {DECREMENTO}")
    print(f"- Intervalo de checagem: {INTERVALO_LOOP}s")
    print("=" * 60)

    while True:
        try:
            linhas = driver.find_elements(By.XPATH, "//table//tbody/tr[.//input[contains(@value, 'Enviar') or contains(@type, 'button') or contains(@type, 'submit') or @type='text']]")
            
            if not linhas:
                linhas = driver.find_elements(By.XPATH, "//tr[.//input[contains(@type, 'text')]]")

            if not linhas:
                print("[!] Nenhuma linha de lance encontrada na tela atual. Aguardando...")
                time.sleep(INTERVALO_LOOP)
                continue

            for idx, linha in enumerate(linhas, start=1):
                try:
                    colunas = linha.find_elements(By.TAG_NAME, "td")
                    if not colunas:
                        continue

                    # Se configurado para apenas marcados, ignora desmarcados
                    if APENAS_LOTES_SELECIONADOS:
                        if not linha_esta_marcada(linha):
                            continue

                    # Extrai texto do número do lote (geralmente na coluna 1 ou 2)
                    texto_linha = linha.text
                    match_lote = re.search(r'^\s*(\d+)', texto_linha) or re.search(r'(\d+)', colunas[1].text if len(colunas) > 1 else "")
                    if match_lote:
                        lote_num = int(match_lote.group(1))

                    # 2. Obter valores das colunas (1º Colocado e Meu Lance)
                    # Busca por valores numéricos formatados na linha
                    valores_encontrados = []
                    for td in colunas:
                        texto_td = td.text.strip()
                        # Se o texto parece um preço (ex: 138,0000 ou 16,9200)
                        if re.search(r'\d+[,\.]\d{2,4}', texto_td):
                            valores_encontrados.append(converter_para_decimal(texto_td))

                    if len(valores_encontrados) < 2:
                        continue

                    # Na tabela:
                    # [1º Lance, 2º Lance, 3º Lance, Meu Lance]
                    primeiro_lugar = valores_encontrados[0]
                    meu_lance = valores_encontrados[-1]  # 'Meu Lance' fica na coluna antes de 'Efetuar Lance'

                    # Se 'Meu Lance' for igual a 0 ou não detectado diretamente, verifica o dot / status
                    # Se Meu Lance for maior que o 1º Lugar, significa que NÃO estamos em primeiro
                    if meu_lance > primeiro_lugar:
                        regras = carregar_regras_lotes()
                        chave_lote = str(lote_num or idx)
                        conf = regras.get(chave_lote, {"minimo": Decimal('1.0000'), "decremento": DECREMENTO})
                        decremento = conf.get("decremento", DECREMENTO)
                        valor_minimo = conf.get("minimo", Decimal('1.0000'))

                        novo_lance = primeiro_lugar - decremento

                        print(f"\n[LOTE {lote_num or idx}] ⚠️ NÃO ESTAMOS EM 1º LUGAR!")
                        print(f"   1º Lugar: R$ {primeiro_lugar} | Meu Lance: R$ {meu_lance}")
                        print(f"   Novo lance calculado: R$ {novo_lance} (Mínimo permitido: R$ {valor_minimo})")

                        # Verificação de segurança (Stop Loss)
                        if novo_lance < valor_minimo:
                            print(f"   🛑 ALERTA: Novo lance R$ {novo_lance} é menor que o mínimo seguro R$ {valor_minimo}. Lance cancelado!")
                            continue

                        # 3. Localizar Campo de Texto e Botão de Enviar Lance
                        campo_lance = linha.find_element(By.XPATH, ".//input[@type='text']")
                        botao_enviar = linha.find_element(By.XPATH, ".//input[@value='Enviar Lance' or @value='Enviar' or contains(@type, 'button') or contains(@type, 'submit')] | .//button[contains(text(), 'Enviar')]")

                        # 4. Inserir o novo valor
                        campo_lance.click()
                        campo_lance.send_keys(Keys.CONTROL + "a")
                        campo_lance.send_keys(Keys.BACKSPACE)
                        valor_formatado = formatar_para_lance(novo_lance)
                        campo_lance.send_keys(valor_formatado)
                        time.sleep(0.1)

                        # 5. Clicar em Enviar Lance
                        botao_enviar.click()
                        print(f"   ✅ [LANCE ENVIADO] R$ {valor_formatado} para o Lote {lote_num or idx}!")

                        # Se houver modal de confirmação (ex: 'Deseja confirmar o lance?')
                        try:
                            modal_confirm = WebDriverWait(driver, 1.5).until(
                                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Sim') or contains(text(), 'Confirmar') or contains(text(), 'OK')]"))
                            )
                            modal_confirm.click()
                            print("   [+] Confirmação aceita no modal.")
                        except Exception:
                            pass

                    elif meu_lance == primeiro_lugar:
                        # Já estamos em 1º lugar!
                        pass

                except Exception as e:
                    # Erro específico ao processar uma linha individual
                    continue

        except KeyboardInterrupt:
            print("\n[!] Robô finalizado pelo usuário.")
            break
        except Exception as e:
            print(f"[!] Erro no loop principal: {e}")
            time.sleep(INTERVALO_LOOP)

        time.sleep(INTERVALO_LOOP)


if __name__ == "__main__":
    try:
        from painel_lances import PainelRoboLance
        app = PainelRoboLance()
        app.mainloop()
    except Exception as e:
        driver = inicializar_driver()
        try:
            monitorar_e_enviar_lances(driver)
        finally:
            pass
