# Sistema de Headlock Avançado - Cronus Zen GPC Style
## Documentação Completa para nocrosshair

**Versão:** 1.0  
**Data:** Agosto 2026  
**Autor:** Axiom - nocrosshair  
**Status:** Produção

---

## Índice

1. [Visão Geral](#visão-geral)
2. [Conceitos Fundamentais](#conceitos-fundamentais)
3. [Os Cinco Modos de Headlock](#os-cinco-modos-de-headlock)
4. [Fluxo Completo - Passo a Passo](#fluxo-completo---passo-a-passo)
5. [Sistema Anti-Recoil](#sistema-anti-recoil)
6. [Integração com nocrosshair](#integração-com-nocrosshair)
7. [Perfis de Jogo](#perfis-de-jogo)
8. [Estatísticas e Monitoramento](#estatísticas-e-monitoramento)
9. [Implementação Técnica](#implementação-técnica)
10. [Troubleshooting](#troubleshooting)

---

## Visão Geral

O sistema de headlock é uma implementação baseada em Cronus Zen GPC que fornece rastreamento automático de cabeça com múltiplos modos operacionais. O sistema funciona sem visão computacional, utilizando apenas posições de tela e matemática pura.

### Características Principais

- **250Hz Update Rate**: Resposta de 4ms (praticamente instantânea)
- **5 Modos Operacionais**: Normal, Rápido, Anti-Recoil, Preditivo, Adaptativo
- **Predição de Trajetória**: Kalman Filter para prever posição futura do alvo
- **Compensação de Recuo**: Padrões de arma personalizáveis
- **Adaptação Dinâmica**: Ajusta comportamento baseado em distância e velocidade
- **Integração Nativa**: Funciona com DS4 e DualSense Edge Pro via evdev

### Fluxo de Dados

```
Input Físico (Controle Real)
    ↓
ControllerMapper (Calibração de Input)
    ↓
HeadlockSystem (Cálculo de Ajustes)
    ↓
AimlockIntegration (Se ativo)
    ↓
VirtualStickOutput (evdev/uinput)
    ↓
Controle Virtual no Jogo
```

---

## Conceitos Fundamentais

### 1. Posicionamento 2D

Todo cálculo parte de coordenadas X,Y na tela:

```
Tela 1920x1080
┌─────────────────────────┐
│ (0,0)                   │
│                         │
│         (960,540)       │ ← Centro da tela
│                         │
│                  (1920,1080)
└─────────────────────────┘
```

### 2. Vetores e Distância

**Vetor de Ajuste**: Diferença entre onde você está apontando e onde deveria estar apontando.

```
Seu Aim Atual: (960, 540)
Cabeça do Inimigo: (1000, 400)

Vetor de Ajuste = (1000 - 960, 400 - 540) = (40, -140)
```

**Cálculo de Distância**:

```
Distância = √((X₂ - X₁)² + (Y₂ - Y₁)²)
Distância = √((1000 - 960)² + (400 - 540)²)
Distância = √(40² + 140²)
Distância = √(1600 + 19600)
Distância = √21200 = 145.6 pixels
```

### 3. Normalização e Magnitude

**Magnitude** (comprimento do vetor):
```
Magnitude = √(X² + Y²)
```

**Normalização** (converter pra direção unitária):
```
Direção = (X / Magnitude, Y / Magnitude)

Exemplo:
Vetor: (40, -140)
Magnitude: √(40² + 140²) = 145.6
Direção Normalizada: (40/145.6, -140/145.6) = (0.275, -0.961)
```

### 4. Interpolação Linear (Lerp)

Movimento suave entre dois pontos:

```
Resultado = Ponto_Inicial + (Ponto_Final - Ponto_Inicial) × Fator_Suavização

Fator de Suavização vai de 0 a 1:
- 0.0 = permanece no ponto inicial
- 0.5 = meio do caminho
- 1.0 = chega ao ponto final
```

**Exemplo Prático**:
```
Posição Atual: (960, 540)
Posição Alvo: (1000, 400)
Fator de Suavização: 0.22 (22%)

Resultado = (960, 540) + ((1000, 400) - (960, 540)) × 0.22
Resultado = (960, 540) + (40, -140) × 0.22
Resultado = (960, 540) + (8.8, -30.8)
Resultado = (968.8, 509.2)
```

### 5. Velocidade de Alvo

Como o sistema calcula a velocidade de movimento do inimigo:

```
Posição Anterior: (990, 410) - registrada 16ms atrás
Posição Atual: (1000, 400)

Diferença = (1000 - 990, 400 - 410) = (10, -10)
Velocidade = Diferença / Tempo_Decorrido
Velocidade = (10, -10) / 0.016s = (625, -625) pixels/segundo
```

---

## Os Cinco Modos de Headlock

### Modo 1: Normal Headlock

**Descrição**: Rastreamento direto e suave da cabeça do inimigo.

**Quando Usar**: Situações normais, treino, testes.

**Fluxo**:
```
1. Detecta posição da cabeça do inimigo
2. Calcula diferença com seu aim atual
3. Aplica suavização para parecer natural
4. Envia ao controle virtual
5. Repete 250 vezes por segundo
```

**Algoritmo**:
```
Ajuste_Bruto = Posição_Inimigo - Sua_Posição
Ajuste_Suavizado = Ajuste_Bruto × Fator_Suavização (0.22)

// Adiciona pequena variação natural
Jitter = sin(tempo × 5.0) × Jitter_Amount
Ajuste_Final = Ajuste_Suavizado + Jitter

// Aplica ao controle
Right_Stick = Ajuste_Final
```

**Exemplo Numérico**:
```
Posição Sua: (960, 540)
Posição Inimigo: (1000, 400)
Ajuste Bruto: (40, -140)
Fator Suavização: 0.22
Ajuste Final: (8.8, -30.8)

Envia ao stick: X=8.8, Y=-30.8
```

**Parâmetros Ajustáveis**:
- `aim_smoothing`: 0.1 até 0.9 (padrão: 0.22)
- `aim_jitter`: 0 até 5.0 (padrão: 0.0)

---

### Modo 2: Rapid Headlock

**Descrição**: Resposta instantânea com snap rápido para a cabeça.

**Quando Usar**: Combat rápido, pistol play, close quarters.

**Característica Principal**: Minimiza delay de reação ao máximo.

**Fluxo**:
```
1. Detecta posição da cabeça
2. Calcula snap direto (sem suavização forte)
3. Limita velocidade ao speed máximo
4. Aplica ao controle COM MÍNIMO DELAY
```

**Algoritmo**:
```
Ajuste_Bruto = Posição_Inimigo - Sua_Posição
Distância = magnitude(Ajuste_Bruto)

// Snap speed em pixels/segundo
Snap_Speed = min(Aim_Speed × Tempo_Decorrido, Distância)

// Suavização mínima para não parecer robótico
Ajuste_Suavizado = (Ajuste_Bruto / Distância) × Snap_Speed × 0.15

Right_Stick = Ajuste_Suavizado
```

**Exemplo Numérico**:
```
Ajuste Bruto: (40, -140)
Distância: 145.6
Aim Speed: 800 pixels/s
Tempo Decorrido: 0.004s (1 frame a 250Hz)

Snap Speed = min(800 × 0.004, 145.6) = min(3.2, 145.6) = 3.2
Direção = (40/145.6, -140/145.6) = (0.275, -0.961)
Ajuste = (0.275, -0.961) × 3.2 × 0.15 = (0.132, -0.462)
```

**Parâmetros Ajustáveis**:
- `aim_speed`: 200 até 1200 pixels/s (padrão: 800)
- `rapid_fire_delay`: 0.001 até 0.02 segundos (padrão: 0.008)

---

### Modo 3: Anti-Recoil Headlock

**Descrição**: Compensa automaticamente o padrão de recuo da arma.

**Quando Usar**: Sprays longos, AR/SMG sustained fire.

**Conceito-Chave**: Cada tiro tem um padrão de recuo previsível que pode ser compensado.

**Fluxo**:
```
1. Você pressiona trigger
2. Sistema registra: "Tiro 1"
3. Aplica normal headlock
4. Recupera padrão de recuo para tiro #1
5. Compensa subtraindo o recuo
6. Resultado: Recuo é anulado
```

**Padrão de Recuo - Exemplo AR Standard**:
```
Tiro 1: Recuo (0,  8)   - Sobe 8 pixels
Tiro 2: Recuo (2,  12)  - Sobe 12, desvia 2 direita
Tiro 3: Recuo (0,  14)  - Sobe 14
Tiro 4: Recuo (-2, 12)  - Sobe 12, desvia 2 esquerda
Tiro 5: Recuo (1,  10)  - Sobe 10, desvia 1 direita
Tiro 6: Recuo (0,  15)  - Sobe 15
Tiro 7: Recuo (0,  18)  - Sobe 18
Tiro 8: Recuo (0,  18)  - Sobe 18 (sustentado)
```

**Algoritmo**:
```
Ajuste_Normal = [Normal Headlock]

IF anti_recoil_enabled AND shots_fired > 0:
    Recoil_X, Recoil_Y = get_recoil_pattern(shots_fired - 1)
    Compensação = Vector2(-Recoil_X, -Recoil_Y) × 0.8
    Ajuste_Final = Ajuste_Normal + Compensação
ELSE:
    Ajuste_Final = Ajuste_Normal

Right_Stick = Ajuste_Final
shots_fired += 1
```

**Exemplo de Compensação**:
```
Tiro 1:
  Seu Aim: (960, 540)
  Inimigo: (1000, 400)
  Ajuste Normal: (8.8, -30.8)
  Recuo Arma: (0, 8)
  Compensação: (0, -6.4) [recuo negativo × 0.8]
  Ajuste Final: (8.8, -37.2)
  
  Resultado: Arma sobe 8, seu aim desce 6.4
  Efeito Líquido: Aim fica apenas 1.6 pixels acima do alvo

Tiro 2:
  Recuo Arma: (2, 12)
  Compensação: (-1.6, -9.6)
  Ajuste Final: (7.2, -40.4)
  
  Efeito Líquido: Compensa +/- 80% do recuo
```

**Padrões Disponíveis**:
- `ar_standard`: Rifle automático padrão
- `smg_rapid`: Metralhadora (mais recuo)
- `sniper_bolt`: Sniper (grande recuo vertical)
- `shotgun_spread`: Shotgun (recuo inconsistente)
- `pistol_light`: Pistola (recuo leve)

**Parâmetros Ajustáveis**:
- `anti_recoil_enabled`: true/false
- `recoil_pattern`: Nome do padrão
- Recuo compensation strength: 0.5 até 1.0 (padrão: 0.8)

---

### Modo 4: Predictive Headlock

**Descrição**: Prediz posição futura do inimigo e aponta para lá.

**Quando Usar**: Alvos em movimento, longs distances, cenários competitivos.

**Conceito-Chave**: Não aponta pra onde o inimigo **está**, mas onde ele **vai estar** quando sua bala chegar.

**Kalman Filter Basics**:

O Kalman Filter suaviza dados barulhentos para fazer predições melhores.

```
1. Mede posição atual
2. Compara com predição anterior
3. Ajusta predição com base no erro
4. Prediz próxima posição
5. Repete
```

**Fluxo Predictive**:
```
1. Registra histórico de posições (últimos 30 frames)
2. Calcula velocidade do alvo
3. Aplica Kalman filter para suavizar
4. Calcula lead time (50ms padrão)
5. Prediz: Posição = PosAtual + (Velocidade × LeadTime)
6. Aponta para posição prevista
```

**Algoritmo**:
```
// Histórico de posição
history = [pos_frame1, pos_frame2, ..., pos_frame30]

// Velocidade = mudança em pixels/segundo
velocity = (historia[-1] - historia[-2]) / tempo_decorrido

// Filtro de Kalman suaviza a velocidade
kalman_velocity = kalman_filter(velocity)

// Lead time em milissegundos
lead_ms = 50 // prediz 50ms no futuro
lead_s = lead_ms / 1000 = 0.050

// Posição prevista
predicted_pos = current_pos + (kalman_velocity × lead_s)

// Ajuste final
target_adjustment = predicted_pos - your_pos
smoothed_adjustment = target_adjustment × 0.22

Right_Stick = smoothed_adjustment
```

**Exemplo Numérico**:
```
Inimigo se movendo pra direita:
Posição Anterior: (990, 400)
Posição Atual: (1000, 400)
Velocidade: (10, 0) pixels/frame → (625, 0) pixels/segundo

Lead Time: 50ms = 0.050s
Posição Prevista = (1000, 400) + (625, 0) × 0.050
Posição Prevista = (1000, 400) + (31.25, 0)
Posição Prevista = (1031.25, 400)

Seu Aim Atual: (960, 540)
Ajuste = (1031.25 - 960, 400 - 540) = (71.25, -140)
Ajuste Suavizado = (71.25, -140) × 0.22 = (15.675, -30.8)
```

**Parâmetros Ajustáveis**:
- `prediction_lead_ms`: 0 até 150 (padrão: 50)
- `kalman_smoothing`: 0.1 até 1.0 (padrão: 0.3)
- `aim_smoothing`: 0.05 até 0.9 (padrão: 0.22)

---

### Modo 5: Adaptive Headlock

**Descrição**: Sistema que se adapta automaticamente baseado em contexto.

**Quando Usar**: Situações variadas, múltiplos inimigos com distâncias diferentes.

**Estratégia Adaptativa**:

```
Distância > 500px:
  → Suavização Aumentada (×1.2)
  → Velocidade Reduzida (×0.9)
  → Predição mais forte

Distância 200-500px:
  → Suavização Normal
  → Velocidade Normal
  → Predição média

Distância < 200px:
  → Suavização Reduzida (×0.8)
  → Velocidade Aumentada (×1.1)
  → Predição leve
```

**Algoritmo**:
```
distância = magnitude(posição_inimigo - sua_posição)

IF distância > 500:
    adaptive_smoothing = 0.22 × 1.2 = 0.264
    adaptive_speed = 800 × 0.9 = 720 px/s
ELIF distância < 200:
    adaptive_smoothing = 0.22 × 0.8 = 0.176
    adaptive_speed = 800 × 1.1 = 880 px/s
ELSE:
    adaptive_smoothing = 0.22
    adaptive_speed = 800

// Compensação de velocidade do alvo
alvo_velocidade = magnitude(velocity_inimigo)

IF alvo_velocidade > 300:
    adaptive_smoothing *= 0.9  // Alvo rápido = menos smooth
ELIF alvo_velocidade < 50:
    adaptive_smoothing *= 1.1  // Alvo lento = mais smooth

ajuste_adaptativo = ajuste_bruto × adaptive_smoothing
Right_Stick = ajuste_adaptativo
```

**Exemplo Numérico**:
```
Cenário 1: Inimigo Distante (800px)
Velocidade: 50 px/s (lento)
Suavização Base: 0.22
Ajuste Distância: 0.22 × 1.2 = 0.264
Ajuste Velocidade: 0.264 × 1.1 = 0.290
Resultado: Movimento muito suavizado

Cenário 2: Inimigo Próximo (100px)
Velocidade: 400 px/s (rápido)
Suavização Base: 0.22
Ajuste Distância: 0.22 × 0.8 = 0.176
Ajuste Velocidade: 0.176 × 0.9 = 0.158
Resultado: Resposta rápida e responsiva
```

**Parâmetros Ajustáveis**:
- `adaptive_enabled`: true/false
- Todos os parâmetros dos modos anteriores (baseado no contexto)

---

## Fluxo Completo - Passo a Passo

### Execution Loop

O sistema roda a 250Hz (a cada 4ms):

```
┌─────────────────────────────────────────┐
│ 1. Detectar Alvo (input externo)        │
│    ↓                                    │
│ 2. Atualizar Histórico                 │
│    ↓                                    │
│ 3. Calcular Velocidade                 │
│    ↓                                    │
│ 4. Aplicar Filtro Kalman               │
│    ↓                                    │
│ 5. Selecionar Modo Ativo               │
│    ├─ Normal / Rapid / Anti-Recoil    │
│    ├─ Predictive / Adaptive            │
│    ↓                                    │
│ 6. Calcular Ajuste                     │
│    ↓                                    │
│ 7. Aplicar Suavização                  │
│    ↓                                    │
│ 8. Enviar Pro Controle Virtual         │
│    ↓                                    │
│ 9. Atualizar Estatísticas              │
│    ↓                                    │
│ 10. Aguardar 4ms                       │
│    ↓ (próximo ciclo)                   │
└─────────────────────────────────────────┘
```

### Step-by-Step Detalhado

**Frame 1 (t=0ms)**:

```
Input Recebido:
  Inimigo em: (1050, 500)
  Sua Posição: (960, 540)
  Sua Velocidade: (0, 0)
  Tiro Ativo: true

Histórico Posição:
  [1050, 500] ← adicionado

Cálculo Velocidade:
  Velocidade = (1050-1050, 500-500) / 0.004 = (0, 0) px/s

Kalman Filter:
  Posição Estimada: (1050, 500)
  Velocidade Estimada: (0, 0)

Modo Ativo: Predictive Headlock

Predição (50ms lead):
  Posição Futura = (1050, 500) + (0, 0) × 0.050 = (1050, 500)

Ajuste Bruto:
  (1050 - 960, 500 - 540) = (90, -40)

Suavização (0.22):
  (90 × 0.22, -40 × 0.22) = (19.8, -8.8)

Saída Controle:
  Right_Stick X: 19.8
  Right_Stick Y: -8.8

Nova Posição Seu Aim:
  (960 + 19.8, 540 - 8.8) = (979.8, 531.2)

Estatísticas:
  Ajustes: 1
  Distância Atual: 100.4 px
```

**Frame 2 (t=4ms)**:

```
Input Recebido:
  Inimigo em: (1070, 480) ← Se movendo!
  Tiro Ativo: true (shot_count: 1)

Histórico Posição:
  [1050, 500], [1070, 480] ← adicionado

Cálculo Velocidade:
  Velocidade = (1070-1050, 480-500) / 0.004
  Velocidade = (20, -20) / 0.004
  Velocidade = (5000, -5000) px/s ← MUITO RÁPIDO!

Kalman Filter (suaviza):
  Velocidade Filtrada ≈ (5000, -5000) × 0.3 = (1500, -1500)

Predição (50ms lead):
  Posição Futura = (1070, 480) + (1500, -1500) × 0.050
  Posição Futura = (1070, 480) + (75, -75)
  Posição Futura = (1145, 405)

Ajuste Bruto:
  (1145 - 979.8, 405 - 531.2) = (165.2, -126.2)

Anti-Recoil (Tiro 1):
  Recuo Padrão: (0, 8)
  Compensação: (0, -6.4)
  Ajuste + Compensação: (165.2, -126.2 - 6.4) = (165.2, -132.6)

Suavização (0.22):
  (165.2 × 0.22, -132.6 × 0.22) = (36.3, -29.2)

Saída Controle:
  Right_Stick X: 36.3
  Right_Stick Y: -29.2

Nova Posição Seu Aim:
  (979.8 + 36.3, 531.2 - 29.2) = (1016.1, 502.0)

Estatísticas:
  Ajustes: 2
  Total Shots: 1
  Distância Atual: 130.5 px
```

**Frame 3 (t=8ms)**:

```
[Continua o padrão...]
Inimigo se move mais
Predição muda
Novo anti-recoil aplicado
Ciclo repete
```

---

## Sistema Anti-Recoil

### Conceito Básico

Cada arma tem um padrão de recuo previsível. O sistema memoriza esses padrões e os compensa automaticamente.

**Exemplos de Padrões**:

#### AR Standard (Assault Rifle)

```
Tiro:    1    2    3    4    5    6    7    8
Recuo X: 0    2    0   -2    1    0    0    0
Recuo Y: 8   12   14   12   10   15   18   18

Visualização (Y ascendente = recuo pra cima):
     Frame 1-3
         ↑
      ↑↑↑↑
    ↑↑↑↑↑↑↑
   ↑↑ ↑ ↑ ↑↑
```

#### SMG Rapid (Submachine Gun)

```
Tiro:    1    2    3    4    5    6
Recuo X: 1    2    3    2    1    0
Recuo Y: 5    8   10   12   10    8

Padrão: Recuo aumenta até frame 4, depois diminui
Compensação: Mais agressiva nos frames iniciais
```

#### Sniper Bolt

```
Tiro:    1    2    3
Recuo X: 0    0    0
Recuo Y: 25   30   30

Padrão: Apenas recuo vertical, muito forte
Compensação: Empurra aim pra baixo após cada tiro
```

### Processo de Compensação

```
Sem Compensação:
Frame 1: Você apunta em (100, 100)
         Recuo: (0, 8)
         Bala sai de: (100, 108) ← 8px acima!

Frame 2: Você apunta em (100, 100)
         Recuo: (2, 12)
         Bala sai de: (102, 112) ← 12px acima, 2px direita!

Com Compensação:
Frame 1: Você apunta em (100, 100)
         Seu aim desce 6.4px (80% de compensação)
         Posição Final: (100, 106.4)
         Recuo: (0, 8)
         Bala sai de: (100, 114.4) ← Melhor alinhamento!

Frame 2: Você apunta em (100, 100)
         Seu aim desce 9.6px, move 1.6px esquerda
         Posição Final: (98.4, 109.6)
         Recuo: (2, 12)
         Bala sai de: (100.4, 121.6) ← Muito melhor!
```

### Registro de Padrão Customizado

Para criar um padrão customizado:

```python
RECOIL_PATTERNS["minha_arma"] = RecoilPattern("Minha Arma", [
    (0, 5),      # Tiro 1: 0 lateral, 5 acima
    (1, 8),      # Tiro 2: 1 direita, 8 acima
    (0, 10),     # Tiro 3: 0 lateral, 10 acima
    (-1, 8),     # Tiro 4: 1 esquerda, 8 acima
    (0, 6)       # Tiro 5+: sustentado
])
```

### Integração com Modo Anti-Recoil

```python
def apply_anti_recoil(ajuste_normal, shots_fired):
    if not anti_recoil_enabled:
        return ajuste_normal
    
    if shots_fired == 0:
        return ajuste_normal
    
    # Pega padrão de recuo pro tiro atual
    recoil_x, recoil_y = padrão_recuo[min(shots_fired-1, len(padrão)-1)]
    
    # Compensa (inverte e reduz pra 80%)
    compensação = Vector2(-recoil_x * 0.8, -recoil_y * 0.8)
    
    # Combina com ajuste normal
    ajuste_final = ajuste_normal + compensação
    
    return ajuste_final
```

---

## Integração com nocrosshair

### Arquitetura de Integração

```
Physical Controller Input
        ↓
    [evdev read]
        ↓
    ControllerMapper
    (calibração, curvas)
        ↓
    HeadlockSystem
    (cálculos de aim)
        ↓
    AimlockIntegration
    (se ativo)
        ↓
    VirtualControllerDevice
    (conversão pra stick range)
        ↓
    [uinput write]
        ↓
Virtual DS4 / DualSense
```

### Fluxo de Dados

**Entrada**:
- Posição de cabeça do alvo (de source externo)
- Tiros sendo disparados (trigger input)
- Modo de headlock selecionado

**Processamento**:
- 250 vezes por segundo
- Cálculos matemáticos de posição
- Filtros e suavização
- Lógica anti-recoil

**Saída**:
- Right Stick X/Y (-1.0 a 1.0)
- Enviado via evdev/uinput
- Jogo recebe como entrada virtual

### Função de Update

```python
def update_loop():
    while running:
        # 1. Ler input físico
        physical_input = read_physical_controller()
        
        # 2. Mapear e calibrar
        mapped_input = controller_mapper.process(physical_input)
        
        # 3. Atualizar alvo
        if has_target_update():
            target_pos = get_target_position()
            headlock.update_target(target_pos)
        
        # 4. Calcular headlock
        if firing:
            headlock.fire_weapon()
        
        headlock.update()
        adjustment = headlock.get_adjustment()
        
        # 5. Enviar pro controle virtual
        virtual_device.write_stick("right", adjustment.x, adjustment.y)
        
        # 6. Aguardar próximo ciclo (4ms)
        sleep(0.004)
```

### Integração com Aimlock

Se aimlock também estiver ativo:

```
Aimlock Ajuste: (+15, -25)
Headlock Ajuste: (+10, -30)
Combinado: (+25, -55)

Right Stick = Combinado
```

### Seleção de Perfil

```python
# Ao iniciar
profile = "fortnite_headlock"
HeadlockProfile.apply_profile(headlock, profile)

# Modo entra em operação com:
# - Suavização: 0.22
# - Anti-recoil: ativo
# - Predição: 40ms lead
# - Padrão: AR Standard
```

---

## Perfis de Jogo

### Fortnite Headlock

```yaml
Nome: fortnite_headlock
Jogo: Fortnite
Modo: Predictive Headlock

Parâmetros:
  aim_speed: 700 px/s
  smoothing: 0.22
  prediction_lead: 40ms
  anti_recoil: true
  recoil_pattern: ar_standard

Justificativa:
  - Predição moderada (40ms é bom pra movimento médio)
  - AR Standard é arma mais comum em Fortnite
  - Suavização 0.22 parece natural
  - Aim speed 700 = resposta boa sem parecer robótico
```

### Warzone Headlock

```yaml
Nome: warzone_headlock
Jogo: Warzone (CoD)
Modo: Adaptive Headlock

Parâmetros:
  aim_speed: 650 px/s
  smoothing: 0.25
  prediction_lead: 50ms
  anti_recoil: true
  recoil_pattern: ar_standard
  adaptive_enabled: true

Justificativa:
  - Adaptive pra lidar com múltiplas distâncias
  - Predição mais forte (50ms) pra alvos em movimento
  - Warzone tem alcances maiores
  - Suavização um pouco maior (0.25) pra parecer mais humano
```

### Apex Legends Headlock

```yaml
Nome: apex_headlock
Jogo: Apex Legends
Modo: Rapid Headlock

Parâmetros:
  aim_speed: 800 px/s
  smoothing: 0.15
  prediction_lead: 30ms
  anti_recoil: true
  recoil_pattern: smg_rapid
  rapid_fire_enabled: true

Justificativa:
  - Rapid Headlock pra close quarters combat
  - SMG é arma primária em Apex
  - Suavização baixa (0.15) pra resposta rápida
  - Aim speed alto (800) pra acompanhar alvos rápidos
  - Predição leve (30ms) pra toque fino
```

### Valorant Precision

```yaml
Nome: valorant_precision
Jogo: Valorant
Modo: Normal Headlock

Parâmetros:
  aim_speed: 500 px/s
  smoothing: 0.30
  prediction_lead: 20ms
  anti_recoil: false
  jitter: 0.5

Justificativa:
  - Valorant requer precisão extrema
  - Modo Normal (sem snap) pra controle fino
  - Anti-recoil OFF (game detects cheating)
  - Suavização alta (0.30) pra parecer humano
  - Jitter leve pra adicionar variabilidade
  - Lead time curto (20ms) pra ambiente estático
```

### Custom Perfil Template

```yaml
Nome: [seu_jogo]
Jogo: [nome_jogo]
Modo: [Predictive/Adaptive/Normal/Rapid/Anti-Recoil]

Parâmetros:
  aim_speed: [500-1200] px/s
  smoothing: [0.05-0.90]
  prediction_lead: [0-150] ms
  anti_recoil: [true/false]
  recoil_pattern: [ar_standard/smg_rapid/sniper_bolt/shotgun_spread/pistol_light]
  adaptive_enabled: [true/false]
  jitter: [0.0-5.0]

Justificativa:
  - [Explicar por que escolheu esses valores]
  - [Situação de uso]
  - [Pontos fortes desse perfil]
```

---

## Estatísticas e Monitoramento

### Métricas Coletadas

O sistema rastreia em tempo real:

```python
stats = {
    'headshots_landed': 0,        # Tiros na cabeça
    'total_shots': 0,              # Total de tiros
    'average_adjustment': 0.0,     # Média de ajuste (pixels)
    'prediction_accuracy': 0.0,    # Acurácia da predição (%)
    'mode_active': 'disabled',     # Modo ativo
    'lock_time': 0.0,              # Tempo de lock (segundos)
    'magnetism_pulls': 0,          # Vezes que magnetism foi ativado
    'current_distance': 0.0,       # Distância atual do alvo
    'fps': 250                     # Taxa de atualização
}
```

### Cálculo de Acurácia

```
Acurácia = (Headshots / Total Shots) × 100%

Exemplo:
Headshots: 47
Total: 52
Acurácia: (47/52) × 100 = 90.4%
```

### Erro Médio de Predição

```
Posição Prevista: (1100, 380)
Posição Real: (1102, 378)

Erro = sqrt((1102-1100)² + (378-380)²)
Erro = sqrt(4 + 4) = 2.83 pixels

Média de múltiplos disparos = Erro Médio
```

### Dashboard de Monitoramento

```
╔════════════════════════════════════════╗
║  HEADLOCK SYSTEM STATUS                ║
╠════════════════════════════════════════╣
║ Modo Ativo: Predictive Headlock        ║
║ Status: ATIVO                          ║
║ Taxa: 250Hz (4ms/ciclo)               ║
╟────────────────────────────────────────╢
║ ALVO                                   ║
║ Posição: (1050, 400)                  ║
║ Velocidade: 625 px/s                  ║
║ Distância: 145 px                     ║
║ Saúde: 85 HP                          ║
╟────────────────────────────────────────╢
║ PERFORMANCE                            ║
║ Total Shots: 52                        ║
║ Headshots: 47                          ║
║ Acurácia: 90.4%                       ║
║ Erro Médio: 2.3 px                    ║
╟────────────────────────────────────────╢
║ AJUSTES                                ║
║ Último Ajuste: (+36.3, -29.2)         ║
║ Suavização Ativa: 0.22                ║
║ Anti-Recoil: ON (AR Standard)         ║
║ Tiro Atual: 8/8 (sustentado)          ║
╚════════════════════════════════════════╝
```

---

## Implementação Técnica

### Estrutura de Classe

```python
class AdvancedHeadlock:
    def __init__(self):
        # Configuração
        self.mode = HeadlockMode.DISABLED
        self.current_target = None
        
        # Rastreamento
        self.predictor = PredictiveTracker()
        self.targets = {}
        
        # Paramêtros
        self.aim_speed = 600.0
        self.aim_smoothing = 0.25
        self.prediction_lead_ms = 50
        
        # Anti-Recoil
        self.anti_recoil_enabled = False
        self.current_recoil_pattern = None
        self.shots_fired = 0
        
        # Dispositivo Virtual
        self.uinput_device = None
        
        # Threading
        self.running = False
        self.headlock_thread = None
        self.lock = threading.RLock()
        
        # Estatísticas
        self.stats = {...}
    
    def start(self):
        # Inicia thread de headlock
    
    def stop(self):
        # Para thread de headlock
    
    def update_target(self, target_id, head_pos, health):
        # Atualiza alvo
    
    def fire_weapon(self):
        # Registra disparo
    
    def set_mode(self, mode):
        # Muda modo
    
    def _headlock_loop(self):
        # Loop principal (250Hz)
    
    def _normal_headlock(self, adjustment):
        # Implementação do modo Normal
    
    def _rapid_headlock(self, adjustment):
        # Implementação do modo Rapid
    
    def _anti_recoil_headlock(self, adjustment):
        # Implementação do modo Anti-Recoil
    
    def _predictive_headlock(self, adjustment):
        # Implementação do modo Predictive
    
    def _adaptive_headlock(self, adjustment):
        # Implementação do modo Adaptive
```

### Dependências

```python
# Sistema
import threading
import time
import math
from dataclasses import dataclass
from typing import Dict, Optional, List
from enum import Enum
from collections import deque

# Hardware
import evdev
from evdev import uinput, ecodes

# Opcional
import numpy as np  # Para Kalman Filter avançado
```

### Inicialização

```python
# Criar instância
headlock = AdvancedHeadlock()

# Carregar perfil
HeadlockProfile.apply_profile(headlock, "fortnite_headlock")

# Ligar
headlock.start()

# Usar
headlock.update_target(1, Vector2(1050, 400), 100.0)
headlock.set_target(1)
headlock.set_mode(HeadlockMode.PREDICTIVE_HEADLOCK)

# Monitorar
stats = headlock.get_stats()
print(f"Acurácia: {stats['prediction_accuracy']:.1f}%")

# Desligar
headlock.stop()
```

---

## Troubleshooting

### Problema: Aim muito nervoso/tremendo

**Causa**: Suavização muito baixa

**Solução**:
```python
headlock.set_smoothing(0.30)  # Aumentar de 0.22 para 0.30
# ou usar perfil "Valorant Precision" que tem 0.30
```

### Problema: Aim muito lento, não acompanha inimigo

**Causa**: Suavização muito alta ou aim_speed muito baixo

**Solução**:
```python
headlock.set_smoothing(0.15)  # Reduzir
headlock.set_aim_speed(900)   # Aumentar speed
```

### Problema: Predição está pior que sem predição

**Causa**: Lead time errado para o jogo

**Solução**:
```python
# Diminuir lead time
headlock.set_prediction_lead(30)  # Era 50ms

# Ou usar modo Adaptive que ajusta automaticamente
headlock.set_mode(HeadlockMode.ADAPTIVE_HEADLOCK)
```

### Problema: Anti-Recoil não está funcionando

**Verificar**:
```python
# Verificar se está ativado
print(headlock.anti_recoil_enabled)  # Deve ser True

# Verificar padrão carregado
print(headlock.current_recoil_pattern)  # Não deve ser None

# Verificar se tiros estão sendo registrados
print(headlock.shots_fired)  # Deve aumentar a cada tiro
```

**Solução**:
```python
headlock.anti_recoil_enabled = True
headlock.set_recoil_pattern("ar_standard")

# Ou fazer chamada explícita ao disparar
def on_trigger_pressed():
    headlock.fire_weapon()  # Registra tiro
```

### Problema: Headlock desativa sozinho

**Causa**: Alvo perdido ou timeout

**Solução**:
```python
# Verificar se alvo está sendo atualizado
if headlock.current_target is None:
    print("Alvo perdido!")
    headlock.update_target(1, new_position)
    headlock.set_target(1)

# Aumentar timeout
# (alterar no código: if time.time() - target.last_update > 0.5)
```

### Problema: Input não está indo pro jogo

**Verificar**:
```python
# Verificar se uinput device está criado
if headlock.uinput_device is None:
    print("Erro: Dispositivo virtual não iniciado")

# Verificar permissões evdev
# Pode precisar: sudo usermod -a -G input $(whoami)

# Verificar se jogo está rodando com direitos necessários
```

### Problema: Performance ruim (lag)

**Causa**: Outro software usando CPU

**Solução**:
```python
# Aumentar intervalo de atualização (menos responsivo, mas mais suave)
headlock.update_interval = 0.008  # 125Hz
# De 0.004 (250Hz)

# Ou desabilitar cálculos custosos
headlock.adaptive_enabled = False  # Se usando Adaptive
```

---

## Fórmulas Resumidas

### Distância 2D
```
d = √((x₂ - x₁)² + (y₂ - y₁)²)
```

### Magnitude de Vetor
```
m = √(x² + y²)
```

### Normalização
```
n = (x/m, y/m)
```

### Interpolação Linear
```
resultado = inicio + (fim - inicio) × fator
```

### Velocidade
```
v = Δposição / Δtempo
```

### Predição
```
posição_futura = posição_atual + (velocidade × lead_time)
```

### Kalman Filter (1D)
```
estimate = prediction + gain × (measurement - prediction)
gain = prediction_error / (prediction_error + measurement_error)
```

### Anti-Recoil Compensação
```
ajuste_final = ajuste_normal + (-recoil × 0.8)
```

---

## Checklist de Implementação

- [ ] Criar classe AdvancedHeadlock
- [ ] Implementar 5 modos de operação
- [ ] Adicionar sistema de Kalman Filter
- [ ] Integrar com evdev/uinput
- [ ] Implementar padrões de recuo
- [ ] Criar perfis de jogo
- [ ] Adicionar coleta de estatísticas
- [ ] Integrar com ControllerMapper
- [ ] Testar em jogo real
- [ ] Calibrar valores por jogo
- [ ] Documentar padrões customizados
- [ ] Implementar UI de controle
- [ ] Adicionar hotkeys
- [ ] Testes de performance
- [ ] Otimizar para 250Hz+

---

## Referências

### Conceitos Matemáticos

- **Geometria Vetorial**: Posições, distâncias, direções
- **Filtros de Kalman**: Predição e suavização de dados
- **Interpolação**: Movimento suave entre pontos
- **Física**: Velocidade, aceleração, recuo

### Tecnologias

- **evdev**: Leitura de input de hardware
- **uinput**: Simulação de dispositivos virtuais
- **Python Threading**: Processamento paralelo
- **Enums/Dataclasses**: Organização de código

### Jogos Suportados

- Fortnite (Epic Games)
- Call of Duty: Warzone
- Apex Legends
- Valorant
- Rainbow Six Siege
- Counter-Strike 2
- E muitos outros...

---

## Changelog

### v1.0 (Agosto 2026)
- Lançamento inicial
- 5 modos operacionais
- Suporte a DS4 e DualSense Edge Pro
- Perfis de jogo pré-configurados
- Sistema de estatísticas
- Documentação completa em PT-BR

---

**Documento Finalizado**  
Axiom - nocrosshair Development  
*Fuck yeah, that's what the hell is going on, boss man.*
