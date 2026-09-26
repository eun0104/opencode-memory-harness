# 사용 안내서

[English](USAGE.md) | 한국어

이 문서는 opencode + oh-my-openagent 환경에서 하네스를 설치하고, 실제 프로젝트에서 처음부터
끝까지 쓰는 방법을 시나리오별로 설명합니다. 예시 출력은 모두 이 저장소의 도구로 실제 실행한
결과입니다.

## 목차

1. [한눈에 보기](#1-한눈에-보기)
2. [설치와 확인](#2-설치와-확인)
3. [시나리오 1 — 새 프로젝트: 계획 직후 설정](#3-시나리오-1--새-프로젝트-계획-직후-설정)
4. [시나리오 2 — 구현 시작: 새 세션에서 첫 잎 열기](#4-시나리오-2--구현-시작-새-세션에서-첫-잎-열기)
5. [시나리오 3 — 작업 도중: 체크포인트와 compaction](#5-시나리오-3--작업-도중-체크포인트와-compaction)
6. [시나리오 4 — 물리 이론 추가와 변경: 논문을 근거로](#6-시나리오-4--물리-이론-추가와-변경-논문을-근거로)
7. [시나리오 5 — 세션 마무리와 병합](#7-시나리오-5--세션-마무리와-병합)
8. [시나리오 6 — 외부 요인으로 막힌 기준](#8-시나리오-6--외부-요인으로-막힌-기준)
9. [시나리오 7 — 주기적 큐레이션](#9-시나리오-7--주기적-큐레이션)
10. [시나리오 8 — 며칠 뒤 복귀, 직접 상태 확인](#10-시나리오-8--며칠-뒤-복귀-직접-상태-확인)
11. [시나리오 9 — 기존 프로젝트에 적용](#11-시나리오-9--기존-프로젝트에-적용)
12. [승인 지점 정리](#12-승인-지점-정리)
13. [하네스 업데이트](#13-하네스-업데이트)
14. [문제 해결](#14-문제-해결)

## 1. 한눈에 보기

```text
[계획 세션]   Prometheus와 계획 → .omo/ 아래 계획 파일
              session-start (첫 실행) → AGENTS.md 구역, tools/harness.py, ADR, (이론 문서)
              → 설정 커밋 승인 → 세션 종료
[구현 세션]   session-start → feature/<잎> 브랜치 → gate 테스트 먼저 → 작업
              ↳ 체크포인트 커밋 반복 (compaction이 와도 status 한 번으로 복구)
              session-end → 결정 기록, gate 실행, 끝났으면 main 병합 제안
[잎 약 5개마다] /tune-docs → 제안서 → 항목별 승인 → 적용
```

| 궁금한 것 | 어디에 있나 |
|---|---|
| 무엇을 하기로 했나 | `.omo/` 아래 계획 파일 (경로는 AGENTS.md에 한 줄) |
| 지금 무엇을 하고 있나 | 브랜치 이름 `feature/<잎>` |
| 다 됐나 | `tests/gates/test_<잎>.py`의 gate 테스트 |
| 다음에 무엇을 하려 했나 | 마지막 체크포인트 커밋의 `Next:` 줄 |
| 무엇이 이미 실패했나 | 브랜치 커밋들의 `Tried:` 줄 |
| 왜 이렇게 만들었나 | `docs/adr/`의 ADR |
| 어떤 물리를 쓰고 있나 | `docs/theory.md` |

## 2. 설치와 확인

### 스킬 복사

프로젝트별 설치를 권합니다. 스킬 버전이 프로젝트와 함께 고정되고, 프로젝트 저장소에 커밋해
두면 나중에 어떤 규칙으로 작업했는지도 남습니다.

```powershell
# 하네스 저장소를 받아 둔 위치
cd C:\projects\opencode-memory-harness
git pull

# 대상 프로젝트에 설치
$proj = "C:\projects\my-device-model"
New-Item -ItemType Directory -Force "$proj\.opencode\skills" | Out-Null
Copy-Item -Recurse -Force skills\* "$proj\.opencode\skills\"

# 선택: /tune-docs 명령
New-Item -ItemType Directory -Force "$proj\.opencode\commands" | Out-Null
Copy-Item -Force skills\context-curation\command\tune-docs.md "$proj\.opencode\commands\"
```

설치 후 폴더 구조는 이렇게 됩니다.

```text
my-device-model\
└── .opencode\
    ├── skills\
    │   ├── session-start\SKILL.md
    │   ├── session-checkpoint\SKILL.md
    │   ├── session-end\SKILL.md
    │   └── context-curation\SKILL.md
    └── commands\tune-docs.md
```

모든 프로젝트에서 같은 버전을 쓰려면 `.opencode\skills\` 대신
`$HOME\.config\opencode\skills\`에 복사합니다. 두 곳에 모두 있으면 프로젝트별 설치가
우선하도록 의도한 것이므로, 헷갈리지 않게 한쪽만 두는 편이 좋습니다.

### 요구 사항

- Python 3.8 이상 (3.8~3.13에서 테스트함)
- Git
- 프로젝트 환경의 pytest (gate 테스트용). 하네스 도구 자체는 표준 라이브러리만 씁니다.

### 확인

opencode를 프로젝트 폴더에서 열고 이렇게 물어봅니다.

```text
사용할 수 있는 스킬 목록을 보여줘.
```

`session-start`, `session-checkpoint`, `session-end`, `context-curation` 네 개가 보이면
됩니다. 보이지 않으면 [문제 해결](#14-문제-해결)을 보세요.

## 3. 시나리오 1 — 새 프로젝트: 계획 직후 설정

**언제:** Prometheus(계획 에이전트)와 논의해 계획 파일이 만들어진 직후, **같은 세션**에서.

계획 세션에는 "왜 이 접근을 택했고 무엇을 버렸는지"가 대화로만 남아 있습니다. 세션을 닫기
전에 그것을 파일로 옮기는 것이 이 단계의 목적입니다.

**입력:**

```text
session-start 스킬로 하네스를 설정해줘.
```

**에이전트가 하는 일:**

1. 방금 만든 계획 파일 경로를 대화에서 가져옵니다(계획을 다시 읽지 않습니다).
2. AGENTS.md에 하네스 구역을 씁니다. 기억 규칙과 계획 경로가 들어가며, compaction 후에도
   유지되는 복구의 닻입니다. AGENTS.md가 이미 있으면 표시 주석 사이에 덧붙이기만 합니다.
3. `tools/harness.py`를 복사합니다.
4. `docs/adr/0001-record-decisions-as-adrs.md`와, 계획 대화에서 정한 결정마다 ADR을
   씁니다(택한 접근, 버린 대안과 이유, 사용자가 말한 제약).
5. 계획이 물리 이론이나 방정식을 다루면 `docs/theory.md`를 만들고, AGENTS.md에 인용 규칙
   한 줄을 넣습니다([시나리오 4](#6-시나리오-4--물리-이론-추가와-변경-논문을-근거로) 참고).
6. Git을 확인합니다. 저장소가 아니면 `git init`을 할지 묻고, 계획 파일이 git-ignore되어
   있으면 알려줍니다. `.gitignore`에 `__pycache__/`, `.pytest_cache/`를 넣습니다.
7. `main`에 설정 커밋을 제안합니다. 올릴 파일 경로와 메시지를 보여주고 **승인을 기다립니다**.
8. todo를 모두 정리하고, 구현은 새 세션에서 시작하라고 안내한 뒤 멈춥니다.

**승인할 것:** `git init`(필요할 때), 설정 커밋의 파일 목록과 메시지.

**결과:**

```text
AGENTS.md                              ← 하네스 구역 (약 500 토큰)
tools/harness.py
docs/adr/0001-record-decisions-as-adrs.md
docs/adr/0002-....md                   ← 계획의 근거
docs/theory.md                         ← 이론을 다룰 때만
.gitignore
```

**여기서 세션을 닫으세요.** 계획 세션은 이미 무겁습니다.

> opencode의 `/init`은 실행하지 마세요. 코드를 보면 알 수 있고 코드가 바뀌면 어긋나는
> 내용으로 AGENTS.md를 채웁니다.

## 4. 시나리오 2 — 구현 시작: 새 세션에서 첫 잎 열기

**언제:** 설정 후 새 세션, 또는 이전 잎을 병합한 뒤 새 세션.

**입력:**

```text
session-start 해줘.
```

**에이전트가 하는 일:**

1. `python tools/harness.py status`를 실행합니다. `main`에 있으므로 활성 잎이 없습니다.

   ```text
   Branch: main
   Uncommitted: none
   Note: on 'main', not a feature/* branch: no active leaf
   ```

2. 병합 안 된 `feature/*` 브랜치가 있으면 그것을 이어갈지 묻습니다.
3. 계획을 읽고 다음 항목을 골라 `git switch -c feature/fit-mobility`로 브랜치를 엽니다.
   브랜치 이름은 영문 소문자와 `-`를 씁니다.
4. **코드보다 먼저** `tests/gates/test_fit_mobility.py`에 합격 기준을 테스트로 씁니다.

   ```python
   import pytest

   GATE = dict(strict=True, raises=(AssertionError, NotImplementedError))


   @pytest.mark.xfail(**GATE, reason="gate: low-field limit equals mu0")
   def test_low_field_limit():
       from src.mobility import mu
       assert abs(mu(1e-9, mu0=1400.0, Ec=18.0) - 1400.0) < 1e-6


   @pytest.mark.xfail(**GATE, reason="gate: fit to data/run07.csv within 5% at every point")
   def test_fit_run07_within_5_percent():
       raise NotImplementedError


   @pytest.mark.xfail(strict=True, reason="blocked: 77 K data from fab")
   def test_77k():
       raise NotImplementedError
   ```

5. 모든 gate가 XFAIL인지 확인합니다.

   ```text
   XFAIL tests/gates/test_fit_mobility.py::test_low_field_limit - gate: low-field limit equals mu0
   XFAIL tests/gates/test_fit_mobility.py::test_fit_run07_within_5_percent - gate: fit to data/run07.csv within 5% at every point
   XFAIL tests/gates/test_fit_mobility.py::test_77k - blocked: 77 K data from fab
   3 xfailed in 0.02s
   ```

6. `checkpoint: gates for fit-mobility` 커밋을 남기고, todo 목록(작업 최대 5개 +
   `checkpoint`)을 만든 뒤 잎, 다음 행동, 남은 gate를 세 줄로 보고하고 작업을 시작합니다.

**사용자가 할 일: gate 테스트를 검토하세요.** 이 파일이 "완료"의 정의입니다. 허용 오차가
적절한지, 빠진 기준은 없는지 여기서 보는 것이 이후 어떤 검토보다 효과가 큽니다. 나중에
에이전트가 기준을 느슨하게 바꾸려면 ADR을 먼저 써야 합니다.

## 5. 시나리오 3 — 작업 도중: 체크포인트와 compaction

### 체크포인트

에이전트는 사건이 생길 때마다 feature 브랜치에 체크포인트 커밋을 남깁니다. gate 하나를
통과하거나, 대안 중 하나를 고르거나, 어떤 접근이 실패하거나, 다음 todo로 넘어갈 때입니다.
승인 없이 커밋하며, 이것이 compaction을 견디는 장치입니다.

```text
checkpoint: mu(E) implemented, low-field gate closed

Next: implement fit() in src/mobility.py by linear least squares on 1/mu = 1/mu0 + E/(mu0*Ec); run test_fit_run07_within_5_percent

Tried: scipy.optimize.curve_fit — scipy is not available on the internal network

Learned: [gotcha] run07.csv mobility column is in cm2/Vs, not m2/Vs
```

| 줄 | 뜻 |
|---|---|
| `Next:` | 맥락 없이도 바로 시작할 수 있는 다음 행동 (필수) |
| `Tried:` | 실패한 접근과 이유. 다시 시도하지 않음 |
| `Evidence:` | 테스트로 만들 수 없는 기준을 닫은 관측값 |
| `Learned:` | `[gotcha]` 뜻밖의 동작, `[candidate]` 오래 남길 만한 사실 |
| `ADR:` | 이 체크포인트에서 쓴 ADR 경로 |

직접 남기게 하려면 이렇게 입력합니다.

```text
체크포인트 남겨.
```

### gate가 닫히는 방식

구현이 기준을 맞추면 strict 모드 때문에 xfail 표시가 남아 있는 한 테스트가 실패합니다.

```text
FAILED tests/gates/test_fit_mobility.py::test_low_field_limit - [XPASS(strict...
```

여기서 FAILED는 "기준을 맞췄으니 표시를 떼라"는 뜻입니다. 에이전트는 표시를 떼고 다시 돌려
통과를 확인한 뒤 같은 커밋에 담습니다. 기준을 못 맞춘 채 "완료"라고 말할 수 없고, 맞췄는데
표시를 남겨 둘 수도 없습니다. 오타나 import 오류는 `raises=` 덕분에 "아직 못
맞춤"으로 숨지 않고 FAILED로 드러납니다.

### compaction이 왔을 때

AGENTS.md 규칙에 따라 에이전트는 목표가 기억나지 않으면 가장 먼저 상태를 확인합니다.

```text
Branch: feature/fit-mobility  (leaf: fit-mobility, 2 commit(s) since main)
Next: implement fit() in src/mobility.py by linear least squares on 1/mu = 1/mu0 + E/(mu0*Ec); run test_fit_run07_within_5_percent
  from 956a661e18 "checkpoint: mu(E) implemented, low-field gate closed"
Tried (do not repeat):
  - scipy.optimize.curve_fit — scipy is not available on the internal network
Open gates for this leaf (2, 1 blocked) in tests/gates/test_fit_mobility.py:
  - tests/gates/test_fit_mobility.py:12 test_fit_run07_within_5_percent — gate: fit to data/run07.csv within 5% at every point
  - tests/gates/test_fit_mobility.py:17 test_77k — blocked: 77 K data from fab
Uncommitted: none
```

compaction 후 에이전트가 헤매거나 이미 실패한 방법을 다시 시도하면 이렇게 입력하세요.

```text
python tools/harness.py status 를 실행하고, Next부터 이어가. Tried에 있는 방법은 쓰지 마.
```

## 6. 시나리오 4 — 물리 이론 추가와 변경: 논문을 근거로

`docs/theory.md`는 지금 적용 중인 물리를 담는 **하나의 살아 있는 문서**입니다. 모델이 바뀌면
코드를 바꾼 그 체크포인트에서 해당 부분을 제자리에서 다시 씁니다. "업데이트:" 메모를 덧붙이지
않으므로, 언제 읽어도 현재 모델을 한 흐름으로 설명합니다.

### 새 메커니즘 접목

논문 PDF를 함께 주는 것이 가장 좋습니다.

```text
첨부한 논문의 식 (8)을 이동도 모델에 접목해줘. 온도 의존성을 추가하는 거야.
```

에이전트는 구현과 함께 같은 체크포인트에서 `docs/theory.md`를 갱신합니다.

```markdown
### EQ-mu-T — temperature scaling of mu0

$$ \mu_0(T) = \mu_0(300) (T/300)^{-\alpha} $$

- Symbols and units: T [K], alpha dimensionless
- Assumptions: phonon-limited scattering dominates
- Valid for: 200–400 K
- Source: [R2] eq. (8), p. 12
- Implementation: `src/mobility.py::mu0_of_T`
- Verification: `tests/gates/test_mu_temperature.py::test_eq_mu_t_300k_limit`
- Status: adopted

## References

- [R2] <저자>, "<제목>," <학술지> <권>, <쪽> (<연도>).
  DOI: <PDF에서 읽은 DOI> — checked: pdf 2026-09-27
```

### 근거 문헌 규칙 (거짓 근거 방지)

- DOI, arXiv ID, ISBN, 사내 보고서 번호는 **원문에서 직접 읽었거나 사용자가 준 것만** 씁니다.
  기억에서 꺼낸 식별자는 금지입니다. 그럴듯하게 생긴 기억 속 DOI가 바로 거짓 근거의
  전형이기 때문입니다.
- 어떻게 확인했는지 남깁니다: `checked: pdf`(PDF에서 읽음), `checked: user`(사용자가 줌),
  `checked: online`(온라인에서 확인).
- 확인할 수 없으면 `[TBD: source]`로 두고 미해결 질문에 올립니다. 나중에 DOI를 알려주시면
  `checked: user`로 채웁니다.

```text
R2의 DOI는 10.xxxx/xxxxx 야. 채워줘.
```

사내망에서는 대부분 `checked: pdf` 또는 `checked: user`가 됩니다.

### 식을 교체하거나 뺄 때

에이전트는 먼저 옛 형태와 교체 이유를 ADR로 남기고, 그다음 `docs/theory.md`를 제자리에서
다시 씁니다. 옛 식은 이론 문서에서는 사라지지만 ADR과 Git 이력에 남습니다.

### 자동 검사

큐레이션 감사(`docs_inventory.py`)가 이론 문서를 기계적으로 검사합니다. 식마다 근거, 구현,
검증 항목이 있는지, DOI 형식과 확인 경로, 인용한 문헌이 목록에 있는지, 적어 둔 구현 함수와
검증 테스트가 실제로 있는지 봅니다. 아직 구현하지 않은 함수를 가리키고 확인 경로 없는 DOI가
있는 문서라면 이렇게 보고합니다.

```text
## 8. Theory document

`docs/theory.md`: 2 equation(s), 2 reference(s).

**Problems (fix before trusting the document):**
- EQ-mu-T: Implementation `src/mobility.py::mu0_of_T` not defined in that file
- [R2]: identifier without 'checked: pdf | user | online'

Open `[TBD]` links: EQ-mu-T: valid for; EQ-mu-T: verification.
```

## 7. 시나리오 5 — 세션 마무리와 병합

**입력:**

```text
오늘은 여기까지. 마무리해줘.
```

**에이전트가 하는 일 (`session-end`):**

1. 이번 세션의 결정 중 ADR이 없는 것을 ADR로 남깁니다.
2. 마지막 체크포인트를 남깁니다. `Next:`는 이 대화를 전혀 모르는 다음 세션이 바로 시작할 수
   있을 만큼 구체적으로 씁니다.
3. gate 테스트를 돌립니다. 오래 걸리는 테스트는 먼저 묻습니다.
4. 모델 코드를 바꿨다면 `docs/theory.md`의 구현·검증 링크와 모델 개요를 확인하고, 남은
   `[TBD]`를 보고합니다.
5. 모든 `gate:`가 닫혔으면(또는 `blocked:`만 남았으면) main 병합을 제안합니다.
6. 큐레이션 시점이면 `/tune-docs`를 제안만 합니다.
7. todo를 정리하고 세 줄로 보고합니다: 한 일, `Next:`, 병합 여부.

**승인할 것:** main 병합. 에이전트는 `git merge --no-ff`로 병합하며, 체크포인트 기록이
사라지지 않도록 squash하지 않습니다.

**에이전트가 하지 않는 것:** push. 원격 저장소를 쓴다면 직접 올리세요.

```powershell
git push
```

gate가 남아 있으면 병합을 제안하지 않고, 다음 세션이 같은 브랜치에서 이어갑니다.

## 8. 시나리오 6 — 외부 요인으로 막힌 기준

측정 데이터, 장비, 다른 팀을 기다리는 기준은 `blocked:`로 표시합니다.

```python
@pytest.mark.xfail(strict=True, reason="blocked: 77 K data from fab")
def test_77k():
    raise NotImplementedError
```

- `status`는 막힌 gate를 따로 셉니다: `Open gates for this leaf (2, 1 blocked)`.
- `blocked:`만 남으면 승인 하에 병합할 수 있습니다. 막힌 gate는 main에서 계속 열린 상태로
  보입니다.
- 데이터가 오면 그 gate를 넘겨받는 새 잎을 엽니다.

```text
77 K 데이터가 data/run11_77K.csv 로 들어왔어. 막혀 있던 test_77k를 새 잎으로 진행하자.
```

## 9. 시나리오 7 — 주기적 큐레이션

**언제:** `session-end`가 제안할 때(잎 약 5개 병합, `Learned:` 3줄 이상 등), 또는 에이전트가
같은 것을 자꾸 잊는다고 느낄 때.

**전제:** 새 세션, `main` 브랜치, 커밋 안 된 변경 없음.

**Pass A — 제안:**

```text
/tune-docs
```

에이전트는 감사를 돌리고, 체크포인트 줄·ADR·`.omo/` notepad를 수확해, 오래 남을 사실을 골라
`docs/_tuning-proposal.md`에 제안서를 쓰고 **멈춥니다**. 다른 파일은 건드리지 않습니다.

**검토:** 항목 ID로 답합니다.

```text
A1, B1, B3, C1 승인. B2는 거절 — 한 번만 나온 얘기야. D1은 보류.
```

**Pass B — 적용 (가능하면 새 세션):** 에이전트가 `feature/curation-<날짜>` 브랜치에서 승인된
항목만 적용하고, 재구성을 ADR로 남기고, `docs/.curation-state.json`을 갱신하고, 제안서를
지운 뒤 감사를 다시 돌려 확인합니다. 마지막으로 main 병합을 제안합니다.

**승인할 것:** 제안서 항목별, 큐레이션 브랜치 병합.

## 10. 시나리오 8 — 며칠 뒤 복귀, 직접 상태 확인

에이전트 없이 PowerShell에서 직접 확인할 수 있습니다.

```powershell
cd C:\projects\my-device-model

python tools\harness.py status                    # 지금 어디, 다음 행동, 남은 gate
python tools\harness.py gates --all               # 모든 잎의 열린 gate
python tools\harness.py harvest --keys Learned    # 지금까지 배운 것들
python tools\harness.py harvest --keys Tried      # 실패한 접근들
git log --oneline --first-parent main             # 병합된 잎 목록
```

그다음 opencode에서 `session-start 해줘`로 이어가면 됩니다.

## 11. 시나리오 9 — 기존 프로젝트에 적용

- **AGENTS.md가 이미 있으면** `session-start`가 기존 내용은 그대로 두고 끝에 하네스 구역만
  덧붙입니다. 예전 `/init` 결과가 많이 들어 있다면 첫 큐레이션에서 줄이는 것을 제안받게
  됩니다.
- **계획 파일이 없으면** 먼저 Prometheus와 계획을 세우세요. `session-start`는 계획이 없으면
  계획부터 할지 묻고 멈춥니다.
- **기존 테스트는 그대로** 둡니다. gate는 `tests/gates/` 아래에만 생깁니다.
- 진행 중인 작업이 있다면 먼저 커밋하거나 정리한 뒤 시작하는 편이 깔끔합니다.

## 12. 승인 지점 정리

| 에이전트가 알아서 함 | 사용자 승인이 필요함 | 하지 않음 |
|---|---|---|
| `feature/*` 브랜치 생성 | `git init` | push |
| 체크포인트 커밋 | `main`의 설정 커밋 | rebase, reset, stash, amend |
| gate 테스트 작성, 통과 시 표시 제거 | `main` 병합 | `git add -A`, `git add .` |
| ADR 작성 | 큐레이션 제안 항목 적용 | 브랜치 삭제 (요청 시에만) |
| `docs/theory.md` 갱신 | 큐레이션 브랜치 병합 | opencode `/init` |
| `status`, `gates`, `harvest` 실행 | 느린 테스트 실행 (먼저 물어봄) | 기억에서 DOI 작성 |
| | 계획 파일이 git-ignore일 때의 처리 | 설치된 스킬 파일 수정 |

## 13. 하네스 업데이트

하네스 저장소가 갱신되면 두 가지를 복사합니다. `tools/harness.py`는 프로젝트마다 복사본이
있으므로 함께 바꿔야 합니다.

```powershell
cd C:\projects\opencode-memory-harness
git pull

$proj = "C:\projects\my-device-model"
Copy-Item -Recurse -Force skills\* "$proj\.opencode\skills\"
Copy-Item -Force skills\session-start\scripts\harness.py "$proj\tools\harness.py"
```

AGENTS.md의 하네스 구역은 자동으로 바뀌지 않습니다. 새 버전의
`skills\session-start\templates\agents-section.md`와 달라진 점이 있으면 큐레이션 때 참고하거나
직접 반영하세요.

## 14. 문제 해결

**스킬이 목록에 보이지 않는다.**
경로가 `<프로젝트>\.opencode\skills\<이름>\SKILL.md`인지 확인하세요(`skills` 복수형). 폴더
이름과 SKILL.md 첫머리의 `name:`이 같아야 합니다. opencode는 작업 폴더에서 Git 저장소 최상위까지
올라가며 스킬을 찾습니다. 그래도 안 보이면 opencode를 다시 시작하세요.

**`/tune-docs`가 없다.**
`<프로젝트>\.opencode\commands\tune-docs.md`(또는 `$HOME\.config\opencode\commands\`)에
있는지 확인하세요. 명령 없이도 "context-curation 스킬을 실행해줘"로 같은 일을 할 수 있습니다.

**에이전트가 체크포인트를 안 남기고 길게 달린다.**
AGENTS.md에 `<!-- memory-harness:start -->` 구역이 있는지 확인하세요. 있다면 이렇게
상기시킵니다: "AGENTS.md 규칙대로 todo는 5개 + checkpoint로 다시 짜고, 지금 체크포인트 남겨."

**에이전트가 main에서 커밋하려 한다.**
체크포인트 스킬은 `feature/*`가 아니면 커밋하지 않고 알려주게 되어 있습니다. 거절하고
"session-start로 잎 브랜치를 먼저 열어"라고 하세요.

**`status`가 이상하게 나온다.**

| 표시 | 뜻과 조치 |
|---|---|
| `detached HEAD at ...` | 브랜치가 아닌 커밋에 있음. `git switch <브랜치>` |
| `base 'main' not found` | 기본 브랜치가 `master` 등. 하네스는 `main`을 가정함. 이름을 바꾸거나(`git branch -m master main`) `--base master`로 실행 |
| `gate file ... is missing` | 잎 브랜치인데 gate가 없음. 에이전트에게 gate부터 쓰게 함 |
| `xfail is not strict` 경고 | `strict=True`가 빠진 표시. 통과해도 열린 것으로 남으므로 고쳐야 함 |
| `no raises=...` 경고 | import 오류도 "아직 못 맞춤"으로 숨을 수 있음. `raises=`를 추가 |

**gate 테스트가 XFAIL이 아니라 FAILED로 나온다.**
대개 import 오류나 오타입니다. `raises=(AssertionError, NotImplementedError)` 덕분에 숨지 않고
드러난 것이니 테스트나 코드를 고치면 됩니다. `XPASS(strict)`는 기준을 맞췄는데 표시가 남은
것이므로 표시를 떼면 됩니다.

**감사가 `identifier without 'checked: ...'`를 보고한다.**
출처 확인 없이 식별자가 적혀 있다는 뜻입니다. PDF를 주거나 직접 확인한 DOI를 알려주세요.
확인할 수 없으면 `[TBD: source]`로 바꾸는 것이 맞습니다.

**PowerShell에서 커밋 메시지가 깨진다.**
큰따옴표 안의 `$`와 백틱(`` ` ``)은 PowerShell이 해석합니다. 커밋 메시지에서 피하거나 작은
따옴표를 쓰세요.

**에이전트가 `/init`을 제안한다.**
거절하세요. AGENTS.md는 기억 규칙과 경로 안내만 담는 자리입니다. 필요한 사실은 큐레이션이
근거를 갖춰 올립니다.
