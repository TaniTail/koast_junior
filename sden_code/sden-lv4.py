import asyncio
import os
import random
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

# 다운로드 폴더 설정
DOWNLOAD_FOLDER = os.path.abspath("downloads")
MTIS_URL = "https://mtis.komsa.or.kr/stg/traffic/liveSea"

# 브라우저 프로필 다양화를 위한 설정
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0"
]

VIEWPORTS = [
    {'width': 1920, 'height': 1080},
    {'width': 1366, 'height': 768},
    {'width': 1440, 'height': 900}
]

async def is_ip_blocked(page):
    """개선된 서버 차단 감지 로직"""
    try:
        # 페이지 컨텐츠 확인
        content = await page.content()
        block_indicators = ["접근이 차단", "과도한 요청", "Error", "차단", "access denied", "too many requests"]
        if any(indicator in content.lower() for indicator in block_indicators):
            print("⚠️ 차단 관련 메시지 감지됨")
            return True

        # 응답 상태 확인
        response = await page.request.get(MTIS_URL)
        if response.status in [403, 429, 503]:
            print(f"⚠️ 서버 응답 코드: {response.status}")
            wait_time = int(response.headers.get("Retry-After", "300"))
            print(f"⏳ {wait_time}초 후 재시도")
            await asyncio.sleep(wait_time)
            return True

        return False
    except Exception as e:
        print(f"차단 확인 중 오류 발생: {e}")
        return True

async def add_natural_delay():
    """더 자연스러운 요청 간격 생성"""
    base_delay = random.normalvariate(5, 2)  # 평균 5초, 표준편차 2초
    if random.random() < 0.1:  # 10% 확률로 더 긴 대기
        base_delay *= random.uniform(3, 6)
    delay = max(2, min(base_delay, 30))  # 2초에서 30초 사이로 제한
    await asyncio.sleep(delay)

async def download_traffic_data(page, date_time):
    """수정된 다운로드 함수: 레벨 4 선택 추가 및 재시도 제거"""
    try:
        print(f" {date_time} 데이터 다운로드 중...")

        # 페이지 이동 확인
        await page.goto(MTIS_URL)
        print(f" {MTIS_URL} 로 이동 완료.")

        # 3. 날짜 입력 필드
        date_input_selector = "#trafficVolumeDateTime"
        await page.wait_for_selector(date_input_selector, timeout=10000)

        # 기존 텍스트 지우기 후 입력
        await page.click(date_input_selector)
        await page.press(date_input_selector, "Control+A")
        await page.press(date_input_selector, "Backspace")
        await page.fill(date_input_selector, date_time)
        
        # 레벨 4 선택하기 (새로 추가된 부분)
        level4_selector = "#gridLevel4"
        await page.wait_for_selector(level4_selector, timeout=10000)
        await page.click(level4_selector)
        print(f" 레벨 4 선택 완료.")

        # 4. 결과조회 버튼 클릭
        search_button_selector = "button.btn_search.pannel02_02_submit"
        await page.wait_for_selector(search_button_selector, timeout=10000)
        await page.click(search_button_selector)
        await asyncio.sleep(3)

        # 5. 다운로드 버튼 찾기
        download_button_selector = "button:has-text('엑셀다운')"

        try:
            # 타임아웃 시간을 줄여서 빠르게 파일 없음 감지
            await page.wait_for_selector(download_button_selector, timeout=5000)
        except:
            print(f"❌ 데이터 없음: {date_time} (파일 없음)")
            return False

        while not await page.locator(download_button_selector).is_visible():
            print(f"⏳ 다운로드 버튼 활성화 대기 중... ({date_time})")
            await asyncio.sleep(1)

        async with page.expect_download(timeout=60000) as download_info:
            await page.click(download_button_selector)
        download = await download_info.value

        filename = f"교통량_lv4_{date_time.replace(' ', '_').replace(':', '')}.xlsx"
        file_path = os.path.join(DOWNLOAD_FOLDER, filename)
        await download.save_as(file_path)

        print(f"✅ 다운로드 완료: {file_path}")
        return True

    except Exception as e:
        print(f"⚠️ 다운로드 중 오류 발생 ({date_time}): {e}")
        return False

async def run_all():
    async with async_playwright() as p:
        # 브라우저 프로필 다양화 적용
        browser = await p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--disable-automation"
            ]
        )
        
        # 랜덤한 브라우저 프로필 설정
        context = await browser.new_context(
            accept_downloads=True,
            viewport=random.choice(VIEWPORTS),
            user_agent=random.choice(USER_AGENTS)
        )
        
        page = await context.new_page()

        # 사이트 접속 테스트
        await page.goto(MTIS_URL)
        print(f" 사이트 정상적으로 로드됨: {MTIS_URL}")

        # 시작 날짜 (2023년 2월 1일 00:00)
        start_date = datetime(2024, 1, 1, 0, 0)
        # 종료 날짜 (2025년 2월 20일 23:00)
        end_date = datetime(2025, 2, 20, 23, 0)
        # 1시간 단위 증가
        time_delta = timedelta(hours=1)

        current_date = start_date
        request_count = 0
        failed_dates = []  # 실패한 날짜 기록

        while current_date <= end_date:
            date_time_str = current_date.strftime("%Y-%m-%d %H시")
            print(f"📅 다운로드 시도: {date_time_str}")

            # IP 차단 확인
            if await is_ip_blocked(page):
                print("🔄 새로운 브라우저 세션 시작...")
                await context.close()
                context = await browser.new_context(
                    accept_downloads=True,
                    viewport=random.choice(VIEWPORTS),
                    user_agent=random.choice(USER_AGENTS)
                )
                page = await context.new_page()
                continue

            # 다운로드 시도 (재시도 로직 제거)
            success = await download_traffic_data(page, date_time_str)
            if not success:
                failed_dates.append(date_time_str)

            # 자연스러운 대기 시간 추가
            await add_natural_delay()

            current_date += time_delta
            request_count += 1

            # 일정 주기로 세션 갱신
            if request_count % 50 == 0:
                print("🔄 주기적 세션 갱신...")
                await context.clear_cookies()
                await asyncio.sleep(random.uniform(30, 60))

        # 실패한 날짜 기록
        if failed_dates:
            with open('failed_downloads.txt', 'w', encoding='utf-8') as f:
                for date in failed_dates:
                    f.write(f"{date}\n")

        await browser.close()

if __name__ == "__main__":
    # 다운로드 폴더 생성
    os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
    asyncio.run(run_all())