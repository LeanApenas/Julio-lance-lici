# Robô de Lances Automáticos em Python 🤖

Este script monitora a tabela de lances da licitação em tempo real. Se você não estiver em 1º lugar, ele calcula automaticamente o valor do **1º colocado menos 1 centavo (R$ 0,01)**, preenche o campo e clica em **Enviar Lance**.

---

## ⚙️ Configurações Principais ([`robo_lance.py`](file:///c:/Users/l/Desktop/lance/robo_lance.py))

No arquivo `robo_lance.py`, você pode ajustar:

- **`DECREMENTO`**: Valor a subtrair do 1º colocado (padrão: `0.01`).
- **`LIMITES_MINIMOS`**: Trava de segurança (Stop-Loss) para não dar lances abaixo do seu custo:
  ```python
  LIMITES_MINIMOS = {
      1: Decimal('25.0000'),  # Lote 1 não baixa de R$ 25,00
      6: Decimal('100.0000'), # Lote 6 não baixa de R$ 100,00
  }
  ```
- **`APENAS_LOTES_SELECIONADOS`**: Se `True`, monitora apenas os lotes cujo checkbox estiver marcado na tela.
- **`INTERVALO_LOOP`**: Intervalo em segundos entre cada checagem (padrão: `1.0` segundo).

---

## 🚀 Como Usar

### Passo 1: Abrir o Chrome com Depuração
1. Dê 2 cliques no arquivo [`abrir_chrome_debug.bat`](file:///c:/Users/l/Desktop/lance/abrir_chrome_debug.bat).
2. Uma janela do Google Chrome será aberta.
3. Faça o login normal no portal da licitação (com seu certificado digital/token ou usuário e senha) e entre na tela da disputa de lances.

### Passo 2: Iniciar o Robô
1. Dê 2 cliques no arquivo [`iniciar_robo.bat`](file:///c:/Users/l/Desktop/lance/iniciar_robo.bat) (ou execute `python robo_lance.py` no terminal).
2. O script se conectará à janela do Chrome já aberta e começará o monitoramento automático.
