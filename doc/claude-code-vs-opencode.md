# Claude Code Agent vs OpenCode Agent 비교 · 설치 · 작성 가이드

> 기준일: 2026-07-09 · 터미널 기반 CLI 코딩 에이전트 비교

---

## 1. 한눈에 보기

| 항목 | **Claude Code** | **OpenCode** |
|---|---|---|
| 개발/유지 | Anthropic (공식) | SST → Anomaly + 오픈소스 커뮤니티 |
| 라이선스 | 상용(비공개) | 오픈소스 (GitHub 160K+ stars) |
| 구현 언어 | — (네이티브 바이너리) | Go (Bubble Tea TUI) |
| 모델 | Anthropic Claude 계열 (Opus/Sonnet/Haiku) | 75+ 프로바이더 (Anthropic, OpenAI, Google, xAI, DeepSeek, Mistral, Ollama 등) |
| 과금 | 구독($20~$200/월) 또는 API 종량제 | SW 무료, 모델 API 비용만 지불 (로컬 모델은 $0) |
| 컨텍스트 파일 | `CLAUDE.md` | `AGENTS.md` (개방형 표준) |
| 확장 | MCP, 서브에이전트, 훅, 스킬, 플러그인 | MCP, 커스텀 에이전트, 프로바이더 확장 |
| 대상 | 최신 모델 + 완성도/편의 우선 | 모델 자유·저비용·개방성 우선 |

**한 줄 요약:** 최신 Claude 모델과 매끄러운 통합·완성도를 원하면 **Claude Code**, 모델 선택의 자유와 저비용·오픈소스를 원하면 **OpenCode**.

---

## 2. 기능·성능 비교

### 2.1 아키텍처 / 모델

**Claude Code**는 Anthropic이 만든 공식 도구로, Node 패키지가 실제로는 런타임에 Node를 쓰지 않는 네이티브 바이너리를 내려받아 실행한다. Anthropic의 Claude 모델(Opus / Sonnet / Haiku)에 최적화돼 있어 모델-도구 간 통합이 가장 매끄럽다.

**OpenCode**는 Go로 작성된 오픈소스 도구로, [Models.dev](https://models.dev) 카탈로그를 통해 75개 이상의 프로바이더에 연결된다. Anthropic, OpenAI, Google Vertex, Amazon Bedrock, Groq는 물론 Ollama·LM Studio·llama.cpp 로컬 모델까지 OpenAI 호환 레이어로 사용할 수 있다. 대화·세션은 로컬 SQLite에 저장된다.

### 2.2 에이전트 구조

Claude Code는 메인 에이전트가 계획·통합을 맡고, **서브에이전트**가 코드 리뷰·테스트·프런트엔드 QA·보안 점검 같은 한정된 작업을 각자의 컨텍스트 윈도우·프롬프트·권한으로 수행한다. v2.1.198(7/1) 기준 서브에이전트는 기본 백그라운드로 실행되며, worktree 작업 완료 시 커밋·푸시·draft PR 생성까지 가능하다.

OpenCode는 **Build**와 **Plan** 두 개의 기본 에이전트를 내장하며 `Tab` 키로 전환한다. Vim 유사 편집기, LSP 통합(코드 인텔리전스), 도구 실행 통합을 제공한다.

### 2.3 확장성

| 확장 기능 | Claude Code | OpenCode |
|---|---|---|
| MCP 서버 | ✅ (GitHub, 브라우저, DB, 배포 API 등) | ✅ |
| 훅(Hooks) | ✅ 세션 시작/도구 호출/중단/서브에이전트 완료 등 라이프사이클 이벤트 | 제한적 |
| 스킬(Skills) | ✅ 재사용 지식·워크플로우 | — |
| 슬래시 커맨드 | ✅ 커스텀 지원 | ✅ |
| 플러그인 | ✅ 스킬·서브에이전트·커맨드·훅·MCP를 묶은 설치 단위 | 프로바이더·설정 중심 |

Claude Code는 훅으로 "중단 전 테스트 실행", "생성 파일 편집 차단", "커밋 전 lint 검사", "의존성 변경 후 보안 스캔" 같은 프로젝트 규칙 강제가 강점이다.

### 2.4 성능·비용 관점

100시간 사용 비교 등 커뮤니티 리뷰 종합:

- **Claude Code**: Opus 등 최상위 모델을 구독가로 쓸 수 있고 완성도·편의성이 높다. 기본 요금이 상대적으로 높다.
- **OpenCode**: 기본 비용이 낮고 모델 전환이 자유롭다. 다만 2026년 5월 기준 Claude Pro/Max 구독을 OpenCode 안에서 쓰는 것은 공식 지원되지 않는다(별도 API 키 필요).

---

## 3. 설치 방법

### 3.1 Claude Code

**요구사항**
- OS: macOS 13+ / Ubuntu 20.04+·Debian 10+ / Windows 10(1809+, WSL)
- RAM: 최소 4GB(대형 코드베이스는 8GB 권장)
- Node.js 22 이상 (npm 설치 시). 구버전이면 EBADENGINE 경고가 뜨지만 설치·실행은 됨
- 인터넷 연결(Anthropic 클라우드 API) + 계정: Pro($20)·Max($100~200)·Team·Enterprise·Console(API) 중 하나

**설치 (권장: 네이티브 인스톨러)**
v2.1.15(2026-01-21)부터 공식 표준 설치는 네이티브 인스톨러로 전환됐다(npm은 여전히 지원되나 deprecated).

```bash
# npm 방식 (여전히 동작)
npm install -g @anthropic-ai/claude-code@latest
# ⚠️ sudo 사용 금지 (권한/보안 문제)

# 실행
claude
```

첫 실행 시 브라우저가 열리며 Anthropic 계정 로그인·인가를 진행한다.

### 3.2 OpenCode

**설치**

```bash
# npm
npm install -g opencode-ai

# 또는 Go
# (Go 툴체인으로 빌드/설치)

# 실행 (프로젝트 디렉터리에서)
opencode
```

**인증·프로바이더 설정**

```bash
# API 키 등록 (~/.local/share/opencode/auth.json 에 저장)
opencode auth login

# 사용 가능한 모델 목록 확인 (provider/model 형식)
opencode models
```

프로젝트 루트에 `opencode.json`을 두어 프로바이더·모델·권한을 설정한다. 우선순위는 **프로젝트 설정 > 전역 설정 > 원격 설정**.

```jsonc
// opencode.json (예시)
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "anthropic": {
      "models": { "claude-sonnet-4-6": {} }
    }
  }
}
```

---

## 4. 작성 / 사용 가이드

### 4.1 컨텍스트 파일: CLAUDE.md vs AGENTS.md

핵심 차이 — Claude Code는 `CLAUDE.md`를, 그 외 대부분의 도구(OpenAI Codex, Cursor, Copilot, Gemini CLI, Windsurf 등)는 개방형 표준 `AGENTS.md`를 읽는다. **Claude Code는 AGENTS.md를 직접 읽지 않는다**(2026년 5월 Anthropic 문서 확인).

**멀티툴 권장 전략**

`AGENTS.md`를 단일 진실 원천으로 두고, `CLAUDE.md`는 이를 임포트하는 얇은 레이어로 둔다.

```markdown
<!-- CLAUDE.md -->
@AGENTS.md
```

또는 심볼릭 링크:

```bash
ln -s AGENTS.md CLAUDE.md
```

이렇게 하면 하나만 관리하면서 두 표준을 모두 만족한다.

### 4.2 컨텍스트 파일 작성 베스트 프랙티스

- **분량은 짧게.** 공식 권장은 200줄 이하(길어도 300줄). Claude Code 시스템 프롬프트가 이미 지시 예산의 약 50개를 쓰며, 프런티어 모델이 안정적으로 따르는 지시는 약 150~200개.
- **추론 가능한 내용은 빼라.** 코드·패키지 매니페스트에서 알 수 있는 정보는 넣지 말고, 에이전트가 **알 수 없는 비자명한 정보**만 담는다.
- **자동 생성 파일은 반드시 다듬어라.** 연구에 따르면 LLM이 생성한 컨텍스트 파일은 오히려 성공률을 약 3% 낮췄고, 사람이 쓴 파일은 약 4% 높였다. 컨텍스트 파일은 추론 비용을 20%+ 늘린다. `/init`이나 생성기는 출발점으로만 쓰고 공격적으로 편집·삭제하라.

**권장 섹션**

```markdown
# Project Overview        # 프로젝트 한 줄 설명
# Build & Test Commands   # 빌드·테스트 명령
# Code Style              # 코드 스타일 규칙
# Testing Instructions    # 테스트 방법
# Security Considerations  # 보안 주의사항
# Commit / PR Guidelines  # 커밋·PR 규칙
```

### 4.3 커스텀 에이전트·커맨드 (Claude Code)

전문 에이전트를 만드는 5가지 방법:

1. **Task 서브에이전트** — 메인 에이전트가 위임하는 격리 루프
2. **`.claude/agents` YAML** — 파일로 정의하는 서브에이전트
3. **커스텀 슬래시 커맨드** — 반복 워크플로우를 명령으로
4. **CLAUDE.md 페르소나** — 역할 지시
5. **관점 프롬프트(perspective prompts)**

### 4.4 OpenCode 사용 팁

- `Tab` 키로 Build ↔ Plan 에이전트 전환. 계획 수립은 Plan, 실행은 Build.
- `opencode models`로 정확한 `provider/model` 문자열을 확인 후 설정에 사용.
- 로컬 모델(Ollama 등)로 민감 코드를 완전 로컬에서 처리 가능 — 프라이버시·비용 우위.

---

## 5. 어느 것을 선택할까

**Claude Code를 선택** — 최신 SOTA 모델(Opus)을 구독가로 쓰고 싶고, 훅·스킬·플러그인·서브에이전트 등 완성도 높은 통합 워크플로우가 필요할 때. 팀 표준화와 안정성 우선.

**OpenCode를 선택** — 여러 모델을 자유롭게 전환하고 싶고, 저비용 또는 로컬 모델을 원하며, 오픈소스로 내부를 통제·커스터마이즈하고 싶을 때.

많은 팀은 **둘 다** 두고, `AGENTS.md`를 단일 컨텍스트 원천으로 공유해 도구에 상관없이 일관된 규칙을 유지한다.

---

## 출처

- [OpenCode Docs (opencode.ai)](https://opencode.ai/docs/) · [Agents](https://opencode.ai/docs/agents/) · [CLI](https://opencode.ai/docs/cli/) · [Providers](https://opencode.ai/docs/providers/) · [Config](https://opencode.ai/docs/config/)
- [Claude Code Docs — Extend](https://code.claude.com/docs/en/features-overview) · [Setup](https://code.claude.com/docs/en/setup)
- [@anthropic-ai/claude-code (npm)](https://www.npmjs.com/package/@anthropic-ai/claude-code)
- [Claude Code Agent Teams, Subagents & MCP: 2026 Playbook — Developers Digest](https://www.developersdigest.tech/blog/claude-code-agent-teams-subagents-2026)
- [OpenCode Developer Guide 2026 — Developers Digest](https://www.developersdigest.tech/blog/opencode-developer-guide-2026)
- [How to Install Claude Code (2026) — NxCode](https://www.nxcode.io/resources/news/install-claude-code-setup-guide-2026)
- [OpenCode vs Claude Code: After 100 hours — Composio](https://composio.dev/content/claude-code-vs-open-code)
- [OpenCode vs Claude Code (July 2026) — Morph](https://www.morphllm.com/comparisons/opencode-vs-claude-code)
- [AGENTS.md vs CLAUDE.md: Definitive Guide — Blink](https://blink.new/blog/agents-md-vs-claude-md) · [AGENTS.md Guide — Morph](https://www.morphllm.com/agents-md-guide)
- [State of CLI Coding Agents, Mid-2026 — arcbjorn](https://blog.arcbjorn.com/state-of-cli-coding-agents-2026)
