# Redis 설치 가이드 (Windows)

## 개요

이 프로젝트는 Redis를 선택사항으로 사용합니다. Redis는 채팅 세션 컨텍스트 공유와 분산 세션 스토리지에 사용됩니다.

**참고**: Redis가 없어도 애플리케이션은 정상 작동하지만, 채팅 세션 컨텍스트 공유 기능이 비활성화됩니다.

## Windows에서 Redis 설치 방법

### 방법 1: Memurai 사용 (권장 - Windows 네이티브)

Memurai는 Windows용 Redis 호환 서버입니다.

1. **Memurai 다운로드**
   - https://www.memurai.com/get-memurai 접속
   - "Download Memurai Developer Edition" 클릭 (무료)
   - 설치 파일 다운로드

2. **설치**
   - 다운로드한 `.msi` 파일 실행
   - 설치 마법사 따라 진행
   - 기본 설정으로 설치 완료

3. **서비스 확인**
   ```powershell
   # PowerShell에서 실행
   Get-Service Memurai
   ```

4. **연결 테스트**
   ```powershell
   # Redis CLI가 설치되어 있다면
   redis-cli ping
   # 응답: PONG
   ```

5. **환경 변수 설정**
   `.env` 파일에 추가:
   ```env
   REDIS_URL=redis://localhost:6379/0
   ```

### 방법 2: WSL2 + Linux Redis 설치

1. **WSL2 설치**
   ```powershell
   # 관리자 권한 PowerShell에서 실행
   wsl --install
   ```
   - 재부팅 필요

2. **WSL2에서 Redis 설치**
   ```bash
   # WSL2 Ubuntu 터미널에서 실행
   sudo apt update
   sudo apt install redis-server -y
   ```

3. **Redis 서비스 시작**
   ```bash
   sudo service redis-server start
   ```

4. **자동 시작 설정**
   ```bash
   sudo systemctl enable redis-server
   ```

5. **연결 테스트**
   ```bash
   redis-cli ping
   # 응답: PONG
   ```

6. **환경 변수 설정**
   `.env` 파일에 추가:
   ```env
   REDIS_URL=redis://localhost:6379/0
   ```

### 방법 3: Docker 사용 (Docker Desktop 필요)

1. **Docker Desktop 설치**
   - https://www.docker.com/products/docker-desktop/ 접속
   - Docker Desktop for Windows 다운로드 및 설치

2. **Redis 컨테이너 실행**
   ```powershell
   docker run -d --name redis -p 6379:6379 redis:latest
   ```

3. **컨테이너 상태 확인**
   ```powershell
   docker ps
   ```

4. **환경 변수 설정**
   `.env` 파일에 추가:
   ```env
   REDIS_URL=redis://localhost:6379/0
   ```

### 방법 4: Chocolatey 사용 (패키지 매니저)

1. **Chocolatey 설치** (아직 설치하지 않은 경우)
   - https://chocolatey.org/install 접속
   - 관리자 권한 PowerShell에서 설치 스크립트 실행

2. **Redis 설치**
   ```powershell
   # 관리자 권한 PowerShell에서 실행
   choco install redis-64 -y
   ```

3. **Redis 서비스 시작**
   ```powershell
   redis-server --service-install
   redis-server --service-start
   ```

4. **환경 변수 설정**
   `.env` 파일에 추가:
   ```env
   REDIS_URL=redis://localhost:6379/0
   ```

## 설치 확인

### 1. Redis 서버 실행 확인

**Windows 서비스 확인:**
```powershell
Get-Service | Where-Object {$_.Name -like "*redis*" -or $_.Name -like "*memurai*"}
```

**포트 확인:**
```powershell
netstat -an | findstr 6379
```

### 2. Redis CLI로 연결 테스트

Redis CLI가 설치되어 있다면:
```powershell
redis-cli ping
# 응답: PONG
```

### 3. Python으로 연결 테스트

```python
import redis
r = redis.Redis(host='localhost', port=6379, db=0)
print(r.ping())  # True 출력 시 성공
```

### 4. 애플리케이션 로그 확인

서버 실행 시 다음 로그가 출력되면 성공:
```
INFO: Redis client initialized with redis://localhost:6379/0
```

다음 로그가 출력되면 Redis가 비활성화된 상태:
```
WARNING: REDIS_URL not configured. Chat session context sharing is disabled.
```

## 문제 해결

### Redis 연결 실패 시

1. **서비스가 실행 중인지 확인**
   ```powershell
   Get-Service | Where-Object {$_.Name -like "*redis*"}
   ```

2. **방화벽 확인**
   - Windows 방화벽에서 포트 6379가 허용되어 있는지 확인

3. **포트 사용 중 확인**
   ```powershell
   netstat -ano | findstr 6379
   ```

4. **환경 변수 확인**
   - `.env` 파일에 `REDIS_URL`이 올바르게 설정되어 있는지 확인
   - 서버 재시작 필요

### Redis 없이 개발하기

Redis가 설치되어 있지 않아도 애플리케이션은 정상 작동합니다. 다만 다음 기능이 제한됩니다:

- ❌ 채팅 세션 컨텍스트 공유 (다중 서버 환경)
- ✅ 기본 세션 관리 (메모리 기반)
- ✅ 단일 서버 환경에서의 모든 기능

## 프로덕션 환경

프로덕션 환경에서는 다음을 권장합니다:

1. **Redis 클러스터 사용** (고가용성)
2. **Redis 비밀번호 설정**
   ```env
   REDIS_URL=redis://:password@localhost:6379/0
   ```
3. **SSL/TLS 연결** (가능한 경우)
   ```env
   REDIS_URL=rediss://localhost:6380/0
   ```

## 참고 자료

- Memurai: https://www.memurai.com/
- Redis 공식 문서: https://redis.io/docs/
- WSL2 설치: https://learn.microsoft.com/ko-kr/windows/wsl/install

