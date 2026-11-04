# PHP2Shell 취약점 분석

2026년 11월 5일 기준 · CVE-2026-109618 · CVE-2026-109619

PHP2Shell은 PHP 런타임의 요청 처리와 정리 과정에서 발생하는 두 메모리 안전성 결함이다. 두 CVE 모두 인증 없이 웹 워커 권한으로 원격 코드 실행(RCE)이 가능하며, PHP 보안팀은 각각 CVSS v4.0 **9.2(Critical)**로 평가했다. Apache `mod_php`에서는 애플리케이션 코드가 실행되기 전의 HTTP 요청 처리 경로에서 RCE가 검증됐다. PHP-FPM에서도 CVE-2026-109619의 세션 경로가 검증됐으며, 그 경로에는 특정 애플리케이션 동작이 필요하다. [CVE-2026-109618 권고문][oom] · [CVE-2026-109619 권고문][state]

## 영향 버전

| PHP 브랜치 | 수정 전 업스트림 버전 | 최초 수정 버전 |
| --- | --- | --- |
| 8.2 | 8.2.0–8.2.34 | **8.2.35** |
| 8.3 | 8.3.0–8.3.35 | **8.3.36** |
| 8.4 | 8.4.0–8.4.26 | **8.4.27** |
| 8.5 | 8.5.0–8.5.11 | **8.5.12** |

PHP는 2026년 10월 21일 두 CVE의 수정 릴리스를 발표했다. PHP 8.1 이하를 운영한다면 공급업체 보안 공지를 확인한다. PHP 보안팀은 7.4, 8.0, 8.1용 최소 소스 백포트도 공개했다. 배포판 패키지는 업스트림보다 낮은 버전 번호에서도 패치를 포함할 수 있다. 예를 들어 Ubuntu 24.04 LTS의 `php8.3-fpm` 수정 패키지는 `8.3.6-0ubuntu0.24.04.13`이다. [PHP 릴리스 공지][release] · [Ubuntu USN-8948-1][ubuntu]

## CVE-2026-109618 — 메모리 부족으로 중단된 요청의 정리

수정 전 PHP는 메모리 할당에 실패하면 `longjmp()`로 현재 실행 문맥을 벗어났다. 요청 상태 일부가 외부에서 참조 가능한 시점과 초기화가 끝나는 시점 사이에 할당 실패가 발생하면, 상태를 완성하거나 되돌리는 코드가 건너뛰어진다. 이후 요청 종료 루틴이 그 상태를 정상 데이터로 해석할 수 있다. 실패한 할당과 손상된 상태는 서로 다른 데이터에 속할 수 있다. [CVE-2026-109618 권고문][oom]

`mod_php`는 요청 시작에 실패해도 요청 종료 루틴을 호출한다. 이 때문에 PHP 코드를 실행하기 전의 multipart 파싱 중에 메모리가 고갈돼도 문제가 드러난다. 특히 multipart 헤더를 메모리에 표현하는 비용이 전송 크기보다 커질 수 있어 HTTP 본문 크기와 PHP 힙 사용량을 각각 제한해야 한다. PHP-FPM은 요청 시작 실패 시 자식 프로세스를 종료한다. PHP 보안팀은 시작 이후 애플리케이션 경로의 영향 가능성을 소스에서 확인했다. [CVE-2026-109618 권고문][oom]

## CVE-2026-109619 — 다음 요청에서 해제된 상태 재사용

1. 요청 A의 PHP 연산이 요청 힙의 상태를 워커 전역 필드에 기록한다. 이 연산을 **생성 단계(producer)**라고 한다.
2. 치명적 오류로 정리가 중단되거나, 종료 중에 새 진단 정보가 기록된다. PHP가 요청 A의 힙을 해제한 뒤에도 워커 전역 필드에 참조가 남는다.
3. 같은 워커가 요청 B를 받는다. 일반 요청 초기화가 참조를 지우기 전에 후속 연산이 이 상태를 읽거나 처리하는 **소비 단계(consumer)**에서 해제 후 사용(use-after-free)이 발생할 수 있다. [CVE-2026-109619 권고문][state]

PHP 8.5의 치명적 오류 백트레이스와 세션 업로드 진행률이 확인된 사례다. 세션 경로는 multipart 처리 중 일반 세션 초기화보다 먼저 동작할 수 있다. PHP-FPM에서 검증된 경로는 요청 시작에 성공한 뒤 애플리케이션 실행 중 상태가 기록되고 치명적 오류가 난 경우다. 같은 워커에 도달한 다음 요청의 세션 업로드 진행률 처리에서 남은 상태를 사용한다. [CVE-2026-109619 권고문][state]

| 실행 환경 | CVE-2026-109618 | CVE-2026-109619 |
| --- | --- | --- |
| Apache `mod_php` | 기본 입력·메모리 제한과 다중 prefork 워커 환경에서 HTTP RCE 검증 | 백트레이스 및 세션 경로 RCE 검증 |
| PHP-FPM | 요청 시작 이후의 취약 가능성을 소스 분석으로 확인 | 애플리케이션 동작이 필요한 세션 경로에서 RCE 검증 |

위 표는 PHP 보안팀의 검증 범위를 정리한 것이다. 웹 요청을 처리하는 다른 SAPI도 업데이트 대상에 포함한다. [OOM 권고문][oom] · [전역 상태 권고문][state] · [PHP 보안 공지][release]

## 패치에서 달라진 동작

- **메모리 제한 처리** — 소프트 한도를 넘으면 VM이 안전한 지점에 도달할 때 오류를 처리한다. 더 높은 하드 한도를 넘기려는 할당에서는 프로세스를 즉시 종료하므로 PHP 종료 핸들러도 실행되지 않는다. 하드 한도 종료 메시지는 표준 오류 스트림으로 출력된다. 워커의 종료 코드 `137`을 조사할 때는 이 메시지와 OS의 OOM 종료 기록을 함께 확인한다. [PHP 메모리 설정 매뉴얼][memory]
- **요청 전역 상태** — 요청 시작 초기에 접근할 수 있는 전역 필드들의 초기화와 정리 범위를 보강해, 다음 요청이 이전 요청 소유의 값을 참조하는 경로를 차단한다. PHP 8.4의 수정 커밋에는 두 CVE의 변경이 함께 들어 있다. [PHP 8.4 패치 커밋][patch]

## 예제 실행

두 예제는 Python 3.8 이상과 표준 라이브러리만 사용한다. 실행 검증 범위는 예제의 출력과 종료 코드다. 실제 PHP 워커에서의 RCE와 메모리 손상은 공식 권고문의 검증 결과를 정리했다. 패치의 메모리 한도 동작은 PHP 소스의 회귀 테스트에서 확인할 수 있다. [소프트 한도 테스트][soft-test] · [하드 한도 테스트][hard-test]

### 1. 워커 상태 수명 모형

[stale_state_demo.py](examples/stale_state_demo.py)는 두 요청을 같은 워커 객체로 표현한다. 요청 종료 시 딕셔너리를 비워 힙 해제를 모사하고, 다음 요청 시작 전에 남은 핸들을 조회한다. 핸들이 정리되지 않은 경우와 정리된 경우를 나란히 관찰할 수 있다.

```console
$ python3 examples/stale_state_demo.py
reset_on_shutdown=False: STALE_HANDLE
reset_on_shutdown=True: NO_STALE_HANDLE
```

### 2. 업스트림 패치 기준 확인

[check_version.py](examples/check_version.py)는 지정한 PHP 버전을 표의 최초 수정 버전과 비교한다. `--source upstream`은 PHP 프로젝트의 정식 릴리스를 그대로 사용한 경우에 지정한다. 배포판이나 제품 공급업체의 빌드는 공급업체 권고문에서 패키지 개정판을 확인한다. 실제 웹 워커의 버전과 패키지 출처를 입력값으로 사용한다.

```console
$ python3 examples/check_version.py 8.4.26 --source upstream
BELOW_UPSTREAM_FIX — PHP 8.4.26; first fixed release is 8.4.27.
$ python3 examples/check_version.py 8.4.27 --source upstream
MEETS_UPSTREAM_FIX — PHP 8.4.27; first fixed release is 8.4.27.
$ python3 examples/check_version.py 8.3.6-0ubuntu0.24.04.13 --source vendor
REVIEW_REQUIRED — confirm the package build against the vendor advisory.
```

| 종료 코드 | 의미 |
| --- | --- |
| `0` | 입력 버전이 두 CVE의 업스트림 수정 기준을 충족 |
| `1` | 입력 버전이 업스트림 수정 기준보다 낮음 |
| `2` | 공급업체 빌드 또는 표 밖의 브랜치로 수동 확인 필요, 혹은 명령줄 입력 오류 |

## 운영 환경 점검

1. 외부에서 접근할 수 있는 `mod_php`와 PHP-FPM부터 확인한다. 각 가상 호스트와 FPM 풀이 연결된 패키지 또는 컨테이너 이미지까지 매핑한다. CLI의 `php -v`는 그 CLI 바이너리의 버전만 표시한다. [PHP 보안 공지][release]
2. 수정 릴리스나 공급업체 백포트 패키지를 배포하고 Apache 및 PHP-FPM 워커를 재시작한다. 배포 후에는 웹 요청을 처리하는 프로세스가 새 빌드를 사용하고 있는지 확인한다. [PHP 보안 공지][release] · [PHP2Shell 연구팀 권고][research]
3. 즉시 패치할 수 없다면 서버 또는 FPM 풀 설정에서 `session.upload_progress.enabled=0`을 적용한다. PHP 8.5에서 `fatal_error_backtraces=0`은 검증된 백트레이스 경로를 차단한다. 둘 다 워커를 재시작해 적용하고, 전체 취약점의 해결은 PHP 업데이트로 추적한다. [CVE-2026-109619 권고문][state]
4. 프록시 접근 로그의 multipart 요청과 PHP·웹서버 로그의 요청 시작 오류, 반복 OOM, 워커 종료를 시간대와 서비스 기준으로 대조한다. 이 신호는 조사 단서이며 정상 업로드나 자원 고갈에서도 발생할 수 있다. [CVE-2026-109619 권고문][state] · [PHP2Shell 연구팀 권고][research]

### 후속 권고 — CVE-2026-115560

PHP 팀은 10월 23일 별도 세션 권고를 냈다. 세션 업로드 진행률을 사용하면서 시작 설정의 `session.serialize_handler`가 `php_binary` 또는 `php_serialize`이고, 애플리케이션이 `session_start()` 전에 런타임에서 이를 `php`로 바꾸는 경우가 대상이다. 권고는 다음 정기 수정 릴리스까지 `session.upload_progress.enabled=0`을 적용하는 것이다. 위 버전 확인 예제의 범위는 CVE-2026-109618과 CVE-2026-109619다. [PHP 후속 권고][release]

[oom]: https://github.com/php/php-src/security/advisories/GHSA-w8hw-w9fx-j79w
[state]: https://github.com/php/php-src/security/advisories/GHSA-6wmf-4rv5-p3rp
[release]: https://www.php.net/archive/2026.php
[ubuntu]: https://ubuntu.com/security/notices/USN-8948-1
[patch]: https://github.com/php/php-src/commit/506e87fa7dcd
[memory]: https://www.php.net/manual/en/ini.core.php#ini.memory-hard-limit-percent
[research]: https://www.php2shell.com/
[soft-test]: https://github.com/php/php-src/blob/php-8.4.27/Zend/tests/oom_soft_limit_exceeded.phpt
[hard-test]: https://github.com/php/php-src/blob/php-8.4.27/Zend/tests/oom_hard_limit_exceeded.phpt
