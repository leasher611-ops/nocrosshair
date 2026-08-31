# Prompt pra Kimi AI

---

Olá Kimi! Preciso da sua ajuda com um projeto de aim assist pra Fortnite. Vou descrever tudo em detalhes.

## O que é o projeto

O **nocrosshair** é um software open-source que roda no Linux e converte mouse+teclado em controle virtual (DS4/DS5) pra usar no Fortnite via Xbox Cloud Gaming (xCloud). A ideia é ter aim assist estilo Cronus Zen mas via software.

**Stack técnica:**
- Python 3.10+, PyQt6, python-evdev
- Cria um controle virtual (UInput) que o xCloud reconhece como DS4/DS5
- Mouse → right stick (ABS_RX/ABS_RY), Teclado → left stick + botões
- Loop de flush roda a ~1000Hz escrevendo no controle virtual

## Arquitetura atual (5 camadas)

Implementamos um sistema de layers estilo Cronus Zen, onde cada camada é independente:

```
Layer 1: Slowdown + Rotational (AA básico)
  └─ Reduz velocidade do stick quando perto do alvo
  └─ Reforça direção do movimento (rotational boost)

Layer 2: Aim Lock + Silent Aim (só ADS)
  └─ Aim Lock: trava a mira na direção do stick quando perto do alvo
  └─ Silent Aim: oscilação quadrada X que ativa o AA nativo do jogo

Layer 3: Camera Hit (só hip fire)
  └─ Silent Hit: oscilação quando atirando sem mirar

Layer 4: Track + Snap
  └─ Tracking: momentum na direção do movimento
  └─ Head Snap: pulo vertical suave quando engajado

Layer 5: Sticky + Magnetic
  └─ Persistência quando para o stick
  └─ Pull magnético na direção do movimento
```

## Como funciona a oscilação (técnica real do Cronus Zen)

Baseado na pesquisa de scripts GPC reais:

**Padrão Square (Sahr03):**
```python
# Oscilação quadrada alternada X a cada 20ms (50Hz)
off_x = drift_dir * amplitude  # +amplitude ou -amplitude
# A cada 20ms inverte a direção
drift_dir = -drift_dir
```

**Padrão Circle (MikeCrowne):**
```python
# Órbita circular somada ao input
off_x = cos(angle) * amplitude
off_y = sin(angle) * amplitude * 0.3  # Y reduzido
angle = (angle + speed * delta_ms) % 360
```

**Escala GPC → evdev:**
- GPC usa escala 0-100 (0-100% do stick)
- evdev usa -32768 a 32767
- 30 GPC = 30% do stick = ~9830 evdev (community standard)
- Nossa fórmula: `gpc_amp = 5.0 + intensity * 3.0`

## O problema principal

**A mira não "gruda" no alvo como deveria.** O AA nativo do Fortnite tem dois sistemas:

1. **Slowdown** (right stick): reduz sensibilidade quando o retículo cruza um alvo
2. **Rotational** (left stick): rotaciona a câmera pra manter o alvo enquadrado

O problema é que nosso KBM → controle virtual pode não estar alimentando o AA corretamente. Hipóteses:

1. **O mouse é DELTA, o stick é ABSOLUTO** — a conversão pode estar perdendo informação
2. **O xCloud processa AA no servidor** — latência de 50-100ms pode atenuar micro-oscilações
3. **Rotational precisa de LEFT STICK (strafe)** — nosso silent_aim orbita o right stick (slowdown), não o left
4. **Amplitude pode estar abaixo da deadzone do jogo** — deadzone ~5% = ~1600 evdev

## O que eu quero saber

1. **Como o Cronus Zen alimenta o AA do Fortnite especificamente?** Qual a técnica exata que faz a mira "grudar"?

2. **Qual a diferença entre ativar slowdown vs rotational?** O silent aim (right stick) ativa o slowdown ou o rotational?

3. **Como fazer a mira "tremer" (o efeito visível)?** Nossa intensidade 7 = 26% do stick ainda não causa tremor visível.

4. **O que é "rotational aim assist" e como injetar input no left stick pra ativa-lo?** Precisamos de micro-oscilação no left stick também?

5. **Quais outros truques os scripts premium usam que nós não temos?** Anti-recoil, burst mode, etc.

6. **Como o reWASD configura KBM → controle virtual pra Fortnite?** Eles usam alguma técnica especial de conversão?

7. **Deadzone e response curve** — quais configs do jogo maximizam o efeito do script?

8. **Update rate** — 50Hz (20ms) é suficiente ou precisamos de mais?

Por favor, responda com o máximo de detalhes técnicos possível, incluindo valores, fórmulas e código se possível. Obrigado!

---

*Código fonte: https://github.com/leasher611-ops/nocrosshair (público)*
*Branch: master*
*Arquivos principais:*
- `nocrosshair/features/aim_layers.py` — as 5 camadas
- `nocrosshair/features/silent_aim_qt.py` — Silent Aim/Hit + Quick Tune
- `nocrosshair/features/aim_assist.py` — pipeline antigo + presets (fn_luna_style)
- `nocrosshair/core/input_loop.py` — integração das layers no flush
- `nocrosshair/core/config.py` — configurações do aim assist
- `docs/RESEARCH_AIM.md` — pesquisa técnica completa
- `Plataforma: Linux, Python 3.10+, Xbox Cloud Gaming (xCloud)*
