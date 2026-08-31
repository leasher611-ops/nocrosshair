# AIM ASSIST — Pesquisa Técnica Profunda
### Como o Cronus Zen, reWASD e a comunidade implementam "aim assist" em Fortnite

**Data:** 2026-08-30 · **Fonte:** yew.gg, ScarZens, GitHub GPC scripts, reWASD community, MDM Scripts, RocketMod, Panda Aim V8, EvilBot V6, Aimlock V10

---

## 1. O MECANISMO REAL DO AIM ASSIST NO FORTNITE

### 1.1 Dois sistemas separados

O AA de controle do Fortnite tem **duas partes independentes**:

| Sistema | Gatilho | Efeito |
|---------|---------|--------|
| **Slowdown** | Retículo passa *sobre ou perto* de inimigo | Sensibilidade de look cai ("fricção") — o retículo "gruda" ao cruzar um alvo |
| **Rotational** | **Strafe** (movimento lateral no left stick) mirando num alvo | A câmera rotaciona levemente para manter o alvo enquadrado |

### 1.2 O detalhe crítico (a regra de ouro)

> **Ambos os sistemas exigem stick input ativo e contínuo.**
> Com o left stick parado, o rotational assist "não faz quase nada".

A Epic fez isso de propósito: **o AA recompensa quem está se movendo e mirando — não mira por quem está parado.**

**Implicação prática:** um jogador que "nunca para de alimentar o sistema com input" parece ter AA muito mais forte. Cada pausa do polegar = o rotational desengaja.

### 1.3 O que o script de hardware faz (e não faz)

- O Cronus Zen fica **entre o controle e o console** — modifica o *timing e o formato* dos inputs na camada de hardware
- **Não existe dial de "força de AA"** no jogo que o script possa girar
- O script faz: garantir que as **condições de ativação** (movimento contínuo e bem formado) estejam presentes com muito mais consistência que um polegar humano
- O polegar humano: "jerks", sobrecorrige, **pausa quando leva tiro** → cada pausa desengaja o AA
- O script: mantém micro-ajustes suaves o fight inteiro → o AA fica engajado

### 1.4 Mitos (o que o script NÃO faz)

1. **Não dá lock-on na cabeça** — o Zen não vê a tela; tudo é input-side
2. **Não "adiciona" AA** — só alimenta o AA que já existe com input bem formado
3. **Você ainda mira** — o script refina, não joga por você

---

## 2. A IMPLEMENTAÇÃO GPC REAL (Cronus Zen — código fonte)

O script `complete_zen_system.gpc` (GitHub, open-source) mostra a implementação canônica:

### 2.1 Padrões de movimento (SHAPES)

```
CIRCLE   : stick_x = (intensity * cos(angle)) / 100      ← círculo puro
           stick_y = (intensity * sin(angle)) / 100
           angle = (angle + speed) % 360

TRIANGLE : scanning em 3 lados (interpolação linear)

SPIRAL   : raio expande/contrai: radius = intensity * expansion / 100

HELIX    : x = cos(angle) * intensity/2 ; y = sin(angle*2) * intensity/200
           (frequência dupla no Y = órbita elíptica)

SCARED   : círculo base + offset aleatório (imprevisível)
```

### 2.2 Parâmetros do sistema

| Parâmetro | Intervalo | Default | Descrição |
|-----------|-----------|---------|-----------|
| **Intensity** | 10-100 | 30 | Amplitude do padrão (0-100% do stick) |
| **Speed** | 1-10x | 2 | Velocidade angular do padrão |
| **Update rate** | 50Hz | 20ms | Frequência de escrita no stick |
| **Ativação** | LT > 50 OU RT > 50 | — | O padrão só roda quando LT/RT pressionado |

### 2.3 O ponto crucial da implementação

```gpc
// Aplica o padrão em cima do input do jogador (não substitui):
set_val(XB1_RX, clamp(get_val(XB1_RX) + stick_x, -100, 100));
set_val(XB1_RY, clamp(get_val(XB1_RY) + stick_y, -100, 100));
```

**O padrão é SOMADO ao input do jogador** — nunca o substitui. O stick do jogador continua dominante; o script adiciona a micro-oscilação em cima.

### 2.4 Tabela de seno pré-computada (eficiência)

O GPC usa uma lookup table de 91 valores de seno (0-90°) em vez de `sin()` — por limitação de recursos do hardware (CPU < 80%, update 50Hz).

---

## 3. VALORES REAIS DOS SCRIPTS PREMIUM

### 3.1 Panda Aim V8 (Warzone/Cronus Zen)

```
Aim Assist Strength: 100      (0-100)
Aim Assist Speed:    25
Aim Radius:          18       ← raio da órbita
Tracking Size:       10
Tracking Speed:      25
Recoil V/H:          0        (ajustar por arma)
VM Speed:            1
```

### 3.2 EvilBot V6 (Warzone)

```
ADS Aim Size:        15       ← tamanho da órbita em ADS
ADS Aim Speed:       20
ADS + Fire Size:     16
ADS + Fire Speed:    15
Fire Aim Size:       17
Fire Aim Speed:      30
Left/Right Deadzone: 5
```

### 3.3 Aimlock V10 (CoD)

```
TaylorRadius:  15     ← raio da órbita polar
TaylorAngle:   15     ← passo angular por frame
PolarRadius:   15
PolarAngle:    20
PolarBoost:    5/10   (raio/ângulo extra quando atirando)
Legacy AR:     RY=25 (anti-recoil por arma)
```

### 3.4 Padrão observado

Todos os scripts premium usam a mesma arquitetura:
1. **Órbita polar** (círculo no right stick) com raio 15-18 e velocidade 20-30
2. **Soma ao input do jogador** (nunca substitui)
3. **Ativa em ADS/atiro** (LT/RT pressionado)
4. **Anti-recoil por arma** (compensação V/H)
5. **Menu OLED** para ajustar em tempo real

---

## 4. O MÉTODO DE TUNING DA COMUNIDADE (Quick Tune real)

### 4.1 O processo (ScarZens — Fortnite)

```
1. Baseline com TUDO desligado (jogue algumas partidas)
2. Liga UM mod só (aim assist boosting) a ~1/3 do máximo
3. Testa em ALVOS EM MOVIMENTO (não estáticos — Creative não serve)
4. Sobe em incrementos pequenos — uma partida inteira por passo
5. PARA no momento em que ficar "magnético"
6. Se a mira "puxa sozinha" → passou do ponto → desce
```

### 4.2 Regras de ouro

- **Curva Exponential** no jogo (mais suave para input de script)
- **Deadzone ~5%** (look e ADS) — deadzone larga come os micro-ajustes
- **Aim assist strength no jogo: MÁXIMO** (o script amplifica; abaixo disso capa tudo)
- **ADS sens abaixo da look sens** (tracking sustentado > flick)
- **Hipfire quer valor MENOR que ADS** (close range o AA do jogo já é forte)
- Nunca muda configuração in-game depois de tunar (invalida tudo)

### 4.3 O "tremor" (o que o Quick Tune procura)

O tremor visível na tela = **raio da órbita grande demais** somado ao input do jogador. Quando o raio excede certo valor, a câmera oscila visivelmente. O método:
1. Sobe a intensidade até a tela tremer
2. Desce 1 passo → valor perfeito (grudento sem jitter)

**Não existe detecção automática confiável** — é o jogador que vê a tela. (No nosso caso, o v1 tem o `is_shaking()` como bônus, mas o método primário é o visual.)

---

## 5. O CASO reWASD (KBM → Controle Virtual)

### 5.1 Como o público configura (config "keyboard and mouse aim assist Fortnite" por Aether)

- **"Lock input method as mouse"** — o remap trata o mouse como mouse
- **CapsLock como shift** — "use caplock as to use mouse hold it" (segurar para ativar o modo)
- Features usadas: **hardware mapping, key combo, shift mode, turbo, paddle mapping, left stick custom deadzone**

### 5.2 Config do vortex1M (Exponential)

```
Exponential response curve
Look: 100 100
ADS: 77 77
Aim assist strength: 77%
```

### 5.3 Estratégia reWASD para AA no KBM

O reWASD em si **não tem motor de aim assist** — é um remapper. O que o público faz:
1. Converte o mouse em **right stick** (com curva/dampening)
2. Usa **turbo / combos** para macro de movimento
3. Confia no **AA nativo do jogo** (que vê um controle virtual)
4. O "truque" é manter o **input do stick sempre ativo** — micro-movimentos

### 5.4 Diferença reWASD vs Cronus Zen

| | reWASD | Cronus Zen |
|---|---|---|
| Hardware | Software (roda no PC) | Hardware físico (entre controle e console) |
| AA nativo | Tem motor próprio + virtual | Só moldura input |
| Órbita | Não tem por padrão (comunidade faz com combos/turbo) | Tem (GPC shapes) |
| Ajuste | GUI no PC | OLED no dispositivo |

---

## 6. O QUE ISSO SIGNIFICA PARA O NOCROSSHAIR V1

### 6.1 Diagnóstico do nosso "zero efeito"

O v1 usa **KBM → right stick virtual**. O nosso `silent_aim_qt` aplicava:
- Órbita circular com raio 200-3000 (unidades evdev)
- Somado ao input do mouse → right stick

**Por que não sente efeito?** Hipóteses (em ordem de probabilidade):

1. **O mouse é DELTA, o stick é ABSOLUTO.** No KBM, o mouse move o cursor com deltas; o Fortnite recebe o "right stick" do controle virtual. O Fortnite processa o right stick como **velocidade** (deflexão = velocidade de rotação). Um micro-círculo de raio 200-3000 em cima do input do mouse pode ser **abaixo da deadzone do jogo** ou **insignificante comparado ao movimento do mouse**.

2. **O Fortnite via Xbox Cloud (streaming) processa o AA no SERVIDOR.** O input do controle virtual viaja até o servidor do xCloud; lá o AA roda. A latência de streaming (~50-100ms) + o processamento podem "atenuar" micro-oscilações de raio pequeno.

3. **O "rotational AA" precisa de LEFT STICK (strafe), não right stick.** O artigo do yew.gg é claro: rotational = strafe = left stick. O nosso silent_aim_qt orbita o **right stick** — que ativa o **slowdown** (fricção), não o rotational.

### 6.2 Correções necessárias (baseadas na pesquisa)

1. **Órbita no RIGHT stick** → ativa **slowdown** (o "sticky" ao cruzar o alvo) — o objetivo do Silent Aim
2. **Micro-oscilação no LEFT stick** → ativa **rotational** (o "grude" de tracking) — o objetivo do Rotational Aim
3. **Valores em escala de deadzone do jogo**: deadzone ~5% = ~1600 unidades (32767 * 0.05). A órbita precisa **cruzar a deadzone** para o jogo detectar input.
4. **Somar ao input, nunca substituir** (como o GPC: `set_val(RX, get_val(RX) + offset)`)
5. **Update rate consistente** (o GPC usa 50Hz = 20ms; o nosso loop do v1 roda a ~1000Hz no AA tick — ok)
6. **Intensidade em % do stick** (como o GPC): intensity 30% = 9830 unidades. O nosso "nível 5" = raio 1600 = ~5% — MUITO fraco. O GPC default é 30%!

### 6.3 A escala que importa

| Escala GPC (0-100) | Unidades evdev (0-32767) | Efeito |
|---|---|---|
| 10 (mínimo) | ~3277 | Sutil, abaixo/na deadzone |
| 30 (default) | ~9830 | **Visível — padrão da comunidade** |
| 50 | ~16384 | Forte |
| 100 | ~32767 | Máximo |

**O nosso nível 5/8 (raio 1600-2440 = 5-7%) está ABAIXO do mínimo GPC (10% = 3277).** É por isso que "zero efeito".

---

## 7. CONCLUSÃO TÉCNICA

1. **AA do Fortnite = slowdown (right stick) + rotational (left stick)**, ambos exigem input contínuo
2. **Scripts premium = órbita polar** (raio 15-18 GPC = ~4900-5900 evdev) **somada ao input** do jogador
3. **Intensidade padrão da comunidade: 30% do stick** (~9830 evdev) — nosso 5/8 estava em ~5-7%
4. **Quick Tune = visual** (jogador vê o tremor na tela) — não tem sensor confiável
5. **reWASD = remapper puro**; o público confia no AA nativo do jogo + mantém input ativo
6. **Para KBM → virtual**: o mouse é delta; o stick é absoluto. A conversão precisa escalar corretamente e a órbita precisa estar ACIMA da deadzone do jogo (~1600) e próxima do padrão da comunidade (~5000-10000)

---

## 8. REFERÊNCIAS

- yew.gg — "Fortnite Aim Assist + Cronus Zen — How It Actually Works" (2026-08-05)
- ScarZens — "Best Cronus Zen Aim Assist Settings for Fortnite" (2026-08-18)
- GitHub MikeCrowne/Cronus-zen-Scripts — `complete_zen_system.gpc` (GPC real)
- reWASD Community — config "keyboard and mouse aim assist Fortnite" (Aether)
- reWASD Community — config "vortex1M Exponential" (Exponential, 100/100, ADS 77/77, AA 77%)
- Panda Aim V8 / EvilBot V6 / Aimlock V10 — specs de scripts premium
- RocketMod — "Aim Assist Configuration 2026"
- MDM Scripts — "Cronus Zen Aim Assist Guide"

---

## 9. ANÁLISE DOS SCRIPTS REAIS (código fonte analisado)

### 9.1 Sahr03/Zen_Scripts (GitHub) — os mais simples e reveladores

**v1_semi_aim_assist.lua** — o "silent aim" canônico:
```lua
define DRIFT_RADIUS = 10;   // ±10% do stick
define DRIFT_DELAY = 20;    // 20ms (50Hz)

combo AIM_ASSIST {
    set_val(AIM_STICK, DRIFT_RADIUS);   // +10%
    wait(DRIFT_DELAY);
    set_val(AIM_STICK, -DRIFT_RADIUS);  // -10%
    wait(DRIFT_DELAY);
}
```
- **OSCILAÇÃO QUADRADA** (não círculo!)
- **`set_val` SUBSTITUI** o stick (não soma)
- Ativa quando L2 (ADS) pressionado

**v2_Advanced_zen_script.lua** — refinado:
```lua
define DRIFT_RADIUS = 8;   // ±8%
define DRIFT_DELAY = 16;   // 16ms (62Hz)

combo AIM_ASSIST {
    set_val(RX, DRIFT_RADIUS * drift_direction);  // X
    wait(DRIFT_DELAY);
    set_val(RY, DRIFT_RADIUS * drift_direction);  // Y
    wait(DRIFT_DELAY);
    drift_direction = -drift_direction;           // inverte
}
```
- Alterna entre eixo X e Y
- Inverte a direção a cada ciclo

**Full_Accessablity.lua** — mesmo padrão com amplitude 5:
```lua
combo AIM_ASSIST {
    set_val(AIM_STICK_X, 5 * drift_direction);
    wait(16);
    set_val(AIM_STICK_Y, 5 * drift_direction);
    wait(16);
    drift_direction = -drift_direction;
}
```

### 9.2 MikeCrowne/Cronus-zen-Scripts (GitHub) — padrões avançados

**TRULY_FINAL_aim_assist_shapes.gpc** — 5 padrões somados ao input:
```gpc
combo apply_aim_assist {
    // CIRCLE
    stick_x = (intensity * get_cos(angle)) / 100;
    stick_y = (intensity * get_sin(angle)) / 100;
    angle = (angle + speed) % 360;
    // ...
    set_val(XB1_RX, get_val(XB1_RX) + stick_x);  // SOMA ao input
    set_val(XB1_RY, get_val(XB1_RY) + stick_y);
    wait(20);  // 50Hz
}
```
- Intensity 10-100, Speed 1-10, update 50Hz (wait 20ms)
- 5 formas: Circle, Triangle, Spiral, Helix, Scared
- **SOMA ao input do jogador** (get_val + offset) — diferente do Sahr03

### 9.3 Comparação das duas técnicas

| | Sahr03 (silent aim base) | MikeCrowne (GPC shapes) |
|---|---|---|
| Padrão | Quadrado X↔Y alternado | Círculo/Triângulo/Espiral |
| Operação | `set_val` (substitui) | `set_val(get_val + offset)` (soma) |
| Amplitude | ±5-10 GPC (±1638-3277) | 10-100 GPC (3277-32767) |
| Frequência | 50-62Hz (16-20ms) | 50Hz (20ms) |
| Uso | Silent aim puro | Aim assist agressivo |

### 9.4 Conclusão final para o nocrosshair v1

O `silent_aim_qt.py` agora implementa:
- **Padrão "square"** (default): oscilação quadrada X↔Y alternada, técnica Sahr03
- **Padrão "circle"**: órbita circular somada ao input, técnica MikeCrowne
- Escala: nível 1-10 → ±8-80 GPC → ±2621-26214 evdev (15-80% do stick)
- Delay 20ms (50Hz) como os scripts reais

