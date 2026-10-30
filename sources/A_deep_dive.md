# 중국 반도체 소재기업 Deep Dive: 차세대 메모리(4F²·3D DRAM·HBM·HBF) 소재 자립 가능성과 Choke Point 판정 (기준일 2026.10.30)

**결론부터 말하면, 중국은 2026년 10월 현재 차세대 메모리에 필요한 소재를 "자국 공급망만으로" 확보할 수 없다. 기존 공정의 연장선에 있는 소재(Wet·Gas 범용품·300mm Wafer·CMP Slurry·Target)는 DRAM 기준 L3(Critical 양산)에 상당 부분 도달했지만, 4F²·HBM에서 새로 쓰이거나 요구 수준이 높아지는 소재(ArF-i PR·Top coat·PR 원료, 4F²용 신규 ALD 전구체, HBM 패키징 소재, 고순도 특수가스 일부)는 L1~L2에 머문다. 진짜 병목은 소재보다 장비(ArF-i 스캐너와 유지보수, Hybrid bonder, 계측)에 더 크게 걸려 있다.**

---

## TL;DR

- **자립 판정: "부분 자립, 2028년 이전 완전 자립 불가".** 기존 소재의 연장선인 Wet·Gas 범용품·Wafer·Slurry·Target은 L3에 들어섰다. 반면 4F²/HBM 신규 소재와 PR 계열은 L1~L2다. PR은 鼎龙股份(Dinglong)이 2026.6.11 자발 공시로 "두 곳의 선두 팹 고객이 최근 합계 근 1,000갤런 신규 주문"(KrF+ArF 합산 물량이며 ArF-i 단독 아님, 300톤 라인은 3.20 가동)을 확인한 것이 최고 수준이다(A). 하지만 이 물량은 연산 300톤 라인 대비 1~2% 수준(추정)이고 Critical 레이어 적용 여부도 공개되지 않았다.
- **Choke point Top 3: ① ArF-i PR+Top coat(멀티 패터닝 Critical 레이어) ② PR 원료(수지·PAG·모노머 고급 등급) ③ 4F²·3D DRAM용 신규 ALD 전구체와 그 금속 원료.** 장비 병목(ArF-i 스캐너, Hybrid bonder, Overlay/CD 계측)은 별도로 표시했으며, 소재 병목보다 해소가 더 어렵다고 판단한다.
- **가설 판정: H1 대체로 채택(단, 鼎龙의 재주문 공시로 "재주문 단계"까지는 확인되어 일부 수정). H2 기각(근거 불충분).** 珠海基石科技(Zhuhai Cornerstone)는 인프라 투입은 확인되지만(설립 후 17개월 만에 시생산 신고, A), Qual·양산 결과는 공개 근거로 확인되지 않는다. **H3 부분 채택.** "기존 소재 연장선"은 L3, "신규 도입 소재"는 L1~L2다.

---

## 1. Executive Summary

### 1-1. 자립 가능성 결론

| 구분 | 판정 | 핵심 근거 (등급) |
|---|---|---|
| 4F² DRAM 소재 | **부분 자립 (L2 중심)** | CXMT 4F² 제품은 "연내 출시 발표"만 있고 양산은 미확인(B). [trendforce](https://www.trendforce.com/news/2026/10/12/news-cxmt-accelerates-4f%C2%B2-dram-push-eyes-year-end-server-ddr5-rdimm-launch/) ArF-i 멀티 패터닝 PR 국산화율은 1% 미만~5% 미만(B) [qq](https://news.qq.com/rain/a/20250328A01R2C00) [chyxx](https://www.chyxx.com/industry/1259886.html) |
| HBM 소재 | **취약 (L1~L2)** | 华海诚科 GMC는 샘플 단계, 언더필은 양산 준비 단계(C, 招股书를 인용한 2차 자료). [x](https://x.com/LinQingV/status/2056719347725603102) 安集 TSV/Hybrid bonding용 Slurry는 양산(B) |
| 3D DRAM 소재 (추정) | **취약 (L1~L2, 추정)** | 3D NAND 소재의 연장선이므로 YMTC 공급망 활용이 가능하다고 추정. 다만 신규 전구체와 고선택비 식각가스가 병목 |
| HBF 소재 (추정) | **취약 (L1, 추정)** | 3D NAND 소재(L3)와 HBM 적층·본딩 소재(L1~L2)의 결합이라 약한 쪽이 상한을 정함 |
| 원료(Tier-2) | **PR 원료와 금속 원료가 가장 취약** | 고급 PR 수지·PAG 국산화율 "편저"(B). [sina](https://www.sina.cn/news/detail/5317391384052455.html) 雅克 전구체 금속 원료는 "국산화 계획 단계"(B). 江丰 원가의 73.46%가 원재료이고 고순도 금속은 소수 공급사에 의존(B) | [sina](https://finance.sina.com.cn/wm/2026-05-09/doc-inhxhcxm1639959.shtml) [xueqiu](https://xueqiu.com/5159371081/387469240)

### 1-2. Choke Point Top 10 (소재·원료)

| 순위 | 소재/원료 | 영향 공정 | 중국 자립 단계 | 해외 의존 (추정) | 주 공급국 | 대체 소요 (추정) | 비고 |
|---|---|---|---|---|---|---|---|
| 1 | ArF-i PR + Top coat (Critical 레이어) | 4F², 3D DRAM, HBM 베이스다이 | L2 | 95% 이상 | 일본 | 3~5년 | 국산화율 "<1%"(CEMIA) ~ "<5%"(光大) [qq](https://news.qq.com/rain/a/20250328A01R2C00) [chyxx](https://www.chyxx.com/industry/1259886.html) |
| 2 | PR 원료: 고급 수지·PAG·모노머 | PR 전체 | L1~L2 | 70~90% | 일본·미국 | 3~5년 | 鼎龙은 "핵심 원료 100% 자산" 주장(B, 회사 발언 인용) [ifeng](https://finance.ifeng.com/c/8v7VoXw4Sum) |
| 3 | 4F²/3D DRAM용 신규 ALD 전구체 (High-k·금속계) | 4F², 3D DRAM | L1~L2 | 70% 이상 | 한국·일본·미국·유럽 | 2~4년 | 雅克은 UP Chemical(한국) 생산이 주력. 국내 江苏先科는 "배치 시생산"(B) | [cfi](https://quotewh.cfi.cn/ybdata.aspx?id=20260509000108)
| 4 | 고순도 특수가스: C4F6 고순도, PH3/AsH3/B2H6, Kr/Ne 혼합 | 고종횡비 식각, 도핑 | L1~L2 | 90% 이상 | 미·일·한·유럽 | 2~3년 | 해당 품목 국산화율 "<10%"(C) |
| 5 | HBM Temporary bonding/Debonding 소재 | HBM, HBF | L1 (미확인) | 90% 이상 | 일본·미국·독일 | 2~3년 | 공개 근거 없음. 데이터 공백 |
| 6 | HBM MUF/GMC·Underfill | HBM, HBF | L1~L2 | 80% 이상 | 일본 | 2~3년 | 华海诚科 GMC 샘플, 언더필 양산 준비(C) [x](https://x.com/LinQingV/status/2056719347725603102) |
| 7 | Si-ARC·Top coating 등 Ancillary 고급 품목 | 4F² 멀티 패터닝 | L1~L2 | 80% 이상 | 일본·미국 | 2~3년 | 恒坤: "고객 검증 단계"(A, 招股书 문의 회신). SOC/BARC는 L3 [10jqka](http://notice.10jqka.com.cn/api/pdf/1823119353d04828_1747753427/%E6%81%92%E5%9D%A4%E6%96%B0%E6%9D%90%EF%BC%9A8-1%E5%8F%91%E8%A1%8C%E4%BA%BA%E5%8F%8A%E4%B8%AD%E4%BB%8B%E6%9C%BA%E6%9E%84%E5%85%B3%E4%BA%8E%E9%A6%96%E8%BD%AE%E5%AE%A1%E6%A0%B8%E9%97%AE%E8%AF%A2%E5%87%BD%E7%9A%84%E5%9B%9E%E5%A4%8D.pdf) |
| 8 | Target용 초고순도 금속 원료 (Ta, Cu 6N, Co 등) | 배선, TSV | L2~L3 | 40~60% | 일본·미국 | 1~3년 | 江丰: 탄탈 공급망 "극히 긴장"(A, 年报) | [sina](http://file.finance.sina.com.cn/211.154.219.97:9494/MRGG/CNSESZ_STOCK/2026/2026-4/2026-04-16/12096894.PDF)
| 9 | 7N급 초고순도 가스 전반 | 첨단 공정 전반 | L2 | 80% 이상 | 미·일·유럽 | 2~3년 | 7nm 이하용 국산화율 <20%(C) |
| 10 | Hybrid bonding 유전막(SiCN) 전구체와 본딩 CMP 세트 | HBM4 이후, 4F² CoP, HBF | L1~L2 | 70% 이상 | 미·일·한 | 2~3년 | 安集 Slurry는 양산(B), 전구체는 근거 미확보 |

**장비 병목 (별도 표시, 소재보다 우선순위 높음):** ArF-i 스캐너 신규 도입과 유지보수(美 MATCH Act(H.R. 8170, 2026.4.2 하원 발의)는 SMIC·화웨이·CXMT·Hua Hong·YMTC에 대한 액침 DUV 장비 판매·유지보수 금지와 네덜란드·일본의 150일 내 보조 조치를 담고 있으나 아직 법안 단계로 시행되지 않음, B: Tom's Hardware·Hardware Busters), Hybrid bonder, Overlay/CD 계측, Track(코터/디벨로퍼). 이 중 노광·계측·코터/디벨로퍼·이온주입은 "장비 국산화의 취약 고리"로 보도되었다(C).

---

## 2. 환율 표와 표기 규칙

### 2-1. 적용 환율 (CNY→KRW)

| 적용 대상 | 기준 | 적용 환율 (1 CNY) | 비고 |
|---|---|---|---|
| 2014 실적·출자 | 연평균 | 171원 | USD/KRW 1,053, USD/CNY 6.16로 교차 산출 |
| 2016 실적 | 연평균 | 175원 | USD/KRW 1,160, USD/CNY 6.64 |
| 2019 실적·출자 | 연평균 | 169원 | USD/KRW 1,166, USD/CNY 6.91 |
| 2023 실적 | 연평균 | 184원 | USD/KRW 1,305, USD/CNY 7.08 |
| 2024 실적 | 연평균 | 190원 | USD/KRW 1,364, USD/CNY 7.19 |
| 2025 실적 | 연평균 | 197원 | USD/KRW 약 1,420, USD/CNY 약 7.19 (**작성자 추정치, 확정치로 교체 권고**) |
| 2026 실적·전망·투자계획 | 기준일 2026.10.30 | 200원 | **작성자 가정치(미검증)**. 본 리서치에서 기준일 고시환율을 확보하지 못함. 서울외국환중개 고시치로 교체 필요 |

> 환율은 본 조사 범위에서 1차 고시자료로 검증하지 못했다. 원화 환산치는 규모 감 파악용이며, 경영진 보고 전 확정 환율로 일괄 재계산할 것을 권고한다.

### 2-2. 표기 규칙
- 근거 등급: **A** = 공시·정부자료·법인등기·IR 기록, **B** = 증권사·주요 언론·학술, **C** = 업계 추정·익명·SNS·투자 커뮤니티
- **[사실]** 은 출처에 명시된 내용, **[추정]** 은 작성자 추론이다. 표 안의 "(추정)"은 작성자 계산 또는 판단이다.
- 자립 단계: L1 시제품 공급 / L2 Non-critical 양산 / L3 Critical 양산 / L4 원료까지 자립

---

## 3. 배경 타임라인 (2014~2026): 경쟁력은 어떻게 만들어졌나

### 3-1. 연도별 이정표

| 연도 | 정책·자본 | 수요·기업 | 외부 요인 | 등급 |
|---|---|---|---|---|
| 2014.6 | 《国家集成电路产业发展推进纲要》 발표 [cnbeta](https://m.cnbeta.com.tw/view/1432464.htm) | – | – | B |
| 2014.9 | 大基金 1기 설립. 등록자본 987.2억 위안, 최종 모집 1,387억 위안(약 23.7조 원). 장비·소재 투자 비중 약 6% [cnbeta](https://m.cnbeta.com.tw/view/1432464.htm) | – | – | B (cnBeta/企查查 인용) |
| 2016 | – | 雅克科技(Yoke), 한국 UP Chemical을 약 11.79억 위안(약 2,060억 원)에 인수. UP Chemical은 2004년부터 SK하이닉스 공급사 | – | B | [laohucaijing](http://m.laohucaijing.com/news/index/150689/)
| 2016~2017 | 지방 클러스터 형성 (合肥 CXMT, 武汉 YMTC) | 恒坤新材, 2017년 수입 KrF PR(KKPC/SKMP 대리)로 12인치 팹 공급 개시 [sina](https://finance.sina.com.cn/tech/digi/2024-12-30/doc-inecfrav1252351.shtml) | – | A (恒坤 문의 회신) |
| 2019.10 | 大基金 2기 설립, 2,041.5억 위안(약 34.5조 원). 장비·소재를 중점 투자 대상으로 명시 [cls](https://www.cls.cn/detail/1686968) [eeo](http://www.eeo.com.cn/2024/0603/664753.shtml) | – | 미 Entity List 확대(화웨이) | B |
| 2020~2021 | 14차 5개년 계획 기간. "2025년 KrF/ArF PR 국산화율 10%" 목표 보도 [qq](https://news.qq.com/rain/a/20250328A01R2C00) | 南大光电 ArF PR 첫 고객 통과(2020년 전후). [cls](https://m.cls.cn/detail/699696) SiCarrier(新凯来技术) 2021.8 설립 [sina](https://finance.sina.com.cn/jjxw/2025-04-09/doc-inespyit2933694.shtml) | – | 목표치는 C (출처 원문 미확인) |
| 2022 | – | 新凯来工业机器 2022.6.7 설립, 珠海基石科技 2022.6.30 설립 [gdhc-shebaidu](http://www.gdhc-shebaidu.com/upload/iaEdW/file/202401/20240126155526_96003.pdf) [jrj](https://m.jrj.com.cn/madapter/stock/2025/03/28080149099248.shtml) | 미 2022.10 반도체 수출통제 | A (天眼查·安评) | [nomadsemi](https://www.nomadsemi.com/p/what-sicarriers-president-said-at)
| 2023 | – | 基石 Zhuhai 라인 시생산 신고(2023.11.24). [gdhc-shebaidu](http://www.gdhc-shebaidu.com/upload/iaEdW/file/202401/20240126155526_96003.pdf) CXMT, IEDM 2023에서 8Gb 4F²(VCT) 연구 어레이 발표 [lavx](https://news.lavx.hu/article/cxmt-president-says-first-4f-dram-will-be-a-server-ddr5-rdimm-due-by-year-end) | 日 METI 2023.7 첨단 장비 23종 수출관리 [huxiu](https://www.huxiu.com/article/4877456.html) | A / B |
| 2024.5 | 大基金 3기 설립, 3,440억 위안(약 65.4조 원), 존속기간 15년(~2039), 재정부 17.44% [eeo](http://www.eeo.com.cn/2024/0603/664753.shtml) [cnbeta](https://m.cnbeta.com.tw/view/1432464.htm) | 南大 ArF 3종 통과, 매출 1,000만 위안 돌파 [eastmoney](https://caifuhao.eastmoney.com/news/20260828005942332962820) | 2024.12 美 Entity List 140개사 추가(SiCarrier·Cornerstone·宇量昇·SwaySure·SiEn·鹏新旭 등), [federalregister](https://public-inspection.federalregister.gov/2024-28267.pdf) HBM 대중 판매 제한 | A (Federal Register) / B | [federalregister](https://public-inspection.federalregister.gov/2024-28267.pdf) [x](https://x.com/WillRinehart/status/1863637557524959341)
| 2025 | 15차 5개년(2026~2030) 준비 | 恒坤新材 科创板 상장(2025.11.18). [tencent](https://developer.cloud.tencent.com.cn/article/2643377) 鼎龙 ArF/KrF 2종 첫 수주. SiCarrier, SEMICON China 첫 공개(2025.3) [Wikipedia](https://en.wikipedia.org/wiki/SiCarrier) | 日 2025.11 ArF/EUV PR 수출관리 편입설(C). [xueqiu](https://xueqiu.com/1914357104/386633422) 반대로 "단공 전설은 해관 데이터상 사실무근"이라는 반박 보도(B, 虎嗅) [huxiu](https://www.huxiu.com/article/4877456.html) | 혼재 | [nomadsemi](https://www.nomadsemi.com/p/what-sicarriers-president-said-at)
| 2026 | 15차 5개년 개시 | 鼎龙 300톤 라인 가동(3.20), 재주문 공시(6월). [investing](https://cn.investing.com/news/stock-market-news/article-3413656) CXMT 상장(7.27), G5 양산(9월), 4F² 발표(10.10) [trendforce +2](https://www.trendforce.com/news/2026/10/12/news-cxmt-accelerates-4f%C2%B2-dram-push-eyes-year-end-server-ddr5-rdimm-launch/) | 中, 대일 이중용도 수출통제 강화(2026.1, C/B). [eastmoney](https://caifuhao.eastmoney.com/news/20260527160738902783260) 日 "기술관리 사전보고" 대상 확대(2026.8, B) [huxiu](https://m.huxiu.com/article/4885105.html) | A / B / C |

### 3-2. 요인별 기여도 평가

| 요인 | 기여 메커니즘 | 효과 판정 | 근거 |
|---|---|---|---|
| 정책 (大基金·5개년) | 장비·소재 자본 공급. 3기는 1·2기 합보다 큰 규모 [eeo](http://www.eeo.com.cn/2024/0603/664753.shtml) | **높음 (자본), 중간 (기술)**. 14차 5개년의 PR 10% 목표는 미달(2025년 ArF <1~5%) | B |
| 지방 자본 (SZMII 등) | 深圳国资 → SZMII → SiCarrier → 基石으로 이어지는 100% 국유 체인 [gdhc-shebaidu](http://www.gdhc-shebaidu.com/upload/iaEdW/file/202401/20240126155526_96003.pdf) [sina](https://finance.sina.com.cn/jjxw/2025-04-09/doc-inespyit2933694.shtml) | **높음**. 장비·소재·Fab 수직 루프 형성 | A (天眼查/安评) | [nomadsemi](https://www.nomadsemi.com/p/what-sicarriers-president-said-at)
| 화웨이 | 지분 없이 인력·기술·수요를 제공하는 것으로 추정. BIS가 SiCarrier 별칭으로 "Huawei Starlight Engineering Department" 명시 [nomadsemi](https://www.nomadsemi.com/p/what-sicarriers-president-said-at) | **높음 (추정)**. 단, 화웨이는 SiCarrier와 무관하다고 공개 부인 [techbuzzchina](https://chips.techbuzzchina.com/companies/sicarrier) | A (BIS) / B (Reuters 인용) | [nomadsemi](https://www.nomadsemi.com/p/what-sicarriers-president-said-at)
| 哈勃投资(Hubble) | 본 조사 범위의 SiCarrier·基石 지분 사슬에서 **확인되지 않음** | 판정 보류 | – |
| 수요 (CXMT·YMTC·SMIC) | 국산 우선 검증. CXMT 2024 원재료 구매 약 114.7억 위안(약 2.18조 원) | **매우 높음**. 국산 PR의 실질 검증처 | C (招股书를 인용한 2차 자료) |
| 인력 | 基石이 일본·한국·대만 인력을 영입(Nikkei 보도), SwaySure는 前 Elpida 사장 坂本幸雄이 이끌었음 [trendforce](https://www.trendforce.com/news/2025/05/29/news-huawei-reportedly-pushes-chip-chemical-independence-through-zhuhai-cornerstone-rivaling-global-giants/) [digitimes](https://www.digitimes.com/news/a20250515PD215/huawei-dram-dongguan-government-shenzhen.html) | 중간~높음 | B |
| 해외 M&A | 雅克-UP Chemical: 한국 생산·인증 자산을 그대로 확보 | **높음**. 단, 핵심 생산은 여전히 한국 | B | [laohucaijing](http://m.laohucaijing.com/news/index/150689/)
| 수출통제 | 국산 검증 기회 확대(가속). 동시에 원료·분석장비 조달 제약(제약) | **양면적** | B/C |

---

## 4. 소재별 4축 비교표와 자립 단계

### 4-1. 종합 지수 비교 (한국 대표 기업 = 100, 대리지표 사용 칸은 ※)

| 소재 | Global Top | 한국 대표 | 중국 상위 | 중국 지수 (개발/품질※/가격※/Capa) | DRAM 기준 자립 단계 |
|---|---|---|---|---|---|
| PR (ArF-i/KrF) | JSR·TOK·信越 | 동진쎄미켐 | 鼎龙·南大·彤程(科华)·恒坤·上海新阳 | 70 / 40※ / 110※ / 60 | KrF L2~L3, ArF-i **L2**, i-line L3 |
| PR Ancillary (SOC/BARC) | Merck·Nissan Chem·DuPont | 동진·SK머티리얼즈퍼포먼스 | 恒坤新材 | 90 / 80※ / 110※ / 80 | SOC/BARC **L3**, Si-ARC/Top coat L1~L2 |
| CMP Slurry | Fujimi·Entegris(CMC)·Resonac | 솔브레인·KCTech | 安集科技 | 120 / 100※ / 100※ / 110 | **L3** (W, Cu barrier, Ceria) |
| CMP Pad | DuPont | SKC(SK엔펄스) | 鼎龙股份 | 90 / 80※ / 110※ / 90 | L3 (추정, 매출 상세 미확보) |
| Wet (범용) | Stella·Mitsubishi Chem | 솔브레인·동우화인켐 | 兴福电子·江化微·晶瑞 | 100 / 90※ / 110※ / 120 | **L3** (磷酸·硫酸) |
| Wet (Functional) | Entegris·Merck | 솔브레인 | 安集·兴福 | 90 / 80※ / 100※ / 80 | L2~L3 |
| Precursor | Merck·Air Liquide·Adeka | SK트리켐·한솔케미칼·솔브레인 | 雅克科技(UP Chem)·南大光电 | 100※ / 100※ / 100※ / 90 | **L3** (UP Chemical 한국 생산 기준), 중국 내 생산은 L2 |
| Target | JX금속·Honeywell·Tosoh | 솔브레인·LT메탈 | 江丰电子·有研新材 | 100 / 90※ / 110※ / 120 | **L3** (Al·Ti·Cu), Ta는 원료 제약 |
| 300mm Wafer | 信越·SUMCO | SK실트론 | 沪硅产业·西安奕斯伟 | 80 / 70※ / 120※ / 120 | 메모리 **L3** (로직보다 국산화율 높음, A) | [qq](https://file.finance.qq.com/finance/hs/pdf/2025/09/02/2025090215080241983420853.pdf)
| Process Gas | Linde·Air Liquide·대양일산 | SK스페셜티·원익머트리얼즈 | 中船特气·华特·昊华·南大 | 90 / 80※ / 120※ / 150 (NF3·WF6) | 범용 **L3**, 고급 특수가스 L1~L2 |

> 지수는 공개 데이터(매출·마진·Capa·검증 공시)를 근거로 한 **작성자 정성 추정치**다. 한국 = 100은 해당 품목 한국 대표 기업 대비 상대 위치를 뜻한다. 가격 지수가 100을 넘으면 더 싸다는 뜻이다.

### 4-2. 소재별 상세 (선정 근거·4축·한계)

#### (1) PR (+Ancillary): 핵심 병목

**선정 근거:** ArF/KrF 공시 진척(鼎龙·南大), KrF 점유율(彤程/科华), 12인치 Ancillary 매출(恒坤), 품목 폭(上海新阳). 基石은 H2 검증 대상이라 포함했다.

| 기업 | 개발 (노드·검증 단계) | 품질 대리지표 | 가격 대리지표 | Capa | 등급 |
|---|---|---|---|---|---|
| 鼎龙股份(Dinglong) | ArF 4종·KrF 4종 배치 수주. 40여 종 포트폴리오, 근 30종 송샘플, 10종 이상 갤런 샘플 테스트 [investing](https://cn.investing.com/news/stock-market-news/article-3413656) | "두 곳의 선두 팹 양산 라인에서 순조롭게 적용", 재주문 근 1,000갤런 [investing](https://cn.investing.com/news/stock-market-news/article-3413656) | 2025.1~3분기 R&D 3.89억 위안(약 766억 원), 매출 대비 14.41% [eastmoney](https://caifuhao.eastmoney.com/news/20251105193714779996010) | 1기 30t/년, 2기 300t/년 (2026.3.20 가동, 램프업 중) [investing](https://cn.investing.com/news/stock-market-news/article-3413656) [toutiao](https://www.toutiao.com/article/7650309358969995817/) | A (공시) / B |
| 南大光电(NATA) | ArF 6종 고객 검증 통과(2025년 3종 추가) [sina](https://finance.sina.com.cn/stock/aigc/jgdy/2026-04-16/doc-inhuryek2923724.shtml) | 2025년 ArF 매출 2,000만 위안 이상(약 39억 원). "만산 아님" [sina](https://finance.sina.com.cn/stock/relnews/cn/2026-04-21/doc-inhvfqcm0292317.shtml) | 子公司가 단량체·수지·감광제 자체 개발 역량 보유 [cs](https://www.cs.com.cn/ssgs/01/2026/04/16/detail_2026041610004396.html) | 공식 50t/년. 500t 신규 라인은 미공시 추정(C) [stcn](https://www.stcn.com/article/detail/3771772.html) [eastmoney](https://caifuhao.eastmoney.com/news/20260627153941347658840) | A (IR 기록) |
| 彤程新材 / 北京科华 | KrF 다수 팹 배치 공급 | KrF 국내 점유율 "40% 이상" [xueqiu](https://xueqiu.com/1980283165/394304495) | 자체 KrF 수지가 수입 대비 35% 저렴하다는 주장 [x](https://x.com/aiwangupiao/status/2008910293251023135) | 상하이 1,000t 시생산 보도 [zhihu](https://zhuanlan.zhihu.com/p/2058241464979678498) | C (점유율·원가 수치는 1차 출처 미확인) |
| 恒坤新材 | SOC/BARC 주력. KrF·i-line 판매, ArF-i "검증 통과, 소량 공급" [cls](https://www.cls.cn/detail/2040439) | SOC 국내 점유율 10% 이상(2023). 고객 A의 자사 SOC·BARC 공급 1위 [sse](https://static.sse.com.cn/stock/disclosure/announcement/c/202507/002050_20250714_GZD0.pdf) [sina](https://finance.sina.com.cn/tech/digi/2024-12-30/doc-inecfrav1252351.shtml) | 자산 KrF 2024 매출 1,285만 위안(약 24억 원), ArF 41만 위안 [sse](https://static.sse.com.cn/stock/disclosure/announcement/c/202507/002050_20250714_GZD0.pdf) | KrF 가동률 20% 미만 보도 | A (招股书 문의 회신) / B |
| 上海新阳 | KrF 10곳 이상 검증·수주, ArF-i "수주"(C) [xueqiu](https://xueqiu.com/1980283165/394304495) [zhihu](https://zhuanlan.zhihu.com/p/2058241464979678498) | – | – | 2025년 PR 판매 800t 주장(C) [xueqiu](https://xueqiu.com/1980283165/394304495) | C |
| 珠海基石科技 | 웹사이트: "0.18µm·90nm·65nm 대응 IC 범용 PR". ArF-i는 주장하지 않음 [cnstchem](https://www.cnstchem.com/) | 고객 공개 없음 | – | Phase 1은 "소량산 라인 분구". 전체 부지 전자화학품 계획 30,000t/년(PR 단독 수치 아님) [gdhc-shebaidu](http://www.gdhc-shebaidu.com/upload/iaEdW/file/202401/20240126155526_96003.pdf) [gd](http://drc.gd.gov.cn/xmgg/content/post_4254392.html) | A (安评·节能审查) |

**국산화율: 출처별 차이 (기준 혼재 주의)**

| 품목 | 출처 (날짜) | 수치 | 기준 | 등급 | 평가 |
|---|---|---|---|---|---|
| ArF | 中国电子材料行业协会 via 智研 (2026) | <1% [chyxx](https://www.chyxx.com/industry/1259886.html) | 명시 없음 (금액 추정) | B | **가장 신뢰** |
| ArF | 证券市场周刊 (2025.12) | <1% [weeklyonstock](https://static.weeklyonstock.com/25/1201/zbf095953.html) | 명시 없음 | B | 일치 |
| ArF | 光大证券 via 腾讯 (2025.3) | KrF/ArF <5% [qq](https://news.qq.com/rain/a/20250328A01R2C00) | 명시 없음 | B | 상한 |
| ArF | IIM 백서 (2025) | "10% 돌파" [iim](https://www.iim.net.cn/2358/view-19622-1.html) | 명시 없음 | C | 과대 가능성 |
| ArF/KrF | 中商情报网 (2025.4) | "30% 돌파" [askci](https://www.askci.com/news/20250414/161436274461847523477001.shtml) | 명시 없음 | C | **기각 (공시와 모순)** |
| KrF | 证券市场周刊 (2025.12) | 1~2% [weeklyonstock](https://static.weeklyonstock.com/25/1201/zbf095953.html) | – | B | – |
| KrF | CEMIA via 智研 (2026) | 약 3% [chyxx](https://www.chyxx.com/industry/1259886.html) | – | B | – |
| KrF | 研精毕智 (2026) | 5~10% [yjbzr](https://www.yjbzr.com/analyze/8012.html) | – | C | – |
| KrF | IIM (2025) | 25% [iim](https://www.iim.net.cn/2358/view-19622-1.html) | – | C | 과대 |
| g/i-line | 证券市场周刊 / CEMIA / 研精毕智 | 약 10% / 20~25% / 50% 이상 [chyxx +2](https://www.chyxx.com/industry/1259886.html) | – | B/B/C | 편차 큼 |

[추정] 鼎龙의 재주문 근 1,000갤런(약 3.8kL, 약 4톤)은 2기 연산 300톤의 약 1.3%다. 南大의 ArF 매출 2,000만 위안은 CXMT 한 곳의 2024 PR 구매액 약 13.9억 위안(114.7억 × 12.16%, C)의 약 1.4%에 불과하다. 이 비율로 보면 국산 ArF 점유율 "<1~5%"가 실물에 부합한다.

**과장 보도 검증:** "南大光电 28nm ArF Dry 수율 99.7%, 500톤 전면 달성"(搜狐·知乎, 2026.7~10) [sohu](https://www.sohu.com/a/1092336553_122483451)  [zhihu](https://zhuanlan.zhihu.com/p/2058241464979678498) 은 **기각(C)**이다. 회사 IR(A)은 공식 Capa 50t, "만산 아님", 2025 매출 2,000만 위안이라고 밝혀 상충한다. [sina](https://finance.sina.com.cn/stock/relnews/cn/2026-04-21/doc-inhvfqcm0292317.shtml) [stcn](https://www.stcn.com/article/detail/3771772.html)

**한계 구분**
- 일시적 한계: Capa 램프업, 품목 수(鼎龙 8종)
- 구조적 한계: ① 고급 수지·PAG의 분자량 분포·금속 불순물 관리(국산화율 "편저", B) [sina](https://www.sina.cn/news/detail/5317391384052455.html) ② ArF-i 스캐너 접근이 제한되어 평가 자체가 병목 ③ 일본 공급사의 현장 기술지원 철수설(C) [eastmoney](https://caifuhao.eastmoney.com/news/20260627010652957993380) 로 공정 튜닝 노하우 공백

**일본 수출통제: 상충 정보**

| 주장 | 출처 | 등급 | 판정 |
|---|---|---|---|
| 2026.1Q 대일 PR 수입 111.3t(-95%), ArF/EUV 수입 0 [163](https://www.163.com/dy/article/L0DE6DPH0556BYNU.html) [huxiu](https://www.huxiu.com/article/4877456.html) | 网易·东方财富 재인용 | C | 원 해관 데이터 미확인 |
| "단공 전설은 해관 데이터상 단절적 하락 없음, 사실무근" [huxiu](https://www.huxiu.com/article/4877456.html) | 虎嗅 | B | 반증 |
| 日, PR을 "기술관리 사전보고" 대상(기술이전 관리)에 편입 [guancha](https://www.guancha.cn/kegongliliang/2026_08_21_828164.shtml) | 观察者网 (2026.8) | B | 상품 수출금지가 아니라 **기술 이전 관리**임 |
| 日 4대사 2026.6.22 동시 단공 통보 [eastmoney](https://caifuhao.eastmoney.com/news/20260627010652957993380) [bbd](https://www.bbd.com.hk/article/7199/%E6%97%A5%E6%9C%AC%E5%9B%9B%E5%A4%A7%E5%85%89%E5%88%BB%E8%86%A0%E5%B7%A8%E9%A0%AD%E5%81%9C%E6%AD%A2%E5%B0%8D%E8%8F%AF%E5%87%BA%E5%8F%A3%E9%A7%90%E5%A0%B4%E5%B7%A5%E7%A8%8B%E5%B8%AB%E5%85%A8%E6%92%A4%E8%88%87%E5%9C%8B%E7%94%A2%E6%9B%BF%E4%BB%A3%E9%80%B2%E5%B1%95) | 东方财富 财富号·蓝莓观察 | C | 1차 확인 불가 |

[판단] 일본의 "PR 상품 수출 전면 금지"는 **확인되지 않는다**. 다만 기술이전 관리 강화는 사실이며(B), 중국 팹의 국산 Qual을 가속하는 정책 신호로는 유효하다.

#### (2) CMP Slurry (+Pad)
- **安集科技(Anji):** 2025 Slurry 매출 20.40억 위안(약 4,019억 원, +32.06%), 매출총이익률 58.28%. TECHCET 기준 글로벌 점유율 약 8%→11%→13%(3년)(A, 年报). [xueqiu](https://www.xueqiu.com/S/SH688019/384056748) [sina](https://finance.sina.com.cn/jjxw/2026-04-16/doc-inhuryef7835157.shtml) 자체 생산한 국산 세리아 연마재로 만든 Slurry가 양산 중(A). [cninfo](http://static.cninfo.com.cn/finalpage/2026-04-16/1225108553.PDF) TSV/Hybrid bonding용 Slurry 양산(B). [xueqiu](https://xueqiu.com/5159371081/384289445) R&D 비중 17.76%(A). [xueqiu](https://www.xueqiu.com/S/SH688019/384056748)
- **鼎龙股份:** Pad 국내 1위로 추정. Slurry 매출 +54%(B).
- **판정:** DRAM **L3**. 세리아 원료 자립으로 **L4 근접**. 구조적 한계는 작다.

#### (3) Wet (+Functional)
- **兴福电子:** 12인치 전공정 전자급 인산 국내 점유율 39.3%→55.8%→69.7%(2021~23), 황산 9.97%→18.25%→31.22%(A, 招股书). [sina](https://finance.sina.com.cn/roll/2025-01-22/doc-inefvcyc7809769.shtml) SEMI G3(인산)·G5(황산), 고객은 SMIC·YMTC·CXMT·SK하이닉스(A). [nbd](https://www.nbd.com.cn/articles/2025-01-23/3733821.html) [sina](https://finance.sina.com.cn/roll/2025-01-22/doc-inefvcyc7809769.shtml)
- IC용 Wet 전체 국산화율: 2021년 35% → 2023년 45% 초과(B, CEMIA). [sina](https://finance.sina.com.cn/jjxw/2025-01-23/doc-inefxtpe4806380.shtml) 安集 Functional Wet 매출 4.53억 위안(약 892억 원), 매출총이익률 50.00%, 글로벌 약 6%(A). [xueqiu](https://www.xueqiu.com/S/SH688019/384056748) [sina](https://finance.sina.com.cn/jjxw/2026-04-16/doc-inhuryef7835157.shtml)
- **판정:** 범용 **L3~L4** (황린 등 원료를 그룹 내 조달). Functional은 L2~L3.

#### (4) Precursor
- **雅克科技(Yoke):** 2025 전구체 매출 21.11억 위안(약 4,159억 원, +8.01%), 매출총이익률 44.79%(B). [sina](https://finance.sina.com.cn/wm/2026-05-09/doc-inhxhcxm1639959.shtml) CXMT에 DRAM 첨단 공정용 High-k·Si계 전구체 공급(회사 互动平台, A/B). [eastmoney](https://caifuhao.eastmoney.com/news/20260928164004546435900) 국내 江苏先科는 "고객 검증 통과 후 배치 시생산"(B). [cfi](https://quotewh.cfi.cn/ybdata.aspx?id=20260509000108) "금속 원료 국산화를 계획·포석 중"(B). [sina](https://finance.sina.com.cn/wm/2026-05-09/doc-inhxhcxm1639959.shtml) 이는 **현재 금속 원료를 해외에 의존한다는 뜻**이다.
- **南大光电:** 2025 전구체(MO원 포함) 매출 7.14억 위안(약 1,407억 원)(B). [sina](https://stock.finance.sina.com.cn/stock/view/paper.php?symbol=sh000001&reportid=833469214128)
- **판정:** 공급 자체는 L3이지만 **중국 영토 내 생산 기준 L2**, 원료는 L1~L2다. UP Chemical(한국) 자산은 한국 정부·고객 정책에 노출되어 있어 "해외 차단 시 유지" 조건(L4)을 충족하지 못한다.

#### (5) Target
- **江丰电子(KFMI):** 2025 Target 매출 28.50억 위안(약 5,615억 원, +22.13%), 매출총이익률 34.24%(A/B). [sina](https://finance.sina.com.cn/stock/aiassist/agqsjs/2026-04-28/doc-inhvzwqc1695678.shtml) 직접재료비가 원가의 73.46%. [xueqiu](https://xueqiu.com/5159371081/387469240) 탄탈 Target·링 "글로벌 공급망 극도로 긴장"(A, 年报). [sina](http://file.finance.sina.com.cn/211.154.219.97:9494/MRGG/CNSESZ_STOCK/2026/2026-4/2026-04-16/12096894.PDF) 한국 공장 투자 2.56억 위안(B). [xueqiu](https://xueqiu.com/5159371081/387469240)
- **판정:** Al·Ti·Cu **L3**. Ta·특수 합금은 L2~L3이며, 고순도 금속 원료는 **L2**.

#### (6) 300mm Wafer
- **沪硅产业(NSIG):** 300mm Capa 2024 65만 → 2025.6 75만 → 2026.6 100만 장/월. 2026년 말 120만 장/월 목표(A, 半年报). [sgpjbg +2](https://m.sgpjbg.com/labelsyh/huguichanye300mmguipianchanneng.html) 300mm 판매량 +90% 이상이지만 가격 하락으로 손실이 이어짐(B). [sgpjbg](https://m.sgpjbg.com/labelsyh/huguichanye300mmguipianchanneng.html) [sina](https://cj.sina.com.cn/articles/view/5597884738/14da8f142020027gjk) "메모리용 국산화율이 로직보다 높다"(A, IR 기록). [qq](https://file.finance.qq.com/finance/hs/pdf/2025/09/02/2025090215080241983420853.pdf)
- **西安奕斯伟(Eswin):** 2026.6 월 출하 100만 장 돌파(B). [10jqka](https://news.10jqka.com.cn/field/20260724/678411044.shtml) 招股书에 2026 중국 업체 출하 예상 295만 장/월(A). [sse](https://static.sse.com.cn/stock/disclosure/announcement/c/202508/002043_20250804_NH02.pdf)
- **판정:** 메모리 **L3**. 폴리실리콘·석영 도가니 원료 자립도는 본 조사에서 미확인.

#### (7) Process Gas
- **中船特气:** NF3 18,500t/년(글로벌 약 27%, 1위), WF6 2,000~2,230t/년(글로벌 공동 1위)(B). 2026H1 매출 19.04억 위안(약 3,808억 원, +83%)(B). [eastmoney](https://caifuhao.eastmoney.com/news/20260705211621277211050) [eastmoney](https://caifuhao2.eastmoney.com/news/20260726221314211346580)
- 국산화율 상충: 2025년 25%(集微咨询 보고서 A) vs 2025년 45%(集微咨询 보고서 B) vs 2024년 35%(光大). [163 +2](https://www.163.com/dy/article/L9TQ5VV00511RIVP.html) 같은 기관에서도 상충한다. 7N급은 20% 미만(C). [sohu](https://www.sohu.com/a/1092859756_166680) 고순도 C4F6·PH3/AsH3·Kr/Ne 혼합은 10% 미만(C). [eastmoney](https://caifuhao2.eastmoney.com/news/20260726221314211346580)
- **판정:** NF3·WF6·NH3 **L3~L4**. 고급 특수가스는 **L1~L2**.

---

## 5. 화웨이·SiCarrier 생태계 Deep Dive

### 5-1. 지분 구조도 (企查查·天眼查·安评 문서 기준)

```
深圳市国资委 (Shenzhen SASAC)
 └─100%─ 深圳市重大产业投资集团 (SZMII)                    [A: 企查查 via 新浪 2025.4]
      └─100%─ 深圳市深芯恒科技投资有限公司                  [A]
           └─100%─ 深圳市新凯来技术有限公司 (SiCarrier Technologies, 2021.8, 등록자본 15억 위안) [A]
                ├─95.6522%─ 深圳新凯来工业机器有限公司 (SiCarrier Industrial Machines, 2022.6.7, 등록자본 10억 위안)
                │            └─ 나머지 4.3478%: 深圳市均隆高新产业创业投资中心(有限合伙)   [A: 天眼查]
                ├─100%─ 珠海基石科技有限公司 (Zhuhai Cornerstone, 2022.6.30, 法人独资, 법정대표 余海) [A: 安评 2024.1]
                └─控股─ 长光集智光学科技有限公司 (Changguang Jizhi, 광학 부품)          [B: 与非网]

화웨이(Huawei): 등기상 지분 없음 [A]. BIS는 SiCarrier 별칭으로 "Huawei Starlight Engineering Department" 기재 [A].
  화웨이는 SiCarrier와 무관하다고 공개 부인 [B, Reuters 2025.5 인용].
  SiCarrier 계측 부문장 郦舟剑이 화웨이 무선 R&D 부사장 겸 직원지주 대표로 보도 [B/C].
  Nikkei는 화웨이 연관 인물 辛小红이 基石의 监事라고 보도 [B].
哈勃投资(Hubble): 위 지분 사슬 어디에서도 확인되지 않음.
```

**상충 해소: "SiCarrier 100% 보유" vs "SZMII 투자"**
- 두 표현은 **모순이 아니다.** 基石의 직접 모회사는 **深圳市新凯来技术有限公司(100%, 法人独资)**다(A, 安评 문서). [gdhc-shebaidu](http://www.gdhc-shebaidu.com/upload/iaEdW/file/202401/20240126155526_96003.pdf) SiCarrier Technologies는 深芯恒을 거쳐 SZMII가 간접 100% 보유한다(A). [nomadsemi](https://www.nomadsemi.com/p/what-sicarriers-president-said-at) [sina](https://finance.sina.com.cn/jjxw/2025-04-09/doc-inespyit2933694.shtml) 따라서 "SZMII 투자"는 최종 지배 관계를 표현한 것이다.
- 雪球의 "基石은 新凯来가 100% 보유" [xueqiu](https://xueqiu.com/5225397506/336461582) 는 방향은 맞지만, 新凯来**工业机器**(제조 법인)가 아니라 新凯来**技术**(지주)가 모회사다.
- 지분 변동 가능성: Reuters(2025.5, TrendForce 2025.5.14 인용)는 深圳市가 SiCarrier 자회사 지분 약 25%를 800억 위안 밸류(약 16조 원, 노광 자산 제외)로 매각해 1차로 28억 달러를 조달하는 방안을 검토 중이라고 보도했다(B). TrendForce(2025.9.5, 界面·科创板日报 인용)는 수주 100억 위안 이상(고객에 SMIC·Hua Hong 포함), 노광 제외 밸류 650억 위안이라고 보도했다(B). **현 시점 등기 재확인 필요.**

### 5-2. 장비 계열사

| 명칭 | 확인 내용 | 모회사 관계 | 등급 |
|---|---|---|---|
| 深圳新凯来工业机器 (Shenzhen SiCarrier Industrial Machines) | BIS 표기 "Shenzhen Xinkailai Industrial Machinery Co., Ltd.". SEMICON China 2025에서 식각·박막·확산·계측 등 공개(31종 주장) [federalregister](https://public-inspection.federalregister.gov/2024-28267.pdf) [techbuzzchina](https://chips.techbuzzchina.com/companies/sicarrier) | 新凯来技术 95.65% [sina](https://finance.sina.com.cn/jjxw/2025-04-09/doc-inespyit2933694.shtml) | A | [nomadsemi](https://www.nomadsemi.com/p/what-sicarriers-president-said-at) [federalregister](https://public-inspection.federalregister.gov/2024-28267.pdf)
| 上海宇量昇 (Shanghai Yuliangsheng) | 2024.12 Entity List 등재. 노광기 관련 보도. 利和兴은 "新凯来·华为·宇量昇 고객 업무 추진"이라고 답변 [federalregister](https://public-inspection.federalregister.gov/2024-28267.pdf) [toutiao](https://www.toutiao.com/article/7619570073388335622/) | **지분 관계 미확인** | A (BIS) / B | [federalregister](https://public-inspection.federalregister.gov/2024-28267.pdf)
| 长光集智光学 | 광학 핵심 부품. 新凯来 控股 [eefocus](https://www.eefocus.com/article/1908298.html) | 新凯来技术 控股 | B |
| 深圳掌格仪器 (Shenzhen Zhangge Instrument) | 2024.12 Entity List에 같은 묶음으로 등재 [federalregister](https://public-inspection.federalregister.gov/2024-28267.pdf) | 관계 미확인 | A | [federalregister](https://public-inspection.federalregister.gov/2024-28267.pdf)
| ZTOP/Zetop (광학 검사) | Digitimes/Bloomberg가 언급. [digitimes](https://www.digitimes.com/news/a20250515PD215/huawei-dram-dongguan-government-shenzhen.html) **중국어 법인명 미확인** | 미확인 | C |
| YourSend (공정 장비) | Digitimes/Bloomberg가 언급. **중국어 법인명 미확인** | 미확인 | C |

### 5-3. 연계 Fab

| 영문 (보도) | 중국어 (확인 수준) | 성격 | Entity List | SZMII 지분 | 등급 |
|---|---|---|---|---|---|
| PXW Semiconductor Manufactory | 鹏新旭 (BIS에 "Shenzhen Pengxinxu Technology"와 "PXW Semiconductor Manufactory"가 별도 기재) | 로직. SiCarrier 장비 테스트 Fab으로 보도 [americanaffairsjournal](https://americanaffairsjournal.org/2026/02/innovation-under-pressure-chinas-semiconductor-industry-at-a-crossroads/) | O (2024.12) | 투자 보도(B) | A/B | [trendforce](https://www.trendforce.com/news/2025/05/05/news-huawei-reportedly-builds-7nm-ai-chip-line-in-first-shot-at-making-its-own-high-end-chips/) [federalregister](https://public-inspection.federalregister.gov/2024-28267.pdf)
| Pensun Technology (PST) | 鹏芯微 (Digitimes는 "前 鹏新述/PXX"로 표기, [digitimes](https://www.digitimes.com/news/a20250515PD215/huawei-dram-dongguan-government-shenzhen.html) TechNode·Nikkei는 鹏芯微 = PengXinWei로 표기) | 28/40nm 파운드리 | Bloomberg 보도 | 투자 보도(B) | B, **명칭 상충** | [nomadsemi](https://www.nomadsemi.com/p/what-sicarriers-president-said-at) [x](https://x.com/WillRinehart/status/1863637557524959341)
| SwaySure (SWX) | 昇维旭 | DRAM. 前 Elpida 坂本幸雄. 140k wpm 계획설(C) [digitimes](https://www.digitimes.com/news/a20250515PD215/huawei-dram-dongguan-government-shenzhen.html) [hardforum](https://hardforum.com/threads/huawei-to-make-its-own-hbm-memory-via-unofficial-subsidiary-swaysure.2048719/) | O | 투자 보도(B) | A/B | [trendforce](https://www.trendforce.com/news/2025/05/05/news-huawei-reportedly-builds-7nm-ai-chip-line-in-first-shot-at-making-its-own-high-end-chips/) [federalregister](https://public-inspection.federalregister.gov/2024-28267.pdf)
| Pengjin High-Tech (PJHT) | 鹏进高科 | 전력·장비 | 2024.12 등재 **안 됨** | 미확인 | B | [x](https://x.com/WillRinehart/status/1863637557524959341)
| SiEn (Qingdao) | 芯恩(青岛) | MCU/PMIC | O | 미확인 | A | [federalregister](https://public-inspection.federalregister.gov/2024-28267.pdf)
| DGGMT | (东莞) 중국어명 미확인 | 화웨이 东莞 첨단 라인 추정 | – | 미확인 | C |
| JHICC | 福建晋华 | DRAM | O (기존 등재) | 해당 없음 | A | [federalregister](https://public-inspection.federalregister.gov/2024-28267.pdf)

> 연계 Fab의 SZMII 지분은 TechNode·Tom's Hardware(Nikkei 인용) 수준(B)이다. 본 조사에서 법인등기로 확인하지 못해 **A등급으로 상향하지 않았다.**

### 5-4. 생태계 효과 검증: Qual 기간이 실제로 단축되었나?

| 항목 | 증거 | 판정 |
|---|---|---|
| 투입: 장비 | SiCarrier 식각·계측(광학/X선) 장비 보유. [techbuzzchina](https://chips.techbuzzchina.com/companies/sicarrier) 노광은 宇量昇(양산 실적 미확인) | 존재 (A/B) |
| 투입: 평가 Fab | PXW가 SiCarrier 장비 평가 Fab으로 보도(B) [americanaffairsjournal](https://americanaffairsjournal.org/2026/02/innovation-under-pressure-chinas-semiconductor-industry-at-a-crossroads/) | 존재 (B) |
| 투입: 소재 | 基石: 10만㎡ 이상 건물, 3만㎡ 이상 고등급 클린룸, 연구거점 3곳(회사 주장). [cnstchem](https://www.cnstchem.com/) 직원 400명 이상(C) 또는 500~999명(구인 포털). [zhcpt](https://zhjy.zhcpt.edu.cn/web/index/company-info?id=65130) [pharmcube](https://bydrug.pharmcube.com/news/detail/03204b9d8f08d06ecf5de844751b9df8) 특허 42건(天眼查, 2025.5) [sina](https://cj.sina.com.cn/articles/view/1704103183/65928d0f02007xvuc?froms=ggmp) | 존재 (A/C) |
| 결과: 시생산 | 설립 2022.6.30 → 시생산 신고 2023.11.24 = **17개월** [gdhc-shebaidu](http://www.gdhc-shebaidu.com/upload/iaEdW/file/202401/20240126155526_96003.pdf) | 확인 (A) |
| 결과: Qual·양산·재주문 | 특정 팹 Qual·양산·재주문 **공개 근거 없음**. 八亿时空 IR은 "恒坤·珠海基石 모두 도약 준비 중"이라고만 언급 [dfcfw](https://pdf.dfcfw.com/pdf/H22_AN202501101641882323_1.pdf) | **미확인** |
| 역효과 | Entity List로 "EAR 대상 전 품목" 허가 필요(A). [federalregister](https://www.federalregister.gov/documents/2024/12/05/2024-28267/additions-and-modifications-to-the-entity-list-removals-from-the-validated-end-user-veu-program) 미국산 분석장비(KLA 계측·CD-SEM 등)·소프트웨어·일부 원료 조달에 제약 [추정] | 구조적 제약 | [federalregister](https://public-inspection.federalregister.gov/2024-28267.pdf)

**판정:** 장비·Fab·소재의 수직 루프 **인프라는 존재한다(A/B)**. 그러나 "Qual 기간 단축"이라는 **결과는 공개 데이터로 입증되지 않는다**. 17개월 만의 시생산 신고는 빠르지만, 이는 생산 인허가 속도이지 Qual 속도가 아니다.

---

## 6. 공정별 소재 맵과 Heat Map

### 6-1. 노광 경로 전제: ArF-i 멀티 패터닝

[사실] CXMT는 2026.9 G5 DRAM을 **EUV 없이 SAQP**로 양산한다고 발표했다(B, 서울경제). [sedaily](https://en.sedaily.com/finance/2026/10/14/chinas-cxmt-touts-next-generation-dram-with-no-specs-or) [추정] 따라서 4F²·차세대 노드의 Critical 레이어(Active, WL/BL, Storage node contact)는 ArF-i + SAQP/LELE 조합이 기본이다. 패턴 레이어 하나당 노광 횟수는 EUV 단일 노광 대비 2~4배로 늘어난다(SAQP는 노광 1회 + Spacer 증착·식각 2회, 컷 마스크 별도).

| 소재 수요 영향 (EUV 대비, 추정) | 배수 | 자립 단계 |
|---|---|---|
| ArF-i PR·Top coat | 레이어당 1.5~3배 | L2 |
| BARC/SOC/Si-ARC | 1.5~3배 | SOC/BARC L3, Si-ARC L1~L2 |
| Spacer용 ALD 산화막·질화막 전구체 | 2~4배 | L2~L3 |
| Hardmask (ACL, 탄소계) | 2배 이상 | L2 (추정) |
| 식각가스 (C4F6·C4F8 등) | 2배 이상 | 범용 L3, 고순도 L1~L2 |

### 6-2. 공정별 필요 소재 맵

| 공정 | 필수 신규·강화 소재 | 근거 |
|---|---|---|
| **4F² (VCT/VSG)** | 수직 채널용 에피/선택적 증착 전구체, Buried WL/BL용 금속(W·Mo·Ru) 전구체·Target, 고종횡비 식각가스, 신규 High-k(HZO 등) ALD 전구체, SAQP 소재 일체, 어레이-주변회로 W2W Hybrid bonding 소재 | Samsung ISSCC 2026 (VCT+W2W Hybrid bonding, B 2차), SK하이닉스 VLSI 2025 (4F² VG+CuA), CXMT IEDM 2023 (JL-GAA VCT + 육각 커패시터) [lavx](https://news.lavx.hu/article/cxmt-president-says-first-4f-dram-will-be-a-server-ddr5-rdimm-due-by-year-end) [tomshardware](https://www.tomshardware.com/pc-components/ssds/chinas-memory-maker-cxmt-reportedly-violates-us-export-rules-with-its-18nm-3d-dram-chipmaker-blatantly-presented-new-tech-at-industry-conference-report) |
| **HBM** | TSV용 Cu 도금액·Barrier/Seed Target, TSV Reveal/본딩용 CMP Slurry, Temporary bonding/Debonding 접착제, MUF/GMC/NCF/Underfill, Hybrid bonding용 SiCN 유전막 | 일반 공정 지식 + 华海诚科·联瑞 (C) [x](https://x.com/LinQingV/status/2056719347725603102) |
| **3D DRAM (추정)** | Si/SiGe 다층 에피 전구체, 고종횡비 식각·측면 리세스용 선택식각액·가스, 3D NAND와 유사한 계단(Staircase) 소재 | **추정** (IEDM·VLSI의 3D DRAM 발표 경향 기반) |
| **HBF (추정)** | 3D NAND 셀 소재(ONO·W 전구체 등, YMTC 공급망) + HBM 적층·본딩 소재 | **추정** |

### 6-3. Heat Map (소재 × 공정, 중국 자립 단계)

| 소재 | 4F² | HBM | 3D DRAM (추정) | HBF (추정) |
|---|---|---|---|---|
| ArF-i PR + Top coat | 🔴 L2 | 🟠 L2~L3 (베이스다이 레이어는 덜 Critical) | 🔴 L2 | 🟠 L2~L3 (YMTC 공급망) |
| KrF / i-line PR | 🟡 L2~L3 | 🟢 L3 | 🟡 L2~L3 | 🟢 L3 |
| SOC/BARC | 🟢 L3 | 🟢 L3 | 🟢 L3 | 🟢 L3 |
| Si-ARC / 고급 Ancillary | 🔴 L1~L2 | 🟡 L2 | 🔴 L1~L2 | 🟡 L2 |
| PR 원료 (수지·PAG·모노머) | 🔴 L1~L2 | 🔴 L1~L2 | 🔴 L1~L2 | 🔴 L1~L2 |
| CMP Slurry (세리아·W·Cu) | 🟢 L3 | 🟢 L3 (TSV/HB 양산) | 🟢 L3 | 🟢 L3 |
| CMP Pad | 🟢 L3 (추정) | 🟡 L2~L3 | 🟢 L3 (추정) | 🟢 L3 (추정) |
| Wet 범용 (인산·황산) | 🟢 L3~L4 | 🟢 L3~L4 | 🟢 L3~L4 (고선택 인산은 3D NAND에서 검증) | 🟢 L3~L4 |
| Functional Wet | 🟡 L2~L3 | 🟡 L2~L3 | 🟡 L2~L3 | 🟡 L2~L3 |
| 기존 ALD/CVD 전구체 | 🟢 L3 (UP Chem 기준) | 🟢 L3 | 🟡 L2~L3 | 🟢 L3 |
| 신규 ALD 전구체 (4F²/3D용) | 🔴 L1~L2 | – | 🔴 L1 | 🟠 L2 |
| Target (Al/Ti/Cu) | 🟢 L3 | 🟢 L3 | 🟢 L3 | 🟢 L3 |
| Target (Ta·신규 금속) / 고순도 금속 원료 | 🟠 L2 | 🟠 L2 (TSV Barrier) | 🟠 L2 | 🟠 L2 |
| 300mm Wafer | 🟢 L3 | 🟢 L3 | 🟡 L2~L3 (다층 에피 웨이퍼 미확인) | 🟢 L3 |
| 범용 가스 (NF3·WF6·NH3) | 🟢 L3~L4 | 🟢 L3~L4 | 🟢 L3~L4 | 🟢 L3~L4 |
| 고급 특수가스 (C4F6 고순도·도펀트·Kr/Ne) | 🔴 L1~L2 | 🟠 L2 | 🔴 L1~L2 | 🟠 L2 |
| Temp. bonding/Debonding | – | 🔴 L1 (미확인) | – | 🔴 L1 (미확인) |
| MUF/GMC/Underfill | – | 🔴 L1~L2 | – | 🔴 L1~L2 |
| Hybrid bonding 유전막·본딩 소재 | 🔴 L1~L2 (W2W) | 🔴 L1~L2 | 🔴 L1~L2 | 🔴 L1~L2 |
| **[장비] ArF-i 스캐너·유지보수** | ⚫ 장비 병목 | ⚫ | ⚫ | ⚫ |
| **[장비] Hybrid bonder** | ⚫ (W2W) | ⚫ | ⚫ | ⚫ |
| **[장비] Overlay/CD 계측** | ⚫ | ⚪ 보통 | ⚫ | ⚪ |

🟢 L3 이상 / 🟡 L2~L3 / 🟠 L2 / 🔴 L1~L2 / ⚫ 장비 병목

### 6-4. CXMT 4F² 사실 확인

| 항목 | 발표 (사실) | 확인된 양산 | 등급 |
|---|---|---|---|
| 발표 | 2026.10.10 集成电路与Chiplet大会에서 曹堪宇 총재가 "연내 4F² 기반 서버 DDR5 RDIMM 출시" 발표 [trendforce](https://www.trendforce.com/news/2026/10/12/news-cxmt-accelerates-4f%C2%B2-dram-push-eyes-year-end-server-ddr5-rdimm-launch/) | **미확인** | B (第一财经 via TrendForce) |
| 기술 | Vertical Surrounded Gate(VCT 계열). 4F² 관련 공개 특허 패밀리 300개 이상(曹堪宇는 "업계 선도 포트폴리오"라고 주장, TrendForce 2026.10.12. 같은 보도에서 CXMT는 2Q26 DRAM 매출 점유율 9.5%로 4위). IEDM 2023 8Gb 어레이(JL-GAA VCT + 육각 커패시터, 18nm half-pitch) | – | B |
| 적용 범위 | "일부만 4F² 적용 가능성"(머니투데이, 2026.10) [trendforce](https://www.trendforce.com/news/2026/10/12/news-cxmt-accelerates-4f%C2%B2-dram-push-eyes-year-end-server-ddr5-rdimm-launch/) | 미공개 | B |
| 사양·Capa·수율 | 속도·용량 **미공개**. 초기 수율 10% 미만 가능성(전문가 추정, 서울경제) [lavx](https://news.lavx.hu/article/cxmt-president-says-first-4f-dram-will-be-a-server-ddr5-rdimm-due-by-year-end) [sedaily](https://en.sedaily.com/finance/2026/10/14/chinas-cxmt-touts-next-generation-dram-with-no-specs-or) | 미공개 | C |
| 양산 시점 | 전문가들은 양산까지 최소 2년으로 추정 [sedaily](https://en.sedaily.com/finance/2026/10/14/chinas-cxmt-touts-next-generation-dram-with-no-specs-or) | – | C |
| 비교 | Samsung: ISSCC 2026(2월) 16Gb 4F²(VCT+W2W), 2028년 전후 양산 목표(Hardware Busters). 2027 Qual 일정은 출처 미확인. Micron CTO Scott DeBoer는 2026.10.21 웨비나에서 4F²가 "현재 로드맵에 없다"고 밝혔고, 발표 자료에는 "실행 가능한 스케일링 경로가 없다"고 적혀 있다(Nikkei via TrendForce 2026.10.22) | – | B/C |
| Hybrid bonding 병행 | 보도상 언급 | 미확인 | B |

**판정:** "출시 발표"(사실)와 "양산"(미확인)을 분리해야 한다. 2026년 말 제품이 나오더라도 샘플·한정 출하일 가능성이 높다(추정).

---

## 7. 가설 검증 (H1~H3)

### H1. DUV급 이상 PR은 "양산화" 보도는 있으나 Critical·첨단 노드 대량 공급과 장기 계약은 확인되지 않는다

| 지지 근거 | 반증 근거 |
|---|---|
| 南大光电 IR(A): ArF 2025 매출 2,000만 위안 이상, "만산 아님", 공식 Capa 50t | **鼎龙 2026.6.11 자발 공시(A):** ArF-i·KrF 수백 갤런을 "두 곳의 선두 팹 양산 라인에서 순조롭게 적용", 두 고객의 신규 주문 합계 근 1,000갤런(KrF+ArF 합산), 8종(ArF 4·KrF 4) 배치 수주 → **"양산 적용 + 재주문" 단계는 사실** |
| 恒坤 招股书(A): ArF 2024 매출 41만 위안, ArF-i "소량 공급" | 恒坤 ArF-i가 "선진 NAND·DRAM"에 적용된다고 기재(A) |
| 국산화율 ArF <1%(CEMIA, B) | – |
| 장기 계약(LTA) 공시 **없음**. Critical 레이어 적용 명시 **없음** | – |
| "99.7% 수율·500톤 달성"은 회사 IR과 모순(C, 기각) | – |
| i-line: 국산 공급 확대는 사실이나 국산화율 10~50%로 편차가 커서 "대량"의 정의 의존 | – |

**판정: 대체로 채택 (수정 채택).** ArF-i는 "샘플 → Qual → 양산 적용 → 재주문"까지 **1개사(鼎龙)가 확인**했다. 그러나 "Critical 레이어 대량 공급"과 "장기 계약"은 미확인이다. 물량은 300톤 라인 대비 약 1% 수준이다(추정). 基石의 ArF 양산 보도는 출처가 없는 头条 기사뿐이라 **실체가 없다(C, 기각)**.

### H2. 珠海基石科技는 SiCarrier 생태계 덕에 중국 PR 기업 중 가장 빠르게 개발 경쟁력을 확보 중이다

| 기업 | PR 사업 착수 (기준) | 첫 Qual/수주 | 양산·재주문 | 소요 (개월, 추정) | 등급 |
|---|---|---|---|---|---|
| 珠海基石科技 | 2022.6 설립 | **미확인** | **미확인** | 시생산 신고까지 17 | A (시생산만) |
| 鼎龙股份 | 약 2020~21 (KrF/ArF 연구개발 착수, 추정) | 2025 하반기 2종 수주 | 2026.6 재주문 | 약 48~60 | A/B |
| 南大光电 | 약 2017 (ArF 국가 프로젝트, 추정) | 약 2020 첫 통과 | 2024~25 연속 공급 | 약 36~48 (Qual까지) | A/B |
| 恒坤新材 | 2020 자산 개시 | 2020~22 SOC/BARC | KrF 2023~24 확대 | 약 24~36 (Ancillary) | A |
| 徐州博康 / 北京科华 / 上海新阳 | 본 조사에서 착수 시점 데이터 미확보 | – | – | – | 공백 |

| 간접 신호 | 基石 현황 | 등급 |
|---|---|---|
| 채용 | PHS 수지 합성(음이온·라디칼 중합) 엔지니어 채용 → **KrF 개발 시사(추정)**. "R&D의 60% 이상이 박사" | A (구인 공고) |
| 특허 | 42건(天眼查 2025.5) 또는 27건(2025 초 보도). CN118994991B(조성물·반도체 소자 제조, 등록), CN119978922A(반사방지 조성물, BARC형, 2025.5 공개) | B |
| 인허가 | 安评 竣工验收(2024.1) Phase 1 "소량산 라인". 별도 컬러(디스플레이) PR 프로젝트 존재 | A |
| 해외 인력 | 일본·한국·대만 인재 영입(Nikkei, 익명 근거) | B |
| 연계 Fab 공급 | **근거 없음** | – |
| 역효과 | EAR 전 품목 허가 필요 → 미국산 계측·분석장비·원료 조달 제약 [추정]. 구체 사례 보도는 없음 | A (규정) / 추정 |
| 주의 | 一部 목록에서 珦盛新材料(다른 ArF 기업)의 실적이 基石으로 오기됨 | – |

**판정: 기각 (근거 불충분).** 인프라 투입은 확인되지만(A), 결과(Qual·양산 개월 수)는 공개 데이터로 측정할 수 없다. 웹사이트가 주장하는 노드(0.18µm~65nm)는 i-line/KrF/ArF Dry 수준이다. 반면 鼎龙은 이미 ArF-i 재주문 단계다. **"가장 빠르다"는 주장은 현 시점에서 지지되지 않는다.** 단, 비공개 수직 루프의 특성상 실적이 공시되지 않았을 가능성은 남는다(반대 시나리오).

### H3. 7대 소재 중 PR 계열 제외 대부분은 4F²·HBM 기준 L3 이상에 도달했다

| 소재 | 4F² | HBM | H3 부합 |
|---|---|---|---|
| Slurry | L3 | L3 | O |
| Wet 범용 | L3~L4 | L3~L4 | O |
| Wafer | L3 | L3 | O |
| Target (범용 금속) | L3 | L3 | O |
| 범용 가스 | L3~L4 | L3~L4 | O |
| Precursor | 기존 L3 / **신규 L1~L2** | L3 | △ |
| 특수가스 고급 | **L1~L2** | L2 | X |
| HBM 패키징 소재 (7대 외 연계) | – | **L1~L2** | X |

**판정: 부분 채택.** 기존 공정의 연장선에 있는 소재는 L3다. 그러나 4F²·HBM이 새로 요구하는 전구체·특수가스·패키징 소재는 L1~L2다. 그리고 L3 소재 상당수도 원료(금속·PR 원료)는 L2에 머물러 **L4가 아니다.**

---

## 8. 전망 시나리오 (2028·2030)

### 8-1. 소재별 자립 단계 전망

| 소재 | 2026.10 | 2028 (작성자 전망) | 2030 (작성자 전망) | 회사·정부 목표 (참고) |
|---|---|---|---|---|
| ArF-i PR | L2 | L2~L3 (Non-critical 다수, 일부 Critical) | L3 | 전문가: "2025~2030 매년 3~5%p 상승"(光大, B) |
| PR 원료 | L1~L2 | L2 | L2~L3 | 鼎龙: "핵심 원료 100% 자산" 주장 |
| Si-ARC/Top coat | L1~L2 | L2 | L3 | 恒坤 募投 |
| Slurry/Pad | L3 | L3~L4 | L4 | 安集: 세리아 자산 |
| Wet | L3~L4 | L4 | L4 | – |
| 신규 전구체 | L1~L2 | L2 | L2~L3 | 雅克: 금속 원료 국산화 계획 |
| Target 원료 | L2 | L2~L3 | L3 | 江丰: 한국·국내 증설 |
| 300mm Wafer | L3 | L3 (공급과잉 위험) | L3~L4 | 沪硅: 2026 말 120만 장/월 | [sgpjbg](https://m.sgpjbg.com/labelsyh/huguichanye300mmguipianchanneng.html)
| 고급 특수가스 | L1~L2 | L2 | L2~L3 | 업계: 2030 국산화율 60% 목표(C) | [sohu](https://www.sohu.com/a/1092859756_166680)
| HBM 패키징 소재 | L1~L2 | L2 | L2~L3 | CXMT 상하이 후공정 2026 말 가동 계획(C) |

### 8-2. 정부 전략별 시나리오

| 시나리오 | 전제 | 2028 결과 | 확률 (작성자 판단) |
|---|---|---|---|
| **기본** | 大基金 3기 집행 지속, 일본 기술관리 점진 강화, 미 DUV 유지보수 부분 제한 | PR은 Non-critical 전환 완료, Critical은 이원화(국산+잔존 수입). 4F² 소량 양산 | 55% |
| **가속** | 일본 PR 실질 단공 + 미 MATCH 법안 시행 → 국산 강제 채택. 화웨이·SiCarrier 루프가 비공개로 성과 | 국산 ArF-i Critical 채택이 강제로 진행되지만 수율 손실을 감수. PR 원료 병목이 부각됨 | 25% |
| **지연** | 장비(ArF-i 스캐너·계측) 병목 심화, 국산 소재 품질 사고, 웨이퍼·가스 과잉 투자 조정 | 소재가 아니라 노광 능력이 상한을 결정. 4F² 양산 2029년 이후 | 20% |

---

## 9. 기업 프로파일 (요약)

| 기업 | 상장 | 핵심 사업 | 2025 핵심 수치 | 메모리 고객 | 자립 기여 | 리스크 |
|---|---|---|---|---|---|---|
| 鼎龙股份(Dinglong) | 300054.SZ | Pad·Slurry·PR | 2025.1~3분기 반도체 매출 15.34억 위안(약 3,022억 원), R&D율 14.41% | 선두 팹 2곳 (이름 비공개) | ArF-i 재주문 1호 | PR 물량 규모 작음 |
| 南大光电(NATA) | 300346.SZ | 특수가스·전구체·ArF PR | 매출 25.85억 위안(약 5,093억 원), 특수가스 15.36억 | YMTC 인증 보도(C) | ArF 6종 | ArF 매출 비중 미미 |
| 恒坤新材 | 科创板 (2025.11 상장) | SOC/BARC·KrF·TEOS | 2024 매출 5.48억 위안(약 1,041억 원). 최대 고객 의존 64% | 고객 A (국내 12인치 팹) | Ancillary L3 | 고객 집중, 수입 대리 비중 |
| 彤程新材 / 北京科华 | 603650.SH | KrF·i-line | 2025.1~3분기 매출 25.23억 위안(전사) | CXMT 공급 보도(C) | KrF 주력 | 수치 대부분 C |
| 珠海基石科技 | 비상장 | IC PR·컬러 PR·CMP·Wet·전구체(계획) | 비공개. 투자 8억 위안(2023, 약 1,472억 원) | 미확인 | 미확인 | Entity List |
| 安集科技(Anji) | 688019.SH | Slurry·Functional Wet | 매출 25.04억 위안(약 4,933억 원), 순이익 7.84억 | SMIC·YMTC·Hua Hong | L3~L4 | 원재료 비중 75% | [sina](https://finance.sina.com.cn/jjxw/2026-04-16/doc-inhuryef7835157.shtml)
| 兴福电子 | 688545.SH | 전자급 인산·황산 | 인산 점유율 69.7%(2023) | SMIC·YMTC·CXMT·SK하이닉스 | L3~L4 | 범용품 가격 | [nbd](https://www.nbd.com.cn/articles/2025-01-23/3733821.html) [dfcfw](https://pdf.dfcfw.com/pdf/H3_AP202501151641937375_1.pdf)
| 雅克科技(Yoke) | 002409.SZ | 전구체·PR(디스플레이)·특수가스 | 매출 86.11억 위안(약 1.70조 원), 전구체 21.11억 | SK하이닉스·CXMT | 전구체 L3 (한국 생산) | 한국 자산 의존, 금속 원료 | [laohucaijing](http://m.laohucaijing.com/news/index/150689/) [sina](https://stock.finance.sina.com.cn/stock/go.php/vReport_Show/kind/search/rptid/831668465275/index.phtml)
| 江丰电子(KFMI) | 300666.SZ | Target·부품 | 매출 46.04억 위안(약 9,070억 원), Target 28.50억 | 국내외 주요 팹 | L3 | 고순도 금속 원료 | [gz-cmc](https://huacheng.gz-cmc.com/pages/2026/06/02/1bd02ce7bb244c70803f92775552fb8f.html)
| 沪硅产业(NSIG) | 688126.SH | 300mm·SOI | 2026H1 매출 23.17억 위안(약 4,634억 원) | 메모리 비중 높음 | L3 | 가격 하락·적자 | [sina](https://cj.sina.com.cn/articles/view/5597884738/14da8f142020027gjk)
| 西安奕斯伟(Eswin) | 科创板 | 300mm | 월 출하 100만 장 이상(2026.6) | 국내 메모리 | L3 | 공급과잉 | [10jqka](https://news.10jqka.com.cn/field/20260724/678411044.shtml)
| 中船特气 | 688146.SH | NF3·WF6 | 2026H1 매출 19.04억 위안 | 국내외 (美光·SK하이닉스 공급 보도) | L3~L4 | 범용품 위주 | [163](https://www.163.com/dy/article/L9TQ5VV00511RIVP.html) [eastmoney](https://caifuhao2.eastmoney.com/news/20260726221314211346580)

---

## 10. 권고 (SK하이닉스 소재전략 관점)

1. **중국 소재 위협의 우선순위를 재정의할 것.** 단기(~2028) 가격 압력은 Slurry·Wet·범용 가스·웨이퍼에서 온다. 安集 Slurry 매출총이익률 58%, 沪硅의 가격 하락에도 이어지는 증설이 그 근거다. [sina](https://finance.sina.com.cn/jjxw/2026-04-16/doc-inhuryef7835157.shtml) [sina](https://cj.sina.com.cn/articles/view/5597884738/14da8f142020027gjk) PR·신규 전구체는 위협이 아니라 **중국 측 병목**이다.
2. **雅克/UP Chemical 노출도를 점검할 것.** 같은 전구체 공급사가 SK하이닉스와 CXMT 양쪽에 공급한다(B). [laohucaijing](http://m.laohucaijing.com/news/index/150689/) 기술 유출 관리와 공급 이원화 정책을 검토할 필요가 있다.
3. **CXMT 4F² 모니터링 지표를 고정할 것.** ① 제품 사양 공개 ② 서버 고객 Qual ③ 국산 ArF-i PR의 4F² 레이어 채택 공시(鼎龙·南大) ④ 장비(ArF-i 스캐너) 수급.
4. **데이터 공백을 보완할 것.** 基石의 Qual 실적, Temp. bonding 소재 중국 공급사, 3D DRAM용 다층 에피 웨이퍼, 연계 Fab 법인등기는 본 보고서에서 확인하지 못했다. 이 항목은 企查查 유료 조회와 현지 네트워크로 보강해야 한다.

---

## 11. Caveats

- **출처 등급 분포:** 핵심 판정(PR 단계, 지분 구조, Slurry·Wet·Wafer·Target 수치)은 A/B 근거다. 일본 단공·Capa 과장 수치·연계 Fab 지분 등 상당수는 C이므로 판정에 반영하지 않거나 상충으로 표기했다.
- **국산화율:** 물량·금액 기준이 출처마다 명시되지 않아 기준별로 분리 제시할 수 없었다. 대부분 금액 기준으로 추정된다.
- **환율:** 2025 연평균과 기준일 환율은 작성자 추정·가정치이므로 확정치로 교체해야 한다.
- **3D DRAM·HBF:** 모든 판정은 추정이다. CXMT·YMTC의 관련 소재 공시는 없다.
- **조사 한계:** 본 조사의 검색 예산 내에서 徐州博康·北京科华·上海新阳의 1차 공시, HBM 임시접착 소재 중국 공급사, 哈勃投资의 소재 포트폴리오는 확보하지 못했다.
- **출처 표기 방식:** 출처는 별도 목록 대신 각 표와 문장에 출처 기관·날짜·등급으로 인라인 표기했다.