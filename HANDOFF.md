# 작업 인계: 클라이밍 정모 리포트

다른 컴퓨터에서 이어서 작업하기 위한 정리입니다. (작성 2026-11-26)

## 0. 옮기는 방법

1. `climbing-report.zip`을 새 컴퓨터에서 원하는 폴더(예: `C:\Code\climbing-report`)에 풉니다.
   zip 안에 git 기록(`.git`)까지 들어 있어서 커밋도 그대로 이어집니다.
2. 그 폴더를 열고 Claude Code 세션을 시작한 뒤, 아래 **5. 새 세션에 붙여 넣을 말**을 입력합니다.
3. 확인: `python main.py --render-only` 를 돌리고 `docs/index.html`을 열어 보면 지금과 같은 페이지가 나옵니다.
   (Python 3.10 이상, 외부 패키지 없음)

> 파일 없이 설명만으로는 똑같이 만들 수 없습니다. 암장 좌표 40여 개(`gyms.json`), 찾아 둔 모임 목록
> (`data/groups.json` 115개, `config.json`의 `extra_groups` 27개)는 브라우저로 하나하나 확인한 값이라
> 다시 만들면 결과가 달라집니다. 반드시 zip을 같이 옮기세요.

## 1. 무엇을 만들었나

- 참고한 사이트: https://unordinaryeye.github.io/climbing-report/ (소모임 클라이밍 정모를 매일 정리한 정적 페이지.
  저장소에는 결과 HTML만 있고 생성 코드는 공개돼 있지 않음 → 직접 새로 만듦)
- 내 버전: 소모임 공개 페이지에서 클라이밍 모임의 정모를 모아 한 장짜리 페이지로 정리
  - **경기권 / 서울권 탭** (첫 탭 경기권, `index.html#서울` 로 바로 열기)
  - 지역별 통계: 오늘·내일 정모, 7일 합계, 암장 수, 새로 올라온 정모
  - 날짜 탭, **낮클 / 퇴근클**(17:00 기준) 필터
  - **암장 지도** (Leaflet + OpenStreetMap, API 키 필요 없음)
    - 지도를 한 번 누르거나 Ctrl/⌘ + 휠일 때만 휠 확대 (페이지 스크롤과 충돌 방지)
    - 확대 13 이상에서 암장 이름 표시, ⤢ 전체 화면(Esc로 닫기), ◎ 전체 보기
    - 마커를 누르면 그 암장의 정모 목록, 목록의 📍 버튼을 누르면 지도에서 그 암장으로 이동
  - 날짜별 보관 페이지 `docs/reports/날짜.html`, 목록 `docs/archive.html`
- 마지막 수집(2026-11-25): 요청 119회, 모임 115곳, 7일 안 정모 183건(서울+경기)
  - 경기 43건 중 40건, 서울 140건 중 133건이 지도에 표시됨.
    나머지는 '장소 미정', '참석 카톡방' 같은 암장이 아닌 글자

## 2. 파일 구조

| 파일 | 역할 |
|---|---|
| `main.py` | 수집 → 리포트 생성. `--max N`(요청 수 제한), `--render-only`(마지막 수집 결과로 페이지만 다시) |
| `climbing_report/somoim.py` | 소모임 페이지 읽기·파싱 |
| `climbing_report/gyms.py` | 장소 글자 → 암장 하나로 묶고 좌표 붙이기 |
| `climbing_report/render.py` | HTML/CSS/JS 생성 (탭, 지도, 목록) |
| `config.json` | 지역, 기간, 시작 페이지, 꼭 넣을 모임(`extra_groups`), 요청 간격·상한 |
| `gyms.json` | 암장 사전 (브랜드·지점·별칭·좌표) |
| `data/groups.json` | 지금까지 찾은 클라이밍 모임 목록 (실행할 때마다 쌓임) |
| `data/last_run.json` | 마지막 수집 결과 (NEW 표시 기준) |
| `.github/workflows/daily.yml` | GitHub Actions: 6시간마다(05:07 · 11:07 · 17:07 · 23:07 KST) 실행 후 `docs`, `data` 커밋 |
| `README.md` | 사용법, 지역·암장 추가 방법, GitHub 설정 |

## 3. 지금까지 알아낸 것 (중요한 결정과 이유)

**소모임 수집**
- robots.txt가 `/` 를 허용. **공개 HTML 페이지만 읽고 내부 API(`/api/...`)는 쓰지 않음.**
  (내부 API 호출은 Claude 자동 모드에서 거부됐음 → 다시 시도하지 말 것)
- 데이터는 Next.js flight 데이터(`self.__next_f.push([1,"..."])`) 안에 있음.
  모임 페이지의 `groupInfoData` = {group, members, events, similarGroups}.
  정모: `eid`, `e_d`(YYYYMMDD), `e_t`(HHMM), `en`(제목), `el`(장소), `emm`(정원).
  참석 인원은 화면 카드 글자 `|N|/|M|`에서 읽음. 클라이밍 관심사 코드는 `it2 == "18007"`.
- **멤버 이름 등 개인 정보는 저장하지 않음.**
- 소모임 검색 페이지(`/groups/search/지역/지역/클라이밍`)는 주소의 지역을 무시하고 접속 IP 위치(성남 근처)로 결과를 줌.
  그래서 동탄·수원 쪽 모임이 빠졌었음 → 소모임 화면의 `/운동-스포츠/클라이밍` 페이지에서 도시별로 한 번 모아서
  경기 모임 27개를 `extra_groups`에 고정(pinned)해 둠.
- 모임 페이지의 '비슷한 모임'을 따라가며 목록을 넓히고, 60일 동안 정모가 없으면 뺌(고정 모임은 제외).
- 요청은 1초 간격, 실행당 최대 300회.
- (2026-11-27) 6시간마다 실행으로 바꾸면서 요청을 줄임: 그날 첫 실행만 전체(약 90회),
  나머지는 오늘·내일 정모가 있는 모임 20곳만(`light_max_requests`). 정모 없는 모임은 3일, 검색 페이지는 7일에 한 번.
  읽지 않은 모임의 정모는 `data/last_run.json`에서 이어 씀. 하루 약 150~160회(전부 읽으면 약 480회).

**암장 묶기**
- `gyms.json`: 별칭(예: 논더클) > 브랜드+지점 > 지점이 하나뿐인 브랜드 이름 순으로 맞춤.
  장소 칸이 비어 있으면 정모 제목에서 '브랜드+지점'이나 별칭을 찾음.
- 경기 암장 좌표는 카카오맵 웹 검색으로 확인(2026-11-25).
- `KAKAO_REST_API_KEY` 환경변수가 있으면 사전에 없는 장소를 카카오 로컬 검색으로 찾아 `data/geocode_cache.json`에 저장(선택).

**당근 모임 → 하지 않기로 함**
- 당근 robots.txt가 Claude 계열 에이전트(`Claude-User`, `ClaudeBot`, `anthropic-ai` 등)를 사이트 전체에서 차단.
  Claude가 모임 페이지를 열어 볼 수 없어서 수집기를 만들지 않음.

## 4. 남은 일: GitHub에 올려 매일 자동 갱신

- git 저장소는 이미 만들어져 있음(`main` 브랜치, 첫 커밋 + 이 인계 문서 커밋).
- 할 일
  1. github.com에서 새 저장소를 **직접** 만들기 (예: `climbing-report`, 무료 Pages를 쓰려면 Public).
     README·.gitignore 추가 옵션은 끄고 빈 저장소로.
  2. `git remote add origin https://github.com/<아이디>/climbing-report.git` → `git push -u origin main`
  3. Settings → Pages → Deploy from a branch → `main` / `/docs`
  4. Settings → Actions → General → Workflow permissions → **Read and write permissions**
  5. Actions 탭 → `daily report` → **Run workflow**로 한 번 실행해서 확인
     (GitHub 서버는 해외에 있어서 소모임이 다르게 응답할 수 있음. 첫 실행 결과를 꼭 볼 것)
  6. (선택) Settings → Secrets → `KAKAO_REST_API_KEY`
- 주의: 저장소 활동이 60일 없으면 GitHub가 예약 실행을 멈출 수 있음. 예약 실행은 몇 분~수십 분 늦을 수 있음.
  소모임 이용약관의 자동 수집 조항은 직접 확인할 것.

## 5. 새 세션에 붙여 넣을 말

```
이 폴더는 '클라이밍 정모 리포트' 프로젝트야. 다른 컴퓨터에서 하던 작업을 옮겨 왔어.
먼저 HANDOFF.md와 README.md를 읽고 지금 상태를 파악해 줘.
그다음 python main.py --render-only 로 페이지가 똑같이 만들어지는지 확인하고,
HANDOFF.md의 '4. 남은 일' 순서대로 GitHub에 올려서 매일 자동 갱신되게 도와줘.
지켜야 할 것: 소모임은 공개 HTML 페이지만 읽고 내부 API는 쓰지 않기, 멤버 이름은 저장하지 않기,
당근 모임은 수집하지 않기, 푸시 전에는 나한테 확인받기.
```
