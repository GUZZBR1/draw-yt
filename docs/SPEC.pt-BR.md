# SPEC — DrawTube Coreset

**Projeto:** coletor de vídeos do YouTube + poda inteligente de frames (Dataset Pruning / Coreset Selection) para gerar dado real de outros setups pro Draw.
**Data:** 2026-11-09 · **Autor:** Julia, a pedido do Lucas · **Status:** spec — nenhuma linha de código ainda, nenhum download feito por esta spec.
**Onde mora:** `~/workspace/draw-lab/youtube-coreset/` (esta pasta). Corpus irmão já existente: `~/workspace/draw-video-corpus/`.

---

## 0. Resumo em um parágrafo

Baixar vídeo do YouTube é problema resolvido (`yt-dlp`, a ferramenta por baixo de quase todos os sites de download). O projeto de verdade é o que vem depois: de cada vídeo, extrair os frames e **descartar 97–99% deles**, ficando só com a menor fração que ensina o máximo — frames diversos de mesas, câmeras, luzes e papéis que não são os do Lucas, frames onde os modelos atuais erram, e negativos duros (cena sem papel). O produto final não é um monte de vídeo: é um **coreset** — um subconjunto pequeno, balanceado, rotulável e dividido por sessão — pronto pra virar fine-tune e régua de generalização do Draw, em dataset **privado** no Kaggle.

## 1. Problema que este projeto resolve

Diagnóstico vigente do Draw (2026-11-06, confirmado nas bancadas até a t14 em 2026-11-09):

1. **O gargalo não é o modelo nem falta de dado bruto — é tradução:** converter material bruto em exemplos rotulados e julgáveis.
2. **O medo central é generalização:** FT-dyn (folha) + w8 (tinta) funcionam na mesa do Lucas; fora dela, a presença desaba. Medido no Kinetics-700 `writing` (567 clips de YouTube, setups alheios, relatório `draw-video-corpus/KINETICS_FULL_REPORT.md`): **veto total em 368/567 clips (64,9%)**, sólido (≥90% de frames com folha) em só **18/567 (3,2%)**.
3. **Não existe dataset pronto** de gente escrevendo/desenhando em papel sobre a mesa com anotação (pesquisa de 2026-11-02/03, Kaggle + HuggingFace varridos). Quem quiser esse dado, constrói o coletor.

Este projeto é esse coletor. Ele não treina modelo nenhum; ele produz o insumo que destrava (1) e mede (2).

### Não-objetivos

- Não é um site/app público de download, nem serviço pra terceiros. Uso pessoal/interno do Draw.
- Não substitui a captura real da mesa do Lucas nem o holdout selado — alimenta um holdout **de outro setup**, que hoje não existe (0 sessões de outro setup revisadas).
- Não resolve flicker nem geometria por si só — resolve a falta de dado diverso e de negativos reais pra atacar presença/ausência e generalização.

## 2. Regras inegociáveis (do Lucas, já vigentes)

| # | Regra | Como a spec cumpre |
|---|-------|--------------------|
| R1 | Divisão por **sessão**, nunca por frame | Aqui: 1 vídeo = 1 sessão. Nenhum vídeo aparece em dois conjuntos (treino × régua). A divisão é por `video_id`, e por `channel_id` quando o mesmo canal grava sempre no mesmo setup. |
| R2 | Pixels de YouTube **nunca** públicos | Corpus CC BY verificado pode ir a dataset **privado** do Kaggle; corpus de licença padrão fica só como índice (IDs + timestamps), pixels de uso interno na VM/kernel, nunca re-hospedados. Igual ao precedente: índice do Kinetics no Kaggle é privado e sem pixels (`guzzbr/draw-kinetics-writing-index`). |
| R3 | Licença se **verifica por vídeo**, nunca se presume | Campo `license` do próprio YouTube via yt-dlp; presente = CC declarado pelo autor; vazio = licença padrão. Método já provado com controle (ver §3.2). |
| R4 | Nada baixa no disco do Lucas; dataset não mora lá | Toda a perna de download roda onde o §3.3 decidir (kernel Kaggle ou VM da Julia). Na máquina do Lucas: nada. |
| R5 | Medir antes de prometer; smoke antes de corrida | Cada fase (§9) tem portão com número medido antes da fase seguinte. Download em massa só depois da prova de 1 vídeo. |
| R6 | Quem gera não julga | Os modelos que pseudo-rotulam (FT-dyn, w8) não decidem sozinhos o que entra no conjunto final: há veto clássico, cota de revisão humana e disjunção provada contra as réguas seladas (§7). |
| R7 | Régua selada não vira treino | Qualquer frame/clip já usado em régua (ex.: os 187 clips da `absence_v1`, os 567 do censo Kinetics) é excluído do treino por lista de exclusão com interseção provada = 0, como foi feito nos Negativos Reais v1 (668 frames, disjunção provada por script). |

## 3. Arquitetura — 7 estágios

Fluxo: `descoberta → licença → download → frames → poda → juízo/rótulo → pacote Kaggle`
Cada estágio grava um manifesto (CSV/JSONL) e um recibo (contagens de entrada/saída). Nenhum estágio apaga a saída do anterior até o pacote final ser conferido.

### 3.1 Descoberta (busca)

- **Ferramenta:** `yt-dlp 2026.10.26` (venv existente em `draw-video-corpus/kinetics/venv/`), busca plana `--flat-playlist` — **medido nesta VM: funciona, ~4–11 s/busca**.
- **Consultas** (EN + PT, herdadas da caça CC BY de 2026-11-05 e ampliadas): `drawing on paper`, `sketching timelapse`, `handwriting on paper`, `writing on notebook`, `drawing tutorial top view`, `pencil drawing timelapse`, `escrevendo no papel`, `desenhando no papel`, `escrevendo no caderno`, `desenho no papel` + novas: `bullet journal writing overhead`, `calligraphy on paper top view`, `study with me writing desk`, `whiteboard to paper` (negativo).
- **Filtro de licença na busca:** URL de resultados com `sp=EgIwAQ%253D%253D` (filtro Creative Commons do YouTube) pra trilha CC BY; busca sem filtro só pra trilha índice/uso interno.
- **Saída:** `candidates.csv` — esquema já existente e reaproveitado: `video_id, url, title, channel, duration_s, upload_date, view_count, license_field, cc_by_confirmed, classe_enquadramento, thumb_checked, queries, notes`.
- **Recibo da rodada 0 (já medido, 2026-11-05):** 10 buscas → 80 resultados → **77 vídeos únicos, 77/77 com CC BY confirmado**, dos quais **33 servem** (papel/caderno + mão real), somando **4,13 h** de vídeo. Arquivo: `draw-video-corpus/ccby-hunt/candidates.csv` (77 linhas). Esta spec parte desse estoque, não do zero.

### 3.2 Verificação de licença e enquadramento

- **Licença:** `yt-dlp -j --skip-download --ignore-no-formats-error` com `player_client=tv,ios,web_embedded` — **medido: ~15–18 s/vídeo, 77/77 sem erro nesta VM**. O cliente web padrão bate no bot-check do YouTube no IP desta VM (`Sign in to confirm you're not a bot`); essa rota alternativa é a que funciona (evidência: `draw-video-corpus/ccby-hunt/EGRESS_EVIDENCE.md`).
- **Prova de discriminação do método (já feita):** vídeo CC retorna `license = "Creative Commons Attribution license (reuse allowed)"`; controle fora do filtro (Art for Kids Hub, `fdm1_QInzfM`) retorna `license = None`.
- **Enquadramento:** título + descrição + thumbnail classificam em: `folha_solta`, `caderno_aberto`, `caderno_fechado/unico`, `quadro` (negativo), `tela` (negativo), `outro` (negativo). Na rodada 0, 9/10 dos melhores conferiram na thumbnail (mão + papel sobre mesa).
- **Portão:** vídeo sem licença confirmada **não** entra na trilha de pixels pro Kaggle; pode entrar só na trilha índice (como o Kinetics).

### 3.3 Download (a perna de rede — ponto crítico medido)

Fato medido, não opinião: **o download de pixels nesta VM está bloqueado** pelo bot-check do YouTube (teste de 2026-11-05 com o vídeo CC BY `sVTAtgzPGhA`, 15 s: falhou; logs em `draw-video-corpus/ccby-hunt/download_test*.log`). Metadado passa, pixel não.

Rotas, em ordem de tentativa, **uma de cada vez, sem repetir rota morta em loop**:

1. **Kernel Kaggle (rota principal).** Precedente direto: a rodada CC BY foi desenhada pra baixar de dentro de um kernel Kaggle. Vantagens: egresso diferente, e o dataset já nasce onde o treino roda (sem transferência depois). Prova obrigatória: 1 vídeo curto → conferir bytes + duração + `ffprobe` → só então o lote.
2. **VM da Julia com cliente alternativo** (`player_client=android`, lição dos Negativos v1: `yt-dlp` atual + `android` + `--no-check-certificate` já destravou rota de YouTube em trabalho anterior) — tentar uma vez, com recibo; se cair no bot-check de novo, encerra a rota.
3. **Cookies de sessão logada** — somente se as rotas 1–2 falharem e o Lucas aprovar explicitamente (envolva a conta dele; decisão dele, não da Julia).

- **Formato:** teto 720p, `mp4`, sem áudio (áudio é peso morto pro Draw), duração integral só até 60 min/vídeo; acima disso, baixar a janela central de 60 min e registrar o corte no manifesto.
- **Integridade:** tamanho em bytes + sha256 por arquivo no manifesto; download com resume (`curl -C -` / yt-dlp `--continue`), nunca sobrescrever arquivo bom com arquivo truncado.
- **Saída:** `videos/<video_id>.mp4` + linha no `manifest.jsonl` (§5).

### 3.4 Extração de frames

- **Amostragem base:** 1 fps (`ffmpeg -vf fps=1`) + frames de mudança de cena (`select='gt(scene,0.4)'`) como complemento. Um vídeo de 10 min → ~600 frames base.
- **Pares temporais:** pra cada frame aceito na poda final, guardar também o frame `t+1s` — é o insumo da régua de flicker e dos pares temporais que curaram o flicker na t14. Sem par, o frame serve pra segmentação, não pra temporal.
- **Metadado por frame:** `video_id, t_s, width, height, laplacian_var` (nitidez), `mean_luma`. Frame é JPEG qualidade 90, resolução nativa até 1280px de largura.
- **Escala de referência:** as 4,13 h da rodada 0 → ~14.900 frames a 1 fps. O censo Kinetics avaliou 54.812 frames a ~191 ms/frame (mediana, CPU desta VM) — ou seja, julgar ~15 mil frames com o detector custa ~45–50 min de CPU aqui: viável, sem GPU, sem pressa artificial.

### 3.5 Poda (Dataset Pruning) — o coração do projeto

Quatro níveis, do mais barato pro mais caro. Cada nível só recebe quem passou no anterior. Taxas abaixo são **metas de desenho** a calibrar no piloto (§9, Fase 1) — os números medidos do piloto substituem as metas.

**Nível 0 — poda burra (barata, por pixel)**
Descarta: duplicata exata (sha), quase-duplicata temporal (diferença média entre frames consecutivos abaixo de limiar), borrado (`laplacian_var` no decil inferior do próprio vídeo), preto/branco estourado (luma extrema), letterbox/transição.
*Meta: −40 a −60% dos frames.*

**Nível 1 — poda por domínio (os juízes do Draw)**
Roda em cada frame sobrevivente:
- **FT-dyn**: máscara de folha + confiança/presença;
- **hand_landmarker** (MediaPipe, o mesmo do app): mão presente? quantos pontos visíveis;
- **w8**: densidade de tinta dentro da máscara.
Classifica o frame numa das classes do §6 e descarta `sem_folha_sem_mao` repetidos além da cota de negativos. É o equivalente ao OpenFace como filtro — modelo pronto usado como juiz de domínio, só que os juízes aqui são os do Draw + a mão.
*Atenção à R6: estes juízes têm viés conhecido (FT-dyn veta 64,9% do Kinetics). Por isso o Nível 1 **classifica e prioriza, não veta sozinho** o que é diverso — ver cota de desacordo no Nível 3.*

**Nível 2 — poda por redundância geométrica (Coreset Selection)**
Em cima dos embeddings de cada frame (vetor que resume o conteúdo visual; extrator: DINOv2 pequeno ou o encoder do próprio SegFormer da folha — decidir no piloto pelo custo medido):
- clusteriza os frames de todos os vídeos (k-means ou HDBSCAN);
- dentro de cada cluster, fica com os frames mais representativos (perto do centro) **e** os de borda (longe do centro, são os casos raros);
- algoritmo de referência: **k-center greedy** — seleciona iterativamente o frame mais distante de todos os já selecionados, o que garante cobertura do espaço visual com o menor número de pontos. Na prática: é a formalização de "não quero 500 frames iguais da mesma mesa branca".
*Meta: reduzir o restante a ~10–15%.*

**Nível 3 — poda por informação (Active Learning)**
Sobe no ranking (entra primeiro no orçamento final) quem:
- tem **desacordo entre juízes**: FT-dyn diz folha, clássico (contornos) diz não — ou o contrário;
- tem confiança intermediária do FT-dyn (presença entre 0,3 e 0,7): é onde o modelo está em dúvida, e dúvida rotulada é o exemplo que mais ensina;
- pertence a cluster raro (poucos vídeos com aquele tipo de mesa/papel/luz).
E desce quem o modelo já acerta com confiança alta e é parecido com muito vizinho (exemplo já aprendido).

**Orçamento final (meta do piloto):** 2.000–5.000 frames únicos + seus pares `t+1s`, vindos de ≥30 vídeos/setups distintos, com a composição do §6. De ~15 mil frames extraídos a 1 fps, o coreset final retém ~13–34% — e menos de ~1% de todos os frames dos vídeos na cadência nativa (~30 fps). É essa fração mínima que é o coreset.

### 3.6 Juízo e rótulo

- **Pseudo-rótulo inicial:** máscara do FT-dyn + tinta do w8 + cantos, gravados como proposta, nunca como verdade.
- **Veto clássico:** detector de contornos/quads contesta a máscara; divergência grande marca o frame pra revisão.
- **Revisão humana:** kit visual no padrão do kit do holdout (referência × máscara × diff, ~1 min/página medido): cota aleatória de 10–20% dos aceitos + 100% dos casos de desacordo do Nível 3. A revisão do Lucas (ou de quem ele designar) é a verdade; o resto fica marcado como `pseudo` no manifesto e **nunca** entra em régua.
- **Réguas:** frames de vídeos reservados pra régua (§7) são rotulados de forma independente (foto/frame final menos referência, revisão manual), nunca com pseudo-rótulo dos modelos avaliados.

### 3.7 Pacote Kaggle

- **Trilha CC BY (pixels):** dataset **privado** novo, ex.: `draw-youtube-coreset-v1-private`, contendo frames podados + pares + `manifest.jsonl` + `README` com fonte, licença por vídeo e créditos dos canais (CC BY exige atribuição — o manifesto a carrega por `video_id`).
- **Trilha licença padrão (sem pixels):** só índice — `video_id, tempos, classe, resultado dos juízes` — no padrão do `guzzbr/draw-kinetics-writing-index`. Os frames dessa trilha, se usados, são consumidos localmente (fine-tune local/kernel efêmero) e não re-hospedados.
- **Subida:** fluxo já provado nesta casa (blob correto + PUT via curl; dataset nunca mora no disco do Lucas — R4). Conferir versão `Ready` + listagem de arquivos antes de declarar entregue.

## 4. Conceitos (nomeados, em linguagem simples)

- **Dataset Pruning (poda de dataset):** eliminar dado redundante/ruim de um conjunto grande sem perder desempenho. Aqui: os Níveis 0–3.
- **Coreset (núcleo):** o subconjunto pequeno que, sozinho, treina quase tão bem quanto o conjunto inteiro. Aqui: o pacote final de 2–5 mil frames.
- **Active Learning (aprendizado ativo):** o modelo escolhe o que vale rotular — o que ele acha difícil/incerto. Aqui: Nível 3 (desacordo e dúvida sobem).
- **Sample Complexity / Scaling Laws:** quantos exemplos bastam. Este projeto mede isso na prática pro Draw: o piloto compara treino com 100% dos frames sobreviventes × coreset, na mesma régua — se o coreset empatar, a fração mínima vira o padrão das rodadas seguintes.
- **Data-Centric AI:** o guarda-chuva: melhorar o dado em vez de trocar o modelo. É a direção já adotada pelo Lucas em 2026-11-05 ("esforço vai pro gargalo: dado real").

## 5. Esquema de dados

```
youtube-coreset/
  SPEC.md                  ← este documento
  candidates.csv           ← descoberta (§3.1), esquema herdado da caça CC BY
  manifest.jsonl           ← 1 linha por vídeo baixado
  frames/
    <video_id>/f_<t_s>.jpg ← frames podados (Nível ≥1)
    <video_id>/f_<t_s>_next.jpg
  labels/
    <video_id>/f_<t_s>.png ← máscara proposta/revisada
  manifest_frames.csv      ← 1 linha por frame no coreset
  exclusions.txt           ← video_ids/frame_ids proibidos (réguas existentes)
  receipts/                ← recibo por estágio e por fase
```

`manifest.jsonl` (por vídeo): `video_id, url, channel, channel_id, duration_s, license, license_checked_at, classe_enquadramento, sha256, bytes, download_route, session_split` (`train|holdout_setup|excluded`).

`manifest_frames.csv` (por frame): `frame_id, video_id, t_s, pair_id, sharpness, luma, ftdyn_presence, ftdyn_mask_iou_classic, hand_present, ink_density, cluster_id, prune_level_reached, selection_reason` (`centroide|borda|desacordo|duvida|negativo|aleatorio_revisao`), `label_kind` (`revisado|pseudo`), `label_paths`.

## 6. Classes e cotas do coreset (meta do piloto)

| Classe | O que é | Cota alvo |
|--------|---------|-----------|
| `folha_solta` | folha única sobre mesa, mão escrevendo/desenhando | 25% |
| `caderno_aberto` | duas páginas + vale central (a cegueira conhecida do FT-dyn) | 20% |
| `caderno_simples` | caderno de página única visível / bloco | 15% |
| `papel_parcial` | folha cortada, angulada, fora do enquadramento ideal | 10% |
| `negativo_mesa` | mesa/desk sem papel (negativo duro de presença) | 15% |
| `negativo_parecido` | objeto que parece papel: livro fechado, tablet, envelope, tábua clara | 10% |
| `negativo_outro` | quadro, tela, pessoa sem papel | 5% |

Timelapse entra marcado (`speed=timelapse`): serve pra folha/mão/presença e segmentação; **não** serve pra régua temporal (cadência não é real). Tempo real é subconjunto separado no manifesto (`speed=realtime`).

## 7. Portões de qualidade (antes de qualquer treino usar o pacote)

1. **Disjunção provada:** interseção do pacote com `absence_v1`, com o censo Kinetics (567) e com o holdout selado da mesa = **0**, verificada por script, recibo em `receipts/`.
2. **Divisão por sessão:** nenhum `video_id` (nem `channel_id` de setup único) em dois splits.
3. **Diversidade mínima:** ≥30 vídeos, ≥20 canais, nenhum vídeo com >10% dos frames do coreset.
4. **Amostra visual:** montagem de 100 frames aleatórios do pacote confere com as classes declaradas (≥90% corretos a olho; abaixo disso, volta pra §3.5 calibrar).
5. **Licença:** 100% dos vídeos da trilha de pixels com `cc_by_confirmed=sim` no manifesto.

## 8. Estimativas (âncoras medidas, não promessas)

| Item | Número | Âncora |
|------|--------|--------|
| Estoque inicial CC BY | 77 vídeos, 33 úteis, 4,13 h | caça de 2026-11-05, `candidates.csv` |
| Frames brutos do estoque | ~14.900 @1fps | 4,13 h × 3600 s |
| Julgamento FT-dyn desse volume | ~45–50 min CPU | 191 ms/frame mediano, censo Kinetics (54.812 frames) |
| Coreset final (meta) | 2.000–5.000 frames + pares | desenho do §3.5, calibrar no piloto |
| Download | desconhecido até a prova | bloqueado na VM; prova de 1 vídeo no kernel Kaggle decide |

Custo de treino: nenhum nesta spec. Quando o pacote virar fine-tune, vale o protocolo vigente (smoke verde no mesmo runtime antes da corrida, recibo de utilização).

## 9. Fases de implementação (cada uma termina em recibo)

- **Fase 0 — Prova da perna de download (1 vídeo).** Baixar 1 vídeo CC BY curto (sugestão: `sVTAtgzPGhA`, 15 s, o mesmo do teste bloqueado) de dentro de um kernel Kaggle; conferir sha, duração, `ffprobe`, extrair 15 frames. **Portão:** pixel íntegro na mão. Se a rota Kaggle falhar, tentar a rota 2 uma vez e registrar; nada de lote antes deste portão.
- **Fase 1 — Piloto de poda (5 vídeos).** Pipeline inteiro (§3.4–3.5) em 5 vídeos diversos do estoque (1 folha solta, 1 caderno aberto, 1 timelapse, 1 tempo real, 1 negativo). Medir taxa real de descarte por nível e tempo/frame de cada nível. **Portão:** taxas medidas substituem as metas do §3.5; montagem visual aprovada.
- **Fase 2 — Lote CC BY (33 vídeos).** Rodar nos 33 úteis da rodada 0, montar o coreset v1 dentro das cotas do §6, passar nos portões do §7, subir privado pro Kaggle (§3.7).
- **Fase 3 — Medição da fração mínima.** Fine-tune curto comparando: (a) todos os frames sobreviventes do Nível 1 × (b) coreset final, julgados na **bancada selada + holdout de outro setup** montado da Fase 2 — nunca na régua interna. **Portão:** se (b) ≥ (a), coreset vira o padrão; se (b) < (a), a poda aperta menos e repete-se a Fase 3 uma vez.
- **Fase 4 — Rodadas contínuas.** Novas buscas (rotação de consultas e canais) alimentam v2, v3…; cada rodada acumula no dataset (padrão do self-learning: dataset acumula, parada após 2 rodadas sem ganho na bancada).

## 10. Riscos e mitigações

| Risco | Evidência | Mitigação |
|-------|-----------|-----------|
| Bot-check do YouTube bloqueia download | medido nesta VM em 2026-11-05 | perna Kaggle (§3.3 rota 1), prova de 1 vídeo antes do lote |
| Juízes enviesados podam justamente o dado novo (FT-dyn veta 64,9% de setup alheio) | censo Kinetics | Nível 1 classifica, não veta sozinho; Nível 3 resgata desacordo/dúvida; cota aleatória de revisão inclui frames "reprovados" |
| Timelapse contamina régua temporal | rodada 0: maioria dos longos é timelapse | marca `speed` no manifesto; temporal só usa `realtime` |
| Mesmo canal = mesmo setup vaza entre splits | risco estrutural | split por `channel_id` quando o setup é fixo (R1/§7.2) |
| Licença muda / vídeo sai do ar | natureza do YouTube | manifesto guarda licença verificada com data + sha dos pixels baixados; índice permite reconstruir |
| Volume explode e vira outro dataset imenso | risco de desenho | orçamento de frames é teto, não piso (§3.5); disco local é staging, apaga após subir e conferir (fluxo R4 análogo) |

## 11. Decisões que são do Lucas (não desta spec)

1. Aprovar a Fase 0 (prova de download no kernel Kaggle).
2. Se as rotas 1–2 de download falharem: autorizar ou não a rota 3 (cookies da conta dele).
3. Tornar qualquer versão do dataset **pública** um dia — fora de cogitação por padrão (R2); só com palavra dele.
4. Quando o coreset v1 existir: autorizar o fine-tune da Fase 3 e, depois do veredito da bancada, qualquer troca em produção (regra vigente: swap é dele).

## 12. Critério de sucesso do projeto

O projeto deu certo quando existir, conferido e no Kaggle privado:

1. um coreset v1 dentro de todas as cotas e portões (§6–§7), de ≥30 setups que não são o do Lucas;
2. um **holdout de outro setup** selado a partir dele — a peça que hoje falta pra responder "funciona na mesa dos outros?" com número, e não com medo;
3. a medição da Fase 3 dizendo qual fração do dado bruto bastou — o resultado de Coreset Selection aplicado ao Draw, com recibo.
