# opencode-memory-harness

[English](README.md) | 한국어

opencode 에이전트의 작업 기억이 컨텍스트 compaction과 세션 경계를 넘어 유지되도록 하는 스킬
묶음과 작은 도구 하나입니다. oh-my-openagent의 계획 에이전트가 만든 계획을 따라 진행하는
프로젝트를 대상으로 합니다.

## 문제

한 세션의 창은 200k 토큰이고, 약 70%에서 자동 compaction이 일어나면 가장 앞쪽 맥락부터
사라집니다. 목표, 계획의 근거, 이미 배제한 접근 같은 것들입니다. oh-my-openagent는 todo 목록을
멈추지 않고 이어서 실행하기 때문에, 목록이 길면 어느 항목 한가운데서 compaction이 걸립니다.
에이전트가 자기 진행 상황을 직접 적은 메모는 쉽게 어긋나고, 끝나지 않은 일을 "완료"라고 적을
수도 있습니다.

## 발상

상태를 어긋날 수 없는 곳에 두고, 복구는 명령 하나로 합니다.

| compaction 후의 질문 | 답하는 곳 |
|---|---|
| 지금 무엇을 하고 있었나? | 브랜치: 계획의 한 잎 = `feature/<leaf>` |
| 끝났나? | `tests/gates/`의 gate 테스트. 통과 전까지 strict xfail로 표시 |
| 다음에 무엇을 하려 했나? | 마지막 체크포인트 커밋의 `Next:` 줄 |
| 무엇이 이미 실패했나? | 브랜치의 `Tried:` 줄 |
| 왜 이렇게 만들었나? | `docs/adr/`의 ADR |

compaction 후에도 에이전트가 따르는 AGENTS.md에는 "목표가 기억나지 않으면
`python tools/harness.py status`를 실행하라"는 규칙이 있습니다.

```text
Branch: feature/fit-mobility  (leaf: fit-mobility, 2 commit(s) since main)
Next: implement fit() in src/mobility.py via linearization; check test_fit_run07_within_5_percent
Tried (do not repeat):
  - scipy.optimize.curve_fit — scipy is not installed and external packages are not allowed
Open gates for this leaf (2, 1 blocked) in tests/gates/test_fit_mobility.py:
  - tests/gates/test_fit_mobility.py:16 test_fit_run07_within_5_percent — gate: fit within 5%
  - tests/gates/test_fit_mobility.py:27 test_77k — blocked: 77 K data from fab
Uncommitted: none
```

gate는 `@pytest.mark.xfail(strict=True, raises=(AssertionError, NotImplementedError))`로
표시합니다. 아직 못 맞춘 기준은 XFAIL로 남고, import 오류나 오타는 "아직 못 맞춤"으로 숨지
않고 실패로 드러나며, 통과하기 시작했는데 표시가 남아 있으면 표시를 뗄 때까지 실패합니다.

## 구성

| 구성 요소 | 언제 | 하는 일 |
|---|---|---|
| `session-start` | 계획 직후 한 번, 매 세션 시작 | 첫 실행: AGENTS.md 구역, 도구 복사, 계획 근거를 ADR로 기록. 이후: 상태 확인, 다음 잎 브랜치 열기, 코드보다 gate 테스트 먼저 작성 |
| `session-checkpoint` | 작업 중 모든 사건 경계 | 잎 브랜치에 `Next:` / `Tried:` / `Evidence:` / `Learned:` / `ADR:` 줄을 단 커밋 |
| `session-end` | 세션 끝 | 결정을 ADR로, 마지막 체크포인트, gate 실행, 병합 제안, 큐레이션 알림 |
| `context-curation` | 잎 약 5개 병합마다 | 커밋 줄, ADR, `.omo/` notepad를 수확해 오래 남을 사실을 승격하고 AGENTS.md 예산과 도달성 감사 |
| `tools/harness.py` | 언제든, compaction 직후 가장 먼저 | `status`, `gates`, `harvest`. 표준 라이브러리만 사용 |

에이전트는 `feature/*` 위에서는 자유롭게 커밋합니다. `main`으로의 병합은 항상 사용자 승인을
기다립니다. push, rebase, reset, stash, amend는 하지 않습니다.

## 작업 흐름

1. oh-my-openagent 계획 에이전트와 계획 파일이 만들어질 때까지 계획합니다.
2. 같은 세션에서 `session-start`를 실행합니다. 계획 경로를 담은 AGENTS.md 구역을 쓰고, 도구를
   복사하고, 계획의 근거를 ADR로 남기고, 설정 커밋을 제안합니다. 그리고 멈춥니다. 이 세션은
   이미 무겁기 때문입니다.
3. 새 세션에서 `session-start`를 다시 실행합니다. 다음 계획 항목의 `feature/<leaf>` 브랜치를
   열고 gate 테스트부터 씁니다.
4. 작업합니다. 체크포인트는 todo 항목(작업 최대 5개 뒤에 `checkpoint`)으로 들어가서, todo
   자동 진행 장치가 오히려 체크포인트를 강제합니다.
5. `session-end`가 결정을 기록하고 gate를 돌려 잎이 끝났으면 병합을 제안합니다.
6. 잎이 몇 개 쌓이면 `/tune-docs`로 `context-curation`을 실행합니다. 제안서를 먼저 쓰고, 항목별
   승인을 받은 것만 적용합니다.

opencode의 `/init`은 쓰지 마세요. 코드를 보면 알 수 있고 코드가 바뀌면 어긋나는 내용으로
AGENTS.md를 채웁니다.

## 설치

네 개의 스킬 폴더를 opencode 스킬 디렉터리에 복사합니다. 전역 또는 프로젝트별로 둘 수 있습니다.

```powershell
# 전역 (PowerShell)
$dst = "$HOME\.config\opencode\skills"
New-Item -ItemType Directory -Force $dst | Out-Null
Copy-Item -Recurse -Force skills\* $dst

# 또는 프로젝트별
$dst = "C:\path\to\project\.opencode\skills"
New-Item -ItemType Directory -Force $dst | Out-Null
Copy-Item -Recurse -Force skills\* $dst

# 선택: /tune-docs 명령
New-Item -ItemType Directory -Force "$HOME\.config\opencode\commands" | Out-Null
Copy-Item skills\context-curation\command\tune-docs.md "$HOME\.config\opencode\commands\"
```

복사한 뒤 opencode를 다시 시작해야 스킬이 인식됩니다. `tools/harness.py`는 `session-start`가
첫 실행 때 각 프로젝트에 복사합니다.

요구 사항: Python 3.8 이상, Git, 프로젝트의 pytest. 하네스 도구 자체는 Python 표준
라이브러리만 쓰고 네트워크 요청을 하지 않습니다.

## 저장소 구조

```text
skills/
├── session-start/        SKILL.md, scripts/harness.py, templates (AGENTS.md 구역, gate 테스트, ADR 0001)
├── session-checkpoint/   SKILL.md
├── session-end/          SKILL.md
└── context-curation/     SKILL.md, scripts/docs_inventory.py, references/, templates/, command/
docs/DESIGN.md            설계 계약과 그 근거
tests/                    표준 라이브러리 회귀 테스트
```

## 검증

```bash
python -m unittest discover -s tests -v
```

테스트는 실제 임시 Git 저장소에서의 status/harvest 도구, gate 정적 탐지, 큐레이션 감사, 그리고
스킬 자체의 크기 상한을 다룹니다. 각 세션 스킬은 자신이 보호하려는 바로 그 창에 로드되므로
약 1,500 토큰 아래로 유지해야 합니다.

## 라이선스

아직 정하지 않았습니다.
