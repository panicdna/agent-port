# 커스텀 슬래시 커맨드(`/command`) 작성법 비교: Claude Code vs OpenCode

> 기준일: 2026-07-09 · 두 도구의 사용자 정의 슬래시 커맨드 정의 파일(.md) 작성 방식 차이

---

## 1. 핵심 차이 한눈에

| 항목 | **Claude Code** | **OpenCode** |
|---|---|---|
| 파일 위치 | `~/.claude/commands/` (개인)<br>`.claude/commands/` (프로젝트) | `~/.config/opencode/command/` (전역)<br>`.opencode/command/` (프로젝트) |
| 정의 방식 | Markdown 파일 | Markdown 파일 **또는** `opencode.json`의 `command` 블록 |
| 파일 형식 | YAML frontmatter + 본문(=프롬프트 템플릿) | YAML frontmatter + 본문(=프롬프트 템플릿) |
| 커맨드 이름 | 파일명 (`fix-issue.md` → `/fix-issue`) | 파일명 (`test.md` → `/test`) |
| 필수 필드 | 없음 (전부 선택, `description` 권장) | 없음 (본문 템플릿만 있으면 동작) |
| 인자 치환 | `$ARGUMENTS`, `$1`·`$2`… | `$ARGUMENTS`, `$1`·`$2`… |
| 셸 주입 | `` !`명령` `` + 펜스드 ` ```! ` 블록 | `` !`명령` `` |
| 파일 참조 | `@경로` (또는 Markdown 링크) | `@경로` |
| 도구 제어 | `allowed-tools` (사전 승인 목록) | `agent`가 가진 `permission`을 상속 |
| 실행 주체 | 메인 에이전트(세션) | `agent` 필드로 지정 / `subtask`로 서브에이전트 강제 |
| 모델 지정 | `model:` (`sonnet`/`opus`… 별칭) | `model:` (`provider/model-id` 전체 경로) |
| 네임스페이스 | 하위 폴더 → `/frontend:component` | 하위 폴더 지원 |
| 내장 커맨드 덮어쓰기 | ✖ (내장이 우선, 스킬만 번들 덮어씀) | ✅ (`/init`·`/undo`·`/redo`·`/share`·`/help` 덮어쓰기 가능) |

**요약:** 본문 템플릿 문법(`$ARGUMENTS`, `` !`셸` ``, `@파일`)은 사실상 동일하다. 진짜 차이는 ① **frontmatter 계약** — Claude Code는 `allowed-tools`로 도구를 사전 승인하고, OpenCode는 `agent`/`subtask`로 **누가·어떤 컨텍스트에서 실행할지**를 지정한다는 점, 그리고 ② Claude Code는 슬래시 커맨드를 **Skills 체계로 통합**하는 방향으로 진화 중이라는 점이다.

---

## 2. Claude Code 슬래시 커맨드 작성

`.claude/commands/fix-issue.md`:

```markdown
---
description: GitHub 이슈 번호를 받아 우리 코딩 규칙에 맞게 수정
argument-hint: [issue-number]
allowed-tools: Read, Grep, Bash(gh *), Bash(git *)
model: sonnet
disable-model-invocation: true
---

GitHub 이슈 #$1 을(를) 다음 순서로 수정하라:

1. 이슈 내용 확인: !`gh issue view $1 --json title,body`
2. 문제를 파악하고 최소 변경으로 수정
3. 수정을 커버하는 테스트 추가
4. 커밋 메시지: "Fix #$1: <설명>"
```

호출: `/fix-issue 123`

**작성 규칙**
- **파일명이 곧 커맨드 이름.** `fix-issue.md` → `/fix-issue`. frontmatter에 `name`은 필수가 아니다(있어도 호출명은 파일명 기준).
- `description`: `/` 메뉴에 표시되고, Claude가 **자동 호출 여부를 판단**하는 근거. 자동 호출을 막고 사용자 수동 호출만 허용하려면 `disable-model-invocation: true`.
- `argument-hint`: 자동완성 시 표시되는 인자 힌트(예: `[issue-number]`).
- `allowed-tools`: 커맨드 실행 중 **승인 없이 쓸 수 있는 도구를 사전 승인**하는 목록. `Bash(git *)`처럼 명령 패턴까지 지정 가능. — **도구를 제한하는 게 아니라 허가하는** 방향임에 유의(`permission` 규칙이 여전히 상위).
- `model`: `haiku`/`sonnet`/`opus` 별칭으로 이 커맨드만 모델 오버라이드.
- 본문: `$ARGUMENTS`(전체), `$1`·`$2`(위치 인자)로 치환. `` !`명령` ``은 프롬프트가 모델에 전달되기 **전에** 실행돼 출력이 그 자리에 삽입된다(`allowed-tools`에 해당 `Bash(...)` 필요).
- `@경로`로 파일 내용을 인라인 첨부.

**네임스페이스** — 하위 폴더로 정리한다. `.claude/commands/frontend/component.md` → `/frontend:component`.

> 📌 **진화 중:** 최신 Claude Code는 `.claude/commands/`(클래식 커맨드)와 `.claude/skills/**/SKILL.md`(스킬)를 하나의 체계로 수렴시키고 있다. 클래식 커맨드 파일은 하위 호환으로 계속 동작하지만, 신규 작성은 스킬(`when_to_use`, `context: fork`, `allowed-tools` 등 확장 필드)로 유도된다. 본 문서는 **클래식 `/command` 계약**을 기준으로 한다.

---

## 3. OpenCode 슬래시 커맨드 작성

### 방식 A — Markdown 파일 (`.opencode/command/fix-issue.md`)

```markdown
---
description: GitHub 이슈 번호를 받아 수정
agent: build
model: anthropic/claude-sonnet-4-20250514
subtask: true
---

GitHub 이슈 #$1 을(를) 수정하라.
현재 이슈: !`gh issue view $1`
관련 파일: @src/index.ts
```

> 파일명 `fix-issue.md` 가 곧 커맨드 `/fix-issue`.

### 방식 B — `opencode.json`

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "command": {
    "test": {
      "template": "테스트를 커버리지와 함께 실행하라: !`npm test`",
      "description": "커버리지 포함 테스트 실행",
      "agent": "build",
      "model": "anthropic/claude-sonnet-4-20250514"
    }
  }
}
```

**작성 규칙**
- **`template`(본문)이 실질적 필수.** JSON 방식은 `template` 키, Markdown 방식은 `---` 아래 본문이 프롬프트 템플릿.
- `description`: TUI 커맨드 목록에 표시.
- `agent`: 이 커맨드를 실행할 에이전트 지정(미지정 시 현재 에이전트). 도구 권한은 **그 에이전트의 `permission`을 그대로 상속** — 커맨드 자체에는 도구 허용 필드가 없다.
- `subtask: true`: **서브에이전트로 강제 실행**. 기본(primary) 컨텍스트를 오염시키지 않고, `mode: primary`인 에이전트라도 서브에이전트처럼 격리 실행하게 만든다.
- `model`: 반드시 `provider/model-id` 전체 경로(`opencode models`로 확인).
- 본문: `$ARGUMENTS`(전체), `$1`·`$2`(위치 인자), `` !`명령` ``(셸 출력 삽입), `@파일`(파일 첨부).
- **내장 커맨드 덮어쓰기 가능** — `/init`, `/undo`, `/redo`, `/share`, `/help`를 같은 이름의 커스텀 커맨드로 재정의할 수 있다.

---

## 4. 필드·문법 매핑 대조표

| 목적 | Claude Code | OpenCode |
|---|---|---|
| 이름 | 파일명 | 파일명 (또는 JSON 키) |
| 메뉴 설명 | `description:` | `description:` |
| 프롬프트 템플릿 | `---` 아래 본문 | `---` 아래 본문 (또는 `template`) |
| 전체 인자 | `$ARGUMENTS` | `$ARGUMENTS` |
| 위치 인자 | `$1`, `$2` … | `$1`, `$2` … |
| 인자 힌트 | `argument-hint:` | ✖ |
| 셸 주입(인라인) | `` !`cmd` `` | `` !`cmd` `` |
| 셸 주입(멀티라인) | ` ```! ` 펜스드 블록 | ✖ (인라인만) |
| 파일 참조 | `@경로` / Markdown 링크 | `@경로` |
| 실행 에이전트 지정 | ✖ (세션 메인) | `agent:` |
| 서브에이전트 강제 | ✖ | `subtask: true` |
| 도구 사전 승인 | `allowed-tools:` | ✖ (에이전트 `permission` 상속) |
| 자동 호출 차단 | `disable-model-invocation: true` | ✖ |
| 모델 | `model: sonnet` | `model: anthropic/claude-sonnet-4-...` |
| 네임스페이스 | 하위 폴더 → `/ns:name` | 하위 폴더 |
| 내장 덮어쓰기 | ✖ | ✅ |
| 프로그램 호출 | `SlashCommand`/`Skill` 도구 | 에이전트가 커맨드 호출 |

---

## 5. 구조적 차이의 핵심

### 5.1 "누가 실행하는가"에 대한 철학 차이
- **Claude Code**: 커맨드는 **메인 세션 에이전트**가 그대로 실행하는 프롬프트다. 격리·위임이 필요하면 커맨드가 아니라 **서브에이전트(`.claude/agents/`)**나 스킬의 `context: fork`로 분리한다. 즉 *커맨드 = 프롬프트 매크로*, *에이전트 = 실행 컨텍스트* 로 역할이 분리돼 있다.
- **OpenCode**: 커맨드가 `agent`·`subtask` 필드로 **실행 컨텍스트를 직접 지정**한다. 커맨드 하나가 "어떤 에이전트로, 격리해서 돌릴지"까지 품는다. 커맨드와 에이전트가 더 밀접하게 엮인 설계.

### 5.2 도구 권한 모델
- **Claude Code**: 커맨드 자신이 `allowed-tools`로 **사전 승인 목록**을 갖는다(명령 패턴 단위까지). 서브에이전트 작성 비교 문서의 `tools:`와 성격이 유사 — "이 커맨드 동안은 이 도구들을 물어보지 말고 허용".
- **OpenCode**: 커맨드에는 도구 필드가 없고, 지정한 `agent`의 세분화된 `permission`(read/edit/bash…의 allow/ask/deny, glob 단위)을 **상속**한다. 도구 제어의 무게중심이 커맨드가 아니라 **에이전트**에 있다.

### 5.3 MCP·내장 커맨드
- **Claude Code**: MCP 서버의 프롬프트가 `/mcp__<서버>__<프롬프트>` 형식의 슬래시 커맨드로 자동 노출된다. 내장 커맨드(`/clear`·`/init`·`/model` 등)는 하네스가 직접 처리하며 커스텀으로 덮어쓸 수 없다.
- **OpenCode**: 커스텀 커맨드가 일부 내장 커맨드를 덮어쓸 수 있어 워크플로우를 더 공격적으로 재정의할 수 있다.

---

## 6. 마이그레이션 팁 (Claude Code → OpenCode)

1. 파일을 `.claude/commands/*.md` → `.opencode/command/*.md`로 옮긴다(파일명이 곧 커맨드명이므로 그대로 유지).
2. 본문의 `$ARGUMENTS`·`$1`·`` !`cmd` ``·`@파일` 은 **그대로 재사용** 가능(문법 동일).
3. `model: sonnet` → `model: anthropic/claude-sonnet-4-...` 전체 경로로 교체.
4. `allowed-tools:` 는 OpenCode 커맨드에 대응 필드가 없다 →
   - 필요한 도구 권한을 가진 **에이전트를 만들고**(`permission` 설정), 커맨드에 `agent: <그 에이전트>`로 연결.
   - 격리 실행이 목적이었다면 `subtask: true` 추가.
5. `argument-hint`·`disable-model-invocation` 은 대응 필드가 없다 → 삭제(설명은 `description`으로 흡수).
6. ` ```! ` 멀티라인 셸 블록은 OpenCode에 없다 → 인라인 `` !`cmd` `` 여러 줄로 분해.

### 반대 방향 (OpenCode → Claude Code)
- `agent:`/`subtask:` 는 커맨드 필드로 옮길 수 없다 → 해당 로직은 **서브에이전트 정의**로 분리하고, 커맨드는 프롬프트만 남긴다.
- `template`(JSON) → Markdown 본문으로 이동.
- 내장 커맨드를 덮어쓰던 커맨드는 **이름을 바꿔야 한다**(Claude Code는 내장 덮어쓰기 불가).

---

## 출처

- [Slash commands — Claude Code Docs](https://code.claude.com/docs/en/commands.md)
- [Skills — Claude Code Docs](https://code.claude.com/docs/en/skills.md)
- [MCP prompts as commands — Claude Code Docs](https://code.claude.com/docs/en/mcp.md#use-mcp-prompts-as-commands)
- [Permissions & Skill tool — Claude Code Docs](https://code.claude.com/docs/en/permissions.md)
- [Commands — OpenCode Docs](https://opencode.ai/docs/commands/)
- [Agents — OpenCode Docs](https://opencode.ai/docs/agents/)
- [Config — OpenCode Docs](https://opencode.ai/docs/config/)
- [OpenCode Slash Commands: Complete Reference Guide 2026 — ExplainX](https://www.explainx.ai/blog/opencode-slash-commands-complete-reference-guide-2026)
- [OpenCode CLI Cheat Sheet — ComputingForGeeks](https://computingforgeeks.com/opencode-cli-cheat-sheet/)

---

> **경로 표기 주의:** OpenCode의 커맨드 폴더는 `opencode.json`의 설정 키(`command`)와 동일하게 **단수** `command/`이다(`agent/`도 마찬가지). 일부 서드파티 블로그·자동 요약은 복수 `commands/`로 표기하나, 설정 키와 일치하는 단수형이 정본이다.
